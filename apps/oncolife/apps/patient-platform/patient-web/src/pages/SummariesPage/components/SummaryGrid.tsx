import React from 'react';
import styled from 'styled-components';
import SummaryCard from './SummaryCard';
import type { Summary } from '../../../services/summaries';

const GridContainer = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  width: 100%;
  
  @media (min-width: 768px) {
    grid-template-columns: repeat(2, 1fr);
  }
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 4rem 2rem;
  color: #6C757D;
  
  h3 {
    font-size: 1.5rem;
    margin-bottom: 1rem;
    color: #495057;
  }
  
  p {
    font-size: 1.1rem;
    margin: 0;
  }
`;

interface SummaryGridProps {
  summaries: { data: Summary[] };
  onViewDetails: (summaryId: string) => void;
}

const SummaryGrid: React.FC<SummaryGridProps> = ({ summaries, onViewDetails }) => {
  if (summaries?.data?.length === 0) {
    return (
      <EmptyState>
        <h3>No Summaries Found</h3>
        <p>There are no summaries available for this period</p>
      </EmptyState>
    );
  }

  return (
    <GridContainer>
      {summaries?.data?.map((summary) => (
        <SummaryCard
          key={summary.uuid}
          summary={summary}
          onViewDetails={onViewDetails}
        />
      ))}
    </GridContainer>
  );
};

export default SummaryGrid; 