"""
Genomics Domain Models

Models for genomic/molecular data:
- MolecularSequence (DNA, RNA sequences)
- GeneticVariant (mutations, SNPs)
- GenomicReport (test results)

Critical for Oncolife oncology use case.

FHIR: MolecularSequence, Observation (genetic)
"""

from datetime import datetime
from typing import Literal

from pydantic import Field

from aegis_ontology.models.base import BaseVertex


class MolecularSequence(BaseVertex):
    """
    Molecular sequence data (DNA, RNA, amino acid).
    
    FHIR: MolecularSequence
    """
    
    _label = "MolecularSequence"
    _fhir_resource_type = "MolecularSequence"
    _omop_table = None
    
    # Type
    type: Literal["dna", "rna", "aa"] = Field(..., description="Sequence type")
    
    # Coordinate system
    coordinate_system: int = Field(default=0, description="0-based or 1-based")
    
    # Reference
    reference_seq_id: str | None = Field(default=None, description="Reference sequence ID")
    reference_seq_build: str | None = Field(default=None, description="Genome build (GRCh38)")
    chromosome: str | None = Field(default=None, description="Chromosome (1-22, X, Y, MT)")
    
    # Position
    window_start: int | None = None
    window_end: int | None = None
    
    # Observed sequence
    observed_seq: str | None = Field(default=None, description="Observed sequence string")
    
    # Quality
    quality_score: float | None = None
    read_coverage: int | None = None
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    specimen_id: str | None = None
    performer_id: str | None = None  # Lab that sequenced
    
    # Timing
    performed_datetime: datetime | None = None


class GeneticVariant(BaseVertex):
    """
    Genetic variant (mutation, SNP, CNV).
    
    Critical for oncology - tumor profiling, actionable mutations.
    
    FHIR: Observation (genetic)
    """
    
    _label = "GeneticVariant"
    _fhir_resource_type = "Observation"
    _omop_table = None
    
    # Gene info
    gene_symbol: str = Field(..., description="HGNC gene symbol (e.g., BRCA1, EGFR)")
    gene_id: str | None = Field(default=None, description="NCBI Gene ID")
    
    # Variant identification
    hgvs_coding: str | None = Field(default=None, description="HGVS c. notation")
    hgvs_protein: str | None = Field(default=None, description="HGVS p. notation")
    dbsnp_id: str | None = Field(default=None, description="dbSNP rsID")
    cosmic_id: str | None = Field(default=None, description="COSMIC ID (cancer)")
    
    # Variant type
    variant_type: Literal[
        "SNV", "MNV", "insertion", "deletion", "indel",
        "CNV", "fusion", "structural", "other"
    ] = Field(..., description="Variant type")
    
    # Location
    chromosome: str | None = None
    position_start: int | None = None
    position_end: int | None = None
    reference_allele: str | None = None
    alternate_allele: str | None = None
    
    # Zygosity
    zygosity: Literal["heterozygous", "homozygous", "hemizygous"] | None = None
    allele_frequency: float | None = Field(default=None, description="Variant allele frequency")
    
    # Clinical significance
    clinical_significance: Literal[
        "pathogenic", "likely_pathogenic", "uncertain",
        "likely_benign", "benign"
    ] | None = Field(default=None, description="ACMG classification")
    
    # Actionability (oncology)
    is_actionable: bool = Field(default=False, description="Has targeted therapy")
    therapies: list[str] | None = Field(default=None, description="Associated therapies")
    clinical_trials: list[str] | None = Field(default=None, description="Relevant trials")
    
    # Origin
    origin: Literal["germline", "somatic", "unknown"] = "unknown"
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    sequence_id: str | None = Field(default=None, description="Source sequence")
    report_id: str | None = Field(default=None, description="Genomic report")
    
    # Timing
    identified_date: datetime | None = None


class GenomicReport(BaseVertex):
    """
    Genomic test report (NGS panel, WES, WGS).
    
    FHIR: DiagnosticReport (genetics)
    """
    
    _label = "GenomicReport"
    _fhir_resource_type = "DiagnosticReport"
    _omop_table = None
    
    # Report info
    report_type: Literal[
        "targeted_panel", "comprehensive_panel", 
        "wes", "wgs", "liquid_biopsy", "other"
    ] = Field(..., description="Test type")
    
    panel_name: str | None = Field(default=None, description="Panel name (e.g., FoundationOne)")
    
    # Status
    status: Literal[
        "registered", "partial", "preliminary", 
        "final", "amended", "cancelled"
    ] = "final"
    
    # Specimen
    specimen_type: Literal["tissue", "blood", "saliva", "other"] | None = None
    tumor_type: str | None = Field(default=None, description="Tumor type if oncology")
    
    # Results summary
    variants_detected: int | None = Field(default=None, description="Number of variants found")
    actionable_variants: int | None = None
    
    # Metrics
    tumor_mutational_burden: float | None = Field(default=None, description="TMB (mut/Mb)")
    microsatellite_status: Literal["MSS", "MSI-H", "MSI-L"] | None = None
    
    # Timing
    collected_date: datetime | None = None
    reported_date: datetime | None = None
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    encounter_id: str | None = None
    ordering_provider_id: str | None = None
    performing_lab_id: str | None = None


class Specimen(BaseVertex):
    """
    Biological specimen.
    
    FHIR: Specimen
    """
    
    _label = "Specimen"
    _fhir_resource_type = "Specimen"
    _omop_table = None
    
    # Identifier
    accession_number: str | None = None
    
    # Type
    type: str = Field(..., description="Specimen type (blood, tissue, urine, etc.)")
    type_code: str | None = Field(default=None, description="SNOMED specimen type code")
    
    # Collection
    collected_datetime: datetime | None = None
    collection_method: str | None = None
    body_site: str | None = None
    
    # Status
    status: Literal["available", "unavailable", "unsatisfactory", "entered-in-error"] = "available"
    
    # Container
    container_type: str | None = None
    quantity_value: float | None = None
    quantity_unit: str | None = None
    
    # Relationships
    patient_id: str = Field(..., description="Patient vertex ID")
    encounter_id: str | None = None
    collector_id: str | None = None
