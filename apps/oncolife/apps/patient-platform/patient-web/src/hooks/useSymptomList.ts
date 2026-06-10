import { useState, useEffect, useCallback } from 'react';

const SYMPTOM_LIST_KEY = 'symptom_list';

export const useSymptomList = () => {
  const [symptomList, setSymptomList] = useState<string[]>([]);

  // Initialize symptom list from localStorage on mount
  useEffect(() => {
    const storedSymptoms = localStorage.getItem(SYMPTOM_LIST_KEY);
    if (storedSymptoms) {
      try {
        const parsed = JSON.parse(storedSymptoms);
        if (Array.isArray(parsed)) {
          setSymptomList(parsed);
        }
      } catch (error) {
        console.error('Failed to parse stored symptom list:', error);
        localStorage.removeItem(SYMPTOM_LIST_KEY);
      }
    }
  }, []);

  // Update localStorage and state
  const updateSymptomList = useCallback((newSymptoms: string[]) => {
    setSymptomList(newSymptoms);
    localStorage.setItem(SYMPTOM_LIST_KEY, JSON.stringify(newSymptoms));
  }, []);

  // Add new symptoms to the existing list
  const addSymptoms = useCallback((newSymptoms: string[]) => {
    const updatedSymptoms = [...new Set([...symptomList, ...newSymptoms])];
    updateSymptomList(updatedSymptoms);
  }, [symptomList, updateSymptomList]);

  // Reset symptom list to empty array
  const resetSymptomList = useCallback(() => {
    updateSymptomList([]);
  }, [updateSymptomList]);

  // Get current symptom list
  const getSymptomList = useCallback(() => {
    return symptomList;
  }, [symptomList]);

  return {
    symptomList,
    updateSymptomList,
    addSymptoms,
    resetSymptomList,
    getSymptomList,
  };
}; 