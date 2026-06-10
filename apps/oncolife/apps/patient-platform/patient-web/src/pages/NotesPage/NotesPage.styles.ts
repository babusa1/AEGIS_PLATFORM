/**
 * OncoLife Ruby - Notes/Diary Page Styles
 * Lovable-inspired design with warm colors, left-border cards, For Doctor badge
 */

import styled, { css } from "styled-components";

// Warm Lovable-style colors
const colors = {
  background: '#FAF8F5',
  paper: '#FFFFFF',
  primary: '#4F7CAC',
  primaryLight: '#7BA3C9',
  primaryDark: '#3B5F8A',
  foreground: '#3D3A35',
  muted: '#8A847A',
  border: '#E8E4DD',
  
  // For Doctor badge
  doctor: '#4F7CAC',
  doctorBg: 'rgba(79, 124, 172, 0.08)',
  doctorBorder: 'rgba(79, 124, 172, 0.25)',
  
  // Delete/danger
  danger: '#DC2626',
  dangerBg: '#FEE2E2',
};

export const NotesPageContainer = styled.div`
  flex: 1;
  background-color: ${colors.background};
  display: flex;
  flex-direction: row;
  overflow: hidden;
  height: calc(100vh - 64px);
  
  @media (max-width: 768px) {
    flex-direction: column;
    height: auto;
    min-height: calc(100vh - 120px);
  }
`;

export const NotesSidebarContainer = styled.div`
  width: 320px;
  background: ${colors.paper};
  border-right: 1px solid ${colors.border};
  display: flex;
  flex-direction: column;
  overflow: hidden;
  
  @media (max-width: 992px) {
    width: 280px;
  }
  
  @media (max-width: 768px) {
    width: 100%;
    max-height: 300px;
    border-right: none;
    border-bottom: 1px solid ${colors.border};
  }
`;

export const SidebarHeader = styled.div`
  padding: 1rem;
  border-bottom: 1px solid ${colors.border};
`;

export const SidebarTitle = styled.h3`
  font-family: 'Fraunces', Georgia, serif;
  font-size: 1.125rem;
  font-weight: 600;
  color: ${colors.foreground};
  margin: 0 0 12px 0;
  display: flex;
  align-items: center;
  gap: 8px;
`;

export const SearchInput = styled.div`
  display: flex;
  align-items: center;
  background: ${colors.background};
  border-radius: 12px;
  padding: 10px 14px;
  border: 1px solid ${colors.border};
  transition: all 0.2s ease;
  
  &:focus-within {
    border-color: ${colors.primary};
    background: ${colors.paper};
    box-shadow: 0 0 0 3px rgba(79, 124, 172, 0.1);
  }
  
  svg {
    color: ${colors.muted};
    margin-right: 10px;
    flex-shrink: 0;
  }
  
  input {
    border: none;
    outline: none;
    background: transparent;
    font-size: 0.875rem;
    color: ${colors.foreground};
    width: 100%;
    font-family: 'DM Sans', sans-serif;
    
    &::placeholder {
      color: ${colors.muted};
    }
  }
`;

export const DateNavigation = styled.div`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid ${colors.border};
  background: ${colors.paper};
`;

export const NavButton = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: ${colors.background};
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: ${colors.muted};
  
  &:hover {
    background: rgba(79, 124, 172, 0.1);
    color: ${colors.primary};
  }
  
  svg {
    width: 16px;
    height: 16px;
  }
`;

export const CurrentMonth = styled.span`
  font-size: 0.9375rem;
  font-weight: 600;
  color: ${colors.foreground};
  min-width: 120px;
  text-align: center;
`;

export const NotesListContainer = styled.div`
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  
  @media (max-width: 768px) {
    max-height: 200px;
  }
`;

// Note item card with left border and For Doctor styling
export const NoteItemCard = styled.div<{ $isSelected?: boolean; $isForDoctor?: boolean }>`
  padding: 14px 16px;
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.25s ease;
  margin-bottom: 8px;
  background: ${props => props.$isSelected ? 'rgba(79, 124, 172, 0.08)' : colors.paper};
  border: 1px solid ${props => props.$isSelected ? colors.primary : colors.border};
  box-shadow: 0 2px 12px -4px rgba(0, 0, 0, 0.06);
  
  ${props => props.$isForDoctor && css`
    border-left: 4px solid ${colors.primary};
    background: ${props.$isSelected ? 'rgba(79, 124, 172, 0.12)' : colors.doctorBg};
  `}
  
  &:hover {
    box-shadow: 0 4px 16px -4px rgba(0, 0, 0, 0.1);
    transform: translateY(-1px);
  }
`;

export const NoteItemHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
`;

export const NoteItemTitle = styled.h4`
  font-size: 0.9375rem;
  font-weight: 600;
  color: ${colors.foreground};
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
`;

// "For Doctor" badge - Lovable style
export const ForDoctorBadge = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 8px;
  background: ${colors.doctorBg};
  color: ${colors.doctor};
  border: 1px solid ${colors.doctorBorder};
  border-radius: 9999px;
  font-size: 0.6875rem;
  font-weight: 600;
  white-space: nowrap;
  
  svg {
    width: 10px;
    height: 10px;
  }
`;

export const NoteItemDate = styled.span`
  font-size: 0.75rem;
  color: ${colors.muted};
  display: flex;
  align-items: center;
  gap: 4px;
`;

export const NoteItemPreview = styled.p`
  font-size: 0.8125rem;
  color: ${colors.muted};
  margin: 6px 0 0 0;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  line-height: 1.5;
`;

export const AddNoteButton = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: calc(100% - 16px);
  margin: 8px;
  padding: 12px;
  background: ${colors.primary};
  color: white;
  border: none;
  border-radius: 12px;
  font-weight: 600;
  font-size: 0.875rem;
  cursor: pointer;
  transition: all 0.25s ease;
  box-shadow: 0 4px 12px rgba(79, 124, 172, 0.3);
  
  &:hover {
    background: ${colors.primaryDark};
    transform: translateY(-1px);
    box-shadow: 0 6px 16px rgba(79, 124, 172, 0.4);
  }
`;

export const NoteEditorContainer = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  background: ${colors.paper};
  overflow: hidden;
  
  @media (max-width: 768px) {
    min-height: 400px;
  }
`;

export const EditorHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid ${colors.border};
  background: ${colors.background};
  
  @media (max-width: 576px) {
    flex-direction: column;
    gap: 12px;
    align-items: flex-start;
  }
`;

export const EditorTitleRow = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  flex: 1;
`;

export const EditorTitle = styled.input`
  font-family: 'Fraunces', Georgia, serif;
  font-size: 1.25rem;
  font-weight: 600;
  color: ${colors.foreground};
  border: none;
  outline: none;
  background: transparent;
  flex: 1;
  padding: 8px 12px;
  border-radius: 8px;
  transition: all 0.2s ease;
  
  &:focus {
    background: ${colors.paper};
    box-shadow: 0 0 0 3px rgba(79, 124, 172, 0.1);
  }
  
  &::placeholder {
    color: ${colors.muted};
  }
`;

export const EditorActions = styled.div`
  display: flex;
  gap: 8px;
  
  @media (max-width: 576px) {
    width: 100%;
    justify-content: flex-end;
  }
`;

export const ActionButton = styled.button<{ $variant?: 'primary' | 'danger' | 'doctor' | 'default' }>`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  
  ${props => {
    switch (props.$variant) {
      case 'primary':
        return css`
          background: ${colors.primary};
          color: white;
          border: none;
          
          &:hover {
            background: ${colors.primaryDark};
            transform: translateY(-1px);
          }
        `;
      case 'danger':
        return css`
          background: transparent;
          color: ${colors.danger};
          border: 1px solid ${colors.danger}30;
          
          &:hover {
            background: ${colors.dangerBg};
          }
        `;
      case 'doctor':
        return css`
          background: ${colors.doctorBg};
          color: ${colors.doctor};
          border: 1px solid ${colors.doctorBorder};
          
          &:hover {
            background: rgba(79, 124, 172, 0.15);
          }
        `;
      default:
        return css`
          background: transparent;
          color: ${colors.muted};
          border: 1px solid ${colors.border};
          
          &:hover {
            background: ${colors.background};
          }
        `;
    }
  }}
  
  svg {
    width: 16px;
    height: 16px;
  }
`;

export const EditorContent = styled.div`
  flex: 1;
  padding: 20px;
  overflow-y: auto;
  background: ${colors.paper};
`;

export const EditorTextarea = styled.textarea`
  width: 100%;
  height: 100%;
  min-height: 300px;
  border: none;
  outline: none;
  background: transparent;
  font-family: 'DM Sans', sans-serif;
  font-size: 1rem;
  line-height: 1.7;
  color: ${colors.foreground};
  resize: none;
  
  &::placeholder {
    color: ${colors.muted};
  }
`;

export const EmptyEditorState = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: ${colors.muted};
  text-align: center;
  padding: 40px;
  background: ${colors.background};
  
  .icon {
    font-size: 3rem;
    margin-bottom: 16px;
  }
  
  h3 {
    font-family: 'Fraunces', Georgia, serif;
    font-size: 1.125rem;
    font-weight: 600;
    color: ${colors.foreground};
    margin: 0 0 8px 0;
  }
  
  p {
    font-size: 0.9375rem;
    margin: 0;
    max-width: 300px;
    line-height: 1.6;
  }
`;
