import os
import json
import docx
import numpy as np
from pypdf import PdfReader
from typing import List, Dict, Any

# Force CPU-only inference by default (Fly machines are CPU by default)
os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

# Lazy-load sentence-transformers and faiss to avoid loading them on every import
sentence_transformers = None
faiss = None


def _vector_store_enabled() -> bool:
    return os.getenv("VECTOR_RAG_ENABLED", "false").lower() in ("1", "true", "yes", "on")


def _import_embedding_libraries():
    global sentence_transformers, faiss
    if sentence_transformers is None:
        import sentence_transformers as st
        sentence_transformers = st
    if faiss is None:
        import faiss as f
        faiss = f


class ContextLoader:
    """
    Loads context from files and pre-computed vector stores.
    """

    def __init__(self, directory: str, model_name='all-MiniLM-L6-v2'):
        self.directory = directory
        self.model_name = model_name
        self.vector_store_path = os.path.join(self.directory, "ctcae_index.faiss")
        self.documents_path = os.path.join(self.directory, "ctcae_documents.json")
        self.model = None
        self.index = None
        self.documents = []
        print(f"[CTX] Initializing ContextLoader with directory: {self.directory}")
        print(f"[CTX] Expecting vector store at: {self.vector_store_path}")
        print(f"[CTX] Expecting documents at: {self.documents_path}")
        self._load_vector_store()

    def _initialize_model(self):
        if self.model is None:
            _import_embedding_libraries()
            self.model = sentence_transformers.SentenceTransformer(self.model_name)

    def _load_vector_store(self):
        """Loads the pre-computed FAISS vector store from disk."""
        if not _vector_store_enabled():
            print("[CTX] VECTOR_RAG_ENABLED=false → Skipping FAISS/documents load.")
            self.index = None
            self.documents = []
            return
        if os.path.exists(self.vector_store_path) and os.path.exists(self.documents_path):
            print("[CTX] Loading existing FAISS index and documents.")
            _import_embedding_libraries()
            self.index = faiss.read_index(self.vector_store_path)
            with open(self.documents_path, 'r') as f:
                self.documents = json.load(f)
            print(f"[CTX] Loaded documents count: {len(self.documents)}")
        else:
            print("[CTX] Warning: Pre-built vector store not found. Symptom context will be disabled.")
            if not os.path.exists(self.vector_store_path):
                print(f"[CTX] Missing: {self.vector_store_path}")
            if not os.path.exists(self.documents_path):
                print(f"[CTX] Missing: {self.documents_path}")
            print("[CTX] Please run `python backend/scripts/build_vector_store.py` to generate it.")
            self.index = None
            self.documents = []

    def _load_base_documents(self) -> str:
        """Loads all base documents and returns them as a single string."""
        print("[CTX] Loading base documents...")
        
        documents = []
        
        # Load text files
        text_files = [
            "oncolife_alerts_configuration.txt",
            "oncolifebot_instructions.txt", 
            "written_chatbot_docs.txt"
        ]
        
        for filename in text_files:
            file_path = os.path.join(self.directory, filename)
            if os.path.exists(file_path):
                try:
                    content = self._load_txt(file_path)
                    documents.append(f"=== {filename} ===\n{content}")
                    print(f"[CTX] Loaded {filename} (chars={len(content)})")
                except Exception as e:
                    print(f"[CTX] Error loading {filename}: {e}")
            else:
                print(f"[CTX] Warning: {filename} not found")
        
        # Load PDF file
        pdf_file = "ukons_triage_toolkit_v3_final.pdf"
        pdf_path = os.path.join(self.directory, pdf_file)
        if os.path.exists(pdf_path):
            try:
                content = self._load_pdf(pdf_path)
                documents.append(f"=== {pdf_file} ===\n{content}")
                print(f"[CTX] Loaded {pdf_file} (chars={len(content)})")
            except Exception as e:
                print(f"[CTX] Error loading {pdf_file}: {e}")
        else:
            print(f"[CTX] Warning: {pdf_file} not found")
        
        # Combine all documents
        combined = "\n\n".join(documents)
        print(f"[CTX] Total base documents length: {len(combined)}")
        return combined

    def _append_rag_results(self, base_prompt: str, symptoms: List[str]) -> str:
        """Appends RAG results to the base prompt using Redis caching."""
        if not symptoms:
            print("[CTX] No symptoms provided, skipping RAG")
            return base_prompt
        
        try:
            # Import here to avoid circular imports
            from .retrieval import cached_retrieve
            
            print(f"[CTX] Performing RAG for symptoms: {symptoms}")
            
            # Get CTCAE results (cached)
            ctcae_results = cached_retrieve(symptoms, ttl=1800, k_ctcae=10, k_questions=0)
            ctcae_chunks = [h.get("text", "") for h in ctcae_results.get("ctcae", []) if h.get("text")]
            
            # Get questions results (cached)
            questions_results = cached_retrieve(symptoms, ttl=1800, k_ctcae=0, k_questions=12)
            questions_chunks = [h.get("text", "") for h in questions_results.get("questions", []) if h.get("text")]
            
            # Build RAG section
            rag_sections = []
            
            if ctcae_chunks:
                ctcae_text = "\n---\n".join(ctcae_chunks[:6])
                rag_sections.append(f"=== Relevant CTCAE Criteria for {', '.join(symptoms)} ===\n{ctcae_text}")
            
            if questions_chunks:
                questions_text = "\n---\n".join(questions_chunks[:8])
                rag_sections.append(f"=== Assessment Questions for {', '.join(symptoms)} ===\n{questions_text}")
            
            if rag_sections:
                rag_content = "\n\n".join(rag_sections)
                full_prompt = f"{base_prompt}\n\n=== RAG Results ===\n{rag_content}"
                print(f"[CTX] RAG results appended, total length: {len(full_prompt)}")
                return full_prompt
            else:
                print("[CTX] No RAG results found")
                return base_prompt
                
        except Exception as e:
            print(f"[CTX] Error during RAG: {e}")
            return base_prompt

    def load_context(self, symptoms: List[str] = None) -> str:
        """
        Loads all context including base documents and RAG results.
        This is the main method that returns the complete system prompt.
        """
        print(f"[CTX] Building complete system prompt for symptoms: {symptoms}")
        
        # Step 1: Load base documents
        base_prompt = self._load_base_documents()
        
        # Step 2: Append RAG results (with Redis caching)
        complete_prompt = self._append_rag_results(base_prompt, symptoms)
        
        print(f"[CTX] Complete system prompt built, total length: {len(complete_prompt)}")
        return complete_prompt

    # Keep the existing loader methods (_load_docx, _load_pdf, _load_txt, _load_json)
    def _load_docx(self, file_path: str) -> str:
        """Loads text from a .docx file."""
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])

    def _load_pdf(self, file_path: str) -> str:
        """Loads text from a .pdf file."""
        reader = PdfReader(file_path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    def _load_txt(self, file_path: str) -> str:
        """Loads text from a .txt file."""
        with open(file_path, 'r') as f:
            return f.read()

    def _load_json(self, file_path: str) -> Dict[str, Any]:
        """Loads data from a .json file."""
        with open(file_path, 'r') as f:
            return json.load(f)