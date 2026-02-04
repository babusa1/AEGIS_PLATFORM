"""
Document Chunkers

Split documents into chunks for embedding:
- Semantic chunking (by meaning)
- Sliding window (with overlap)
- Hierarchical (parent-child relationships)
- Sentence-based
"""

from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
import re

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


# =============================================================================
# Chunk Model
# =============================================================================

class Chunk(BaseModel):
    """A document chunk."""
    id: str
    content: str
    
    # Source document
    document_id: str
    document_title: Optional[str] = None
    
    # Position
    chunk_index: int
    start_char: int
    end_char: int
    
    # Hierarchy (for hierarchical chunking)
    parent_id: Optional[str] = None
    level: int = 0
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Embedding (filled later)
    embedding: Optional[List[float]] = None
    
    @property
    def char_count(self) -> int:
        return len(self.content)
    
    @property
    def word_count(self) -> int:
        return len(self.content.split())


# =============================================================================
# Base Chunker
# =============================================================================

class Chunker(ABC):
    """Abstract base class for chunkers."""
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
    
    @abstractmethod
    def chunk(self, document_id: str, content: str, metadata: dict = None) -> List[Chunk]:
        """Split content into chunks."""
        pass
    
    def _generate_chunk_id(self, document_id: str, index: int) -> str:
        """Generate chunk ID."""
        return f"{document_id}_chunk_{index}"


# =============================================================================
# Sliding Window Chunker
# =============================================================================

class SlidingWindowChunker(Chunker):
    """
    Simple sliding window chunker.
    
    Splits text into fixed-size chunks with overlap.
    Good for: General documents, when structure doesn't matter.
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        separator: str = "\n",
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.separator = separator
    
    def chunk(self, document_id: str, content: str, metadata: dict = None) -> List[Chunk]:
        """Split content using sliding window."""
        chunks = []
        
        # Split by separator first to respect natural boundaries
        if self.separator:
            segments = content.split(self.separator)
        else:
            segments = [content]
        
        current_chunk = ""
        current_start = 0
        chunk_index = 0
        char_pos = 0
        
        for segment in segments:
            segment_with_sep = segment + self.separator
            
            if len(current_chunk) + len(segment_with_sep) <= self.chunk_size:
                current_chunk += segment_with_sep
            else:
                # Save current chunk
                if current_chunk.strip():
                    chunks.append(Chunk(
                        id=self._generate_chunk_id(document_id, chunk_index),
                        content=current_chunk.strip(),
                        document_id=document_id,
                        chunk_index=chunk_index,
                        start_char=current_start,
                        end_char=char_pos,
                        metadata=metadata or {},
                    ))
                    chunk_index += 1
                
                # Start new chunk with overlap
                overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else ""
                current_chunk = overlap_text + segment_with_sep
                current_start = char_pos - len(overlap_text)
            
            char_pos += len(segment_with_sep)
        
        # Don't forget the last chunk
        if current_chunk.strip():
            chunks.append(Chunk(
                id=self._generate_chunk_id(document_id, chunk_index),
                content=current_chunk.strip(),
                document_id=document_id,
                chunk_index=chunk_index,
                start_char=current_start,
                end_char=char_pos,
                metadata=metadata or {},
            ))
        
        logger.info(f"Created {len(chunks)} chunks from document {document_id}")
        return chunks


# =============================================================================
# Semantic Chunker
# =============================================================================

class SemanticChunker(Chunker):
    """
    Semantic chunker that respects document structure.
    
    Splits at:
    - Headers/titles
    - Paragraph breaks
    - List items
    - Section boundaries
    
    Good for: Policies, guidelines, structured documents.
    """
    
    # Patterns for section detection
    HEADER_PATTERNS = [
        r'^#{1,6}\s+.+$',  # Markdown headers
        r'^[A-Z][A-Z\s]+:?\s*$',  # ALL CAPS headers
        r'^\d+\.\s+[A-Z].+$',  # Numbered sections
        r'^[A-Z][a-z]+\s+\d+[:.]',  # "Section 1:", "Chapter 1."
        r'^[IVXLCDM]+\.\s+.+$',  # Roman numeral sections
    ]
    
    def __init__(
        self,
        chunk_size: int = 1500,
        chunk_overlap: int = 100,
        min_chunk_size: int = 100,
    ):
        super().__init__(chunk_size, chunk_overlap)
        self.min_chunk_size = min_chunk_size
        self._header_pattern = re.compile('|'.join(self.HEADER_PATTERNS), re.MULTILINE)
    
    def chunk(self, document_id: str, content: str, metadata: dict = None) -> List[Chunk]:
        """Split content semantically."""
        chunks = []
        
        # First, identify sections
        sections = self._identify_sections(content)
        
        chunk_index = 0
        for section in sections:
            # If section is small enough, keep as one chunk
            if len(section["content"]) <= self.chunk_size:
                if len(section["content"]) >= self.min_chunk_size:
                    chunks.append(Chunk(
                        id=self._generate_chunk_id(document_id, chunk_index),
                        content=section["content"],
                        document_id=document_id,
                        chunk_index=chunk_index,
                        start_char=section["start"],
                        end_char=section["end"],
                        metadata={
                            **(metadata or {}),
                            "section_title": section.get("title"),
                        },
                    ))
                    chunk_index += 1
            else:
                # Split large sections by paragraphs
                paragraphs = section["content"].split("\n\n")
                current_chunk = ""
                current_start = section["start"]
                
                for para in paragraphs:
                    if len(current_chunk) + len(para) <= self.chunk_size:
                        current_chunk += para + "\n\n"
                    else:
                        if current_chunk.strip() and len(current_chunk) >= self.min_chunk_size:
                            chunks.append(Chunk(
                                id=self._generate_chunk_id(document_id, chunk_index),
                                content=current_chunk.strip(),
                                document_id=document_id,
                                chunk_index=chunk_index,
                                start_char=current_start,
                                end_char=current_start + len(current_chunk),
                                metadata={
                                    **(metadata or {}),
                                    "section_title": section.get("title"),
                                },
                            ))
                            chunk_index += 1
                        
                        current_chunk = para + "\n\n"
                        current_start = current_start + len(current_chunk)
                
                # Last chunk
                if current_chunk.strip() and len(current_chunk) >= self.min_chunk_size:
                    chunks.append(Chunk(
                        id=self._generate_chunk_id(document_id, chunk_index),
                        content=current_chunk.strip(),
                        document_id=document_id,
                        chunk_index=chunk_index,
                        start_char=current_start,
                        end_char=section["end"],
                        metadata={
                            **(metadata or {}),
                            "section_title": section.get("title"),
                        },
                    ))
                    chunk_index += 1
        
        logger.info(f"Created {len(chunks)} semantic chunks from document {document_id}")
        return chunks
    
    def _identify_sections(self, content: str) -> List[dict]:
        """Identify document sections."""
        sections = []
        
        # Find all headers
        matches = list(self._header_pattern.finditer(content))
        
        if not matches:
            # No headers found, treat whole document as one section
            return [{"content": content, "start": 0, "end": len(content), "title": None}]
        
        # Create sections between headers
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            
            section_content = content[start:end]
            section_title = match.group().strip()
            
            sections.append({
                "content": section_content,
                "start": start,
                "end": end,
                "title": section_title,
            })
        
        # Add content before first header if any
        if matches[0].start() > 0:
            sections.insert(0, {
                "content": content[:matches[0].start()],
                "start": 0,
                "end": matches[0].start(),
                "title": "Introduction",
            })
        
        return sections


# =============================================================================
# Hierarchical Chunker
# =============================================================================

class HierarchicalChunker(Chunker):
    """
    Hierarchical chunker creating parent-child relationships.
    
    Creates:
    - Level 0: Full sections (large context)
    - Level 1: Paragraphs (medium context)
    - Level 2: Sentences (fine-grained)
    
    Good for: Multi-level retrieval, when you need both overview and detail.
    """
    
    def __init__(
        self,
        level_0_size: int = 3000,  # Full sections
        level_1_size: int = 1000,  # Paragraphs
        level_2_size: int = 300,   # Sentences
    ):
        super().__init__(level_1_size)
        self.level_0_size = level_0_size
        self.level_1_size = level_1_size
        self.level_2_size = level_2_size
    
    def chunk(self, document_id: str, content: str, metadata: dict = None) -> List[Chunk]:
        """Create hierarchical chunks."""
        all_chunks = []
        
        # Level 0: Large sections
        level_0_chunker = SlidingWindowChunker(
            chunk_size=self.level_0_size,
            chunk_overlap=200,
            separator="\n\n\n",
        )
        level_0_chunks = level_0_chunker.chunk(document_id, content, metadata)
        
        for l0_chunk in level_0_chunks:
            l0_chunk.level = 0
            l0_chunk.id = f"{document_id}_L0_{l0_chunk.chunk_index}"
            all_chunks.append(l0_chunk)
            
            # Level 1: Medium chunks (paragraphs)
            level_1_chunker = SlidingWindowChunker(
                chunk_size=self.level_1_size,
                chunk_overlap=100,
                separator="\n\n",
            )
            level_1_chunks = level_1_chunker.chunk(
                f"{document_id}_L0_{l0_chunk.chunk_index}",
                l0_chunk.content,
                metadata,
            )
            
            for l1_idx, l1_chunk in enumerate(level_1_chunks):
                l1_chunk.level = 1
                l1_chunk.parent_id = l0_chunk.id
                l1_chunk.id = f"{l0_chunk.id}_L1_{l1_idx}"
                l1_chunk.document_id = document_id
                all_chunks.append(l1_chunk)
                
                # Level 2: Fine-grained (sentences)
                sentences = self._split_sentences(l1_chunk.content)
                current_l2 = ""
                l2_idx = 0
                
                for sentence in sentences:
                    if len(current_l2) + len(sentence) <= self.level_2_size:
                        current_l2 += sentence + " "
                    else:
                        if current_l2.strip():
                            l2_chunk = Chunk(
                                id=f"{l1_chunk.id}_L2_{l2_idx}",
                                content=current_l2.strip(),
                                document_id=document_id,
                                chunk_index=l2_idx,
                                start_char=0,
                                end_char=len(current_l2),
                                parent_id=l1_chunk.id,
                                level=2,
                                metadata=metadata or {},
                            )
                            all_chunks.append(l2_chunk)
                            l2_idx += 1
                        current_l2 = sentence + " "
                
                # Last L2 chunk
                if current_l2.strip():
                    l2_chunk = Chunk(
                        id=f"{l1_chunk.id}_L2_{l2_idx}",
                        content=current_l2.strip(),
                        document_id=document_id,
                        chunk_index=l2_idx,
                        start_char=0,
                        end_char=len(current_l2),
                        parent_id=l1_chunk.id,
                        level=2,
                        metadata=metadata or {},
                    )
                    all_chunks.append(l2_chunk)
        
        logger.info(
            f"Created {len(all_chunks)} hierarchical chunks "
            f"(L0: {len([c for c in all_chunks if c.level == 0])}, "
            f"L1: {len([c for c in all_chunks if c.level == 1])}, "
            f"L2: {len([c for c in all_chunks if c.level == 2])})"
        )
        
        return all_chunks
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]


# =============================================================================
# Clinical Note Chunker
# =============================================================================

class ClinicalNoteChunker(Chunker):
    """
    Specialized chunker for clinical notes.
    
    Recognizes:
    - SOAP sections (Subjective, Objective, Assessment, Plan)
    - Common clinical headers
    - Lab results
    - Medication lists
    """
    
    CLINICAL_SECTIONS = [
        r'(?i)^(chief complaint|cc):?\s*',
        r'(?i)^(history of present illness|hpi):?\s*',
        r'(?i)^(past medical history|pmh):?\s*',
        r'(?i)^(medications|meds|current medications):?\s*',
        r'(?i)^(allergies):?\s*',
        r'(?i)^(social history|sh):?\s*',
        r'(?i)^(family history|fh):?\s*',
        r'(?i)^(review of systems|ros):?\s*',
        r'(?i)^(physical exam|pe|examination):?\s*',
        r'(?i)^(vital signs|vitals):?\s*',
        r'(?i)^(laboratory|labs|lab results):?\s*',
        r'(?i)^(imaging|radiology):?\s*',
        r'(?i)^(assessment):?\s*',
        r'(?i)^(plan):?\s*',
        r'(?i)^(diagnosis|dx):?\s*',
        r'(?i)^(subjective):?\s*',
        r'(?i)^(objective):?\s*',
    ]
    
    def __init__(self, chunk_size: int = 1000):
        super().__init__(chunk_size)
        self._section_pattern = re.compile('|'.join(self.CLINICAL_SECTIONS), re.MULTILINE)
    
    def chunk(self, document_id: str, content: str, metadata: dict = None) -> List[Chunk]:
        """Chunk clinical notes by section."""
        chunks = []
        
        # Find section boundaries
        matches = list(self._section_pattern.finditer(content))
        
        if not matches:
            # No clinical sections found, use semantic chunker
            fallback = SemanticChunker(chunk_size=self.chunk_size)
            return fallback.chunk(document_id, content, metadata)
        
        chunk_index = 0
        
        # Content before first section
        if matches[0].start() > 0:
            pre_content = content[:matches[0].start()].strip()
            if pre_content:
                chunks.append(Chunk(
                    id=self._generate_chunk_id(document_id, chunk_index),
                    content=pre_content,
                    document_id=document_id,
                    chunk_index=chunk_index,
                    start_char=0,
                    end_char=matches[0].start(),
                    metadata={**(metadata or {}), "section": "header"},
                ))
                chunk_index += 1
        
        # Process each section
        for i, match in enumerate(matches):
            section_name = match.group().strip().rstrip(':')
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            
            section_content = content[start:end].strip()
            
            if section_content:
                chunks.append(Chunk(
                    id=self._generate_chunk_id(document_id, chunk_index),
                    content=section_content,
                    document_id=document_id,
                    chunk_index=chunk_index,
                    start_char=start,
                    end_char=end,
                    metadata={
                        **(metadata or {}),
                        "section": section_name.lower(),
                        "is_clinical_section": True,
                    },
                ))
                chunk_index += 1
        
        logger.info(f"Created {len(chunks)} clinical chunks from document {document_id}")
        return chunks
