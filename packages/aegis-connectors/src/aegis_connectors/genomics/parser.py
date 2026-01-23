"""
VCF Parser

Parses Variant Call Format files.
"""

from dataclasses import dataclass, field
from typing import Any
import re
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class Variant:
    """Parsed genetic variant."""
    chromosome: str
    position: int
    id: str
    reference: str
    alternate: str
    quality: float | None
    filter_status: str
    info: dict = field(default_factory=dict)
    genotype: str | None = None
    
    @property
    def is_snp(self) -> bool:
        return len(self.reference) == 1 and len(self.alternate) == 1
    
    @property
    def variant_type(self) -> str:
        if self.is_snp:
            return "SNP"
        elif len(self.reference) > len(self.alternate):
            return "DELETION"
        elif len(self.reference) < len(self.alternate):
            return "INSERTION"
        else:
            return "COMPLEX"


@dataclass
class ParsedVCF:
    """Parsed VCF file."""
    sample_id: str
    variants: list[Variant]
    metadata: dict
    reference_genome: str


class VCFParser:
    """
    Parses VCF files.
    
    Supports VCF 4.x format.
    """
    
    def parse(self, data: str) -> tuple[ParsedVCF | None, list[str]]:
        """Parse VCF data."""
        errors = []
        metadata = {}
        variants = []
        sample_id = "unknown"
        reference = "GRCh38"
        header_columns = []
        
        try:
            lines = data.strip().split("\n")
            
            for line in lines:
                line = line.strip()
                
                if not line:
                    continue
                
                # Metadata lines
                if line.startswith("##"):
                    key, value = self._parse_metadata(line)
                    if key == "reference":
                        reference = value
                    metadata[key] = value
                    continue
                
                # Header line
                if line.startswith("#CHROM"):
                    header_columns = line[1:].split("\t")
                    if len(header_columns) > 9:
                        sample_id = header_columns[9]
                    continue
                
                # Variant line
                variant = self._parse_variant(line, header_columns)
                if variant:
                    variants.append(variant)
            
            logger.info(
                "Parsed VCF",
                sample=sample_id,
                variants=len(variants),
            )
            
            return ParsedVCF(
                sample_id=sample_id,
                variants=variants,
                metadata=metadata,
                reference_genome=reference,
            ), errors
            
        except Exception as e:
            errors.append(f"Parse error: {str(e)}")
            return None, errors
    
    def _parse_metadata(self, line: str) -> tuple[str, str]:
        """Parse metadata line."""
        line = line[2:]  # Remove ##
        if "=" in line:
            key, value = line.split("=", 1)
            return key, value
        return line, ""
    
    def _parse_variant(self, line: str, header: list[str]) -> Variant | None:
        """Parse variant line."""
        try:
            fields = line.split("\t")
            
            if len(fields) < 8:
                return None
            
            # Parse INFO field
            info = {}
            for item in fields[7].split(";"):
                if "=" in item:
                    k, v = item.split("=", 1)
                    info[k] = v
                else:
                    info[item] = True
            
            # Parse genotype if present
            genotype = None
            if len(fields) > 9 and len(header) > 9:
                format_fields = fields[8].split(":")
                sample_fields = fields[9].split(":")
                if "GT" in format_fields:
                    gt_idx = format_fields.index("GT")
                    if gt_idx < len(sample_fields):
                        genotype = sample_fields[gt_idx]
            
            quality = None
            if fields[5] != ".":
                try:
                    quality = float(fields[5])
                except ValueError:
                    pass
            
            return Variant(
                chromosome=fields[0],
                position=int(fields[1]),
                id=fields[2] if fields[2] != "." else f"{fields[0]}:{fields[1]}",
                reference=fields[3],
                alternate=fields[4],
                quality=quality,
                filter_status=fields[6],
                info=info,
                genotype=genotype,
            )
            
        except Exception as e:
            logger.debug(f"Failed to parse variant: {e}")
            return None
    
    def validate(self, data: str) -> list[str]:
        """Validate VCF data."""
        errors = []
        
        if not data.strip():
            errors.append("Empty VCF data")
            return errors
        
        lines = data.strip().split("\n")
        has_header = False
        has_chrom = False
        
        for line in lines:
            if line.startswith("##fileformat=VCF"):
                has_header = True
            if line.startswith("#CHROM"):
                has_chrom = True
                break
        
        if not has_header:
            errors.append("Missing VCF fileformat header")
        
        if not has_chrom:
            errors.append("Missing #CHROM header line")
        
        return errors
