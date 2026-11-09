import axios from 'axios';

/**
 * Reusable Axios API Client configured for IP-SAKTI Sahayak.
 * Routes requests through the Vite development proxy (/api, /health).
 * withCredentials enabled for HttpOnly JWT cookie management.
 */
export const apiClient = axios.create({
  baseURL: '',
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true, // Enables HttpOnly cookie exchange
  timeout: 120000, // 120s buffer for deep multi-query RAG and LLM synthesis
});

// Response interceptor for consistent error extraction
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    let message = 'Network error or server unreachable.';
    if (error.response?.data?.error) {
      message = error.response.data.error;
    } else if (error.response?.data?.message) {
      message = error.response.data.message;
    } else if (error.message) {
      message = error.message;
    }
    return Promise.reject(new Error(message));
  }
);

// ------------------------------------------------------------------------------
// Health & Diagnostics
// ------------------------------------------------------------------------------
export const getHealth = async () => {
  const response = await apiClient.get('/health');
  return response.data;
};

export const getCollectionsStatus = async () => {
  const response = await apiClient.get('/api/collections/status');
  return response.data;
};

export const queryRAG = async ({ query, language = 'English' }) => {
  const response = await apiClient.post('/api/query', { query, language });
  return response.data;
};

// ------------------------------------------------------------------------------
// Authentication Endpoints
// ------------------------------------------------------------------------------
export const registerUser = async ({ email, password, full_name, role = 'researcher' }) => {
  const response = await apiClient.post('/api/auth/register', {
    email,
    password,
    full_name,
    role,
  });
  return response.data;
};

export const loginUser = async ({ email, password }) => {
  const response = await apiClient.post('/api/auth/login', {
    email,
    password,
  });
  return response.data;
};

export const logoutUser = async () => {
  const response = await apiClient.post('/api/auth/logout');
  return response.data;
};

export const getCurrentUser = async () => {
  const response = await apiClient.get('/api/auth/me');
  return response.data;
};

// ------------------------------------------------------------------------------
// Innovation Project & Version Endpoints
// ------------------------------------------------------------------------------
export const getInnovations = async () => {
  const response = await apiClient.get('/api/innovations');
  return response.data;
};

export const createInnovation = async (payload) => {
  const response = await apiClient.post('/api/innovations', payload);
  return response.data;
};

export const getInnovation = async (id) => {
  const response = await apiClient.get(`/api/innovations/${id}`);
  return response.data;
};

export const updateInnovation = async (id, payload) => {
  const response = await apiClient.put(`/api/innovations/${id}`, payload);
  return response.data;
};

export const deleteInnovation = async (id) => {
  const response = await apiClient.delete(`/api/innovations/${id}`);
  return response.data;
};

// ------------------------------------------------------------------------------
// Analysis Execution & Run History
// ------------------------------------------------------------------------------
export const analyzeInnovationProject = async (innovationId) => {
  const response = await apiClient.post(`/api/innovations/${innovationId}/analyze`);
  return response.data;
};

export const getInnovationRuns = async (innovationId) => {
  const response = await apiClient.get(`/api/innovations/${innovationId}/runs`);
  return response.data;
};

export const getSpecificRun = async (innovationId, runId) => {
  const response = await apiClient.get(`/api/innovations/${innovationId}/runs/${runId}`);
  return response.data;
};

export const analyzeInnovation = async (payload) => {
  const response = await apiClient.post('/api/innovation/analyze', payload);
  return response.data;
};

// ------------------------------------------------------------------------------
// Sandboxed Document Upload
// ------------------------------------------------------------------------------
export const uploadInnovationDocument = async (file, onUploadProgress) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await apiClient.post('/api/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: (progressEvent) => {
      if (onUploadProgress && progressEvent.total) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        onUploadProgress(percentCompleted);
      }
    },
  });
  return response.data;
};

export const deleteInnovationDocument = async (documentId) => {
  const response = await apiClient.delete(`/api/documents/${documentId}`);
  return response.data;
};

// ------------------------------------------------------------------------------
// Persistent Conversational Patent Assistant Threads
// ------------------------------------------------------------------------------
export const getAssistantThreads = async () => {
  const response = await apiClient.get('/api/assistant/threads');
  return response.data;
};

export const createAssistantThread = async ({ session_id, title = 'New Research Thread', language = 'English' }) => {
  const response = await apiClient.post('/api/assistant/threads', {
    session_id,
    title,
    language,
  });
  return response.data;
};

export const getAssistantThread = async (threadId) => {
  const response = await apiClient.get(`/api/assistant/threads/${threadId}`);
  return response.data;
};

export const deleteAssistantThread = async (threadId) => {
  const response = await apiClient.delete(`/api/assistant/threads/${threadId}`);
  return response.data;
};

export const chatAssistant = async ({ sessionId, query, language = 'English', filters = null }) => {
  const response = await apiClient.post('/api/assistant/chat', {
    session_id: sessionId,
    query,
    language,
    filters,
  });
  return response.data;
};

export const resetAssistant = async (sessionId) => {
  const response = await apiClient.post('/api/assistant/reset', {
    session_id: sessionId,
  });
  return response.data;
};

export default apiClient;
