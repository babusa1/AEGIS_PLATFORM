"""
Genomics to Graph Transformer
"""

from datetime import datetime
import structlog

from aegis_connectors.genomics.parser import ParsedVCF, Variant

logger = structlog.get_logger(__name__)


# Clinically significant genes
CLINVAR_GENES = {
    "BRCA1", "BRCA2",  # Breast/Ovarian cancer
    "TP53",  # Li-Fraumeni syndrome
    "MLH1", "MSH2", "MSH6",  # Lynch syndrome
    "APC",  # Familial adenomatous polyposis
    "LDLR", "APOB",  # Familial hypercholesterolemia
    "CYP2C19", "CYP2D6",  # Pharmacogenomics
    "CFTR",  # Cystic fibrosis
    "HBB",  # Sickle cell
    "MTHFR",  # Methylation
}


class GenomicsTransformer:
    """Transforms genomic data to graph vertices/edges."""
    
    def __init__(self, tenant_id: str, source_system: str = "genomics"):
        self.tenant_id = tenant_id
        self.source_system = source_system
    
    def transform(self, parsed: ParsedVCF) -> tuple[list[dict], list[dict]]:
        """Transform parsed VCF to vertices and edges."""
        vertices = []
        edges = []
        
        # Create GenomicReport vertex
        report_id = f"GenomicReport/{parsed.sample_id}"
        report_vertex = {
            "label": "GenomicReport",
            "id": report_id,
            "tenant_id": self.tenant_id,
            "source_system": self.source_system,
            "sample_id": parsed.sample_id,
            "reference_genome": parsed.reference_genome,
            "variant_count": len(parsed.variants),
            "created_at": datetime.utcnow().isoformat(),
        }
        vertices.append(report_vertex)
        
        # Transform variants
        for variant in parsed.variants:
            v, e = self._transform_variant(variant, report_id)
            vertices.extend(v)
            edges.extend(e)
        
        return vertices, edges
    
    def _transform_variant(
        self,
        variant: Variant,
        report_id: str,
    ) -> tuple[list[dict], list[dict]]:
        """Transform single variant to vertices/edges."""
        vertices = []
        edges = []
        
        variant_id = f"GeneticVariant/{variant.chromosome}:{variant.position}"
        
        variant_vertex = {
            "label": "GeneticVariant",
            "id": variant_id,
            "tenant_id": self.tenant_id,
            "source_system": self.source_system,
            "chromosome": variant.chromosome,
            "position": variant.position,
            "rs_id": variant.id if variant.id.startswith("rs") else None,
            "reference_allele": variant.reference,
            "alternate_allele": variant.alternate,
            "variant_type": variant.variant_type,
            "quality": variant.quality,
            "filter_status": variant.filter_status,
            "genotype": variant.genotype,
            "is_pathogenic": self._is_pathogenic(variant),
            "gene": variant.info.get("GENE"),
            "clinical_significance": variant.info.get("CLNSIG"),
            "created_at": datetime.utcnow().isoformat(),
        }
        vertices.append(variant_vertex)
        
        # Edge: Report -> Variant
        edges.append({
            "label": "HAS_VARIANT",
            "from_label": "GenomicReport",
            "from_id": report_id,
            "to_label": "GeneticVariant",
            "to_id": variant_id,
            "tenant_id": self.tenant_id,
        })
        
        # Link to gene if known
        gene = variant.info.get("GENE")
        if gene:
            gene_id = f"Gene/{gene}"
            edges.append({
                "label": "IN_GENE",
                "from_label": "GeneticVariant",
                "from_id": variant_id,
                "to_label": "Gene",
                "to_id": gene_id,
                "tenant_id": self.tenant_id,
            })
        
        return vertices, edges
    
    def _is_pathogenic(self, variant: Variant) -> bool:
        """Check if variant is likely pathogenic."""
        clnsig = variant.info.get("CLNSIG", "").lower()
        return "pathogenic" in clnsig
