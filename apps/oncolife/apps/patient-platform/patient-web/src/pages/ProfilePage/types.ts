export interface ProfileData {
  first_name: string;
  last_name: string;
  email_address: string;
  phone_number: string | null;
  date_of_birth: string | null;
  chemotherapy_day?: string;
  reminder_time: string | null;
  doctor_name: string | null;
  clinic_name: string | null;
  // Treatment Info (from oncology profile)
  diagnosis: string | null;
  treatment_type: string | null;
  chemo_plan_name: string | null;
  chemo_start_date: string | null;
  chemo_end_date: string | null;
  current_cycle: number | null;
  total_cycles: number | null;
  last_chemo_date: string | null;
  next_physician_visit: string | null;
  // Emergency contact
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
}

export interface ProfileFormData {
  first_name: string;
  last_name: string;
  email_address: string;
  phone_number: string | null;
  date_of_birth: string | null;
  chemotherapy_day?: string;
  reminder_time: string | null;
  doctor_name: string | null;
  clinic_name: string | null;
  // Treatment Info (from oncology profile)
  diagnosis: string | null;
  treatment_type: string | null;
  chemo_plan_name?: string | null;
  chemo_start_date?: string | null;
  chemo_end_date?: string | null;
  current_cycle?: number | null;
  total_cycles?: number | null;
  last_chemo_date: string | null;
  next_physician_visit: string | null;
  // Emergency contact
  emergency_contact_name: string | null;
  emergency_contact_phone: string | null;
}

export interface ProfilePageProps {
  // Add any props if needed
}

// Chemo timeline types
export interface ChemoDateItem {
  id: number;
  chemo_date: string;
  created_at?: string;
}