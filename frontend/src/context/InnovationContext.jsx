import React, { createContext, useContext, useState } from 'react';
import { analyzeInnovation } from '../api/client';

const InnovationContext = createContext(null);

export function InnovationProvider({ children }) {
  const [analysisResult, setAnalysisResult] = useState(null);
  const [lastSubmittedInnovation, setLastSubmittedInnovation] = useState(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisError, setAnalysisError] = useState(null);
  const [uploadedDocuments, setUploadedDocuments] = useState([]);

  const runAnalysis = async (payload) => {
    setIsAnalyzing(true);
    setAnalysisError(null);
    try {
      setLastSubmittedInnovation(payload);
      const result = await analyzeInnovation(payload);
      setAnalysisResult(result);
      return result;
    } catch (err) {
      const msg = err.message || 'Innovation analysis request failed.';
      setAnalysisError(msg);
      throw new Error(msg);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const clearAnalysis = () => {
    setAnalysisResult(null);
    setAnalysisError(null);
  };

  const clearUploadedDocuments = () => {
    setUploadedDocuments([]);
  };

  return (
    <InnovationContext.Provider
      value={{
        analysisResult,
        setAnalysisResult,
        lastSubmittedInnovation,
        isAnalyzing,
        analysisError,
        uploadedDocuments,
        setUploadedDocuments,
        clearUploadedDocuments,
        runAnalysis,
        clearAnalysis,
      }}
    >
      {children}
    </InnovationContext.Provider>
  );
}

export function useInnovation() {
  const context = useContext(InnovationContext);
  if (!context) {
    throw new Error('useInnovation must be used within an InnovationProvider');
  }
  return context;
}

