/**
 * SummaryCard - Lovable-inspired design
 * Natural language summary with left-border severity indicator
 */

import React from 'react';
import styled, { css } from 'styled-components';
import type { Summary } from '../../../services/summaries';
import { formatDateForDisplay } from '@oncolife/shared-utils';

// Warm Lovable-style colors
const colors = {
  paper: '#FFFFFF',
  primary: '#4F7CAC',
  primaryDark: '#3B5F8A',
  foreground: '#3D3A35',
  muted: '#8A847A',
  border: '#E8E4DD',
  
  // Severity
  severe: '#DC2626',
  severeBg: '#FEE2E2',
  moderate: '#F59E0B',
  moderateBg: '#FEF3C7',
  moderateText: '#92400E',
  mild: '#22C55E',
  mildBg: '#DCFCE7',
  mildText: '#166534',
};

const Card = styled.div<{ $severity?: string }>`
  background: ${colors.paper};
  border: 1px solid ${colors.border};
  border-left: 4px solid ${props => {
    switch (props.$severity?.toLowerCase()) {
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
  height: 100%;
  display: flex;
  flex-direction: column;
  animation: fadeInUp 0.4s ease forwards;

  &:hover {
    box-shadow: 0 8px 32px -8px rgba(0, 0, 0, 0.12);
    transform: translateY(-2px);
  }
  
  @media (min-width: 600px) {
    padding: 1.5rem;
  }
  
  @keyframes fadeInUp {
    from {
      opacity: 0;
      transform: translateY(20px);
    }
    to {
      opacity: 1;
      transform: translateY(0);
    }
  }
`;

const CardHeader = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 0.75rem;
  gap: 0.5rem;
  
  @media (max-width: 400px) {
    flex-direction: column;
  }
`;

const DateText = styled.p`
  font-size: 0.875rem;
  color: ${colors.muted};
  margin: 0;
`;

const SeverityBadge = styled.span<{ $severity?: string }>`
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: capitalize;
  white-space: nowrap;
  
  ${props => {
    switch (props.$severity?.toLowerCase()) {
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

// Natural language summary
const SummaryText = styled.p`
  font-size: 1rem;
  color: ${colors.foreground};
  margin: 0 0 0.75rem 0;
  line-height: 1.6;
  flex: 1;
`;

const SymptomTags = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: auto;
`;

const SymptomTag = styled.span`
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.75rem;
  background: rgba(79, 124, 172, 0.08);
  color: ${colors.primaryDark};
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
`;

const ViewDetailsButton = styled.button`
  width: 100%;
  margin-top: 1rem;
  padding: 0.625rem 1rem;
  background: ${colors.primary};
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background: ${colors.primaryDark};
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(79, 124, 172, 0.3);
  }
`;

interface SummaryCardProps {
  summary: Summary;
  onViewDetails: (summaryId: string) => void;
}

/**
 * Generate natural language summary sentence (Lovable style)
 */
const generateNaturalSummary = (summary: Summary): string => {
  // Parse the bulleted summary to extract symptoms and details
  const bulletedSummary = summary.bulleted_summary || '';
  const lines = bulletedSummary.split(/,\s*-/).map(l => l.replace(/^\s*-?\s*/, '').trim()).filter(Boolean);
  
  // Try to extract key information
  const symptoms = lines.filter(line => 
    !line.toLowerCase().includes('duration') && 
    !line.toLowerCase().includes('tried') &&
    !line.toLowerCase().includes('severity')
  );
  
  const durationLine = lines.find(line => line.toLowerCase().includes('duration'));
  const severityLine = lines.find(line => line.toLowerCase().includes('severity'));
  const triedLine = lines.find(line => line.toLowerCase().includes('tried'));
  
  // Build natural language sentence
  let text = 'You have been experiencing ';
  
  if (symptoms.length > 0) {
    text += symptoms.slice(0, 2).join(' and ').toLowerCase();
  } else {
    text += 'symptoms';
  }
  
  if (durationLine) {
    const duration = durationLine.replace(/duration:?\s*/i, '').toLowerCase();
    text += ` for ${duration}`;
  }
  
  if (severityLine) {
    const severity = severityLine.replace(/severity:?\s*/i, '').toLowerCase();
    text += `, rated as ${severity}`;
  }
  
  if (triedLine) {
    const tried = triedLine.replace(/tried:?\s*/i, '').toLowerCase();
    if (tried && tried !== 'none' && tried !== 'nothing') {
      text += `, and have tried ${tried}`;
    } else {
      text += ', and have not tried any medications';
    }
  }
  
  text += '.';
  
  return text;
};

/**
 * Extract symptom names from summary
 */
const extractSymptoms = (summary: Summary): string[] => {
  const bulletedSummary = summary.bulleted_summary || '';
  const lines = bulletedSummary.split(/,\s*-/).map(l => l.replace(/^\s*-?\s*/, '').trim()).filter(Boolean);
  
  return lines.filter(line => 
    !line.toLowerCase().includes('duration') && 
    !line.toLowerCase().includes('tried') &&
    !line.toLowerCase().includes('severity') &&
    line.length < 30
  ).slice(0, 3);
};

/**
 * Determine severity level from summary
 */
const getSeverity = (summary: Summary): string => {
  const bulletedSummary = summary.bulleted_summary || '';
  const lowerText = bulletedSummary.toLowerCase();
  
  if (lowerText.includes('severe') || lowerText.includes('urgent')) return 'Severe';
  if (lowerText.includes('moderate')) return 'Moderate';
  return 'Mild';
};

const SummaryCard: React.FC<SummaryCardProps> = ({ summary, onViewDetails }) => {
  const formatDate = (dateString: string) => {
    try {
      const date = new Date(dateString);
      return date.toLocaleDateString('en-US', { 
        weekday: 'long', 
        year: 'numeric', 
        month: 'long', 
        day: 'numeric' 
      });
    } catch {
      return formatDateForDisplay(dateString);
    }
  };

  const severity = getSeverity(summary);
  const naturalSummary = generateNaturalSummary(summary);
  const symptoms = extractSymptoms(summary);

  return (
    <Card $severity={severity}>
      <CardHeader>
        <DateText>{formatDate(summary.created_at)}</DateText>
        <SeverityBadge $severity={severity}>{severity}</SeverityBadge>
      </CardHeader>
      
      <SummaryText>
        {summary?.bulleted_summary ? naturalSummary : 'No symptoms recorded for this check-in.'}
      </SummaryText>
      
      {symptoms.length > 0 && (
        <SymptomTags>
          {symptoms.map((symptom, index) => (
            <SymptomTag key={index}>{symptom}</SymptomTag>
          ))}
        </SymptomTags>
      )}
      
      {summary?.bulleted_summary && (
        <ViewDetailsButton onClick={() => onViewDetails(summary.uuid)}>
          View Details
        </ViewDetailsButton>
      )}
    </Card>
  );
};

export default SummaryCard;
