import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';

export interface Patient {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  mrn: string;
  dateOfBirth: string;
  sex: 'Male' | 'Female' | 'Other';
  race: string;
  phoneNumber: string;
  physician: string;
  diseaseType: string;
  associateClinic: string;
  treatmentType: string;
}

export interface PatientsResponse {
  data: Patient[];
  total: number;
  page: number;
  totalPages: number;
}

// Mock data for development
const mockPatients: Patient[] = [
  {
    id: '1',
    firstName: 'Jane',
    lastName: 'Cooper',
    email: 'jane.cooper@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Female',
    race: 'White',
    phoneNumber: '555-0123',
    physician: 'Dr. Smith',
    diseaseType: 'Breast Cancer',
    associateClinic: 'Oncology Center',
    treatmentType: 'Chemotherapy'
  },
  {
    id: '2',
    firstName: 'Esther',
    lastName: 'Howard',
    email: 'esther.howard@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Female',
    race: 'Asian',
    phoneNumber: '555-0124',
    physician: 'Dr. Johnson',
    diseaseType: 'Lung Cancer',
    associateClinic: 'Pulmonary Clinic',
    treatmentType: 'Radiotherapy'
  },
  {
    id: '3',
    firstName: 'Robert',
    lastName: 'Fox',
    email: 'robert.fox@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Male',
    race: 'Black',
    phoneNumber: '555-0125',
    physician: 'Dr. Williams',
    diseaseType: 'Colon Cancer',
    associateClinic: 'Gastroenterology',
    treatmentType: 'Surgery'
  },
  {
    id: '4',
    firstName: 'Tim',
    lastName: 'Jennings',
    email: 'tim.jennings@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Male',
    race: 'Hispanic',
    phoneNumber: '555-0126',
    physician: 'Dr. Brown',
    diseaseType: 'Prostate Cancer',
    associateClinic: 'Urology Center',
    treatmentType: 'Hormone Therapy'
  },
  {
    id: '5',
    firstName: 'Debbie',
    lastName: 'Baker',
    email: 'debbie.baker@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Female',
    race: 'White',
    phoneNumber: '555-0127',
    physician: 'Dr. Davis',
    diseaseType: 'Ovarian Cancer',
    associateClinic: 'Gynecology',
    treatmentType: 'Chemotherapy'
  },
  {
    id: '6',
    firstName: 'Waqas',
    lastName: 'Hafeez',
    email: 'waqas@gmail.com',
    mrn: '21',
    dateOfBirth: '17-01-2001',
    sex: 'Male',
    race: 'Other',
    phoneNumber: '03097273238',
    physician: 'Dr. Wilson',
    diseaseType: 'Brain Tumor',
    associateClinic: 'Neurology',
    treatmentType: 'Surgery'
  },
  {
    id: '7',
    firstName: 'Sarah',
    lastName: 'Miller',
    email: 'sarah.miller@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Female',
    race: 'Asian',
    phoneNumber: '555-0128',
    physician: 'Dr. Taylor',
    diseaseType: 'Melanoma',
    associateClinic: 'Dermatology',
    treatmentType: 'Immunotherapy'
  },
  {
    id: '8',
    firstName: 'Michael',
    lastName: 'Anderson',
    email: 'michael.anderson@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Male',
    race: 'White',
    phoneNumber: '555-0129',
    physician: 'Dr. Garcia',
    diseaseType: 'Leukemia',
    associateClinic: 'Hematology',
    treatmentType: 'Bone Marrow Transplant'
  },
  {
    id: '9',
    firstName: 'Lisa',
    lastName: 'Thompson',
    email: 'lisa.thompson@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Female',
    race: 'Black',
    phoneNumber: '555-0130',
    physician: 'Dr. Martinez',
    diseaseType: 'Pancreatic Cancer',
    associateClinic: 'Oncology Center',
    treatmentType: 'Chemotherapy'
  },
  {
    id: '10',
    firstName: 'David',
    lastName: 'Wilson',
    email: 'david.wilson@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Male',
    race: 'Hispanic',
    phoneNumber: '555-0131',
    physician: 'Dr. Rodriguez',
    diseaseType: 'Liver Cancer',
    associateClinic: 'Hepatology',
    treatmentType: 'Targeted Therapy'
  },
  {
    id: '11',
    firstName: 'Emily',
    lastName: 'Davis',
    email: 'emily.davis@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Female',
    race: 'White',
    phoneNumber: '555-0132',
    physician: 'Dr. Lee',
    diseaseType: 'Thyroid Cancer',
    associateClinic: 'Endocrinology',
    treatmentType: 'Radioactive Iodine'
  },
  {
    id: '12',
    firstName: 'James',
    lastName: 'Johnson',
    email: 'james.johnson@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Male',
    race: 'Black',
    phoneNumber: '555-0133',
    physician: 'Dr. White',
    diseaseType: 'Bladder Cancer',
    associateClinic: 'Urology Center',
    treatmentType: 'BCG Therapy'
  },
  {
    id: '13',
    firstName: 'Maria',
    lastName: 'Garcia',
    email: 'maria.garcia@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Female',
    race: 'Hispanic',
    phoneNumber: '555-0134',
    physician: 'Dr. Chen',
    diseaseType: 'Cervical Cancer',
    associateClinic: 'Gynecology',
    treatmentType: 'Radiation Therapy'
  },
  {
    id: '14',
    firstName: 'John',
    lastName: 'Brown',
    email: 'john.brown@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Male',
    race: 'White',
    phoneNumber: '555-0135',
    physician: 'Dr. Kim',
    diseaseType: 'Kidney Cancer',
    associateClinic: 'Nephrology',
    treatmentType: 'Targeted Therapy'
  },
  {
    id: '15',
    firstName: 'Anna',
    lastName: 'Taylor',
    email: 'anna.taylor@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Female',
    race: 'Asian',
    phoneNumber: '555-0136',
    physician: 'Dr. Patel',
    diseaseType: 'Ovarian Cancer',
    associateClinic: 'Gynecology',
    treatmentType: 'Chemotherapy'
  },
  {
    id: '16',
    firstName: 'William',
    lastName: 'Martinez',
    email: 'william.martinez@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Male',
    race: 'Hispanic',
    phoneNumber: '555-0137',
    physician: 'Dr. Singh',
    diseaseType: 'Testicular Cancer',
    associateClinic: 'Urology Center',
    treatmentType: 'Surgery'
  },
  {
    id: '17',
    firstName: 'Sophia',
    lastName: 'Lee',
    email: 'sophia.lee@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Female',
    race: 'Asian',
    phoneNumber: '555-0138',
    physician: 'Dr. Wang',
    diseaseType: 'Endometrial Cancer',
    associateClinic: 'Gynecology',
    treatmentType: 'Hormone Therapy'
  },
  {
    id: '18',
    firstName: 'Daniel',
    lastName: 'Clark',
    email: 'daniel.clark@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Male',
    race: 'White',
    phoneNumber: '555-0139',
    physician: 'Dr. Anderson',
    diseaseType: 'Esophageal Cancer',
    associateClinic: 'Gastroenterology',
    treatmentType: 'Chemoradiation'
  },
  {
    id: '19',
    firstName: 'Isabella',
    lastName: 'Rodriguez',
    email: 'isabella.rodriguez@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Female',
    race: 'Hispanic',
    phoneNumber: '555-0140',
    physician: 'Dr. Thompson',
    diseaseType: 'Vulvar Cancer',
    associateClinic: 'Gynecology',
    treatmentType: 'Surgery'
  },
  {
    id: '20',
    firstName: 'Christopher',
    lastName: 'Lewis',
    email: 'christopher.lewis@example.com',
    mrn: 'Test',
    dateOfBirth: 'January 1, 2001',
    sex: 'Male',
    race: 'Black',
    phoneNumber: '555-0141',
    physician: 'Dr. Harris',
    diseaseType: 'Penile Cancer',
    associateClinic: 'Urology Center',
    treatmentType: 'Surgery'
  }
];

const fetchPatients = async (
  page: number = 1, 
  search: string = '',
  rowsPerPage: number = 10
): Promise<PatientsResponse> => {
  // For now, return mock data
  // In production, this would be:
  // );
  // return response.data;
  
  // Simulate API delay
  await new Promise(resolve => setTimeout(resolve, 300));
  
  let filteredData = mockPatients;
  
  // Apply search filter
  if (search) {
    filteredData = mockPatients.filter(patient => 
      patient.firstName.toLowerCase().includes(search.toLowerCase()) ||
      patient.lastName.toLowerCase().includes(search.toLowerCase()) ||
      patient.email.toLowerCase().includes(search.toLowerCase()) ||
      patient.mrn.toLowerCase().includes(search.toLowerCase())
    );
  }
  
  const startIndex = (page - 1) * rowsPerPage;
  const endIndex = startIndex + rowsPerPage;
  const paginatedData = filteredData.slice(startIndex, endIndex);
  
  return {
    data: paginatedData,
    total: filteredData.length,
    page,
    totalPages: Math.ceil(filteredData.length / rowsPerPage)
  };
};

export const usePatients = (
  page: number = 1, 
  search: string = '',
  rowsPerPage: number = 10
) => {
  return useQuery({
    queryKey: ['patients', page, search, rowsPerPage],
    queryFn: () => fetchPatients(page, search, rowsPerPage),
  });
};

// Fetch individual patient details
const fetchPatientDetails = async (patientId: string): Promise<Patient> => {
  // For now, return mock data
  // In production, this would be:
  // );
  // return response.data;
  
  await new Promise(resolve => setTimeout(resolve, 200));
  
  const patient = mockPatients.find(p => p.id === patientId);
  if (!patient) {
    throw new Error('Patient not found');
  }
  
  return patient;
};

export const usePatientDetails = (patientId: string) => {
  return useQuery({
    queryKey: ['patientDetails', patientId],
    queryFn: () => fetchPatientDetails(patientId),
    enabled: !!patientId,
  });
};

// Add patient mutation
const addPatient = async (patientData: Omit<Patient, 'id'>): Promise<Patient> => {
  // For now, return mock data
  // In production, this would be:
  //   patientData
  // );
  // return response.data;
  
  await new Promise(resolve => setTimeout(resolve, 500));
  
  const newPatient: Patient = {
    ...patientData,
    id: (mockPatients.length + 1).toString()
  };
  
  mockPatients.push(newPatient);
  return newPatient;
};

export const useAddPatient = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: addPatient,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
    },
  });
};

// Update patient mutation
const updatePatient = async ({ id, ...patientData }: Patient): Promise<Patient> => {
  // For now, return mock data
  // In production, this would be:
  //   patientData
  // );
  // return response.data;
  
  await new Promise(resolve => setTimeout(resolve, 500));
  
  const patientIndex = mockPatients.findIndex(p => p.id === id);
  if (patientIndex === -1) {
    throw new Error('Patient not found');
  }
  
  const updatedPatient: Patient = { id, ...patientData };
  mockPatients[patientIndex] = updatedPatient;
  return updatedPatient;
};

export const useUpdatePatient = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: updatePatient,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['patients'] });
    },
  });
}; 