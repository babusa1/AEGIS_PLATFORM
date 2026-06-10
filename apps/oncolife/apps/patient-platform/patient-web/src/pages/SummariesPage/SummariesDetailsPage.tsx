import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useSummaryDetails } from '../../services/summaries';
import { formatDateForDisplay } from '@oncolife/shared-utils';
import { ArrowLeft, Calendar, FileText, List } from 'lucide-react';
import * as S from './SummariesDetailsPage.styles';

// Import images correctly
import veryHappyImg from '../../assets/VeryHappy.png';
import happyImg from '../../assets/Happy.png';
import neutralImg from '../../assets/Neutral.png';
import sadImg from '../../assets/Sad.png';
import verySadImg from '../../assets/VerySad.png';


const SummariesDetailsPage: React.FC = () => {
  // Fix: route is defined as /summaries/:id, so read `id` not `summaryId`
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data: summary, isLoading, error } = useSummaryDetails(id || '');

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
          <p className="text-gray-600 text-lg">Loading summary details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md mx-auto text-center">
          <div className="text-red-500 text-5xl mb-4">⚠️</div>
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Unable to Load Summary</h2>
          <p className="text-gray-600 mb-6">There was an error loading the summary details. Please try again.</p>
          <button 
            onClick={() => navigate('/summaries')} 
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <ArrowLeft size={16} className="mr-2" />
            Back to Summaries
          </button>
        </div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="bg-white rounded-xl shadow-lg p-8 max-w-md mx-auto text-center">
          <div className="text-gray-400 text-5xl mb-4">📄</div>
          <h2 className="text-xl font-semibold text-gray-800 mb-4">Summary Not Found</h2>
          <p className="text-gray-600 mb-6">The requested summary could not be found.</p>
          <button 
            onClick={() => navigate('/summaries')} 
            className="inline-flex items-center px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            <ArrowLeft size={16} className="mr-2" />
            Back to Summaries
          </button>
        </div>
      </div>
    );
  }

  const getFeelingData = (feeling: string) => {
    const feelings: { [key: string]: { color: string, image: string } } = {
      'Very Happy': { color: 'background-color: #E8F5E8; color: #2E7D32;', image: veryHappyImg },
      'Happy': { color: 'background-color: #E8F5E8; color: #388E3C;', image: happyImg },
      'Neutral': { color: 'background-color: #FFF8E1; color: #F57F17;', image: neutralImg },
      'Sad': { color: 'background-color: #FFF3E0; color: #F57C00;', image: sadImg },
      'Very Sad': { color: 'background-color: #FFEBEE; color: #D32F2F;', image: verySadImg }
    };
    return feelings[feeling] || { color: 'background-color: #F5F5F5; color: #757575;', image: neutralImg };
  };


  return (
    <S.Page>
      {/* Header */}
      <S.Header>
        <S.HeaderContent>
          <S.BackButton onClick={() => navigate('/summaries')}>
            <S.BackButtonIcon>
              <ArrowLeft size={22} />
            </S.BackButtonIcon>
            <S.BackButtonText>Back to Summaries</S.BackButtonText>
          </S.BackButton>
          <S.PageTitle>Conversation Summary</S.PageTitle>
          <S.TitleSpacer />
        </S.HeaderContent>
      </S.Header>

      {/* Content */}
      <S.Content>
        {/* Summary Header Card */}
        <S.SummaryHeaderCard>
          <S.SummaryHeaderContent>
            <S.DateContainer>
              <S.DateIcon>
                <Calendar size={24} />
              </S.DateIcon>
              <S.DateText>{formatDateForDisplay(summary.created_at)}</S.DateText>
            </S.DateContainer>
            {summary.overall_feeling && (
              <S.FeelingContainer style={{ backgroundColor: getFeelingData(summary.overall_feeling).color.split(';')[0].split(':')[1], color: getFeelingData(summary.overall_feeling).color.split(';')[1].split(':')[1] }}>
                <S.FeelingImage 
                  src={getFeelingData(summary.overall_feeling).image} 
                  alt={summary.overall_feeling}
                />
                <S.FeelingText>Overall Feeling: {summary.overall_feeling}</S.FeelingText>
              </S.FeelingContainer>
            )}
          </S.SummaryHeaderContent>
        </S.SummaryHeaderCard>

        {/* Main Content Grid */}
        <S.MainGrid>
          {/* Detailed Summary - Takes up more space */}
          <S.DetailedSummaryContainer>
            <S.Card>
              <S.CardHeader>
                <S.CardIcon style={{ color: '#1976D2' }}>
                  <FileText size={28} />
                </S.CardIcon>
                <S.CardTitle>Detailed Summary</S.CardTitle>
              </S.CardHeader>
              <S.DetailedSummaryText>
                <p>
                  {summary.longer_summary || 'No detailed summary available.'}
                </p>
              </S.DetailedSummaryText>
            </S.Card>
          </S.DetailedSummaryContainer>

          {/* Quick Summary Sidebar */}
          <S.QuickSummaryContainer>
            {summary.bulleted_summary && (
              <S.Card>
                <S.CardHeader>
                  <S.CardIcon style={{ color: '#388E3C' }}>
                    <List size={28} />
                  </S.CardIcon>
                  <S.CardTitle>Quick Summary</S.CardTitle>
                </S.CardHeader>
                <S.QuickSummaryContent 
                  dangerouslySetInnerHTML={{ __html: summary.bulleted_summary }}
                />
              </S.Card>
            )}
          </S.QuickSummaryContainer>
        </S.MainGrid>

        {/* Additional Information Cards */}
        {(summary.symptom_list || summary.medication_list) && (
          <S.AdditionalInfoGrid>
            {/* Symptoms Card */}
            {summary.symptom_list && summary.symptom_list.length > 0 && (
              <S.Card>
                <S.InfoCardTitle>Reported Symptoms</S.InfoCardTitle>
                <S.SymptomsList>
                  {summary.symptom_list.map((symptom, index) => (
                    <S.SymptomTag key={index}>
                      {symptom}
                    </S.SymptomTag>
                  ))}
                </S.SymptomsList>
              </S.Card>
            )}

            {/* Medications Card */}
            {summary.medication_list && summary.medication_list.length > 0 && (
              <S.Card>
                <S.InfoCardTitle>Medications Discussed</S.InfoCardTitle>
                <S.MedicationsList>
                  {summary.medication_list.map((medication, index) => (
                    <S.MedicationItem key={index}>
                      {typeof medication === 'string' ? medication : JSON.stringify(medication)}
                    </S.MedicationItem>
                  ))}
                </S.MedicationsList>
              </S.Card>
            )}
          </S.AdditionalInfoGrid>
        )}
      </S.Content>
    </S.Page>
  );
};

export default SummariesDetailsPage;
