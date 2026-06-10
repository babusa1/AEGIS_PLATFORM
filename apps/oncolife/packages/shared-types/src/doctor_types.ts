export interface DoctorProfile {
    staffUuid: string;
    email: string;
    firstName: string;
    lastName: string;
    role: 'physician' | 'staff' | 'admin';
    npiNumber?: string;
    clinicUuid?: string;
  }
  
  export interface PatientSummary {
    patientUuid: string;
    patientName: string;
    mrn: string;
    latestSymptoms: string[];
    lastUpdated: string;
  }