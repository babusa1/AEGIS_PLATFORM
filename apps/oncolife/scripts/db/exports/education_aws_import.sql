-- =============================================================================
-- OncoLife Education Tables - AWS RDS Import Script
-- Run this on the patient database (oncolife_patient)
-- Generated: 2026-01-20 23:57:36
-- =============================================================================

-- Create tables
CREATE TABLE IF NOT EXISTS education_pdfs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    symptom_code VARCHAR(50) NOT NULL,
    symptom_name VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    source VARCHAR(100),
    file_path VARCHAR(500) NOT NULL,
    summary TEXT,
    keywords TEXT[],
    display_order INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS education_handbooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(255) NOT NULL,
    description TEXT,
    file_path VARCHAR(500) NOT NULL,
    handbook_type VARCHAR(50) NOT NULL DEFAULT 'general',
    display_order INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS education_regimen_pdfs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    regimen_code VARCHAR(50) NOT NULL,
    regimen_name VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    source VARCHAR(100),
    file_path VARCHAR(500) NOT NULL,
    document_type VARCHAR(50) DEFAULT 'overview',
    drug_name VARCHAR(100),
    summary TEXT,
    display_order INTEGER NOT NULL DEFAULT 1,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_education_pdfs_symptom_code ON education_pdfs(symptom_code);
CREATE INDEX IF NOT EXISTS ix_education_handbooks_type ON education_handbooks(handbook_type);
CREATE INDEX IF NOT EXISTS ix_education_regimen_pdfs_regimen ON education_regimen_pdfs(regimen_code);

-- Clear existing data
DELETE FROM education_pdfs;
DELETE FROM education_handbooks;
DELETE FROM education_regimen_pdfs;

-- Education Handbooks Data
INSERT INTO education_handbooks (id, title, description, file_path, handbook_type, display_order, is_active, created_at, updated_at)
VALUES 
('63109664-3195-4a3e-a287-dbd83d1f546b', 'Chemotherapy Basics Handbook', 'Everything you need to know about your chemotherapy treatment journey.', 'handbooks/chemo_basics_handbook.pdf', 'general', 1, true, NOW(), NOW()),
('93948886-ceda-44eb-8cc0-4264b5d78eec', 'Chemo Basics & Who to Call Handbook', 'Comprehensive handbook covering chemotherapy basics, managing side effects, and when/who to call for help. Essential reading for all chemotherapy patients.', 'handbooks/chemo_basics_handbook.pdf', 'general', 1, true, NOW(), NOW());


-- Education PDFs Data
INSERT INTO education_pdfs (id, symptom_code, symptom_name, title, source, file_path, summary, keywords, display_order, is_active, created_at, updated_at) VALUES
('4ce7affb-dc1e-4edf-a88c-28495c90f4b2', 'NAU-203', 'Nausea', 'Managing Nausea During Treatment', 'American Cancer Society', 'symptoms/nausea/ACS_Nausea.pdf', 'Comprehensive guide on preventing and managing nausea during cancer treatment.', ARRAY['nausea','vomiting','anti-nausea','diet'], 1, true, NOW(), NOW()),
('16769aa9-9d5e-4f9e-a7da-29c499f51104', 'NAU-203', 'Nausea', 'Nausea and Vomiting Guide', 'NCI', 'symptoms/nausea/NCI_Nausea_Vomiting.pdf', 'Learn about causes and treatments for nausea and vomiting.', ARRAY['nausea','vomiting','medications'], 1, true, NOW(), NOW()),
('a7124bf0-4aeb-4579-82e7-b9833c061311', 'FEV-202', 'Fever', 'When to Call About Fever', 'Chemocare', 'symptoms/fever/Chemocare_Fever.pdf', 'Important information about fever during chemotherapy treatment.', ARRAY['fever','temperature','infection'], 1, true, NOW(), NOW()),
('7b473825-484a-417c-be48-c695bc5c2ba9', 'FAT-206', 'Fatigue', 'Managing Cancer-Related Fatigue', 'ACS', 'symptoms/fatigue/ACS_Fatigue.pdf', 'Strategies for managing fatigue during cancer treatment.', ARRAY['fatigue','tiredness','energy','rest'], 1, true, NOW(), NOW()),
('a9c8d72a-ae35-49a6-9877-2786b627a97a', 'DIA-205', 'Diarrhea', 'Managing Diarrhea', 'NCI', 'symptoms/diarrhea/NCI_Diarrhea.pdf', 'How to manage diarrhea as a side effect of treatment.', ARRAY['diarrhea','bowel','hydration'], 1, true, NOW(), NOW()),
('50b066c5-e167-41ed-8a71-977d9132d03c', 'CON-210', 'Constipation', 'Constipation Management', 'Chemocare', 'symptoms/constipation/Chemocare_Constipation.pdf', 'Tips for preventing and treating constipation.', ARRAY['constipation','bowel','fiber'], 1, true, NOW(), NOW()),
('e7dae362-8992-4039-b70e-1effac53fc15', 'NAU-203', 'Nausea', 'Nausea and Vomiting - American Cancer Society', 'ACS', 'symptoms/nausea/ACS_Nausea.pdf', 'Comprehensive guide on managing nausea and vomiting during cancer treatment. Covers causes, prevention strategies, when to call your doctor, and practical tips for coping.', ARRAY['nausea','vomiting','anti-nausea','medications','diet'], 1, true, NOW(), NOW()),
('3de80451-3665-4f66-82ed-d494ac802286', 'NAU-203', 'Nausea', '"Nausea, Vomiting & Chemotherapy - Chemocare"', 'Chemocare', '"symptoms/nausea/Nausea,_Vomiting_&_Chemotherapy.pdf"', 'Detailed information about chemotherapy-induced nausea and vomiting. Explains why it happens, types of anti-nausea medications, and self-care measures.', ARRAY['chemotherapy','CINV','antiemetics','ondansetron','prevention'], 2, true, NOW(), NOW()),
('c397cd04-a79b-47d3-9d23-6aa6db50d270', 'NAU-203', 'Nausea', 'Nausea and Vomiting - National Cancer Institute', 'NCI', 'symptoms/nausea/Nausea_and_Vomiting_and_Cancer_-_Side_Effects_-_NCI.pdf', 'NCI fact sheet on nausea and vomiting as side effects of cancer treatment. Includes information on acute, delayed, and anticipatory nausea.', ARRAY['NCI','side effects','treatment','acute','delayed'], 3, true, NOW(), NOW()),
('ee1e3d24-a340-4266-b4df-d482860636fa', 'NAU-203', 'Nausea', 'Management of Chemotherapy-Induced Nausea - OncoLink', 'OncoLink', 'symptoms/nausea/management_of_chemotherapy_induced_nausea_and_vomiting-9679-1-eng-us_1.pdf', 'Clinical guide on managing chemotherapy-induced nausea and vomiting with medication protocols and supportive care strategies.', ARRAY['management','protocol','supportive care','evidence-based'], 4, true, NOW(), NOW()),
('367950c4-9545-47b6-bbe2-4f3cd3c374b7', 'NAU-203', 'Nausea', 'Nausea Management Guide - AI Summary', 'Perplexity AI', 'symptoms/nausea/Nausea-_Perplexity_AI.pdf', 'Comprehensive overview of nausea management strategies compiled from medical sources.', ARRAY['guide','management','overview','tips'], 5, true, NOW(), NOW()),
('8d8d2982-5fd3-4708-a6ff-1d15ef7720b6', 'VOM-204', 'Vomiting', 'Vomiting and Cancer - Cancer.net', 'Cancer.net', 'symptoms/vomiting/cancer.net_vomiting.pdf', 'Patient-friendly guide on managing vomiting during cancer treatment from ASCO''s Cancer.net.', ARRAY['vomiting','ASCO','management','dehydration'], 6, true, NOW(), NOW()),
('e19c1bf7-e55a-4c7c-85a9-5db84c813ab2', 'VOM-204', 'Vomiting', '"Nausea, Vomiting & Chemotherapy - Chemocare"', 'Chemocare', '"symptoms/vomiting/Nausea,_Vomiting_&_Chemotherapy.pdf"', 'Information on chemotherapy-related vomiting, medication options, and practical management tips.', ARRAY['chemotherapy','antiemetics','management'], 7, true, NOW(), NOW()),
('5888e64c-3e5d-4bb6-9659-1e03f839f8d9', 'VOM-204', 'Vomiting', 'Nausea and Vomiting Treatment - NCI PDQ', 'NCI', 'symptoms/vomiting/Nausea_and_Vomiting_Related_to_Cancer_Treatment_PDQr_-_NCI.pdf', 'NCI''s comprehensive PDQ information on cancer treatment-related nausea and vomiting management.', ARRAY['PDQ','treatment','evidence-based','clinical'], 8, true, NOW(), NOW()),
('311a7e2b-f4ea-40e8-b284-7920d506f661', 'VOM-204', 'Vomiting', 'CINV Management Protocol - OncoLink', 'OncoLink', 'symptoms/vomiting/management_of_chemotherapy_induced_nausea_and_vomiting-9679-1-eng-us.pdf', 'Clinical management protocol for chemotherapy-induced nausea and vomiting.', ARRAY['CINV','protocol','management','clinical'], 9, true, NOW(), NOW()),
('b9e79af6-2808-43e1-b87f-004eb189ce55', 'DIA-205', 'Diarrhea', 'Diarrhea - ACS', 'ACS', 'symptoms/diarrhea/Diarrhea1.pdf', 'American Cancer Society guide on managing diarrhea during cancer treatment. Covers causes, diet modifications, and when to seek help.', ARRAY['diarrhea','diet','hydration','BRAT'], 10, true, NOW(), NOW()),
('89f5377c-932b-4dfd-b991-52cc61de1973', 'DIA-205', 'Diarrhea', 'Diarrhea and Chemotherapy - Chemocare', 'Chemocare', 'symptoms/diarrhea/Diarrhea_and_Chemotherapy.pdf', 'Information on chemotherapy-induced diarrhea, medications like Imodium, and dietary recommendations.', ARRAY['chemotherapy','Imodium','loperamide','management'], 11, true, NOW(), NOW()),
('f03edca5-1981-4402-b812-1f913cf6c82a', 'DIA-205', 'Diarrhea', 'Diarrhea and Cancer - NCI', 'NCI', 'symptoms/diarrhea/Diarrhea_and_Cancer_-_Side_Effects_-_NCI.pdf', 'NCI fact sheet on diarrhea as a cancer treatment side effect with management strategies.', ARRAY['NCI','side effects','dehydration','electrolytes'], 12, true, NOW(), NOW()),
('80876140-2cd0-4256-b50a-acd153c71a47', 'CON-210', 'Constipation', 'Constipation - ACS', 'ACS', 'symptoms/constipation/Constipation1.pdf', 'Guide on managing constipation during cancer treatment including diet, fluids, and medications.', ARRAY['constipation','fiber','laxatives','stool softeners'], 13, true, NOW(), NOW()),
('af100e17-825d-4474-b157-ba6510bddd71', 'CON-210', 'Constipation', 'Constipation and Chemotherapy - Chemocare', 'Chemocare', 'symptoms/constipation/Constipation_and_Chemotherapy.pdf', 'Information on chemotherapy-related constipation, opioid-induced constipation, and treatment options.', ARRAY['chemotherapy','opioid','Miralax','Senna'], 14, true, NOW(), NOW()),
('551ef6f5-1237-4573-a22e-d5e7290db963', 'CON-210', 'Constipation', 'Constipation and Cancer - NCI', 'NCI', 'symptoms/constipation/Constipation_and_Cancer_-_Side_Effects_-_NCI.pdf', 'NCI guide on cancer-related constipation causes, prevention, and treatment.', ARRAY['NCI','bowel','medications','diet'], 15, true, NOW(), NOW()),
('0065c803-3875-496a-b7fc-c52aa6b6d7f1', 'APP-209', 'Loss of Appetite', 'Loss of Appetite - ACS', 'ACS', 'symptoms/appetite/LossofAppetite.pdf', 'Tips for managing appetite loss during cancer treatment including eating strategies and nutrition.', ARRAY['appetite','nutrition','weight loss','eating tips'], 16, true, NOW(), NOW()),
('90063388-bbfe-4f1b-84be-298d41d6de82', 'APP-209', 'Loss of Appetite', 'Cancer Treatment Related Lack of Appetite - Chemocare', 'Chemocare', 'symptoms/appetite/Cancer_and_Cancer_Treatment_Related_Lack_of_Appetite_and_Early_Satiety.pdf', 'Information on cancer-related appetite loss and early satiety with practical management tips.', ARRAY['anorexia','early satiety','cachexia','nutrition'], 17, true, NOW(), NOW()),
('42296f50-4a40-4044-936c-45c98c7ae51a', 'APP-209', 'Loss of Appetite', 'Nutrition During Cancer Treatment - OncoLink', 'OncoLink', 'symptoms/appetite/nutrition_during_cancer_treatment-8340-16-eng-us.pdf', 'Comprehensive nutrition guide for cancer patients including managing poor appetite.', ARRAY['nutrition','diet','protein','calories'], 18, true, NOW(), NOW()),
('f06cef32-67eb-4c71-bdaf-dfe08dacff79', 'MSO-208', 'Mouth Sores', 'Mouth Sores - Chat GPT Summary', 'ChatGPT', 'symptoms/mouth_sores/Mouth_Sores-_Chat_GPT.pdf', 'Overview of mouth sore management during cancer treatment.', ARRAY['mucositis','oral care','pain relief'], 19, true, NOW(), NOW()),
('50135cfd-641e-4051-9597-1eeaf4938715', 'MSO-208', 'Mouth Sores', 'Mouth Sores due to Chemotherapy - Chemocare', 'Chemocare', 'symptoms/mouth_sores/Mouth_Sores_due_to_Chemotherapy.pdf', 'Information on chemotherapy-induced mouth sores, magic mouthwash, and oral care.', ARRAY['mucositis','magic mouthwash','oral hygiene','pain'], 20, true, NOW(), NOW()),
('32536e2d-3b5f-4126-ba60-41c651aecbfc', 'MSO-208', 'Mouth Sores', 'Mouth and Throat Problems - NCI', 'NCI', 'symptoms/mouth_sores/Mouth_and_Throat_Problems_and_Cancer_Treatment_-_Side_Effects_-_NCI.pdf', 'NCI guide on oral and throat complications from cancer treatment.', ARRAY['NCI','mucositis','xerostomia','dysphagia'], 21, true, NOW(), NOW()),
('b055fce9-3098-42c9-b3fa-ca03b34b4bba', 'MSO-208', 'Mouth Sores', 'Mouth Sores - Perplexity AI Summary', 'Perplexity AI', 'symptoms/mouth_sores/Mouth_Sores-_Perplexity_AI.pdf', 'Comprehensive guide on managing mouth sores during chemotherapy.', ARRAY['management','prevention','relief'], 22, true, NOW(), NOW()),
('c6cf7342-6549-43a7-9294-68e4e6eb99aa', 'FEV-202', 'Fever', 'Fever - Chat GPT Summary', 'ChatGPT', 'symptoms/fever/Fever-_Chat_GPT.pdf', 'Overview of fever management during cancer treatment.', ARRAY['fever','temperature','infection'], 23, true, NOW(), NOW()),
('7ca6c582-6cdd-4113-808c-16ed12cf7ff0', 'FEV-202', 'Fever', 'Fever and Neutropenic Fever - Chemocare', 'Chemocare', '"symptoms/fever/Fever,_Neutropenic_Fever,_and_their_Relationship_to_Chemotherapy.pdf"', 'Critical information on neutropenic fever, a medical emergency in chemotherapy patients.', ARRAY['neutropenia','neutropenic fever','infection','emergency'], 24, true, NOW(), NOW()),
('f3cba2b5-3a1f-4cb4-b2ba-dff5d3886070', 'FEV-202', 'Fever', 'Fever - Perplexity AI Summary', 'Perplexity AI', 'symptoms/fever/Fever-_Perplexity_AI.pdf', 'Guide on when fever requires immediate medical attention in cancer patients.', ARRAY['fever','100.4','emergency','infection'], 25, true, NOW(), NOW()),
('ff0cac77-656d-49e4-9298-bde8538f4a6c', 'FAT-206', 'Fatigue', 'Fatigue - American Cancer Society', 'ACS', 'symptoms/fatigue/ACS_Fatigue.pdf', 'Comprehensive guide on cancer-related fatigue including causes and management strategies.', ARRAY['fatigue','tiredness','energy','rest'], 26, true, NOW(), NOW()),
('4c441611-8e48-4f60-bcf6-259a70f10613', 'FAT-206', 'Fatigue', 'Fatigue and Cancer Fatigue - Chemocare', 'Chemocare', 'symptoms/fatigue/Fatigue_and_Cancer_Fatigue.pdf', 'Information on cancer-related fatigue distinct from normal tiredness.', ARRAY['cancer fatigue','energy management','rest'], 27, true, NOW(), NOW()),
('c2bd3cb6-bad2-4dc4-b9c3-ad3d24c979c0', 'FAT-206', 'Fatigue', 'Fatigue and Cancer - NCI', 'NCI', 'symptoms/fatigue/Fatigue_and_Cancer_-_Side_Effects_-_NCI.pdf', 'NCI fact sheet on cancer-related fatigue as a common side effect.', ARRAY['NCI','side effect','management','coping'], 28, true, NOW(), NOW()),
('a7c199ee-2b84-43b6-b37c-bb3a04094d7e', 'FAT-206', 'Fatigue', 'Fatigue - OncoLink', 'OncoLink', 'symptoms/fatigue/Fatigue-_OncoLink.pdf', 'Patient education on managing fatigue during and after cancer treatment.', ARRAY['energy conservation','activity','sleep'], 29, true, NOW(), NOW()),
('16e5dab1-23df-4c7e-b986-24bf21b36609', 'FAT-206', 'Fatigue', 'Fatigue - Perplexity AI Summary', 'Perplexity AI', 'symptoms/fatigue/Fatigue-_Perplexity_AI.pdf', 'Comprehensive overview of cancer fatigue management strategies.', ARRAY['management','tips','energy'], 30, true, NOW(), NOW()),
('8af8a66f-eb3e-4c92-93dd-004e76522615', 'COU-215', 'Cough', 'Cough Management - Perplexity AI Summary', 'Perplexity AI', 'symptoms/cough/Cough_Perplexity.pdf', 'Guide on managing cough during cancer treatment, when to seek help, and relief strategies.', ARRAY['cough','respiratory','mucus','relief'], 31, true, NOW(), NOW()),
('22ee82b1-17c4-472f-8842-5442aa39de0e', 'HEA-210', 'Headache', 'Headache Management', 'General', 'symptoms/headache/Headache.pdf', 'Information on headaches during cancer treatment including causes and when to seek emergency care.', ARRAY['headache','pain','neurological','emergency'], 32, true, NOW(), NOW()),
('a505e8ea-26c8-42ef-a560-4b4753e46136', 'NEU-216', 'Neuropathy', 'Neuropathy - Cancer.org', 'Cancer.org', 'symptoms/neuropathy/Cancerorg_Neuropathy.pdf', 'Guide on chemotherapy-induced peripheral neuropathy (CIPN) symptoms and management.', ARRAY['neuropathy','CIPN','numbness','tingling'], 33, true, NOW(), NOW()),
('b2e806ba-b668-4734-8496-86f1febce067', 'NEU-216', 'Neuropathy', 'Neuropathy - NCI', 'NCI', 'symptoms/neuropathy/NCI_NEUROPHATHY.pdf', 'NCI information on peripheral neuropathy as a cancer treatment side effect.', ARRAY['NCI','peripheral','nerve damage','side effect'], 34, true, NOW(), NOW()),
('9792ba6d-db23-41c5-9ae9-0e4ebc6184e6', 'PAI-213', 'Pain', 'Headaches from Chemo - ACS', 'ACS', 'symptoms/pain/Headaches_from_Chemo_and_Other_Cancer_Treatments-_ACS.pdf', 'Information on chemotherapy-related headaches and management strategies.', ARRAY['headache','chemotherapy','pain relief'], 35, true, NOW(), NOW()),
('042db64d-a27d-45bd-b067-a6d748aca646', 'PAI-213', 'Pain', 'Pain and Chemotherapy - Chemocare', 'Chemocare', 'symptoms/pain/Pain_and_Chemotherapy.pdf', 'Guide on different types of pain during chemotherapy and management options.', ARRAY['pain','chemotherapy','medications','relief'], 36, true, NOW(), NOW()),
('2f8203ae-730e-46bd-bb87-a99ab2c9a05a', 'PAI-213', 'Pain', 'Pain and Cancer Treatment - NCI', 'NCI', 'symptoms/pain/Pain_and_Cancer_Treatment_-_Side_Effects_-_NCI.pdf', 'NCI fact sheet on cancer treatment-related pain and management approaches.', ARRAY['NCI','pain management','opioids','non-opioids'], 37, true, NOW(), NOW()),
('c73264b3-1f87-41f4-90f9-4c9b678b8fbf', 'PAI-213', 'Pain', 'Pain - Perplexity AI Summary', 'Perplexity AI', 'symptoms/pain/Pain-_Perplexity_AI.pdf', 'Comprehensive overview of cancer pain management strategies.', ARRAY['pain','management','relief','medications'], 38, true, NOW(), NOW()),
('ae8407d2-5682-4859-8cc7-6f34e5c3d6a3', 'SKI-212', 'Skin Rash', 'Skin Reactions - ACS', 'ACS', 'symptoms/skin_rash/ACS.pdf', 'Guide on skin changes and reactions during cancer treatment.', ARRAY['skin','rash','dryness','itching'], 39, true, NOW(), NOW()),
('1e664558-1a42-4f5e-ae1e-ceae39b52cba', 'SKI-212', 'Skin Rash', 'What Are Skin Reactions - Chemocare', 'Chemocare', 'symptoms/skin_rash/What_Are_Skin_Reactions.pdf', 'Information on chemotherapy-induced skin reactions and care.', ARRAY['skin reactions','chemotherapy','rash','care'], 40, true, NOW(), NOW()),
('fb5416d9-6f30-4f40-bb93-288f0c48d3e7', 'SKI-212', 'Skin Rash', 'Skin and Nail Changes - NCI', 'NCI', 'symptoms/skin_rash/Skin_and_Nail_Changes_and_Cancer_Treatment_-_Side_Effects_-_NCI.pdf', 'NCI guide on skin and nail changes from cancer treatment.', ARRAY['NCI','skin','nails','side effects'], 41, true, NOW(), NOW()),
('f60c18d2-39cc-43df-9ffa-e0e797ddcc20', 'SKI-212', 'Skin Rash', 'Skin Reactions from Radiation - OncoLink', 'OncoLink', 'symptoms/skin_rash/skin_reactions_from_radiation-2067-19-eng-us.pdf', 'Information on radiation-related skin reactions and care.', ARRAY['radiation','skin','dermatitis','care'], 42, true, NOW(), NOW()),
('780c27f2-266f-4073-ab07-b83503369592', 'SKI-212', 'Skin Rash', 'Skin Reactions - Perplexity AI Summary', 'Perplexity AI', 'symptoms/skin_rash/Skin_Reactions-_Perplexity_AI.pdf', 'Overview of skin reaction management during cancer treatment.', ARRAY['skin','management','care','relief'], 43, true, NOW(), NOW()),
('29735d92-9209-466b-bfc5-bc350f4af2ec', 'SWE-214', 'Swelling', 'Edema - ACS', 'ACS', 'symptoms/swelling/Edema-ACS.pdf', 'Guide on swelling (edema) during cancer treatment including causes and management.', ARRAY['edema','swelling','fluid retention'], 44, true, NOW(), NOW()),
('3f4ca7d1-bbb6-48f8-a9d1-dd6dd13dc5cd', 'SWE-214', 'Swelling', 'Edema - Chemocare', 'Chemocare', 'symptoms/swelling/Edema.pdf', 'Information on chemotherapy-related edema and when to contact your doctor.', ARRAY['edema','chemotherapy','legs','ankles'], 45, true, NOW(), NOW()),
('79b8aa2b-3647-4506-b8fd-8b65af37d660', 'SWE-214', 'Swelling', 'Edema and Cancer - NCI', 'NCI', 'symptoms/swelling/Edema_Swelling_and_Cancer_-_Side_Effects_-_NCI.pdf', 'NCI fact sheet on edema as a cancer treatment side effect.', ARRAY['NCI','edema','lymphedema','side effects'], 46, true, NOW(), NOW()),
('c97f283f-0357-4144-aff7-c38d9deceee2', 'EYE-207', 'Eye Problems', 'Eye Problems - Chat GPT Summary', 'ChatGPT', 'symptoms/eye_problems/Eye_Problems-_Chat_GPT.pdf', 'Overview of eye problems during cancer treatment.', ARRAY['eyes','vision','dryness','tearing'], 47, true, NOW(), NOW()),
('0ad86ff6-585f-4919-b7fd-1ef9d0b7e994', 'EYE-207', 'Eye Problems', 'Eye Problems - Chemocare', 'Chemocare', 'symptoms/eye_problems/Eye_Problems.pdf', 'Information on chemotherapy-related eye problems and care.', ARRAY['eyes','chemotherapy','vision changes'], 48, true, NOW(), NOW()),
('fb6df76b-c0d8-408e-b54e-34d49f04f64d', 'EYE-207', 'Eye Problems', 'Eye Problems - Perplexity AI Summary', 'Perplexity AI', 'symptoms/eye_problems/Eye_Problems-_Perplexity_AI.pdf', 'Guide on managing eye symptoms during cancer treatment.', ARRAY['eyes','management','care'], 49, true, NOW(), NOW()),
('4ff7eaac-7d55-4ab2-a89c-f2c10732df1d', 'URI-211', 'Urinary Problems', 'UTI - Chat GPT Summary', 'ChatGPT', 'symptoms/urinary/UTI-_Chat_GPT.pdf', 'Overview of urinary tract infections during cancer treatment.', ARRAY['UTI','urinary','infection'], 50, true, NOW(), NOW()),
('2594443d-36a3-4f6d-a846-ae8d53b19c4e', 'URI-211', 'Urinary Problems', 'Urinary Tract Infection - Chemocare', 'Chemocare', 'symptoms/urinary/Urinary_Tract_Infection_UTI.pdf', 'Information on UTIs in cancer patients including prevention and treatment.', ARRAY['UTI','bladder','infection','antibiotics'], 51, true, NOW(), NOW()),
('20bc260c-777e-4f33-b30f-5e24d7a910d4', 'URI-211', 'Urinary Problems', 'Urinary and Bladder Problems - NCI', 'NCI', 'symptoms/urinary/Urinary_and_Bladder_Problems_and_Cancer_Treatment_-_Side_Effects_-_NCI.pdf', 'NCI guide on urinary and bladder issues from cancer treatment.', ARRAY['NCI','bladder','urinary','side effects'], 52, true, NOW(), NOW()),
('17504040-d03d-4366-9ada-f0cbed9034dc', 'URI-211', 'Urinary Problems', 'UTI - Perplexity AI Summary', 'Perplexity AI', 'symptoms/urinary/UTI-_Perplexity_AI.pdf', 'Guide on urinary problems management during cancer treatment.', ARRAY['UTI','management','prevention'], 53, true, NOW(), NOW()),
('6cf61e79-269b-4c07-972e-f9a771c6cd79', 'URG-103', 'Bleeding', 'Blood Clots - ACS', 'ACS', 'symptoms/bleeding/BloodClots.pdf', 'Information on blood clots and bleeding risks in cancer patients.', ARRAY['blood clots','DVT','PE','bleeding'], 54, true, NOW(), NOW()),
('9bfa0f73-5e3e-412a-90da-7bf9fabdfc07', 'URG-103', 'Bleeding', 'Bleeding Problems - Chemocare', 'Chemocare', 'symptoms/bleeding/Bleeding_Problems.pdf', 'Guide on bleeding problems during chemotherapy including low platelets.', ARRAY['bleeding','platelets','thrombocytopenia'], 55, true, NOW(), NOW()),
('80f7987a-eaa0-4548-9368-c94fa82f92f2', 'URG-103', 'Bleeding', 'Thromboembolism - OncoLink', 'OncoLink', 'symptoms/bleeding/thromboembolism_blood_clot-23680-14-eng-us.pdf', 'Information on thromboembolism and blood clots in cancer patients.', ARRAY['thromboembolism','DVT','PE','prevention'], 56, true, NOW(), NOW()),
('055aee9a-5628-4a08-951d-08ad8283ce9f', 'URG-103', 'Bruising', 'Bruising - ACS', 'ACS', 'symptoms/bruising/Bruising1.pdf', 'Guide on bruising during cancer treatment and when to be concerned.', ARRAY['bruising','platelets','bleeding'], 57, true, NOW(), NOW()),
('d15244be-7d7e-445a-8f20-543f28ae91af', 'URG-103', 'Bruising', 'Bruising (Hematoma) - Chemocare', 'Chemocare', 'symptoms/bruising/Bruising_Hematoma.pdf', 'Information on hematomas and bruising during chemotherapy.', ARRAY['bruising','hematoma','chemotherapy'], 58, true, NOW(), NOW()),
('907298c5-e1d2-4e75-9961-5681fed4dd54', 'URG-103', 'Bruising', 'Bleeding and Bruising - NCI', 'NCI', 'symptoms/bruising/Bleeding_and_Bruising_and_Cancer_Treatment_-_Side_Effects_-_NCI.pdf', 'NCI fact sheet on bleeding and bruising as cancer treatment side effects.', ARRAY['NCI','bleeding','bruising','platelets'], 59, true, NOW(), NOW()),
('fa82f266-488b-4157-adcb-501264e81711', 'LEG-208', 'Leg Pain', 'Blood Clots - DVT Warning', 'ACS', 'symptoms/leg_pain/blood_clots.pdf', 'Critical information on blood clots presenting as leg pain - a potential emergency.', ARRAY['DVT','blood clots','leg pain','emergency'], 60, true, NOW(), NOW())
;


-- Education Regimen PDFs Data
INSERT INTO education_regimen_pdfs (id, regimen_code, regimen_name, title, source, file_path, document_type, drug_name, summary, display_order, is_active, created_at, updated_at) VALUES
('157100f1-67d7-44fc-a769-397ff9bd6975', 'ABVD', 'ABVD (Hodgkin Lymphoma)', 'ABVD Regimen Overview - OncoLink', 'OncoLink', 'regimens/abvd/ABVD.pdf', 'overview', NULL, NULL, 1, true, NOW(), NOW()),
('12d031d8-056e-441d-bf81-7b08df3091e7', 'ABVD', 'ABVD (Hodgkin Lymphoma)', 'Doxorubicin (Adriamycin) - NCCN', 'NCCN', 'regimens/abvd/chemtemplatepreview2.pdf', 'drug_info', 'Doxorubicin', NULL, 2, true, NOW(), NOW()),
('6a04570f-9402-47f4-8fde-c64d86b6c243', 'ABVD', 'ABVD (Hodgkin Lymphoma)', 'Doxorubicin (Adriamycin) - OncoLink', 'OncoLink', 'regimens/abvd/AD_OL.pdf', 'drug_info', 'Doxorubicin', NULL, 3, true, NOW(), NOW()),
('75c6bf5c-cfe5-4ffc-bd75-96d751aa3cb0', 'ABVD', 'ABVD (Hodgkin Lymphoma)', 'Bleomycin - OncoLink', 'OncoLink', 'regimens/abvd/B_OL.pdf', 'drug_info', 'Bleomycin', NULL, 4, true, NOW(), NOW()),
('79515938-cbf1-4129-a466-d249a04a8f5f', 'ABVD', 'ABVD (Hodgkin Lymphoma)', 'Dacarbazine - OncoLink', 'OncoLink', 'regimens/abvd/D2_OL.pdf', 'drug_info', 'Dacarbazine', NULL, 5, true, NOW(), NOW()),
('eaea45e5-a6ec-4c55-8704-ea439efa3862', 'ABVD', 'ABVD (Hodgkin Lymphoma)', 'Vinblastine - OncoLink', 'OncoLink', 'regimens/abvd/V2_OL.pdf', 'drug_info', 'Vinblastine', NULL, 6, true, NOW(), NOW()),
('21d257c8-d651-4e2e-af2b-d0aabce899f5', 'R-CHOP', 'R-CHOP (Non-Hodgkin Lymphoma)', 'Cyclophosphamide - NCCN', 'NCCN', 'regimens/r_chop/NCCN.pdf', 'drug_info', 'Cyclophosphamide', NULL, 7, true, NOW(), NOW()),
('323a2fda-8c73-46eb-95d1-48ba4f0f6acf', 'R-CHOP', 'R-CHOP (Non-Hodgkin Lymphoma)', 'Cyclophosphamide - OncoLink', 'OncoLink', 'regimens/r_chop/C_OL.pdf', 'drug_info', 'Cyclophosphamide', NULL, 8, true, NOW(), NOW()),
('731d6586-83bc-47b6-9d76-fc70b217453a', 'R-CHOP', 'R-CHOP (Non-Hodgkin Lymphoma)', 'Cyclophosphamide Patient Guide - OncoLink', 'OncoLink', 'regimens/r_chop/C_OL_2.pdf', 'drug_info', 'Cyclophosphamide', NULL, 9, true, NOW(), NOW()),
('b52c1d71-fb55-4465-8352-687fc8c95a01', 'R-CHOP', 'R-CHOP (Non-Hodgkin Lymphoma)', 'Doxorubicin - OncoLink', 'OncoLink', 'regimens/r_chop/D_OL.pdf', 'drug_info', 'Doxorubicin', NULL, 10, true, NOW(), NOW()),
('14e2a1bc-4e87-467e-bb76-3dfb7293ef18', 'R-CHOP', 'R-CHOP (Non-Hodgkin Lymphoma)', 'Prednisone - OncoLink', 'OncoLink', 'regimens/r_chop/P_OL.pdf', 'drug_info', 'Prednisone', NULL, 11, true, NOW(), NOW()),
('da3389cf-cdd8-42a5-99d7-9c88eca753f1', 'R-CHOP', 'R-CHOP (Non-Hodgkin Lymphoma)', 'Rituximab - ACS', 'ACS', 'regimens/r_chop/R.pdf', 'drug_info', 'Rituximab', NULL, 12, true, NOW(), NOW()),
('e9eb8223-1654-4379-96a6-7f641b45b700', 'R-CHOP', 'R-CHOP (Non-Hodgkin Lymphoma)', 'Rituximab - OncoLink', 'OncoLink', 'regimens/r_chop/R_OL.pdf', 'drug_info', 'Rituximab', NULL, 13, true, NOW(), NOW()),
('e2ac5540-b831-4dd6-896b-76a6f558634a', 'R-CHOP', 'R-CHOP (Non-Hodgkin Lymphoma)', 'Vincristine - OncoLink', 'OncoLink', 'regimens/r_chop/V_OL.pdf', 'drug_info', 'Vincristine', NULL, 14, true, NOW(), NOW()),
('fb9065ea-9e1f-4b71-b211-d6e546d75546', 'FOLFOX', 'FOLFOX (Colorectal Cancer)', 'FOLFOX Overview - Chat GPT', 'ChatGPT', 'regimens/folfox/Chat_GPT.pdf', 'overview', NULL, NULL, 15, true, NOW(), NOW()),
('c5bb0a15-1845-433e-b13d-f05b768eb1fb', 'FOLFOX', 'FOLFOX (Colorectal Cancer)', 'FOLFOX Overview - Perplexity AI', 'Perplexity AI', 'regimens/folfox/Perplexity_AI.pdf', 'overview', NULL, NULL, 16, true, NOW(), NOW()),
('47f3dae3-99c9-4aaf-869b-544c24a6e218', 'ICE', 'ICE (Lymphoma)', 'ICE Overview - Chat GPT', 'ChatGPT', 'regimens/ice/ICE_Chat_GPT.pdf', 'overview', NULL, NULL, 17, true, NOW(), NOW()),
('f953127c-24f5-409e-acc7-fcdf8eec151a', 'ICE', 'ICE (Lymphoma)', 'ICE Overview - Perplexity AI', 'Perplexity AI', 'regimens/ice/ICE_Perplexity_AI.pdf', 'overview', NULL, NULL, 18, true, NOW(), NOW()),
('4a64afa2-4385-44c2-a686-dcce9318f052', 'ICE', 'ICE (Lymphoma)', 'Carboplatin - OncoLink', 'OncoLink', 'regimens/ice/CP_OL.pdf', 'drug_info', 'Carboplatin', NULL, 19, true, NOW(), NOW()),
('75593bec-fbaf-44e1-a406-c06b490a8c73', 'ICE', 'ICE (Lymphoma)', 'Etoposide - OncoLink', 'OncoLink', 'regimens/ice/E_OL.pdf', 'drug_info', 'Etoposide', NULL, 20, true, NOW(), NOW()),
('74bb7ca2-8b98-41d7-9970-42050983ed6b', 'ICE', 'ICE (Lymphoma)', 'Ifosfamide - OncoLink', 'OncoLink', 'regimens/ice/I_OL.pdf', 'drug_info', 'Ifosfamide', NULL, 21, true, NOW(), NOW()),
('e5d50815-461a-4b4d-8a11-2e3b0ea3b3f7', 'GemOX', 'GemOX (Biliary/Pancreatic Cancer)', 'Gemcitabine - Chemocare', 'Chemocare', 'regimens/gemox/Gemcitabine_Injection.pdf', 'drug_info', 'Gemcitabine', NULL, 22, true, NOW(), NOW()),
('26fea4a7-67cd-452b-8e33-3f98b0c435a2', 'GemOX', 'GemOX (Biliary/Pancreatic Cancer)', 'Oxaliplatin - Chemocare', 'Chemocare', 'regimens/gemox/Oxaliplatin_Injection.pdf', 'drug_info', 'Oxaliplatin', NULL, 23, true, NOW(), NOW()),
('8a0825c8-c197-45fd-b2a7-d58583c4ac86', 'IFL', 'IFL (Colorectal Cancer)', 'IFL Overview - Chat GPT', 'ChatGPT', 'regimens/ifl/Chat_GPT.pdf', 'overview', NULL, NULL, 24, true, NOW(), NOW()),
('dd6eaff3-599c-413d-af5f-f8339e4545d3', 'IFL', 'IFL (Colorectal Cancer)', 'IFL Overview - Perplexity AI', 'Perplexity AI', 'regimens/ifl/Perplexity_AI.pdf', 'overview', NULL, NULL, 25, true, NOW(), NOW()),
('24c190ca-bdec-41ec-9d7c-eb7c4bbcb585', 'MAP', 'MAP (Osteosarcoma)', 'MAP Overview - Chat GPT', 'ChatGPT', 'regimens/map/Chat_GPT.pdf', 'overview', NULL, NULL, 26, true, NOW(), NOW()),
('5d56318f-a366-423c-bfec-54291a0a90a6', 'MAP', 'MAP (Osteosarcoma)', 'MAP Overview - Perplexity AI', 'Perplexity AI', 'regimens/map/Perplexity_AI.pdf', 'overview', NULL, NULL, 27, true, NOW(), NOW())
;
