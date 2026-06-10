/**
 * OncoLife Ruby - Summaries Page Styles
 * Lovable-inspired design with warm colors, left-border cards, natural language
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
  
  // Severity colors
  severe: '#DC2626',
  severeBg: '#FEE2E2',
  moderate: '#F59E0B',
  moderateBg: '#FEF3C7',
  moderateText: '#92400E',
  mild: '#22C55E',
  mildBg: '#DCFCE7',
  mildText: '#166534',
};

export const PageContainer = styled.div`
  flex: 1;
  padding: 1.5rem;
  overflow: auto;
  background: ${colors.background};
  
  @media (min-width: 600px) {
    padding: 2rem;
  }
`;

export const ContentWrapper = styled.div`
  max-width: 900px;
  margin: 0 auto;
`;

export const PageHeader = styled.div`
  margin-bottom: 1.5rem;
  animation: fadeInDown 0.4s ease forwards;
  
  @media (min-width: 600px) {
    margin-bottom: 2rem;
  }
`;

export const PageTitle = styled.h1`
  font-family: 'Fraunces', Georgia, serif;
  font-size: 1.5rem;
  font-weight: 600;
  color: ${colors.foreground};
  margin: 0 0 0.5rem 0;
  
  @media (min-width: 600px) {
    font-size: 1.75rem;
  }
`;

export const PageSubtitle = styled.p`
  font-size: 0.875rem;
  color: ${colors.muted};
  margin: 0;
  
  @media (min-width: 600px) {
    font-size: 1rem;
  }
`;

// Search and Filters row
export const FiltersRow = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
  
  @media (min-width: 600px) {
    flex-direction: row;
    align-items: center;
  }
`;

export const SearchInputWrapper = styled.div`
  position: relative;
  flex: 1;
  
  input {
    width: 100%;
    padding: 0.75rem 1rem 0.75rem 2.5rem;
    background: ${colors.paper};
    border: 1px solid ${colors.border};
    border-radius: 12px;
    font-size: 0.875rem;
    color: ${colors.foreground};
    transition: all 0.2s ease;
    
    &::placeholder {
      color: ${colors.muted};
    }
    
    &:focus {
      outline: none;
      border-color: ${colors.primary};
      box-shadow: 0 0 0 3px rgba(79, 124, 172, 0.1);
    }
  }
  
  svg {
    position: absolute;
    left: 0.875rem;
    top: 50%;
    transform: translateY(-50%);
    width: 16px;
    height: 16px;
    color: ${colors.muted};
    pointer-events: none;
  }
`;

export const FilterButton = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0.75rem;
  background: ${colors.paper};
  border: 1px solid ${colors.border};
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: ${colors.muted};
  
  &:hover {
    border-color: ${colors.primary};
    color: ${colors.primary};
  }
  
  svg {
    width: 18px;
    height: 18px;
  }
`;

export const SelectWrapper = styled.div`
  position: relative;
  min-width: 160px;
  display: flex;
  align-items: center;
  
  select {
    width: 100%;
    padding: 0.75rem 2.25rem 0.75rem 2.25rem;
    background: ${colors.paper};
    border: 1px solid ${colors.border};
    border-radius: 12px;
    font-size: 0.875rem;
    color: ${colors.foreground};
    cursor: pointer;
    appearance: none;
    transition: all 0.2s ease;
    
    &:focus {
      outline: none;
      border-color: ${colors.primary};
    }
  }
  
  /* Left icon (calendar/filter) */
  svg:first-child {
    position: absolute;
    left: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    width: 16px;
    height: 16px;
    color: ${colors.muted};
    pointer-events: none;
    z-index: 1;
  }
  
  /* Right icon (chevron) */
  svg:last-child {
    position: absolute;
    right: 0.75rem;
    top: 50%;
    transform: translateY(-50%);
    width: 16px;
    height: 16px;
    color: ${colors.muted};
    pointer-events: none;
  }
`;

// Summary entries list
export const EntriesList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 1rem;
`;

// Single summary entry card - Lovable style with left border
export const EntryCard = styled.div<{ $severity?: 'mild' | 'moderate' | 'severe' | 'urgent' }>`
  background: ${colors.paper};
  border: 1px solid ${colors.border};
  border-left: 4px solid ${props => {
    switch (props.$severity) {
      case 'urgent':
      case 'severe': return colors.severe;
      case 'moderate': return colors.moderate;
      default: return colors.mild;
    }
  }};
  border-radius: 16px;
  padding: 1.25rem;
  box-shadow: 0 4px 24px -8px rgba(0, 0, 0, 0.08);
  transition: all 0.25s ease;
  cursor: pointer;
  animation: fadeInUp 0.4s ease forwards;
  
  &:hover {
    box-shadow: 0 8px 32px -8px rgba(0, 0, 0, 0.12);
    transform: translateY(-2px);
  }
  
  @media (min-width: 600px) {
    padding: 1.5rem;
  }
`;

export const EntryHeader = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  
  @media (max-width: 500px) {
    flex-direction: column;
    gap: 0.5rem;
  }
`;

export const EntryDate = styled.p`
  font-size: 0.875rem;
  color: ${colors.muted};
  margin: 0;
`;

export const SeverityBadge = styled.span<{ $severity?: 'mild' | 'moderate' | 'severe' | 'urgent' }>`
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: capitalize;
  
  ${props => {
    switch (props.$severity) {
      case 'urgent':
      case 'severe':
        return css`
          background: ${colors.severeBg};
          color: ${colors.severe};
          border: 1px solid ${colors.severe};
        `;
      case 'moderate':
        return css`
          background: ${colors.moderateBg};
          color: ${colors.moderateText};
          border: 1px solid ${colors.moderate};
        `;
      default:
        return css`
          background: ${colors.mildBg};
          color: ${colors.mildText};
          border: 1px solid ${colors.mild};
        `;
    }
  }}
`;

// Natural language summary text
export const SummaryText = styled.p`
  font-size: 1rem;
  color: ${colors.foreground};
  margin: 0 0 0.75rem 0;
  line-height: 1.6;
`;

// Italic quote for additional notes
export const NotesQuote = styled.p`
  font-size: 0.875rem;
  font-style: italic;
  color: ${colors.muted};
  margin: 0 0 0.75rem 0;
`;

// Metadata row (duration, tried, etc.)
export const MetadataRow = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: ${colors.muted};
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
`;

export const MetadataSeparator = styled.span`
  color: ${colors.border};
`;

// Symptom tags row
export const SymptomTags = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
`;

export const SymptomTag = styled.span`
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  background: rgba(79, 124, 172, 0.08);
  color: ${colors.primaryDark};
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
`;

// Navigation container (date picker, today button)
export const NavigationContainer = styled.div`
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  
  .btn-primary {
    background: ${colors.primary};
    border-color: ${colors.primary};
    font-weight: 600;
    font-size: 0.875rem;
    padding: 8px 16px;
    border-radius: 12px;
    transition: all 0.2s ease;
    
    &:hover {
      background: ${colors.primaryDark};
      border-color: ${colors.primaryDark};
      transform: translateY(-1px);
    }
  }
`;

export const DateNavigationGroup = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  background: ${colors.paper};
  padding: 6px;
  border-radius: 12px;
  border: 1px solid ${colors.border};
`;

export const NavigationButton = styled.button`
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: ${colors.muted};
  
  &:hover {
    background: ${colors.background};
    color: ${colors.primary};
  }
  
  svg {
    width: 18px;
    height: 18px;
  }
`;

export const LoadingContainer = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 24px;
  gap: 16px;
  
  span {
    color: ${colors.muted};
    font-size: 0.9375rem;
  }
`;

export const ErrorContainer = styled.div`
  background: ${colors.severeBg};
  border: 1px solid ${colors.severe}30;
  border-radius: 16px;
  padding: 16px 20px;
  margin-bottom: 20px;
  color: ${colors.severe};
  display: flex;
  align-items: center;
  gap: 12px;
`;

export const EmptyState = styled.div`
  text-align: center;
  padding: 64px 24px;
  color: ${colors.muted};
  
  p {
    margin-bottom: 1rem;
    font-size: 1rem;
  }
`;

// Legacy exports for backward compatibility
export const Container = styled.div`
  display: flex;
  flex-direction: column;
  min-height: 100%;
  background-color: ${colors.background};
`;

export const Header = styled.div`
  display: flex;
  align-items: center;
  padding: 20px 24px;
  background: ${colors.paper};
  border-bottom: 1px solid ${colors.border};
  
  @media (max-width: 576px) {
    padding: 16px;
  }
`;

export const Title = styled.h1`
  font-family: 'Fraunces', Georgia, serif;
  font-size: 1.5rem;
  font-weight: 600;
  color: ${colors.foreground};
  margin: 0;
  
  @media (max-width: 576px) {
    font-size: 1.25rem;
  }
`;

export const Content = styled.div`
  display: flex;
  flex-direction: column;
  padding: 24px;
  flex: 1;
  max-width: 900px;
  margin: 0 auto;
  width: 100%;
  
  @media (max-width: 768px) {
    padding: 16px;
  }
`;

// Additional legacy exports for SummaryCard
export const SummaryCard = styled.div`
  background: ${colors.paper};
  border-radius: 16px;
  border: 1px solid ${colors.border};
  border-left: 4px solid ${colors.primary};
  overflow: hidden;
  transition: all 0.25s ease;
  cursor: pointer;
  box-shadow: 0 4px 24px -8px rgba(0, 0, 0, 0.08);
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 32px -8px rgba(0, 0, 0, 0.12);
  }
`;

export const SummaryCardHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  background: rgba(79, 124, 172, 0.04);
  border-bottom: 1px solid ${colors.border};
`;

export const SummaryDate = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: ${colors.foreground};
  font-size: 0.9375rem;
  
  svg {
    color: ${colors.primary};
  }
`;

export const SummaryBadge = styled.span<{ $severity?: 'mild' | 'moderate' | 'severe' | 'urgent' }>`
  display: inline-flex;
  align-items: center;
  padding: 4px 12px;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: capitalize;
  
  ${props => {
    switch (props.$severity) {
      case 'urgent':
      case 'severe':
        return css`
          background: ${colors.severeBg};
          color: ${colors.severe};
          border: 1px solid ${colors.severe};
        `;
      case 'moderate':
        return css`
          background: ${colors.moderateBg};
          color: ${colors.moderateText};
          border: 1px solid ${colors.moderate};
        `;
      default:
        return css`
          background: ${colors.mildBg};
          color: ${colors.mildText};
          border: 1px solid ${colors.mild};
        `;
    }
  }}
`;

export const SummaryCardContent = styled.div`
  padding: 16px 20px;
`;

export const SummarySymptoms = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
`;

export const ViewDetailsLink = styled.div`
  display: flex;
  align-items: center;
  justify-content: flex-end;
  padding: 12px 20px;
  border-top: 1px solid ${colors.border};
  color: ${colors.primary};
  font-size: 0.8125rem;
  font-weight: 600;
  
  svg {
    margin-left: 4px;
    transition: transform 0.2s;
  }
  
  &:hover svg {
    transform: translateX(4px);
  }
`;

export const SummaryGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 1rem;
  
  @media (min-width: 768px) {
    grid-template-columns: repeat(2, 1fr);
  }
`;

export const DatePickerContainer = styled.div`
  display: flex;
  align-items: center;
  
  .MuiTextField-root {
    min-width: 160px;
  }
  
  .MuiInputBase-root {
    background-color: transparent;
    border-radius: 8px;
    font-size: 0.9375rem;
    
    fieldset {
      border: none;
    }
  }
`;

export const CurrentDateDisplay = styled.span`
  color: ${colors.foreground};
  font-weight: 600;
  font-size: 0.9375rem;
  padding: 0 8px;
  min-width: 120px;
  text-align: center;
`;

export const DateDisplayButton = styled.button`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  height: 36px;
  min-width: 160px;
  justify-content: center;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  color: ${colors.foreground};
  font-weight: 600;
  font-size: 0.9375rem;
  
  &:hover {
    background: ${colors.background};
    color: ${colors.primary};
  }
  
  svg {
    width: 16px;
    height: 16px;
    color: ${colors.muted};
  }
`;
