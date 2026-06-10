import React, { useState } from 'react';
import styled from 'styled-components';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../../../utils/apiClient';
import type { ChemoDateItem } from '../types';

// =============================================================================
// Styled Components
// =============================================================================

const TimelineContainer = styled.div`
  padding: 1rem 0;
`;

const TimelineHeader = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
`;

const TimelineTitle = styled.h3`
  color: #1a237e;
  font-size: 1.2rem;
  margin: 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  
  &::before {
    content: '📅';
  }
`;

const AddButton = styled.button`
  background: linear-gradient(135deg, #1a237e 0%, #3949ab 100%);
  color: white;
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  cursor: pointer;
  font-size: 0.9rem;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: transform 0.2s, box-shadow 0.2s;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(26, 35, 126, 0.3);
  }
  
  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }
`;

const DateInputContainer = styled.div`
  background: linear-gradient(135deg, #e8eaf6 0%, #c5cae9 100%);
  border-radius: 12px;
  padding: 1rem;
  margin-bottom: 1.5rem;
  display: flex;
  gap: 1rem;
  align-items: center;
  flex-wrap: wrap;
`;

const DateInput = styled.input`
  padding: 10px 14px;
  border: 2px solid #c5cae9;
  border-radius: 8px;
  font-size: 1rem;
  outline: none;
  
  &:focus {
    border-color: #1a237e;
  }
`;

const ActionButton = styled.button<{ variant?: 'primary' | 'secondary' }>`
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
  
  ${props => props.variant === 'primary' ? `
    background: #4caf50;
    color: white;
    border: none;
    
    &:hover {
      background: #43a047;
    }
  ` : `
    background: transparent;
    color: #666;
    border: 1px solid #ccc;
    
    &:hover {
      background: #f5f5f5;
    }
  `}
  
  &:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
`;

const TimelineContent = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0;
`;

const TimelineSection = styled.div`
  margin-bottom: 1.5rem;
`;

const SectionTitle = styled.h4`
  color: #666;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin: 0 0 0.75rem 0;
`;

const TimelineList = styled.div`
  position: relative;
  padding-left: 24px;
  
  &::before {
    content: '';
    position: absolute;
    left: 8px;
    top: 0;
    bottom: 0;
    width: 2px;
    background: linear-gradient(to bottom, #4caf50, #c8e6c9);
  }
`;

const TimelineItem = styled.div<{ isPast?: boolean; isUpcoming?: boolean }>`
  position: relative;
  padding: 12px 16px;
  margin-bottom: 8px;
  background: ${props => 
    props.isUpcoming 
      ? 'linear-gradient(135deg, #e3f2fd 0%, #bbdefb 100%)' 
      : props.isPast 
        ? 'linear-gradient(135deg, #f5f5f5 0%, #eeeeee 100%)' 
        : 'white'};
  border-radius: 8px;
  border: 1px solid ${props => props.isUpcoming ? '#64b5f6' : '#e0e0e0'};
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  &::before {
    content: '';
    position: absolute;
    left: -20px;
    top: 50%;
    transform: translateY(-50%);
    width: 12px;
    height: 12px;
    border-radius: 50%;
    background: ${props => props.isUpcoming ? '#2196f3' : props.isPast ? '#9e9e9e' : '#4caf50'};
    border: 2px solid white;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  }
`;

const DateText = styled.span<{ isPast?: boolean }>`
  font-size: 1rem;
  font-weight: 500;
  color: ${props => props.isPast ? '#9e9e9e' : '#333'};
`;

const DateLabel = styled.span<{ isUpcoming?: boolean }>`
  font-size: 0.8rem;
  color: ${props => props.isUpcoming ? '#1976d2' : '#666'};
  background: ${props => props.isUpcoming ? '#e3f2fd' : '#f5f5f5'};
  padding: 4px 8px;
  border-radius: 4px;
`;

const DeleteButton = styled.button`
  background: transparent;
  border: none;
  color: #f44336;
  cursor: pointer;
  padding: 4px 8px;
  font-size: 0.8rem;
  border-radius: 4px;
  opacity: 0.6;
  transition: all 0.2s;
  
  &:hover {
    opacity: 1;
    background: #ffebee;
  }
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 2rem;
  color: #666;
  font-style: italic;
`;

const LoadingSpinner = styled.div`
  text-align: center;
  padding: 2rem;
  color: #666;
`;

// =============================================================================
// API Functions
// =============================================================================

const fetchUpcomingChemo = async (): Promise<ChemoDateItem[]> => {
  const response = await apiClient.get('/chemo/upcoming');
  return response.data;
};

const fetchChemoHistory = async (): Promise<ChemoDateItem[]> => {
  const response = await apiClient.get('/chemo/history?limit=10');
  return response.data;
};

const logChemoDate = async (chemoDate: string): Promise<void> => {
  await apiClient.post('/chemo/log', { chemo_date: chemoDate });
};

const deleteChemoDate = async (chemoDate: string): Promise<void> => {
  await apiClient.delete(`/chemo/${chemoDate}`);
};

// =============================================================================
// Helper Functions
// =============================================================================

const formatDate = (dateString: string): string => {
  const date = new Date(dateString);
  return date.toLocaleDateString('en-US', {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
};

const getDaysUntil = (dateString: string): number => {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const targetDate = new Date(dateString);
  const diffTime = targetDate.getTime() - today.getTime();
  return Math.ceil(diffTime / (1000 * 60 * 60 * 24));
};

const getDaysLabel = (dateString: string): string => {
  const days = getDaysUntil(dateString);
  if (days === 0) return 'Today';
  if (days === 1) return 'Tomorrow';
  if (days < 0) return `${Math.abs(days)} days ago`;
  return `In ${days} days`;
};

// =============================================================================
// Component
// =============================================================================

const ChemoTimeline: React.FC = () => {
  const [showAddForm, setShowAddForm] = useState(false);
  const [newDate, setNewDate] = useState('');
  const queryClient = useQueryClient();

  // Queries
  const { data: upcomingDates, isLoading: isLoadingUpcoming } = useQuery({
    queryKey: ['chemo', 'upcoming'],
    queryFn: fetchUpcomingChemo,
  });

  const { data: pastDates, isLoading: isLoadingHistory } = useQuery({
    queryKey: ['chemo', 'history'],
    queryFn: fetchChemoHistory,
  });

  // Mutations
  const addChemoMutation = useMutation({
    mutationFn: logChemoDate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chemo'] });
      setShowAddForm(false);
      setNewDate('');
    },
  });

  const deleteChemoMutation = useMutation({
    mutationFn: deleteChemoDate,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['chemo'] });
    },
  });

  const handleAddDate = () => {
    if (newDate) {
      addChemoMutation.mutate(newDate);
    }
  };

  const handleDeleteDate = (dateStr: string) => {
    if (window.confirm('Are you sure you want to delete this chemotherapy date?')) {
      deleteChemoMutation.mutate(dateStr);
    }
  };

  const isLoading = isLoadingUpcoming || isLoadingHistory;

  // Filter past dates (not in upcoming)
  const filteredPastDates = pastDates?.filter(item => {
    const days = getDaysUntil(item.chemo_date);
    return days < 0;
  }).slice(0, 5) || [];

  return (
    <TimelineContainer>
      <TimelineHeader>
        <TimelineTitle>Chemotherapy Timeline</TimelineTitle>
        <AddButton onClick={() => setShowAddForm(!showAddForm)}>
          {showAddForm ? '✕ Cancel' : '+ Add Date'}
        </AddButton>
      </TimelineHeader>

      {showAddForm && (
        <DateInputContainer>
          <DateInput
            type="date"
            value={newDate}
            onChange={(e) => setNewDate(e.target.value)}
            placeholder="Select date"
          />
          <ActionButton
            variant="primary"
            onClick={handleAddDate}
            disabled={!newDate || addChemoMutation.isPending}
          >
            {addChemoMutation.isPending ? '⏳ Adding...' : '✓ Add Date'}
          </ActionButton>
          <ActionButton
            variant="secondary"
            onClick={() => {
              setShowAddForm(false);
              setNewDate('');
            }}
          >
            Cancel
          </ActionButton>
        </DateInputContainer>
      )}

      {isLoading ? (
        <LoadingSpinner>⏳ Loading timeline...</LoadingSpinner>
      ) : (
        <TimelineContent>
          {/* Upcoming Dates */}
          <TimelineSection>
            <SectionTitle>📆 Upcoming Sessions</SectionTitle>
            {upcomingDates && upcomingDates.length > 0 ? (
              <TimelineList>
                {upcomingDates.map((item) => (
                  <TimelineItem key={item.id} isUpcoming>
                    <div>
                      <DateText>{formatDate(item.chemo_date)}</DateText>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <DateLabel isUpcoming>{getDaysLabel(item.chemo_date)}</DateLabel>
                      <DeleteButton onClick={() => handleDeleteDate(item.chemo_date)}>
                        🗑️
                      </DeleteButton>
                    </div>
                  </TimelineItem>
                ))}
              </TimelineList>
            ) : (
              <EmptyState>No upcoming sessions scheduled</EmptyState>
            )}
          </TimelineSection>

          {/* Past Dates */}
          <TimelineSection>
            <SectionTitle>📋 Recent Sessions</SectionTitle>
            {filteredPastDates.length > 0 ? (
              <TimelineList>
                {filteredPastDates.map((item) => (
                  <TimelineItem key={item.id} isPast>
                    <div>
                      <DateText isPast>{formatDate(item.chemo_date)}</DateText>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <DateLabel>{getDaysLabel(item.chemo_date)}</DateLabel>
                      <DeleteButton onClick={() => handleDeleteDate(item.chemo_date)}>
                        🗑️
                      </DeleteButton>
                    </div>
                  </TimelineItem>
                ))}
              </TimelineList>
            ) : (
              <EmptyState>No past sessions recorded</EmptyState>
            )}
          </TimelineSection>
        </TimelineContent>
      )}
    </TimelineContainer>
  );
};

export default ChemoTimeline;
