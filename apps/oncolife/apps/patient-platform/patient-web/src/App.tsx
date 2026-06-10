/**
 * =============================================================================
 * Patient Portal - Main Application
 * =============================================================================
 * 
 * Module:      App.tsx
 * Description: Main React application entry point for the Patient Portal.
 *              Configures routing, authentication, and global providers.
 * 
 * Created:     2025-12-12
 * Modified:    2026-01-16
 * Author:      Naveen Babu S A
 * Version:     2.1.0
 * 
 * Routes:
 *   /login       - Login page
 *   /signup      - Patient registration
 *   /chat        - Daily symptom check-in
 *   /summaries   - Past triage summaries
 *   /notes       - Patient diary
 *   /education   - Learning resources
 *   /profile     - Account settings
 *   /questions   - Questions for doctor
 * 
 * Copyright:
 *   (c) 2026 OncoLife Health Technologies. All rights reserved.
 * =============================================================================
 */

import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { GlobalStyles, SessionTimeoutManager } from '@oncolife/ui-components';
import { AuthProvider } from './contexts/AuthContext';
import { UserProvider } from './contexts/UserContext';
import { UserTypeProvider } from './contexts/UserTypeContext';
import { useAuth } from './contexts/AuthContext';

// Shared login from ui-components
import LoginPage from './pages/LoginPage';
import ResetPassword from './pages/LoginPage/ResetPassword';
import Acknowledgement from './pages/LoginPage/Acknowledgement';

// Patient-specific pages
import SignUpPage from './pages/SignUpPage';
import Layout from './components/Layout';
import ChatsPage from './pages/ChatsPage';
import { SummariesPage, SummariesDetailsPage } from './pages/SummariesPage';
import NotesPage from './pages/NotesPage';
import EducationPage from './pages/EducationPage';
import ProfilePage from './pages/ProfilePage';
import QuestionsPage from './pages/QuestionsPage';

function RootRedirect() {
  const { isAuthenticated, isLoading } = useAuth();
  if (isLoading) return null;
  return <Navigate to={isAuthenticated ? '/chat' : '/login'} />;
}

function App() {
  return (
    <UserTypeProvider>
      <AuthProvider>
        <UserProvider>
          <GlobalStyles />
          <BrowserRouter>
            <SessionTimeoutManager />
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route path="/reset-password" element={<ResetPassword />} />
              <Route path="/acknowledgement" element={<Acknowledgement />} />
              <Route path="/signup" element={<SignUpPage />} />
              <Route element={<Layout />}>
                <Route path="/chat" element={<ChatsPage />} />
                <Route path="/summaries" element={<SummariesPage />} />
                <Route path="/summaries/:id" element={<SummariesDetailsPage />} />
                <Route path="/notes" element={<NotesPage />} />
                <Route path="/questions" element={<QuestionsPage />} />
                <Route path="/education" element={<EducationPage />} />
                <Route path="/profile" element={<ProfilePage />} />
              </Route>
              <Route path="/" element={<Navigate to="/login" />} />
            </Routes>
          </BrowserRouter>
        </UserProvider>
      </AuthProvider>
    </UserTypeProvider>
  );
}

export default App;