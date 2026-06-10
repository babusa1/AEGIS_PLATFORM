import styled from 'styled-components';

interface NoteItemContainerProps {
  isSelected: boolean;
}

export const NoteItemContainer = styled.div<NoteItemContainerProps>`
  padding: 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid ${props => props.isSelected ? '#2196f3' : '#e9ecef'};
  background-color: ${props => props.isSelected ? '#e3f2fd' : '#ffffff'};
  margin-bottom: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: space-between;

  &:hover {
    background-color: ${props => props.isSelected ? '#e3f2fd' : '#f8f9fa'};
    border-color: ${props => props.isSelected ? '#2196f3' : '#dee2e6'};
  }
`;

export const NoteTitle = styled.h6`
  font-weight: 600;
  color: #495057;
  margin-bottom: 0.5rem;
  font-size: 1rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

export const NotePreview = styled.p`
  color: #6c757d;
  font-size: 0.85rem;
  margin-bottom: 0;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`; 