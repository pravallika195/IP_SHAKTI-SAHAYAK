import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Home from './pages/Home';
import Login from './pages/Login';
import Register from './pages/Register';
import MyInnovations from './pages/MyInnovations';
import InnovationSubmission from './pages/InnovationSubmission';
import AnalysisReport from './pages/AnalysisReport';
import PatentAssistant from './pages/PatentAssistant';
import { AuthProvider } from './context/AuthContext';
import { InnovationProvider } from './context/InnovationContext';

export default function App() {
  return (
    <AuthProvider>
      <InnovationProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/" element={<Layout />}>
              <Route index element={<Home />} />
              <Route path="login" element={<Login />} />
              <Route path="register" element={<Register />} />
              <Route
                path="my-innovations"
                element={
                  <ProtectedRoute>
                    <MyInnovations />
                  </ProtectedRoute>
                }
              />
              <Route path="innovation" element={<InnovationSubmission />} />
              <Route path="report" element={<AnalysisReport />} />
              <Route path="assistant" element={<PatentAssistant />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </InnovationProvider>
    </AuthProvider>
  );
}
