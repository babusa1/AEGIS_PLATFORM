export interface PatientProfile {
    uuid: string;
    email: string;
    firstName: string;
    lastName: string;
    phoneNumber?: string;
    dateOfBirth?: string;
    mrn?: string;
  }
  
  export interface Conversation {
    uuid: string;
    patientUuid: string;
    conversationState: string;
    symptomList?: string[];
    severityList?: Record<string, number>;
    longerSummary?: string;
    bulletedSummary?: string;
    overallFeeling?: string;
    createdAt: string;
    updatedAt: string;
  }