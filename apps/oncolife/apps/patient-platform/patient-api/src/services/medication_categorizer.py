"""
Medication Categorization Service.

This module provides automatic categorization of medications into:
- Chemotherapy drugs (required per spec)
- Supportive medications (optional, improves triage)
- Immunotherapy
- Targeted therapy
- Hormone therapy

The categorization is used for:
- Symptom checker rule configuration
- Neutropenia risk assessment
- Side effect prediction

Data Sources:
- FDA approved oncology drugs
- Common chemotherapy regimens
- Standard supportive care protocols
"""

from typing import Optional, List, Dict, Tuple
from enum import Enum


class MedicationCategory(str, Enum):
    """Categories of medications for oncology patients."""
    CHEMOTHERAPY = "chemotherapy"
    SUPPORTIVE = "supportive"
    IMMUNOTHERAPY = "immunotherapy"
    TARGETED_THERAPY = "targeted_therapy"
    HORMONE_THERAPY = "hormone_therapy"
    OTHER = "other"


# =============================================================================
# CHEMOTHERAPY DRUGS
# =============================================================================

CHEMOTHERAPY_DRUGS = {
    # Alkylating Agents
    "cyclophosphamide": {"brand": ["Cytoxan", "Neosar"], "class": "alkylating"},
    "ifosfamide": {"brand": ["Ifex"], "class": "alkylating"},
    "melphalan": {"brand": ["Alkeran"], "class": "alkylating"},
    "busulfan": {"brand": ["Myleran", "Busulfex"], "class": "alkylating"},
    "temozolomide": {"brand": ["Temodar"], "class": "alkylating"},
    "carboplatin": {"brand": ["Paraplatin"], "class": "alkylating"},
    "cisplatin": {"brand": ["Platinol"], "class": "alkylating"},
    "oxaliplatin": {"brand": ["Eloxatin"], "class": "alkylating"},
    
    # Anthracyclines
    "doxorubicin": {"brand": ["Adriamycin", "Doxil"], "class": "anthracycline"},
    "daunorubicin": {"brand": ["Cerubidine", "DaunoXome"], "class": "anthracycline"},
    "epirubicin": {"brand": ["Ellence"], "class": "anthracycline"},
    "idarubicin": {"brand": ["Idamycin"], "class": "anthracycline"},
    "mitoxantrone": {"brand": ["Novantrone"], "class": "anthracycline"},
    
    # Taxanes
    "paclitaxel": {"brand": ["Taxol", "Abraxane"], "class": "taxane"},
    "docetaxel": {"brand": ["Taxotere"], "class": "taxane"},
    "cabazitaxel": {"brand": ["Jevtana"], "class": "taxane"},
    
    # Antimetabolites
    "methotrexate": {"brand": ["Trexall", "Otrexup"], "class": "antimetabolite"},
    "5-fluorouracil": {"brand": ["Adrucil", "5-FU"], "class": "antimetabolite"},
    "fluorouracil": {"brand": ["Adrucil", "5-FU"], "class": "antimetabolite"},
    "capecitabine": {"brand": ["Xeloda"], "class": "antimetabolite"},
    "gemcitabine": {"brand": ["Gemzar"], "class": "antimetabolite"},
    "cytarabine": {"brand": ["Cytosar-U", "Ara-C"], "class": "antimetabolite"},
    "pemetrexed": {"brand": ["Alimta"], "class": "antimetabolite"},
    "mercaptopurine": {"brand": ["Purinethol"], "class": "antimetabolite"},
    "fludarabine": {"brand": ["Fludara"], "class": "antimetabolite"},
    "cladribine": {"brand": ["Leustatin"], "class": "antimetabolite"},
    
    # Vinca Alkaloids
    "vincristine": {"brand": ["Oncovin", "Vincasar"], "class": "vinca"},
    "vinblastine": {"brand": ["Velban"], "class": "vinca"},
    "vinorelbine": {"brand": ["Navelbine"], "class": "vinca"},
    
    # Topoisomerase Inhibitors
    "etoposide": {"brand": ["VePesid", "Toposar", "VP-16"], "class": "topoisomerase"},
    "irinotecan": {"brand": ["Camptosar"], "class": "topoisomerase"},
    "topotecan": {"brand": ["Hycamtin"], "class": "topoisomerase"},
    
    # Other Chemotherapy
    "bleomycin": {"brand": ["Blenoxane"], "class": "antibiotic"},
    "mitomycin": {"brand": ["Mutamycin"], "class": "antibiotic"},
    "dactinomycin": {"brand": ["Cosmegen"], "class": "antibiotic"},
    "dacarbazine": {"brand": ["DTIC-Dome"], "class": "other"},
    "procarbazine": {"brand": ["Matulane"], "class": "other"},
    "hydroxyurea": {"brand": ["Hydrea"], "class": "other"},
    "asparaginase": {"brand": ["Elspar", "Erwinaze"], "class": "enzyme"},
}


# =============================================================================
# SUPPORTIVE MEDICATIONS
# =============================================================================

SUPPORTIVE_MEDICATIONS = {
    # Growth Factors (G-CSF)
    "filgrastim": {"brand": ["Neupogen"], "purpose": "neutropenia_prevention"},
    "pegfilgrastim": {"brand": ["Neulasta"], "purpose": "neutropenia_prevention"},
    "tbo-filgrastim": {"brand": ["Granix"], "purpose": "neutropenia_prevention"},
    "filgrastim-sndz": {"brand": ["Zarxio"], "purpose": "neutropenia_prevention"},
    "pegfilgrastim-jmdb": {"brand": ["Fulphila"], "purpose": "neutropenia_prevention"},
    "pegfilgrastim-cbqv": {"brand": ["Udenyca"], "purpose": "neutropenia_prevention"},
    "pegfilgrastim-bmez": {"brand": ["Ziextenzo"], "purpose": "neutropenia_prevention"},
    
    # Anti-emetics
    "ondansetron": {"brand": ["Zofran"], "purpose": "antiemetic"},
    "granisetron": {"brand": ["Kytril", "Sancuso"], "purpose": "antiemetic"},
    "palonosetron": {"brand": ["Aloxi"], "purpose": "antiemetic"},
    "dolasetron": {"brand": ["Anzemet"], "purpose": "antiemetic"},
    "aprepitant": {"brand": ["Emend"], "purpose": "antiemetic"},
    "fosaprepitant": {"brand": ["Emend IV"], "purpose": "antiemetic"},
    "netupitant": {"brand": ["Akynzeo"], "purpose": "antiemetic"},
    "dexamethasone": {"brand": ["Decadron"], "purpose": "antiemetic"},
    "prochlorperazine": {"brand": ["Compazine"], "purpose": "antiemetic"},
    "metoclopramide": {"brand": ["Reglan"], "purpose": "antiemetic"},
    "lorazepam": {"brand": ["Ativan"], "purpose": "antiemetic"},
    "dronabinol": {"brand": ["Marinol"], "purpose": "antiemetic"},
    
    # Pain Management
    "morphine": {"brand": ["MS Contin", "Kadian"], "purpose": "pain"},
    "hydromorphone": {"brand": ["Dilaudid"], "purpose": "pain"},
    "oxycodone": {"brand": ["OxyContin", "Roxicodone"], "purpose": "pain"},
    "fentanyl": {"brand": ["Duragesic", "Actiq"], "purpose": "pain"},
    "methadone": {"brand": ["Dolophine"], "purpose": "pain"},
    "tramadol": {"brand": ["Ultram"], "purpose": "pain"},
    
    # Mouth Care
    "palifermin": {"brand": ["Kepivance"], "purpose": "mucositis"},
    "cryotherapy": {"brand": [], "purpose": "mucositis"},
    
    # Anemia
    "epoetin": {"brand": ["Epogen", "Procrit"], "purpose": "anemia"},
    "darbepoetin": {"brand": ["Aranesp"], "purpose": "anemia"},
    
    # Bone Protection
    "zoledronic": {"brand": ["Zometa"], "purpose": "bone"},
    "denosumab": {"brand": ["Xgeva", "Prolia"], "purpose": "bone"},
    "pamidronate": {"brand": ["Aredia"], "purpose": "bone"},
    
    # Diarrhea
    "loperamide": {"brand": ["Imodium"], "purpose": "diarrhea"},
    "diphenoxylate": {"brand": ["Lomotil"], "purpose": "diarrhea"},
    "octreotide": {"brand": ["Sandostatin"], "purpose": "diarrhea"},
    
    # Constipation
    "polyethylene glycol": {"brand": ["Miralax"], "purpose": "constipation"},
    "sennosides": {"brand": ["Senokot"], "purpose": "constipation"},
    "bisacodyl": {"brand": ["Dulcolax"], "purpose": "constipation"},
    "docusate": {"brand": ["Colace"], "purpose": "constipation"},
    "lactulose": {"brand": ["Enulose"], "purpose": "constipation"},
    
    # Neuropathy
    "gabapentin": {"brand": ["Neurontin"], "purpose": "neuropathy"},
    "pregabalin": {"brand": ["Lyrica"], "purpose": "neuropathy"},
    "duloxetine": {"brand": ["Cymbalta"], "purpose": "neuropathy"},
    
    # Anxiety/Sleep
    "alprazolam": {"brand": ["Xanax"], "purpose": "anxiety"},
    "zolpidem": {"brand": ["Ambien"], "purpose": "sleep"},
    "temazepam": {"brand": ["Restoril"], "purpose": "sleep"},
}


# =============================================================================
# IMMUNOTHERAPY
# =============================================================================

IMMUNOTHERAPY_DRUGS = {
    # Checkpoint Inhibitors - PD-1/PD-L1
    "pembrolizumab": {"brand": ["Keytruda"], "target": "PD-1"},
    "nivolumab": {"brand": ["Opdivo"], "target": "PD-1"},
    "atezolizumab": {"brand": ["Tecentriq"], "target": "PD-L1"},
    "durvalumab": {"brand": ["Imfinzi"], "target": "PD-L1"},
    "avelumab": {"brand": ["Bavencio"], "target": "PD-L1"},
    "cemiplimab": {"brand": ["Libtayo"], "target": "PD-1"},
    
    # CTLA-4 Inhibitors
    "ipilimumab": {"brand": ["Yervoy"], "target": "CTLA-4"},
    
    # CAR-T
    "tisagenlecleucel": {"brand": ["Kymriah"], "target": "CAR-T"},
    "axicabtagene ciloleucel": {"brand": ["Yescarta"], "target": "CAR-T"},
    "brexucabtagene autoleucel": {"brand": ["Tecartus"], "target": "CAR-T"},
    "lisocabtagene maraleucel": {"brand": ["Breyanzi"], "target": "CAR-T"},
    "idecabtagene vicleucel": {"brand": ["Abecma"], "target": "CAR-T"},
    
    # Other Immunotherapy
    "interferon alfa": {"brand": ["Intron A", "Roferon-A"], "target": "cytokine"},
    "interleukin-2": {"brand": ["Proleukin"], "target": "cytokine"},
    "bcg": {"brand": ["TheraCys", "TICE BCG"], "target": "vaccine"},
}


# =============================================================================
# TARGETED THERAPY
# =============================================================================

TARGETED_THERAPY_DRUGS = {
    # HER2 Targeted
    "trastuzumab": {"brand": ["Herceptin"], "target": "HER2"},
    "pertuzumab": {"brand": ["Perjeta"], "target": "HER2"},
    "ado-trastuzumab emtansine": {"brand": ["Kadcyla", "T-DM1"], "target": "HER2"},
    "fam-trastuzumab deruxtecan": {"brand": ["Enhertu"], "target": "HER2"},
    "lapatinib": {"brand": ["Tykerb"], "target": "HER2"},
    "neratinib": {"brand": ["Nerlynx"], "target": "HER2"},
    "tucatinib": {"brand": ["Tukysa"], "target": "HER2"},
    
    # EGFR Targeted
    "cetuximab": {"brand": ["Erbitux"], "target": "EGFR"},
    "panitumumab": {"brand": ["Vectibix"], "target": "EGFR"},
    "erlotinib": {"brand": ["Tarceva"], "target": "EGFR"},
    "gefitinib": {"brand": ["Iressa"], "target": "EGFR"},
    "afatinib": {"brand": ["Gilotrif"], "target": "EGFR"},
    "osimertinib": {"brand": ["Tagrisso"], "target": "EGFR"},
    
    # VEGF/Angiogenesis
    "bevacizumab": {"brand": ["Avastin"], "target": "VEGF"},
    "ramucirumab": {"brand": ["Cyramza"], "target": "VEGFR2"},
    "sorafenib": {"brand": ["Nexavar"], "target": "multi-kinase"},
    "sunitinib": {"brand": ["Sutent"], "target": "multi-kinase"},
    "pazopanib": {"brand": ["Votrient"], "target": "multi-kinase"},
    "axitinib": {"brand": ["Inlyta"], "target": "VEGFR"},
    "cabozantinib": {"brand": ["Cometriq", "Cabometyx"], "target": "multi-kinase"},
    "lenvatinib": {"brand": ["Lenvima"], "target": "multi-kinase"},
    "regorafenib": {"brand": ["Stivarga"], "target": "multi-kinase"},
    
    # CDK4/6 Inhibitors
    "palbociclib": {"brand": ["Ibrance"], "target": "CDK4/6"},
    "ribociclib": {"brand": ["Kisqali"], "target": "CDK4/6"},
    "abemaciclib": {"brand": ["Verzenio"], "target": "CDK4/6"},
    
    # PARP Inhibitors
    "olaparib": {"brand": ["Lynparza"], "target": "PARP"},
    "rucaparib": {"brand": ["Rubraca"], "target": "PARP"},
    "niraparib": {"brand": ["Zejula"], "target": "PARP"},
    "talazoparib": {"brand": ["Talzenna"], "target": "PARP"},
    
    # ALK Inhibitors
    "crizotinib": {"brand": ["Xalkori"], "target": "ALK"},
    "ceritinib": {"brand": ["Zykadia"], "target": "ALK"},
    "alectinib": {"brand": ["Alecensa"], "target": "ALK"},
    "brigatinib": {"brand": ["Alunbrig"], "target": "ALK"},
    "lorlatinib": {"brand": ["Lorbrena"], "target": "ALK"},
    
    # BRAF/MEK
    "vemurafenib": {"brand": ["Zelboraf"], "target": "BRAF"},
    "dabrafenib": {"brand": ["Tafinlar"], "target": "BRAF"},
    "encorafenib": {"brand": ["Braftovi"], "target": "BRAF"},
    "trametinib": {"brand": ["Mekinist"], "target": "MEK"},
    "cobimetinib": {"brand": ["Cotellic"], "target": "MEK"},
    "binimetinib": {"brand": ["Mektovi"], "target": "MEK"},
    
    # BCR-ABL
    "imatinib": {"brand": ["Gleevec"], "target": "BCR-ABL"},
    "dasatinib": {"brand": ["Sprycel"], "target": "BCR-ABL"},
    "nilotinib": {"brand": ["Tasigna"], "target": "BCR-ABL"},
    "bosutinib": {"brand": ["Bosulif"], "target": "BCR-ABL"},
    "ponatinib": {"brand": ["Iclusig"], "target": "BCR-ABL"},
    
    # BTK Inhibitors
    "ibrutinib": {"brand": ["Imbruvica"], "target": "BTK"},
    "acalabrutinib": {"brand": ["Calquence"], "target": "BTK"},
    "zanubrutinib": {"brand": ["Brukinsa"], "target": "BTK"},
    
    # mTOR Inhibitors
    "everolimus": {"brand": ["Afinitor"], "target": "mTOR"},
    "temsirolimus": {"brand": ["Torisel"], "target": "mTOR"},
    
    # Proteasome Inhibitors
    "bortezomib": {"brand": ["Velcade"], "target": "proteasome"},
    "carfilzomib": {"brand": ["Kyprolis"], "target": "proteasome"},
    "ixazomib": {"brand": ["Ninlaro"], "target": "proteasome"},
    
    # Other Targeted
    "rituximab": {"brand": ["Rituxan"], "target": "CD20"},
    "obinutuzumab": {"brand": ["Gazyva"], "target": "CD20"},
    "brentuximab vedotin": {"brand": ["Adcetris"], "target": "CD30"},
    "venetoclax": {"brand": ["Venclexta"], "target": "BCL-2"},
}


# =============================================================================
# HORMONE THERAPY
# =============================================================================

HORMONE_THERAPY_DRUGS = {
    # Aromatase Inhibitors
    "letrozole": {"brand": ["Femara"], "type": "aromatase_inhibitor"},
    "anastrozole": {"brand": ["Arimidex"], "type": "aromatase_inhibitor"},
    "exemestane": {"brand": ["Aromasin"], "type": "aromatase_inhibitor"},
    
    # Selective Estrogen Receptor Modulators (SERMs)
    "tamoxifen": {"brand": ["Nolvadex"], "type": "SERM"},
    "toremifene": {"brand": ["Fareston"], "type": "SERM"},
    "raloxifene": {"brand": ["Evista"], "type": "SERM"},
    
    # Selective Estrogen Receptor Degraders (SERDs)
    "fulvestrant": {"brand": ["Faslodex"], "type": "SERD"},
    "elacestrant": {"brand": ["Orserdu"], "type": "SERD"},
    
    # GnRH Agonists
    "leuprolide": {"brand": ["Lupron", "Eligard"], "type": "GnRH_agonist"},
    "goserelin": {"brand": ["Zoladex"], "type": "GnRH_agonist"},
    "triptorelin": {"brand": ["Trelstar"], "type": "GnRH_agonist"},
    
    # Antiandrogens
    "bicalutamide": {"brand": ["Casodex"], "type": "antiandrogen"},
    "enzalutamide": {"brand": ["Xtandi"], "type": "antiandrogen"},
    "apalutamide": {"brand": ["Erleada"], "type": "antiandrogen"},
    "darolutamide": {"brand": ["Nubeqa"], "type": "antiandrogen"},
    "flutamide": {"brand": ["Eulexin"], "type": "antiandrogen"},
    "nilutamide": {"brand": ["Nilandron"], "type": "antiandrogen"},
    
    # CYP17 Inhibitors
    "abiraterone": {"brand": ["Zytiga"], "type": "CYP17_inhibitor"},
}


# =============================================================================
# CATEGORIZATION FUNCTIONS
# =============================================================================

def normalize_medication_name(name: str) -> str:
    """
    Normalize a medication name for lookup.
    
    - Lowercase
    - Remove common suffixes
    - Remove dosage info
    - Handle common abbreviations
    """
    if not name:
        return ""
    
    # Lowercase and strip
    normalized = name.lower().strip()
    
    # Remove dosage patterns
    import re
    normalized = re.sub(r'\d+\s*(mg|g|ml|mcg|iu|units?)\s*(/.*)?', '', normalized)
    
    # Remove common packaging info
    normalized = re.sub(r'\((.*?)\)', '', normalized)
    
    # Remove extra whitespace
    normalized = re.sub(r'\s+', ' ', normalized).strip()
    
    # Handle common brand to generic mappings
    brand_to_generic = {
        "taxol": "paclitaxel",
        "abraxane": "paclitaxel",
        "taxotere": "docetaxel",
        "adriamycin": "doxorubicin",
        "cytoxan": "cyclophosphamide",
        "neosar": "cyclophosphamide",
        "paraplatin": "carboplatin",
        "platinol": "cisplatin",
        "gemzar": "gemcitabine",
        "xeloda": "capecitabine",
        "neulasta": "pegfilgrastim",
        "neupogen": "filgrastim",
        "zofran": "ondansetron",
        "emend": "aprepitant",
        "keytruda": "pembrolizumab",
        "opdivo": "nivolumab",
        "herceptin": "trastuzumab",
        "avastin": "bevacizumab",
        "rituxan": "rituximab",
        "ibrance": "palbociclib",
        "kisqali": "ribociclib",
        "verzenio": "abemaciclib",
        "femara": "letrozole",
        "arimidex": "anastrozole",
        "nolvadex": "tamoxifen",
        "faslodex": "fulvestrant",
        "zometa": "zoledronic",
        "xgeva": "denosumab",
        "prolia": "denosumab",
    }
    
    if normalized in brand_to_generic:
        normalized = brand_to_generic[normalized]
    
    return normalized


def categorize_medication(medication_name: str) -> Tuple[MedicationCategory, Optional[Dict]]:
    """
    Categorize a medication into its appropriate category.
    
    Args:
        medication_name: Name of the medication (brand or generic)
        
    Returns:
        Tuple of (category, metadata dict or None)
    """
    normalized = normalize_medication_name(medication_name)
    
    if not normalized:
        return MedicationCategory.OTHER, None
    
    # Check each category
    if normalized in CHEMOTHERAPY_DRUGS:
        return MedicationCategory.CHEMOTHERAPY, CHEMOTHERAPY_DRUGS[normalized]
    
    if normalized in SUPPORTIVE_MEDICATIONS:
        return MedicationCategory.SUPPORTIVE, SUPPORTIVE_MEDICATIONS[normalized]
    
    if normalized in IMMUNOTHERAPY_DRUGS:
        return MedicationCategory.IMMUNOTHERAPY, IMMUNOTHERAPY_DRUGS[normalized]
    
    if normalized in TARGETED_THERAPY_DRUGS:
        return MedicationCategory.TARGETED_THERAPY, TARGETED_THERAPY_DRUGS[normalized]
    
    if normalized in HORMONE_THERAPY_DRUGS:
        return MedicationCategory.HORMONE_THERAPY, HORMONE_THERAPY_DRUGS[normalized]
    
    # Check if it's a known brand name
    for drug_dict in [
        CHEMOTHERAPY_DRUGS,
        SUPPORTIVE_MEDICATIONS,
        IMMUNOTHERAPY_DRUGS,
        TARGETED_THERAPY_DRUGS,
        HORMONE_THERAPY_DRUGS,
    ]:
        for generic, info in drug_dict.items():
            brands = info.get("brand", [])
            if any(normalized == b.lower() for b in brands):
                if drug_dict == CHEMOTHERAPY_DRUGS:
                    return MedicationCategory.CHEMOTHERAPY, info
                elif drug_dict == SUPPORTIVE_MEDICATIONS:
                    return MedicationCategory.SUPPORTIVE, info
                elif drug_dict == IMMUNOTHERAPY_DRUGS:
                    return MedicationCategory.IMMUNOTHERAPY, info
                elif drug_dict == TARGETED_THERAPY_DRUGS:
                    return MedicationCategory.TARGETED_THERAPY, info
                elif drug_dict == HORMONE_THERAPY_DRUGS:
                    return MedicationCategory.HORMONE_THERAPY, info
    
    return MedicationCategory.OTHER, None


def categorize_medications(medications: List[str]) -> List[Dict]:
    """
    Categorize a list of medications.
    
    Args:
        medications: List of medication names
        
    Returns:
        List of dicts with name, category, and metadata
    """
    results = []
    
    for med in medications:
        category, metadata = categorize_medication(med)
        results.append({
            "name": med,
            "normalized_name": normalize_medication_name(med),
            "category": category.value,
            "metadata": metadata,
        })
    
    return results


def is_chemotherapy(medication_name: str) -> bool:
    """Check if a medication is a chemotherapy drug."""
    category, _ = categorize_medication(medication_name)
    return category == MedicationCategory.CHEMOTHERAPY


def is_supportive(medication_name: str) -> bool:
    """Check if a medication is a supportive medication."""
    category, _ = categorize_medication(medication_name)
    return category == MedicationCategory.SUPPORTIVE


def is_growth_factor(medication_name: str) -> bool:
    """Check if a medication is a growth factor (G-CSF)."""
    category, metadata = categorize_medication(medication_name)
    if category == MedicationCategory.SUPPORTIVE and metadata:
        return metadata.get("purpose") == "neutropenia_prevention"
    return False


def get_neutropenia_risk_medications(medications: List[str]) -> List[str]:
    """
    Get medications from a list that increase neutropenia risk.
    
    Returns chemotherapy drugs and certain targeted therapies.
    """
    high_risk = []
    
    for med in medications:
        category, metadata = categorize_medication(med)
        
        # All chemotherapy increases neutropenia risk
        if category == MedicationCategory.CHEMOTHERAPY:
            high_risk.append(med)
            continue
        
        # Some targeted therapies also cause neutropenia
        if category == MedicationCategory.TARGETED_THERAPY:
            high_risk_targets = ["proteasome", "BTK", "BCR-ABL"]
            if metadata and metadata.get("target") in high_risk_targets:
                high_risk.append(med)
    
    return high_risk


def extract_regimen_medications(regimen_name: str) -> List[str]:
    """
    Extract individual medications from a regimen name.
    
    Examples:
        "ddAC → Paclitaxel" -> ["doxorubicin", "cyclophosphamide", "paclitaxel"]
        "FOLFOX" -> ["5-fluorouracil", "leucovorin", "oxaliplatin"]
        "R-CHOP" -> ["rituximab", "cyclophosphamide", "doxorubicin", "vincristine", "prednisone"]
    """
    # Common regimen abbreviations
    regimen_drugs = {
        "ac": ["doxorubicin", "cyclophosphamide"],
        "ddac": ["doxorubicin", "cyclophosphamide"],
        "tc": ["docetaxel", "cyclophosphamide"],
        "fec": ["5-fluorouracil", "epirubicin", "cyclophosphamide"],
        "caf": ["cyclophosphamide", "doxorubicin", "5-fluorouracil"],
        "cmf": ["cyclophosphamide", "methotrexate", "5-fluorouracil"],
        "tac": ["docetaxel", "doxorubicin", "cyclophosphamide"],
        "folfox": ["5-fluorouracil", "leucovorin", "oxaliplatin"],
        "folfiri": ["5-fluorouracil", "leucovorin", "irinotecan"],
        "folfoxiri": ["5-fluorouracil", "leucovorin", "oxaliplatin", "irinotecan"],
        "capox": ["capecitabine", "oxaliplatin"],
        "xelox": ["capecitabine", "oxaliplatin"],
        "abvd": ["doxorubicin", "bleomycin", "vinblastine", "dacarbazine"],
        "chop": ["cyclophosphamide", "doxorubicin", "vincristine", "prednisone"],
        "r-chop": ["rituximab", "cyclophosphamide", "doxorubicin", "vincristine", "prednisone"],
        "epoch": ["etoposide", "prednisone", "vincristine", "cyclophosphamide", "doxorubicin"],
        "beacopp": ["bleomycin", "etoposide", "doxorubicin", "cyclophosphamide", "vincristine", "procarbazine", "prednisone"],
        "ice": ["ifosfamide", "carboplatin", "etoposide"],
        "gem-cis": ["gemcitabine", "cisplatin"],
        "gem-carbo": ["gemcitabine", "carboplatin"],
        "mvac": ["methotrexate", "vinblastine", "doxorubicin", "cisplatin"],
    }
    
    if not regimen_name:
        return []
    
    normalized = regimen_name.lower().strip()
    
    # Check for known regimens
    for abbrev, drugs in regimen_drugs.items():
        if abbrev in normalized:
            return drugs
    
    # Try to extract individual drug names
    import re
    extracted = []
    
    # Split on common separators
    parts = re.split(r'[→/\-\+,\s]+', normalized)
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
        
        # Check if it's a known drug
        category, _ = categorize_medication(part)
        if category != MedicationCategory.OTHER:
            extracted.append(normalize_medication_name(part))
    
    return extracted if extracted else []



