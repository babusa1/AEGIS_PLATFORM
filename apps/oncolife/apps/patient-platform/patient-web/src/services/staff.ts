import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

export interface Staff {
  id: string;
  firstName: string;
  lastName: string;
  email: string;
  role: string;
  clinicName?: string;
  npiNumber?: string;
}

export interface StaffListResponse {
  data: Staff[];
  total: number;
  page: number;
  page_size: number;
}

export interface AddStaffRequest {
  firstName: string;
  lastName: string;
  email: string;
  role: string;
  clinicName?: string;
  npiNumber?: string;
}

export interface UpdateStaffRequest {
  firstName?: string;
  lastName?: string;
  email?: string;
  role?: string;
  clinicName?: string;
  npiNumber?: string;
}

// Mock data
const mockStaffData: Staff[] = [
  {
    id: '1',
    firstName: 'Jane',
    lastName: 'Cooper',
    email: 'jane.cooper@example.com',
    role: 'physician',
    clinicName: 'City Medical Center',
    npiNumber: '1234567890'
  },
  {
    id: '2',
    firstName: 'Esther',
    lastName: 'Howard',
    email: 'esther.howard@example.com',
    role: 'staff',
    clinicName: 'City Medical Center'
  },
  {
    id: '3',
    firstName: 'Robert',
    lastName: 'Fox',
    email: 'robert.fox@example.com',
    role: 'admin',
    clinicName: 'City Medical Center'
  },
  {
    id: '4',
    firstName: 'Dianne',
    lastName: 'Russell',
    email: 'dianne.russell@example.com',
    role: 'physician',
    clinicName: 'Downtown Clinic',
    npiNumber: '0987654321'
  },
  {
    id: '5',
    firstName: 'Albert',
    lastName: 'Flores',
    email: 'albert.flores@example.com',
    role: 'staff',
    clinicName: 'Downtown Clinic'
  },
  {
    id: '6',
    firstName: 'Ralph',
    lastName: 'Edwards',
    email: 'ralph.edwards@example.com',
    role: 'physician',
    clinicName: 'City Medical Center',
    npiNumber: '1122334455'
  },
  {
    id: '7',
    firstName: 'Cody',
    lastName: 'Fisher',
    email: 'cody.fisher@example.com',
    role: 'staff',
    clinicName: 'Downtown Clinic'
  },
  {
    id: '8',
    firstName: 'Annette',
    lastName: 'Black',
    email: 'annette.black@example.com',
    role: 'admin',
    clinicName: 'City Medical Center'
  },
  {
    id: '9',
    firstName: 'Marvin',
    lastName: 'McKinney',
    email: 'marvin.mckinney@example.com',
    role: 'physician',
    clinicName: 'Downtown Clinic',
    npiNumber: '5566778899'
  },
  {
    id: '10',
    firstName: 'Leslie',
    lastName: 'Alexander',
    email: 'leslie.alexander@example.com',
    role: 'staff',
    clinicName: 'City Medical Center'
  }
];

// Mock storage
let staffData = [...mockStaffData];
let nextId = 11;

// Simulate API delay
const delay = (ms: number) => new Promise(resolve => setTimeout(resolve, ms));

// Get staff list with mock data
const getStaff = async (page: number, search?: string, pageSize: number = 10): Promise<StaffListResponse> => {
  await delay(500); // Simulate network delay
  
  let filteredData = [...staffData];
  
  // Apply search filter
  if (search) {
    const searchLower = search.toLowerCase();
    filteredData = filteredData.filter(staff => 
      staff.firstName.toLowerCase().includes(searchLower) ||
      staff.lastName.toLowerCase().includes(searchLower) ||
      staff.email.toLowerCase().includes(searchLower)
    );
  }
  
  const total = filteredData.length;
  const startIndex = (page - 1) * pageSize;
  const endIndex = startIndex + pageSize;
  const paginatedData = filteredData.slice(startIndex, endIndex);
  
  return {
    data: paginatedData,
    total,
    page,
    page_size: pageSize
  };
};

export const useStaff = (page: number, search?: string, pageSize: number = 10) => {
  return useQuery({
    queryKey: ['staff', page, search, pageSize],
    queryFn: () => getStaff(page, search, pageSize),
  });
};

// Add staff with mock data
const addStaff = async (data: AddStaffRequest): Promise<{ message: string; staff_uuid: string }> => {
  await delay(800); // Simulate network delay
  
  const newStaff: Staff = {
    id: nextId.toString(),
    firstName: data.firstName,
    lastName: data.lastName,
    email: data.email,
    role: data.role,
    clinicName: data.clinicName,
    npiNumber: data.npiNumber
  };
  
  staffData.push(newStaff);
  nextId++;
  
  return {
    message: `${data.role} added successfully`,
    staff_uuid: newStaff.id
  };
};

export const useAddStaff = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: addStaff,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff'] });
    },
  });
};

// Update staff with mock data
const updateStaff = async ({ id, data }: { id: string; data: UpdateStaffRequest }): Promise<{ message: string }> => {
  await delay(600); // Simulate network delay
  
  const staffIndex = staffData.findIndex(staff => staff.id === id);
  
  if (staffIndex === -1) {
    throw new Error('Staff member not found');
  }
  
  // Update the staff member
  staffData[staffIndex] = {
    ...staffData[staffIndex],
    ...data
  };
  
  return {
    message: 'Staff member updated successfully'
  };
};

export const useUpdateStaff = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: updateStaff,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staff'] });
    },
  });
}; 