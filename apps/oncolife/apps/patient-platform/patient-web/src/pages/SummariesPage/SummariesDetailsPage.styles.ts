import styled from "styled-components";

export const Page = styled.div`
  min-height: 100vh;
  background-color: #F8F9FA;
`;

export const Header = styled.div`
  background-color: #FFFFFF;
  border-bottom: 1px solid #E0E0E0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
`;

export const HeaderContent = styled.div`
  max-width: 1400px;
  margin: 0 auto;
  padding: 1.5rem 2rem;
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

export const BackButton = styled.button`
  display: inline-flex;
  align-items: center;
  background: none;
  border: none;
  color: #6C757D;
  cursor: pointer;
  transition: color 0.2s ease;
  font-size: 1.1rem;
  
  &:hover {
    color: #495057;
  }
`;

export const BackButtonIcon = styled.span`
  margin-right: 0.75rem;
`;

export const BackButtonText = styled.span`
  font-weight: 500;
  font-size: 1.1rem;
`;

export const PageTitle = styled.h1`
  font-size: 2.25rem;
  font-weight: 700;
  color: #2C3E50;
  margin: 0;
  letter-spacing: -0.5px;
`;

export const TitleSpacer = styled.div`
  width: 200px;
`;

export const Content = styled.div`
  max-width: 1400px;
  margin: 0 auto;
  padding: 2.5rem 2rem;
`;

export const SummaryHeaderCard = styled.div`
  background-color: #FFFFFF;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid #E0E0E0;
  padding: 2rem;
  margin-bottom: 2rem;
`;

export const SummaryHeaderContent = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
`;

export const DateContainer = styled.div`
  display: flex;
  align-items: center;
  color: #6C757D;
`;

export const DateIcon = styled.span`
  margin-right: 0.75rem;
`;

export const DateText = styled.span`
  font-size: 1.25rem;
  font-weight: 600;
`;

export const FeelingContainer = styled.div`
  display: inline-flex;
  align-items: center;
  padding: 0.75rem 1rem;
  border-radius: 50px;
`;

export const FeelingImage = styled.img`
  width: 20px;
  height: 20px;
  margin-right: 0.75rem;
`;

export const FeelingText = styled.span`
  font-weight: 600;
  font-size: 1.1rem;
`;

export const MainGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
  
  @media (min-width: 1024px) {
    grid-template-columns: 2fr 1fr;
  }
`;

export const DetailedSummaryContainer = styled.div``;

export const Card = styled.div`
  background-color: #FFFFFF;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 1px solid #E0E0E0;
  padding: 2rem;
`;

export const CardHeader = styled.div`
  display: flex;
  align-items: center;
  margin-bottom: 1.5rem;
`;

export const CardIcon = styled.span`
  margin-right: 1rem;
`;

export const CardTitle = styled.h2`
  font-size: 1.5rem;
  font-weight: 700;
  color: #2C3E50;
  margin: 0;
`;

export const DetailedSummaryText = styled.div`
  color: #495057;
  line-height: 1.6;
  
  p {
    margin: 0;
    font-size: 1.1rem;
    line-height: 1.6;
  }
`;

export const QuickSummaryContainer = styled.div``;

export const QuickSummaryContent = styled.div`
  color: #495057;
  line-height: 1.6;
  font-size: 1rem;
  
  & > * {
    margin-bottom: 0.75rem;
  }
  
  & > *:last-child {
    margin-bottom: 0;
  }
`;

export const AdditionalInfoGrid = styled.div`
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
  margin-top: 2rem;
  
  @media (min-width: 768px) {
    grid-template-columns: 1fr 1fr;
  }
`;

export const InfoCardTitle = styled.h3`
  font-size: 1.25rem;
  font-weight: 700;
  color: #2C3E50;
  margin: 0 0 1.5rem 0;
`;

export const SymptomsList = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
`;

export const SymptomTag = styled.span`
  display: inline-block;
  padding: 0.5rem 1rem;
  background-color: #E3F2FD;
  color: #1565C0;
  border-radius: 50px;
  font-size: 1rem;
  font-weight: 500;
`;

export const MedicationsList = styled.div`
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
`;

export const MedicationItem = styled.div`
  padding: 0.75rem 1rem;
  background-color: #F3E5F5;
  border: 1px solid #E1BEE7;
  border-radius: 8px;
  color: #6A1B9A;
  font-size: 1rem;
`; 