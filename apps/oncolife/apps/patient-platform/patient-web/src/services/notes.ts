import { apiClient } from "../utils/apiClient";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { API_CONFIG } from "../config/api";

export const fetchNotes = async (year: number, month: number) => {
  const response = await apiClient.get(API_CONFIG.ENDPOINTS.DIARY.BY_MONTH(year, month));
  // Wrap the array in { data: [] } to match component expectations
  return { data: response.data || [] };
};

export const useFetchNotes = (year: number, month: number) => {
  return useQuery({
    queryKey: ['notes', year, month],
    queryFn: () => fetchNotes(year, month),
    enabled: !!year && !!month,
  });
};

export const saveNewNotes = async (params: { content: string, title: string, marked_for_doctor?: boolean }) => {
  const body = {
    diary_entry: params.content,
    title: params.title,
    marked_for_doctor: params.marked_for_doctor ?? false,
  };
  const response = await apiClient.post(API_CONFIG.ENDPOINTS.DIARY.CREATE, body);
  return response.data;
};

export const useSaveNewNotes = (year: number, month: number) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: saveNewNotes,
    onSuccess: () => {
      // Invalidate and refetch notes for the current year/month
      queryClient.invalidateQueries({ queryKey: ['notes', year, month] });
    },
  });
};

export const updateNote = async (params: {noteId: string, diary_entry: string, title: string }) => {
  const body = {
    diary_entry: params.diary_entry,
    title: params.title,
  };
  const response = await apiClient.patch(API_CONFIG.ENDPOINTS.DIARY.UPDATE(params.noteId), body);
  return response.data;
};

export const useUpdateNote = (year: number, month: number) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: updateNote,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', year, month] });
    },
  });
};  

export const deleteNote = async (params: {noteId: string}) => {
  const response = await apiClient.patch(API_CONFIG.ENDPOINTS.DIARY.DELETE(params.noteId));
  return response.data;
};

export const useDeleteNote = (year: number, month: number) => {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteNote,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notes', year, month] });
    },
  });
};  