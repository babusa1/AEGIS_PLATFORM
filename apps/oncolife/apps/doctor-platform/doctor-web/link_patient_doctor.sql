-- Link patient to doctor (run in oncolife_patient database)

-- Create association table if not exists
CREATE TABLE IF NOT EXISTS patient_physician_associations (
    id SERIAL PRIMARY KEY,
    patient_uuid UUID NOT NULL,
    physician_uuid UUID NOT NULL,
    clinic_uuid UUID NOT NULL,
    is_deleted BOOLEAN NOT NULL DEFAULT false
);

CREATE INDEX IF NOT EXISTS ix_ppa_patient ON patient_physician_associations(patient_uuid);
CREATE INDEX IF NOT EXISTS ix_ppa_physician ON patient_physician_associations(physician_uuid);

-- Ensure test patient exists
INSERT INTO patient_info (uuid, email_address, first_name, last_name, is_deleted)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'test@oncolife.local',
    'Test',
    'Patient',
    false
)
ON CONFLICT (uuid) DO UPDATE SET
    first_name = 'Test',
    last_name = 'Patient',
    email_address = 'test@oncolife.local';

-- Link patient to doctor
INSERT INTO patient_physician_associations (patient_uuid, physician_uuid, clinic_uuid, is_deleted)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    '22222222-2222-2222-2222-222222222222',
    '00000000-0000-0000-0000-000000000000',
    false
)
ON CONFLICT DO NOTHING;

-- Verify
SELECT 'patient_info' as table_name, count(*) as count FROM patient_info WHERE uuid = '11111111-1111-1111-1111-111111111111'
UNION ALL
SELECT 'patient_physician_associations', count(*) FROM patient_physician_associations WHERE patient_uuid = '11111111-1111-1111-1111-111111111111';
