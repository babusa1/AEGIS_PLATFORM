/**
 * SummariesPage - Daily Check-ins (Figma aligned)
 * Shows symptom tracking entries from chat conversations
 */
import React, { useState, useMemo } from 'react';
import { CircularProgress } from '@mui/material';
import { Search, Calendar, Filter, ChevronDown } from 'lucide-react';
import { 
  PageContainer,
  ContentWrapper,
  PageHeader, 
  PageTitle, 
  PageSubtitle,
  FiltersRow,
  SearchInputWrapper,
  SelectWrapper,
  EntriesList,
  EntryCard,
  EntryHeader,
  EntryDate,
  SeverityBadge,
  SummaryText,
  NotesQuote,
  MetadataRow,
  MetadataSeparator,
  SymptomTags,
  SymptomTag,
  LoadingContainer,
  ErrorContainer,
  EmptyState,
} from './SummariesPage.styles';
import { Container, Header, Title, Content } from '@oncolife/ui-components';
import { useSummaries, type Summary } from '../../services/summaries';
import { useNavigate } from 'react-router-dom';

// Date filter options
const DATE_FILTER_OPTIONS = [
  { value: 'all', label: 'All Time' },
  { value: 'today', label: 'Today' },
  { value: 'week', label: 'This Week' },
  { value: 'month', label: 'This Month' },
  { value: 'last30', label: 'Last 30 Days' },
];

// Get unique symptoms from all summaries
const getUniqueSymptoms = (summaries: Summary[]): string[] => {
  const symptoms = new Set<string>();
  summaries.forEach(summary => {
    if (summary.symptom_list && Array.isArray(summary.symptom_list)) {
      summary.symptom_list.forEach(s => symptoms.add(s));
    }
    // Also extract from bulleted_summary
    const bulletedSummary = summary.bulleted_summary || '';
    const lines = bulletedSummary.split(/,\s*-/).map(l => l.replace(/^\s*-?\s*/, '').trim()).filter(Boolean);
    lines.forEach(line => {
      if (!line.toLowerCase().includes('duration') && 
          !line.toLowerCase().includes('tried') &&
          !line.toLowerCase().includes('severity') &&
          line.length < 30) {
        symptoms.add(line);
      }
    });
  });
  return Array.from(symptoms).sort();
};

// Extract symptom names from summary
const extractSymptoms = (summary: Summary): string[] => {
  if (summary.symptom_list && Array.isArray(summary.symptom_list) && summary.symptom_list.length > 0) {
    return summary.symptom_list.slice(0, 4);
  }
  const bulletedSummary = summary.bulleted_summary || '';
  const lines = bulletedSummary.split(/,\s*-/).map(l => l.replace(/^\s*-?\s*/, '').trim()).filter(Boolean);
  return lines.filter(line => 
    !line.toLowerCase().includes('duration') && 
    !line.toLowerCase().includes('tried') &&
    !line.toLowerCase().includes('severity') &&
    line.length < 30
  ).slice(0, 3);
};

// Extract duration from summary
const extractDuration = (summary: Summary): string | null => {
  const bulletedSummary = summary.bulleted_summary || '';
  const durationMatch = bulletedSummary.match(/duration:?\s*([^,\-]+)/i);
  if (durationMatch) {
    return durationMatch[1].trim();
  }
  return null;
};

// Extract medications tried from summary
const extractMedicationsTried = (summary: Summary): string | null => {
  if (summary.medication_list && Array.isArray(summary.medication_list) && summary.medication_list.length > 0) {
    return summary.medication_list.join(', ');
  }
  const bulletedSummary = summary.bulleted_summary || '';
  const triedMatch = bulletedSummary.match(/tried:?\s*([^,\-]+)/i);
  if (triedMatch) {
    const tried = triedMatch[1].trim();
    if (tried.toLowerCase() === 'none' || tried.toLowerCase() === 'nothing') {
      return 'None tried';
    }
    return tried;
  }
  return 'None tried';
};

// Get severity level from summary
const getSeverity = (summary: Summary): 'mild' | 'moderate' | 'severe' | 'urgent' => {
  const bulletedSummary = summary.bulleted_summary || '';
  const lowerText = bulletedSummary.toLowerCase();
  const triageLevel = summary.triage_level?.toLowerCase() || '';
  
  if (lowerText.includes('urgent') || triageLevel.includes('call_911')) return 'urgent';
  if (lowerText.includes('severe') || triageLevel.includes('urgent')) return 'severe';
  if (lowerText.includes('moderate') || triageLevel.includes('notify')) return 'moderate';
  return 'mild';
};

// Generate natural language summary
const generateNaturalSummary = (summary: Summary): string => {
  const symptoms = extractSymptoms(summary);
  const duration = extractDuration(summary);
  const meds = extractMedicationsTried(summary);
  const severity = getSeverity(summary);
  
  let text = 'You have been experiencing ';
  
  if (symptoms.length > 0) {
    text += symptoms.slice(0, 2).join(' and ').toLowerCase();
  } else {
    text += 'symptoms';
  }
  
  if (duration) {
    text += ` for ${duration}`;
  }
  
  text += `, rated as ${severity}`;
  
  if (meds && meds !== 'None tried') {
    text += `, and have tried ${meds.toLowerCase()}`;
  } else {
    text += ', and have not tried any medications';
  }
  
  text += '.';
  
  return text;
};

// Extract personal notes from summary (if any)
const extractPersonalNotes = (summary: Summary): string | null => {
  // Check for personal_notes field first
  if ((summary as any).personal_notes) {
    return (summary as any).personal_notes;
  }
  // Check in longer_summary for quoted text
  const longerSummary = summary.longer_summary || '';
  const quoteMatch = longerSummary.match(/"([^"]+)"/);
  if (quoteMatch) {
    return quoteMatch[1];
  }
  return null;
};

// Filter summaries by date range
const filterByDateRange = (summaries: Summary[], filter: string): Summary[] => {
  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  
  return summaries.filter(summary => {
    const date = new Date(summary.created_at);
    
    switch (filter) {
      case 'today':
        return date >= today;
      case 'week': {
        const weekAgo = new Date(today);
        weekAgo.setDate(weekAgo.getDate() - 7);
        return date >= weekAgo;
      }
      case 'month': {
        const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
        return date >= monthStart;
      }
      case 'last30': {
        const thirtyDaysAgo = new Date(today);
        thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
        return date >= thirtyDaysAgo;
      }
      case 'all':
      default:
        return true;
    }
  });
};

// Filter summaries by symptom
const filterBySymptom = (summaries: Summary[], symptom: string): Summary[] => {
  if (!symptom || symptom === 'all') return summaries;
  
  return summaries.filter(summary => {
    const symptoms = extractSymptoms(summary);
    return symptoms.some(s => s.toLowerCase().includes(symptom.toLowerCase()));
  });
};

// Search summaries
const searchSummaries = (summaries: Summary[], query: string): Summary[] => {
  if (!query.trim()) return summaries;
  
  const lowerQuery = query.toLowerCase();
  return summaries.filter(summary => {
    const symptoms = extractSymptoms(summary);
    const notes = extractPersonalNotes(summary);
    const naturalSummary = generateNaturalSummary(summary);
    
    return (
      symptoms.some(s => s.toLowerCase().includes(lowerQuery)) ||
      (notes && notes.toLowerCase().includes(lowerQuery)) ||
      naturalSummary.toLowerCase().includes(lowerQuery)
    );
  });
};

const SummariesPage: React.FC = () => {
  const navigate = useNavigate();
  
  // State for filters
  const [searchQuery, setSearchQuery] = useState('');
  const [dateFilter, setDateFilter] = useState('all');
  const [symptomFilter, setSymptomFilter] = useState('all');
  
  // Fetch all summaries (we'll filter client-side for now)
  // TODO: Move filtering to backend for better performance
  const { data, isLoading, error } = useSummaries(
    new Date().getFullYear(),
    new Date().getMonth() + 1
  );
  
  // Get all summaries
  const allSummaries = data?.data || [];
  
  // Get unique symptoms for the filter dropdown
  const availableSymptoms = useMemo(() => getUniqueSymptoms(allSummaries), [allSummaries]);
  
  // Apply filters
  const filteredSummaries = useMemo(() => {
    let result = allSummaries;
    result = filterByDateRange(result, dateFilter);
    result = filterBySymptom(result, symptomFilter);
    result = searchSummaries(result, searchQuery);
    return result.sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [allSummaries, dateFilter, symptomFilter, searchQuery]);

  const handleViewDetails = (summaryId: string) => {
    navigate(`/summaries/${summaryId}`);
  };

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
      return dateString;
    }
  };

  return (
    <Container>
      <Header>
        <Title>Daily Check-ins</Title>
      </Header>
      
      <Content>
        <ContentWrapper>
        <PageHeader>
            <PageTitle>Daily Check-ins</PageTitle>
            <PageSubtitle>Your daily symptom tracking entries from chat conversations.</PageSubtitle>
          </PageHeader>
          
          {/* Search and Filters */}
          <FiltersRow>
            <SearchInputWrapper>
              <Search />
              <input 
                type="text"
                placeholder="Search entries..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </SearchInputWrapper>
            
            <SelectWrapper>
              <Calendar size={16} />
              <select 
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
              >
                {DATE_FILTER_OPTIONS.map(opt => (
                  <option key={opt.value} value={opt.value}>{opt.label}</option>
                ))}
              </select>
              <ChevronDown size={16} />
            </SelectWrapper>
            
            <SelectWrapper>
              <Filter size={16} />
              <select 
                value={symptomFilter}
                onChange={(e) => setSymptomFilter(e.target.value)}
              >
                <option value="all">All Symptoms</option>
                {availableSymptoms.map(symptom => (
                  <option key={symptom} value={symptom}>{symptom}</option>
                ))}
              </select>
              <ChevronDown size={16} />
            </SelectWrapper>
          </FiltersRow>
          
          {/* Error State */}
        {error && (
          <ErrorContainer>
              <strong>Error:</strong> {error.message || 'Failed to load check-ins'}
          </ErrorContainer>
        )}

          {/* Loading State */}
        {isLoading ? (
          <LoadingContainer>
            <CircularProgress size={48} />
              <span>Loading your check-ins...</span>
          </LoadingContainer>
          ) : filteredSummaries.length === 0 ? (
            <EmptyState>
              <div style={{ fontSize: '3rem', marginBottom: '1rem' }}>📋</div>
              <h3 style={{ marginBottom: '0.5rem', color: '#495057' }}>No Check-ins Found</h3>
              <p>
                {searchQuery || dateFilter !== 'all' || symptomFilter !== 'all' 
                  ? 'Try adjusting your filters to see more results.'
                  : 'Start a symptom check in the Chat to create your first daily check-in.'}
              </p>
            </EmptyState>
          ) : (
            <EntriesList>
              {filteredSummaries.map((summary, index) => {
                const severity = getSeverity(summary);
                const symptoms = extractSymptoms(summary);
                const duration = extractDuration(summary);
                const meds = extractMedicationsTried(summary);
                const notes = extractPersonalNotes(summary);
                const naturalSummary = generateNaturalSummary(summary);
                
                return (
                  <EntryCard 
                    key={summary.uuid} 
                    $severity={severity}
                    onClick={() => handleViewDetails(summary.uuid)}
                    style={{ animationDelay: `${index * 0.05}s` }}
                  >
                    <EntryHeader>
                      <EntryDate>{formatDate(summary.created_at)}</EntryDate>
                      <SeverityBadge $severity={severity}>
                        {severity === 'urgent' ? 'Severe' : severity.charAt(0).toUpperCase() + severity.slice(1)}
                      </SeverityBadge>
                    </EntryHeader>
                    
                    <SummaryText>{naturalSummary}</SummaryText>
                    
                    {notes && (
                      <NotesQuote>"{notes}"</NotesQuote>
                    )}
                    
                    <MetadataRow>
                      {duration && (
                        <>
                          <span>Duration: {duration}</span>
                          <MetadataSeparator>•</MetadataSeparator>
                        </>
                      )}
                      <span>Tried: {meds || 'None tried'}</span>
                    </MetadataRow>
                    
                    {symptoms.length > 0 && (
                      <SymptomTags>
                        {symptoms.map((symptom, idx) => (
                          <SymptomTag key={idx}>{symptom}</SymptomTag>
                        ))}
                      </SymptomTags>
                    )}
                  </EntryCard>
                );
              })}
            </EntriesList>
          )}
        </ContentWrapper>
      </Content>
    </Container>
  );
};

export default SummariesPage; 
