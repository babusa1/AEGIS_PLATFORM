import styled from 'styled-components';

export const SidebarContainer = styled.div`
  height: 100%;
  min-height: 0;
  background-color: #ffffff;
  border-right: 1px solid #e9ecef;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-width: 280px;
  max-width: 350px;
  flex-shrink: 0;
`;

export const SidebarHeader = styled.div`
  padding: 1rem;
  border-bottom: 1px solid #e9ecef;
  background: #fff;
  position: sticky;
  top: 0;
  z-index: 1;
`;

export const NotesSidebarTitle = styled.div`
  font-size: 1.25rem;
  font-weight: 700;
  color: #2C3E50;
  letter-spacing: -0.5px;
  margin-bottom: 0;
  margin-right: 1rem;
  line-height: 1.2;
`;

export const NotesList = styled.div`
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1rem;
  min-height: 0;
`; 