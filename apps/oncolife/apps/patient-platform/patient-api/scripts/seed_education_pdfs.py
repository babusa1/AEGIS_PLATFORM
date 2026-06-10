"""
Seed script for education PDF metadata.

This script populates the education_pdfs, education_handbooks, and education_regimen_pdfs
tables with metadata for all educational PDF documents.

Run with: python scripts/seed_education_pdfs.py
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import uuid
from datetime import datetime

# Database connection - uses environment variable or defaults to local
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://oncolife_user:oncolife_password@localhost:5432/oncolife_patient"
)

# =============================================================================
# SYMPTOM PDF METADATA
# =============================================================================

SYMPTOM_PDFS = [
    # ===== NAUSEA =====
    {
        "symptom_code": "NAU-203",
        "symptom_name": "Nausea",
        "title": "Nausea and Vomiting - American Cancer Society",
        "source": "ACS",
        "file_path": "symptoms/nausea/ACS_Nausea.pdf",
        "summary": "Comprehensive guide on managing nausea and vomiting during cancer treatment. Covers causes, prevention strategies, when to call your doctor, and practical tips for coping.",
        "keywords": ["nausea", "vomiting", "anti-nausea", "medications", "diet"],
    },
    {
        "symptom_code": "NAU-203",
        "symptom_name": "Nausea",
        "title": "Nausea, Vomiting & Chemotherapy - Chemocare",
        "source": "Chemocare",
        "file_path": "symptoms/nausea/Nausea,_Vomiting_&_Chemotherapy.pdf",
        "summary": "Detailed information about chemotherapy-induced nausea and vomiting. Explains why it happens, types of anti-nausea medications, and self-care measures.",
        "keywords": ["chemotherapy", "CINV", "antiemetics", "ondansetron", "prevention"],
    },
    {
        "symptom_code": "NAU-203",
        "symptom_name": "Nausea",
        "title": "Nausea and Vomiting - National Cancer Institute",
        "source": "NCI",
        "file_path": "symptoms/nausea/Nausea_and_Vomiting_and_Cancer_-_Side_Effects_-_NCI.pdf",
        "summary": "NCI fact sheet on nausea and vomiting as side effects of cancer treatment. Includes information on acute, delayed, and anticipatory nausea.",
        "keywords": ["NCI", "side effects", "treatment", "acute", "delayed"],
    },
    {
        "symptom_code": "NAU-203",
        "symptom_name": "Nausea",
        "title": "Management of Chemotherapy-Induced Nausea - OncoLink",
        "source": "OncoLink",
        "file_path": "symptoms/nausea/management_of_chemotherapy_induced_nausea_and_vomiting-9679-1-eng-us_1.pdf",
        "summary": "Clinical guide on managing chemotherapy-induced nausea and vomiting with medication protocols and supportive care strategies.",
        "keywords": ["management", "protocol", "supportive care", "evidence-based"],
    },
    {
        "symptom_code": "NAU-203",
        "symptom_name": "Nausea",
        "title": "Nausea Management Guide - AI Summary",
        "source": "Perplexity AI",
        "file_path": "symptoms/nausea/Nausea-_Perplexity_AI.pdf",
        "summary": "Comprehensive overview of nausea management strategies compiled from medical sources.",
        "keywords": ["guide", "management", "overview", "tips"],
    },
    
    # ===== VOMITING =====
    {
        "symptom_code": "VOM-204",
        "symptom_name": "Vomiting",
        "title": "Vomiting and Cancer - Cancer.net",
        "source": "Cancer.net",
        "file_path": "symptoms/vomiting/cancer.net_vomiting.pdf",
        "summary": "Patient-friendly guide on managing vomiting during cancer treatment from ASCO's Cancer.net.",
        "keywords": ["vomiting", "ASCO", "management", "dehydration"],
    },
    {
        "symptom_code": "VOM-204",
        "symptom_name": "Vomiting",
        "title": "Nausea, Vomiting & Chemotherapy - Chemocare",
        "source": "Chemocare",
        "file_path": "symptoms/vomiting/Nausea,_Vomiting_&_Chemotherapy.pdf",
        "summary": "Information on chemotherapy-related vomiting, medication options, and practical management tips.",
        "keywords": ["chemotherapy", "antiemetics", "management"],
    },
    {
        "symptom_code": "VOM-204",
        "symptom_name": "Vomiting",
        "title": "Nausea and Vomiting Treatment - NCI PDQ",
        "source": "NCI",
        "file_path": "symptoms/vomiting/Nausea_and_Vomiting_Related_to_Cancer_Treatment_PDQr_-_NCI.pdf",
        "summary": "NCI's comprehensive PDQ information on cancer treatment-related nausea and vomiting management.",
        "keywords": ["PDQ", "treatment", "evidence-based", "clinical"],
    },
    {
        "symptom_code": "VOM-204",
        "symptom_name": "Vomiting",
        "title": "CINV Management Protocol - OncoLink",
        "source": "OncoLink",
        "file_path": "symptoms/vomiting/management_of_chemotherapy_induced_nausea_and_vomiting-9679-1-eng-us.pdf",
        "summary": "Clinical management protocol for chemotherapy-induced nausea and vomiting.",
        "keywords": ["CINV", "protocol", "management", "clinical"],
    },
    
    # ===== DIARRHEA =====
    {
        "symptom_code": "DIA-205",
        "symptom_name": "Diarrhea",
        "title": "Diarrhea - ACS",
        "source": "ACS",
        "file_path": "symptoms/diarrhea/Diarrhea1.pdf",
        "summary": "American Cancer Society guide on managing diarrhea during cancer treatment. Covers causes, diet modifications, and when to seek help.",
        "keywords": ["diarrhea", "diet", "hydration", "BRAT"],
    },
    {
        "symptom_code": "DIA-205",
        "symptom_name": "Diarrhea",
        "title": "Diarrhea and Chemotherapy - Chemocare",
        "source": "Chemocare",
        "file_path": "symptoms/diarrhea/Diarrhea_and_Chemotherapy.pdf",
        "summary": "Information on chemotherapy-induced diarrhea, medications like Imodium, and dietary recommendations.",
        "keywords": ["chemotherapy", "Imodium", "loperamide", "management"],
    },
    {
        "symptom_code": "DIA-205",
        "symptom_name": "Diarrhea",
        "title": "Diarrhea and Cancer - NCI",
        "source": "NCI",
        "file_path": "symptoms/diarrhea/Diarrhea_and_Cancer_-_Side_Effects_-_NCI.pdf",
        "summary": "NCI fact sheet on diarrhea as a cancer treatment side effect with management strategies.",
        "keywords": ["NCI", "side effects", "dehydration", "electrolytes"],
    },
    
    # ===== CONSTIPATION =====
    {
        "symptom_code": "CON-210",
        "symptom_name": "Constipation",
        "title": "Constipation - ACS",
        "source": "ACS",
        "file_path": "symptoms/constipation/Constipation1.pdf",
        "summary": "Guide on managing constipation during cancer treatment including diet, fluids, and medications.",
        "keywords": ["constipation", "fiber", "laxatives", "stool softeners"],
    },
    {
        "symptom_code": "CON-210",
        "symptom_name": "Constipation",
        "title": "Constipation and Chemotherapy - Chemocare",
        "source": "Chemocare",
        "file_path": "symptoms/constipation/Constipation_and_Chemotherapy.pdf",
        "summary": "Information on chemotherapy-related constipation, opioid-induced constipation, and treatment options.",
        "keywords": ["chemotherapy", "opioid", "Miralax", "Senna"],
    },
    {
        "symptom_code": "CON-210",
        "symptom_name": "Constipation",
        "title": "Constipation and Cancer - NCI",
        "source": "NCI",
        "file_path": "symptoms/constipation/Constipation_and_Cancer_-_Side_Effects_-_NCI.pdf",
        "summary": "NCI guide on cancer-related constipation causes, prevention, and treatment.",
        "keywords": ["NCI", "bowel", "medications", "diet"],
    },
    
    # ===== APPETITE =====
    {
        "symptom_code": "APP-209",
        "symptom_name": "Loss of Appetite",
        "title": "Loss of Appetite - ACS",
        "source": "ACS",
        "file_path": "symptoms/appetite/LossofAppetite.pdf",
        "summary": "Tips for managing appetite loss during cancer treatment including eating strategies and nutrition.",
        "keywords": ["appetite", "nutrition", "weight loss", "eating tips"],
    },
    {
        "symptom_code": "APP-209",
        "symptom_name": "Loss of Appetite",
        "title": "Cancer Treatment Related Lack of Appetite - Chemocare",
        "source": "Chemocare",
        "file_path": "symptoms/appetite/Cancer_and_Cancer_Treatment_Related_Lack_of_Appetite_and_Early_Satiety.pdf",
        "summary": "Information on cancer-related appetite loss and early satiety with practical management tips.",
        "keywords": ["anorexia", "early satiety", "cachexia", "nutrition"],
    },
    {
        "symptom_code": "APP-209",
        "symptom_name": "Loss of Appetite",
        "title": "Nutrition During Cancer Treatment - OncoLink",
        "source": "OncoLink",
        "file_path": "symptoms/appetite/nutrition_during_cancer_treatment-8340-16-eng-us.pdf",
        "summary": "Comprehensive nutrition guide for cancer patients including managing poor appetite.",
        "keywords": ["nutrition", "diet", "protein", "calories"],
    },
    
    # ===== MOUTH SORES =====
    {
        "symptom_code": "MSO-208",
        "symptom_name": "Mouth Sores",
        "title": "Mouth Sores - Chat GPT Summary",
        "source": "ChatGPT",
        "file_path": "symptoms/mouth_sores/Mouth_Sores-_Chat_GPT.pdf",
        "summary": "Overview of mouth sore management during cancer treatment.",
        "keywords": ["mucositis", "oral care", "pain relief"],
    },
    {
        "symptom_code": "MSO-208",
        "symptom_name": "Mouth Sores",
        "title": "Mouth Sores due to Chemotherapy - Chemocare",
        "source": "Chemocare",
        "file_path": "symptoms/mouth_sores/Mouth_Sores_due_to_Chemotherapy.pdf",
        "summary": "Information on chemotherapy-induced mouth sores, magic mouthwash, and oral care.",
        "keywords": ["mucositis", "magic mouthwash", "oral hygiene", "pain"],
    },
    {
        "symptom_code": "MSO-208",
        "symptom_name": "Mouth Sores",
        "title": "Mouth and Throat Problems - NCI",
        "source": "NCI",
        "file_path": "symptoms/mouth_sores/Mouth_and_Throat_Problems_and_Cancer_Treatment_-_Side_Effects_-_NCI.pdf",
        "summary": "NCI guide on oral and throat complications from cancer treatment.",
        "keywords": ["NCI", "mucositis", "xerostomia", "dysphagia"],
    },
    {
        "symptom_code": "MSO-208",
        "symptom_name": "Mouth Sores",
        "title": "Mouth Sores - Perplexity AI Summary",
        "source": "Perplexity AI",
        "file_path": "symptoms/mouth_sores/Mouth_Sores-_Perplexity_AI.pdf",
        "summary": "Comprehensive guide on managing mouth sores during chemotherapy.",
        "keywords": ["management", "prevention", "relief"],
    },
    
    # ===== FEVER =====
    {
        "symptom_code": "FEV-202",
        "symptom_name": "Fever",
        "title": "Fever - Chat GPT Summary",
        "source": "ChatGPT",
        "file_path": "symptoms/fever/Fever-_Chat_GPT.pdf",
        "summary": "Overview of fever management during cancer treatment.",
        "keywords": ["fever", "temperature", "infection"],
    },
    {
        "symptom_code": "FEV-202",
        "symptom_name": "Fever",
        "title": "Fever and Neutropenic Fever - Chemocare",
        "source": "Chemocare",
        "file_path": "symptoms/fever/Fever,_Neutropenic_Fever,_and_their_Relationship_to_Chemotherapy.pdf",
        "summary": "Critical information on neutropenic fever, a medical emergency in chemotherapy patients.",
        "keywords": ["neutropenia", "neutropenic fever", "infection", "emergency"],
    },
    {
        "symptom_code": "FEV-202",
        "symptom_name": "Fever",
        "title": "Fever - Perplexity AI Summary",
        "source": "Perplexity AI",
        "file_path": "symptoms/fever/Fever-_Perplexity_AI.pdf",
        "summary": "Guide on when fever requires immediate medical attention in cancer patients.",
        "keywords": ["fever", "100.4", "emergency", "infection"],
    },
    
    # ===== FATIGUE =====
    {
        "symptom_code": "FAT-206",
        "symptom_name": "Fatigue",
        "title": "Fatigue - American Cancer Society",
        "source": "ACS",
        "file_path": "symptoms/fatigue/ACS_Fatigue.pdf",
        "summary": "Comprehensive guide on cancer-related fatigue including causes and management strategies.",
        "keywords": ["fatigue", "tiredness", "energy", "rest"],
    },
    {
        "symptom_code": "FAT-206",
        "symptom_name": "Fatigue",
        "title": "Fatigue and Cancer Fatigue - Chemocare",
        "source": "Chemocare",
        "file_path": "symptoms/fatigue/Fatigue_and_Cancer_Fatigue.pdf",
        "summary": "Information on cancer-related fatigue distinct from normal tiredness.",
        "keywords": ["cancer fatigue", "energy management", "rest"],
    },
    {
        "symptom_code": "FAT-206",
        "symptom_name": "Fatigue",
        "title": "Fatigue and Cancer - NCI",
        "source": "NCI",
        "file_path": "symptoms/fatigue/Fatigue_and_Cancer_-_Side_Effects_-_NCI.pdf",
        "summary": "NCI fact sheet on cancer-related fatigue as a common side effect.",
        "keywords": ["NCI", "side effect", "management", "coping"],
    },
    {
        "symptom_code": "FAT-206",
        "symptom_name": "Fatigue",
        "title": "Fatigue - OncoLink",
        "source": "OncoLink",
        "file_path": "symptoms/fatigue/Fatigue-_OncoLink.pdf",
        "summary": "Patient education on managing fatigue during and after cancer treatment.",
        "keywords": ["energy conservation", "activity", "sleep"],
    },
    {
        "symptom_code": "FAT-206",
        "symptom_name": "Fatigue",
        "title": "Fatigue - Perplexity AI Summary",
        "source": "Perplexity AI",
        "file_path": "symptoms/fatigue/Fatigue-_Perplexity_AI.pdf",
        "summary": "Comprehensive overview of cancer fatigue management strategies.",
        "keywords": ["management", "tips", "energy"],
    },
    
    # ===== COUGH =====
    {
        "symptom_code": "COU-215",
        "symptom_name": "Cough",
        "title": "Cough Management - Perplexity AI Summary",
        "source": "Perplexity AI",
        "file_path": "symptoms/cough/Cough_Perplexity.pdf",
        "summary": "Guide on managing cough during cancer treatment, when to seek help, and relief strategies.",
        "keywords": ["cough", "respiratory", "mucus", "relief"],
    },
    
    # ===== HEADACHE =====
    {
        "symptom_code": "HEA-210",
        "symptom_name": "Headache",
        "title": "Headache Management",
        "source": "General",
        "file_path": "symptoms/headache/Headache.pdf",
        "summary": "Information on headaches during cancer treatment including causes and when to seek emergency care.",
        "keywords": ["headache", "pain", "neurological", "emergency"],
    },
    
    # ===== NEUROPATHY =====
    {
        "symptom_code": "NEU-216",
        "symptom_name": "Neuropathy",
        "title": "Neuropathy - Cancer.org",
        "source": "Cancer.org",
        "file_path": "symptoms/neuropathy/Cancerorg_Neuropathy.pdf",
        "summary": "Guide on chemotherapy-induced peripheral neuropathy (CIPN) symptoms and management.",
        "keywords": ["neuropathy", "CIPN", "numbness", "tingling"],
    },
    {
        "symptom_code": "NEU-216",
        "symptom_name": "Neuropathy",
        "title": "Neuropathy - NCI",
        "source": "NCI",
        "file_path": "symptoms/neuropathy/NCI_NEUROPHATHY.pdf",
        "summary": "NCI information on peripheral neuropathy as a cancer treatment side effect.",
        "keywords": ["NCI", "peripheral", "nerve damage", "side effect"],
    },
    
    # ===== PAIN =====
    {
        "symptom_code": "PAI-213",
        "symptom_name": "Pain",
        "title": "Headaches from Chemo - ACS",
        "source": "ACS",
        "file_path": "symptoms/pain/Headaches_from_Chemo_and_Other_Cancer_Treatments-_ACS.pdf",
        "summary": "Information on chemotherapy-related headaches and management strategies.",
        "keywords": ["headache", "chemotherapy", "pain relief"],
    },
    {
        "symptom_code": "PAI-213",
        "symptom_name": "Pain",
        "title": "Pain and Chemotherapy - Chemocare",
        "source": "Chemocare",
        "file_path": "symptoms/pain/Pain_and_Chemotherapy.pdf",
        "summary": "Guide on different types of pain during chemotherapy and management options.",
        "keywords": ["pain", "chemotherapy", "medications", "relief"],
    },
    {
        "symptom_code": "PAI-213",
        "symptom_name": "Pain",
        "title": "Pain and Cancer Treatment - NCI",
        "source": "NCI",
        "file_path": "symptoms/pain/Pain_and_Cancer_Treatment_-_Side_Effects_-_NCI.pdf",
        "summary": "NCI fact sheet on cancer treatment-related pain and management approaches.",
        "keywords": ["NCI", "pain management", "opioids", "non-opioids"],
    },
    {
        "symptom_code": "PAI-213",
        "symptom_name": "Pain",
        "title": "Pain - Perplexity AI Summary",
        "source": "Perplexity AI",
        "file_path": "symptoms/pain/Pain-_Perplexity_AI.pdf",
        "summary": "Comprehensive overview of cancer pain management strategies.",
        "keywords": ["pain", "management", "relief", "medications"],
    },
    
    # ===== SKIN RASH =====
    {
        "symptom_code": "SKI-212",
        "symptom_name": "Skin Rash",
        "title": "Skin Reactions - ACS",
        "source": "ACS",
        "file_path": "symptoms/skin_rash/ACS.pdf",
        "summary": "Guide on skin changes and reactions during cancer treatment.",
        "keywords": ["skin", "rash", "dryness", "itching"],
    },
    {
        "symptom_code": "SKI-212",
        "symptom_name": "Skin Rash",
        "title": "What Are Skin Reactions - Chemocare",
        "source": "Chemocare",
        "file_path": "symptoms/skin_rash/What_Are_Skin_Reactions.pdf",
        "summary": "Information on chemotherapy-induced skin reactions and care.",
        "keywords": ["skin reactions", "chemotherapy", "rash", "care"],
    },
    {
        "symptom_code": "SKI-212",
        "symptom_name": "Skin Rash",
        "title": "Skin and Nail Changes - NCI",
        "source": "NCI",
        "file_path": "symptoms/skin_rash/Skin_and_Nail_Changes_and_Cancer_Treatment_-_Side_Effects_-_NCI.pdf",
        "summary": "NCI guide on skin and nail changes from cancer treatment.",
        "keywords": ["NCI", "skin", "nails", "side effects"],
    },
    {
        "symptom_code": "SKI-212",
        "symptom_name": "Skin Rash",
        "title": "Skin Reactions from Radiation - OncoLink",
        "source": "OncoLink",
        "file_path": "symptoms/skin_rash/skin_reactions_from_radiation-2067-19-eng-us.pdf",
        "summary": "Information on radiation-related skin reactions and care.",
        "keywords": ["radiation", "skin", "dermatitis", "care"],
    },
    {
        "symptom_code": "SKI-212",
        "symptom_name": "Skin Rash",
        "title": "Skin Reactions - Perplexity AI Summary",
        "source": "Perplexity AI",
        "file_path": "symptoms/skin_rash/Skin_Reactions-_Perplexity_AI.pdf",
        "summary": "Overview of skin reaction management during cancer treatment.",
        "keywords": ["skin", "management", "care", "relief"],
    },
    
    # ===== SWELLING =====
    {
        "symptom_code": "SWE-214",
        "symptom_name": "Swelling",
        "title": "Edema - ACS",
        "source": "ACS",
        "file_path": "symptoms/swelling/Edema-ACS.pdf",
        "summary": "Guide on swelling (edema) during cancer treatment including causes and management.",
        "keywords": ["edema", "swelling", "fluid retention"],
    },
    {
        "symptom_code": "SWE-214",
        "symptom_name": "Swelling",
        "title": "Edema - Chemocare",
        "source": "Chemocare",
        "file_path": "symptoms/swelling/Edema.pdf",
        "summary": "Information on chemotherapy-related edema and when to contact your doctor.",
        "keywords": ["edema", "chemotherapy", "legs", "ankles"],
    },
    {
        "symptom_code": "SWE-214",
        "symptom_name": "Swelling",
        "title": "Edema and Cancer - NCI",
        "source": "NCI",
        "file_path": "symptoms/swelling/Edema_Swelling_and_Cancer_-_Side_Effects_-_NCI.pdf",
        "summary": "NCI fact sheet on edema as a cancer treatment side effect.",
        "keywords": ["NCI", "edema", "lymphedema", "side effects"],
    },
    
    # ===== EYE PROBLEMS =====
    {
        "symptom_code": "EYE-207",
        "symptom_name": "Eye Problems",
        "title": "Eye Problems - Chat GPT Summary",
        "source": "ChatGPT",
        "file_path": "symptoms/eye_problems/Eye_Problems-_Chat_GPT.pdf",
        "summary": "Overview of eye problems during cancer treatment.",
        "keywords": ["eyes", "vision", "dryness", "tearing"],
    },
    {
        "symptom_code": "EYE-207",
        "symptom_name": "Eye Problems",
        "title": "Eye Problems - Chemocare",
        "source": "Chemocare",
        "file_path": "symptoms/eye_problems/Eye_Problems.pdf",
        "summary": "Information on chemotherapy-related eye problems and care.",
        "keywords": ["eyes", "chemotherapy", "vision changes"],
    },
    {
        "symptom_code": "EYE-207",
        "symptom_name": "Eye Problems",
        "title": "Eye Problems - Perplexity AI Summary",
        "source": "Perplexity AI",
        "file_path": "symptoms/eye_problems/Eye_Problems-_Perplexity_AI.pdf",
        "summary": "Guide on managing eye symptoms during cancer treatment.",
        "keywords": ["eyes", "management", "care"],
    },
    
    # ===== URINARY =====
    {
        "symptom_code": "URI-211",
        "symptom_name": "Urinary Problems",
        "title": "UTI - Chat GPT Summary",
        "source": "ChatGPT",
        "file_path": "symptoms/urinary/UTI-_Chat_GPT.pdf",
        "summary": "Overview of urinary tract infections during cancer treatment.",
        "keywords": ["UTI", "urinary", "infection"],
    },
    {
        "symptom_code": "URI-211",
        "symptom_name": "Urinary Problems",
        "title": "Urinary Tract Infection - Chemocare",
        "source": "Chemocare",
        "file_path": "symptoms/urinary/Urinary_Tract_Infection_UTI.pdf",
        "summary": "Information on UTIs in cancer patients including prevention and treatment.",
        "keywords": ["UTI", "bladder", "infection", "antibiotics"],
    },
    {
        "symptom_code": "URI-211",
        "symptom_name": "Urinary Problems",
        "title": "Urinary and Bladder Problems - NCI",
        "source": "NCI",
        "file_path": "symptoms/urinary/Urinary_and_Bladder_Problems_and_Cancer_Treatment_-_Side_Effects_-_NCI.pdf",
        "summary": "NCI guide on urinary and bladder issues from cancer treatment.",
        "keywords": ["NCI", "bladder", "urinary", "side effects"],
    },
    {
        "symptom_code": "URI-211",
        "symptom_name": "Urinary Problems",
        "title": "UTI - Perplexity AI Summary",
        "source": "Perplexity AI",
        "file_path": "symptoms/urinary/UTI-_Perplexity_AI.pdf",
        "summary": "Guide on urinary problems management during cancer treatment.",
        "keywords": ["UTI", "management", "prevention"],
    },
    
    # ===== BLEEDING =====
    {
        "symptom_code": "URG-103",
        "symptom_name": "Bleeding",
        "title": "Blood Clots - ACS",
        "source": "ACS",
        "file_path": "symptoms/bleeding/BloodClots.pdf",
        "summary": "Information on blood clots and bleeding risks in cancer patients.",
        "keywords": ["blood clots", "DVT", "PE", "bleeding"],
    },
    {
        "symptom_code": "URG-103",
        "symptom_name": "Bleeding",
        "title": "Bleeding Problems - Chemocare",
        "source": "Chemocare",
        "file_path": "symptoms/bleeding/Bleeding_Problems.pdf",
        "summary": "Guide on bleeding problems during chemotherapy including low platelets.",
        "keywords": ["bleeding", "platelets", "thrombocytopenia"],
    },
    {
        "symptom_code": "URG-103",
        "symptom_name": "Bleeding",
        "title": "Thromboembolism - OncoLink",
        "source": "OncoLink",
        "file_path": "symptoms/bleeding/thromboembolism_blood_clot-23680-14-eng-us.pdf",
        "summary": "Information on thromboembolism and blood clots in cancer patients.",
        "keywords": ["thromboembolism", "DVT", "PE", "prevention"],
    },
    
    # ===== BRUISING =====
    {
        "symptom_code": "URG-103",
        "symptom_name": "Bruising",
        "title": "Bruising - ACS",
        "source": "ACS",
        "file_path": "symptoms/bruising/Bruising1.pdf",
        "summary": "Guide on bruising during cancer treatment and when to be concerned.",
        "keywords": ["bruising", "platelets", "bleeding"],
    },
    {
        "symptom_code": "URG-103",
        "symptom_name": "Bruising",
        "title": "Bruising (Hematoma) - Chemocare",
        "source": "Chemocare",
        "file_path": "symptoms/bruising/Bruising_Hematoma.pdf",
        "summary": "Information on hematomas and bruising during chemotherapy.",
        "keywords": ["bruising", "hematoma", "chemotherapy"],
    },
    {
        "symptom_code": "URG-103",
        "symptom_name": "Bruising",
        "title": "Bleeding and Bruising - NCI",
        "source": "NCI",
        "file_path": "symptoms/bruising/Bleeding_and_Bruising_and_Cancer_Treatment_-_Side_Effects_-_NCI.pdf",
        "summary": "NCI fact sheet on bleeding and bruising as cancer treatment side effects.",
        "keywords": ["NCI", "bleeding", "bruising", "platelets"],
    },
    
    # ===== LEG PAIN =====
    {
        "symptom_code": "LEG-208",
        "symptom_name": "Leg Pain",
        "title": "Blood Clots - DVT Warning",
        "source": "ACS",
        "file_path": "symptoms/leg_pain/blood_clots.pdf",
        "summary": "Critical information on blood clots presenting as leg pain - a potential emergency.",
        "keywords": ["DVT", "blood clots", "leg pain", "emergency"],
    },
]

# =============================================================================
# HANDBOOK METADATA
# =============================================================================

HANDBOOKS = [
    {
        "title": "Chemo Basics & Who to Call Handbook",
        "description": "Comprehensive handbook covering chemotherapy basics, managing side effects, and when/who to call for help. Essential reading for all chemotherapy patients.",
        "file_path": "handbooks/chemo_basics_handbook.pdf",
        "handbook_type": "general",
        "display_order": 1,
    },
]

# =============================================================================
# REGIMEN PDF METADATA
# =============================================================================

REGIMEN_PDFS = [
    # ===== ABVD =====
    {
        "regimen_code": "ABVD",
        "regimen_name": "ABVD (Hodgkin Lymphoma)",
        "title": "ABVD Regimen Overview - OncoLink",
        "source": "OncoLink",
        "file_path": "regimens/abvd/ABVD.pdf",
        "document_type": "overview",
    },
    {
        "regimen_code": "ABVD",
        "regimen_name": "ABVD (Hodgkin Lymphoma)",
        "title": "Doxorubicin (Adriamycin) - NCCN",
        "source": "NCCN",
        "file_path": "regimens/abvd/chemtemplatepreview2.pdf",
        "document_type": "drug_info",
        "drug_name": "Doxorubicin",
    },
    {
        "regimen_code": "ABVD",
        "regimen_name": "ABVD (Hodgkin Lymphoma)",
        "title": "Doxorubicin (Adriamycin) - OncoLink",
        "source": "OncoLink",
        "file_path": "regimens/abvd/AD_OL.pdf",
        "document_type": "drug_info",
        "drug_name": "Doxorubicin",
    },
    {
        "regimen_code": "ABVD",
        "regimen_name": "ABVD (Hodgkin Lymphoma)",
        "title": "Bleomycin - OncoLink",
        "source": "OncoLink",
        "file_path": "regimens/abvd/B_OL.pdf",
        "document_type": "drug_info",
        "drug_name": "Bleomycin",
    },
    {
        "regimen_code": "ABVD",
        "regimen_name": "ABVD (Hodgkin Lymphoma)",
        "title": "Dacarbazine - OncoLink",
        "source": "OncoLink",
        "file_path": "regimens/abvd/D2_OL.pdf",
        "document_type": "drug_info",
        "drug_name": "Dacarbazine",
    },
    {
        "regimen_code": "ABVD",
        "regimen_name": "ABVD (Hodgkin Lymphoma)",
        "title": "Vinblastine - OncoLink",
        "source": "OncoLink",
        "file_path": "regimens/abvd/V2_OL.pdf",
        "document_type": "drug_info",
        "drug_name": "Vinblastine",
    },
    
    # ===== R-CHOP =====
    {
        "regimen_code": "R-CHOP",
        "regimen_name": "R-CHOP (Non-Hodgkin Lymphoma)",
        "title": "Cyclophosphamide - NCCN",
        "source": "NCCN",
        "file_path": "regimens/r_chop/NCCN.pdf",
        "document_type": "drug_info",
        "drug_name": "Cyclophosphamide",
    },
    {
        "regimen_code": "R-CHOP",
        "regimen_name": "R-CHOP (Non-Hodgkin Lymphoma)",
        "title": "Cyclophosphamide - OncoLink",
        "source": "OncoLink",
        "file_path": "regimens/r_chop/C_OL.pdf",
        "document_type": "drug_info",
        "drug_name": "Cyclophosphamide",
    },
    {
        "regimen_code": "R-CHOP",
        "regimen_name": "R-CHOP (Non-Hodgkin Lymphoma)",
        "title": "Cyclophosphamide Patient Guide - OncoLink",
        "source": "OncoLink",
        "file_path": "regimens/r_chop/C_OL_2.pdf",
        "document_type": "drug_info",
        "drug_name": "Cyclophosphamide",
    },
    {
        "regimen_code": "R-CHOP",
        "regimen_name": "R-CHOP (Non-Hodgkin Lymphoma)",
        "title": "Doxorubicin - OncoLink",
        "source": "OncoLink",
        "file_path": "regimens/r_chop/D_OL.pdf",
        "document_type": "drug_info",
        "drug_name": "Doxorubicin",
    },
    {
        "regimen_code": "R-CHOP",
        "regimen_name": "R-CHOP (Non-Hodgkin Lymphoma)",
        "title": "Prednisone - OncoLink",
        "source": "OncoLink",
        "file_path": "regimens/r_chop/P_OL.pdf",
        "document_type": "drug_info",
        "drug_name": "Prednisone",
    },
    {
        "regimen_code": "R-CHOP",
        "regimen_name": "R-CHOP (Non-Hodgkin Lymphoma)",
        "title": "Rituximab - ACS",
        "source": "ACS",
        "file_path": "regimens/r_chop/R.pdf",
        "document_type": "drug_info",
        "drug_name": "Rituximab",
    },
    {
        "regimen_code": "R-CHOP",
        "regimen_name": "R-CHOP (Non-Hodgkin Lymphoma)",
        "title": "Rituximab - OncoLink",
        "source": "OncoLink",
        "file_path": "regimens/r_chop/R_OL.pdf",
        "document_type": "drug_info",
        "drug_name": "Rituximab",
    },
    {
        "regimen_code": "R-CHOP",
        "regimen_name": "R-CHOP (Non-Hodgkin Lymphoma)",
        "title": "Vincristine - OncoLink",
        "source": "OncoLink",
        "file_path": "regimens/r_chop/V_OL.pdf",
        "document_type": "drug_info",
        "drug_name": "Vincristine",
    },
    
    # ===== FOLFOX =====
    {
        "regimen_code": "FOLFOX",
        "regimen_name": "FOLFOX (Colorectal Cancer)",
        "title": "FOLFOX Overview - Chat GPT",
        "source": "ChatGPT",
        "file_path": "regimens/folfox/Chat_GPT.pdf",
        "document_type": "overview",
    },
    {
        "regimen_code": "FOLFOX",
        "regimen_name": "FOLFOX (Colorectal Cancer)",
        "title": "FOLFOX Overview - Perplexity AI",
        "source": "Perplexity AI",
        "file_path": "regimens/folfox/Perplexity_AI.pdf",
        "document_type": "overview",
    },
    
    # ===== ICE =====
    {
        "regimen_code": "ICE",
        "regimen_name": "ICE (Lymphoma)",
        "title": "ICE Overview - Chat GPT",
        "source": "ChatGPT",
        "file_path": "regimens/ice/ICE_Chat_GPT.pdf",
        "document_type": "overview",
    },
    {
        "regimen_code": "ICE",
        "regimen_name": "ICE (Lymphoma)",
        "title": "ICE Overview - Perplexity AI",
        "source": "Perplexity AI",
        "file_path": "regimens/ice/ICE_Perplexity_AI.pdf",
        "document_type": "overview",
    },
    {
        "regimen_code": "ICE",
        "regimen_name": "ICE (Lymphoma)",
        "title": "Carboplatin - OncoLink",
        "source": "OncoLink",
        "file_path": "regimens/ice/CP_OL.pdf",
        "document_type": "drug_info",
        "drug_name": "Carboplatin",
    },
    {
        "regimen_code": "ICE",
        "regimen_name": "ICE (Lymphoma)",
        "title": "Etoposide - OncoLink",
        "source": "OncoLink",
        "file_path": "regimens/ice/E_OL.pdf",
        "document_type": "drug_info",
        "drug_name": "Etoposide",
    },
    {
        "regimen_code": "ICE",
        "regimen_name": "ICE (Lymphoma)",
        "title": "Ifosfamide - OncoLink",
        "source": "OncoLink",
        "file_path": "regimens/ice/I_OL.pdf",
        "document_type": "drug_info",
        "drug_name": "Ifosfamide",
    },
    
    # ===== GemOX =====
    {
        "regimen_code": "GemOX",
        "regimen_name": "GemOX (Biliary/Pancreatic Cancer)",
        "title": "Gemcitabine - Chemocare",
        "source": "Chemocare",
        "file_path": "regimens/gemox/Gemcitabine_Injection.pdf",
        "document_type": "drug_info",
        "drug_name": "Gemcitabine",
    },
    {
        "regimen_code": "GemOX",
        "regimen_name": "GemOX (Biliary/Pancreatic Cancer)",
        "title": "Oxaliplatin - Chemocare",
        "source": "Chemocare",
        "file_path": "regimens/gemox/Oxaliplatin_Injection.pdf",
        "document_type": "drug_info",
        "drug_name": "Oxaliplatin",
    },
    
    # ===== IFL =====
    {
        "regimen_code": "IFL",
        "regimen_name": "IFL (Colorectal Cancer)",
        "title": "IFL Overview - Chat GPT",
        "source": "ChatGPT",
        "file_path": "regimens/ifl/Chat_GPT.pdf",
        "document_type": "overview",
    },
    {
        "regimen_code": "IFL",
        "regimen_name": "IFL (Colorectal Cancer)",
        "title": "IFL Overview - Perplexity AI",
        "source": "Perplexity AI",
        "file_path": "regimens/ifl/Perplexity_AI.pdf",
        "document_type": "overview",
    },
    
    # ===== MAP =====
    {
        "regimen_code": "MAP",
        "regimen_name": "MAP (Osteosarcoma)",
        "title": "MAP Overview - Chat GPT",
        "source": "ChatGPT",
        "file_path": "regimens/map/Chat_GPT.pdf",
        "document_type": "overview",
    },
    {
        "regimen_code": "MAP",
        "regimen_name": "MAP (Osteosarcoma)",
        "title": "MAP Overview - Perplexity AI",
        "source": "Perplexity AI",
        "file_path": "regimens/map/Perplexity_AI.pdf",
        "document_type": "overview",
    },
]


def seed_database():
    """Seed the education tables with metadata."""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        print("🌱 Starting education PDF seed...")
        
        # Seed symptom PDFs
        print("\n📚 Seeding symptom PDFs...")
        for idx, pdf in enumerate(SYMPTOM_PDFS, 1):
            session.execute(
                text("""
                    INSERT INTO education_pdfs 
                    (id, symptom_code, symptom_name, title, source, file_path, summary, keywords, display_order, is_active)
                    VALUES 
                    (:id, :symptom_code, :symptom_name, :title, :source, :file_path, :summary, :keywords, :display_order, true)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()),
                    "symptom_code": pdf["symptom_code"],
                    "symptom_name": pdf["symptom_name"],
                    "title": pdf["title"],
                    "source": pdf.get("source"),
                    "file_path": pdf["file_path"],
                    "summary": pdf.get("summary"),
                    "keywords": pdf.get("keywords", []),
                    "display_order": idx,
                }
            )
        print(f"  ✅ Seeded {len(SYMPTOM_PDFS)} symptom PDFs")
        
        # Seed handbooks
        print("\n📖 Seeding handbooks...")
        for idx, handbook in enumerate(HANDBOOKS, 1):
            session.execute(
                text("""
                    INSERT INTO education_handbooks 
                    (id, title, description, file_path, handbook_type, display_order, is_active)
                    VALUES 
                    (:id, :title, :description, :file_path, :handbook_type, :display_order, true)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()),
                    "title": handbook["title"],
                    "description": handbook.get("description"),
                    "file_path": handbook["file_path"],
                    "handbook_type": handbook.get("handbook_type", "general"),
                    "display_order": idx,
                }
            )
        print(f"  ✅ Seeded {len(HANDBOOKS)} handbooks")
        
        # Seed regimen PDFs
        print("\n💊 Seeding regimen PDFs...")
        for idx, pdf in enumerate(REGIMEN_PDFS, 1):
            session.execute(
                text("""
                    INSERT INTO education_regimen_pdfs 
                    (id, regimen_code, regimen_name, title, source, file_path, document_type, drug_name, display_order, is_active)
                    VALUES 
                    (:id, :regimen_code, :regimen_name, :title, :source, :file_path, :document_type, :drug_name, :display_order, true)
                    ON CONFLICT DO NOTHING
                """),
                {
                    "id": str(uuid.uuid4()),
                    "regimen_code": pdf["regimen_code"],
                    "regimen_name": pdf["regimen_name"],
                    "title": pdf["title"],
                    "source": pdf.get("source"),
                    "file_path": pdf["file_path"],
                    "document_type": pdf.get("document_type", "overview"),
                    "drug_name": pdf.get("drug_name"),
                    "display_order": idx,
                }
            )
        print(f"  ✅ Seeded {len(REGIMEN_PDFS)} regimen PDFs")
        
        session.commit()
        print("\n✅ Education PDF seed completed successfully!")
        
        # Print summary
        print("\n📊 Summary:")
        print(f"  - Symptom PDFs: {len(SYMPTOM_PDFS)}")
        print(f"  - Handbooks: {len(HANDBOOKS)}")
        print(f"  - Regimen PDFs: {len(REGIMEN_PDFS)}")
        print(f"  - Total: {len(SYMPTOM_PDFS) + len(HANDBOOKS) + len(REGIMEN_PDFS)}")
        
    except Exception as e:
        session.rollback()
        print(f"\n❌ Error seeding database: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
