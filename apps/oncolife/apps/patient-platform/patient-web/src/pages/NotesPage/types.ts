export interface Note {
  id?: string;
  title: string;
  diary_entry: string;
  created_at: string;
  entry_uuid?: string;
  marked_for_doctor?: boolean;
  is_deleted?: boolean;
} 

export interface NoteResponse {
  data: Note[];
  success: boolean;
  error: string;
  status: number;
}