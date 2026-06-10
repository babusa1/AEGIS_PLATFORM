/**
 * =============================================================================
 * Doctor Portal - Main Application
 * =============================================================================
 * 
 * Module:      App.tsx
 * Description: Main React application entry point for the Doctor Portal.
 *              Configures routing, authentication, and global providers.
 * 
 * Created:     2025-12-20
 * Modified:    2026-01-16
 * Author:      Naveen Babu S A
 * Version:     2.1.0
 * 
 * Routes:
 *   /login              - Login page
 *   /dashboard          - Main dashboard with patient ranking
 *   /patients           - Patient list management
 *   /patients/:uuid     - Patient detail with timeline
 *   /staff              - Staff management
 *   /reports            - Weekly reports
 * 
 * Copyright:
 *   (c) 2026 OncoLife Health Technologies. All rights reserved.
 * =============================================================================
 */

import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { GlobalStyles, SessionTimeoutManager } from '@oncolife/ui-components';
import { AuthProvider } from './contexts/AuthContext';
import { UserProvider } from './contexts/UserContext';
import { UserTypeProvider } from './contexts/UserTypeContext';

// Doctor-specific pages
import LoginPage from './pages/LoginPage';
import Layout from './components/Layout';
import DashboardPage from './pages/Dashboard/DashboardPage';
import PatientsPage from './pages/Patients/PatientsPage';
import StaffPage from './pages/Staff/StaffPage';
import PatientDetailPage from './pages/PatientDetail';
import ReportsPage from './pages/Reports';

function App() {
  return (
    <UserTypeProvider userType="doctor">
      <AuthProvider>
        <UserProvider>
          <GlobalStyles />
          <BrowserRouter>
            <SessionTimeoutManager />
            <Routes>
              <Route path="/login" element={<LoginPage />} />
              <Route element={<Layout />}>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/patients" element={<PatientsPage />} />
                <Route path="/patients/:uuid" element={<PatientDetailPage />} />
                <Route path="/reports" element={<ReportsPage />} />
                <Route path="/staff" element={<StaffPage />} />
              </Route>
              <Route path="/" element={<Navigate to="/dashboard" />} />
            </Routes>
          </BrowserRouter>
        </UserProvider>
      </AuthProvider>
    </UserTypeProvider>
  );
}

export default App;