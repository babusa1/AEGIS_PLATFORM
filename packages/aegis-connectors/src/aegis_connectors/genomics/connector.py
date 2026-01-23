"""
Genomics Connector
"""

from typing import Any
import structlog

from aegis_connectors.base import BaseConnector, ConnectorResult
from aegis_connectors.genomics.parser import VCFParser
from aegis_connectors.genomics.transformer import GenomicsTransformer

logger = structlog.get_logger(__name__)


class GenomicsConnector(BaseConnector):
    """
    Genomics Connector.
    
    Parses VCF files and transforms to graph vertices.
    
    Usage:
        connector = GenomicsConnector(tenant_id="lab-a")
        result = await connector.parse(vcf_data)
    """
    
    def __init__(
        self,
        tenant_id: str,
        source_system: str = "genomics",
        patient_id: str | None = None,
    ):
        super().__init__(tenant_id, source_system)
        self.parser = VCFParser()
        self.transformer = GenomicsTransformer(tenant_id, source_system)
        self.patient_id = patient_id
    
    @property
    def connector_type(self) -> str:
        return "genomics"
    
    async def parse(self, data: Any) -> ConnectorResult:
        """Parse VCF data and transform to graph."""
        errors = []
        
        if not isinstance(data, str):
            return ConnectorResult(success=False, errors=["VCF data must be string"])
        
        parsed, parse_errors = self.parser.parse(data)
        errors.extend(parse_errors)
        
        if not parsed:
            return ConnectorResult(success=False, errors=errors)
        
        try:
            vertices, edges = self.transformer.transform(parsed)
        except Exception as e:
            errors.append(f"Transform error: {str(e)}")
            return ConnectorResult(success=False, errors=errors)
        
        # Link to patient if set
        if self.patient_id:
            report_id = f"GenomicReport/{parsed.sample_id}"
            edges.append({
                "label": "HAS_GENOMIC_REPORT",
                "from_label": "Patient",
                "from_id": f"Patient/{self.patient_id}",
                "to_label": "GenomicReport",
                "to_id": report_id,
                "tenant_id": self.tenant_id,
            })
        
        logger.info(
            "Genomics parse complete",
            sample=parsed.sample_id,
            variants=len(parsed.variants),
            vertices=len(vertices),
        )
        
        return ConnectorResult(
            success=len(errors) == 0,
            vertices=vertices,
            edges=edges,
            errors=errors,
            metadata={
                "sample_id": parsed.sample_id,
                "variant_count": len(parsed.variants),
                "reference_genome": parsed.reference_genome,
            },
        )
    
    async def validate(self, data: Any) -> list[str]:
        if not isinstance(data, str):
            return ["VCF data must be string"]
        return self.parser.validate(data)


# Sample VCF for testing
SAMPLE_VCF = """##fileformat=VCFv4.2
##reference=GRCh38
##INFO=<ID=GENE,Number=1,Type=String,Description="Gene name">
##INFO=<ID=CLNSIG,Number=1,Type=String,Description="Clinical significance">
##FORMAT=<ID=GT,Number=1,Type=String,Description="Genotype">
#CHROM	POS	ID	REF	ALT	QUAL	FILTER	INFO	FORMAT	SAMPLE001
chr17	43044295	rs80357906	G	A	99	PASS	GENE=BRCA1;CLNSIG=Pathogenic	GT	0/1
chr13	32315474	rs80359550	C	T	99	PASS	GENE=BRCA2;CLNSIG=Pathogenic	GT	0/1
chr7	117559590	rs113993960	ATCT	A	50	PASS	GENE=CFTR;CLNSIG=Pathogenic	GT	0/1
chr10	87933147	rs1799853	C	T	99	PASS	GENE=CYP2C9;CLNSIG=drug_response	GT	1/1
"""
