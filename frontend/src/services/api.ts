import axios from 'axios';
import type { 
  Amendment, 
  ImpactAnalysisResult, 
  DependencyGraph, 
  ReviewTask, 
  AuditEntry 
} from '@/types';

const API_BASE = '/api/v1';

const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add request interceptor for auth token
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authService = {
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password });
    if (response.data.access_token) {
      localStorage.setItem('auth_token', response.data.access_token);
    }
    return response.data;
  },

  register: async (email: string, password: string, full_name: string) => {
    const response = await api.post('/auth/register', { email, password, full_name });
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('auth_token');
  },

  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },
};

export const amendmentService = {
  upload: async (data: { 
    old_text: string; 
    new_text: string; 
    change_type?: string;
    change_description?: string;
  }): Promise<Amendment> => {
    const response = await api.post('/amendments/upload', data);
    return response.data;
  },

  compare: async (id: string): Promise<Amendment> => {
    const response = await api.post(`/amendments/${id}/compare`);
    return response.data;
  },

  get: async (id: string): Promise<Amendment> => {
    const response = await api.get(`/amendments/${id}`);
    return response.data;
  },

  list: async (): Promise<Amendment[]> => {
    const response = await api.get('/amendments/');
    return response.data.amendments;
  },
};

export const impactService = {
  analyze: async (id: string): Promise<ImpactAnalysisResult> => {
    const response = await api.post(`/impact/${id}/analyze`);
    return response.data;
  },

  get: async (id: string): Promise<ImpactAnalysisResult> => {
    const response = await api.get(`/impact/${id}`);
    return response.data;
  },

  getSummary: async (id: string) => {
    const response = await api.get(`/impact/${id}/summary`);
    return response.data;
  },
};

export const graphService = {
  getFull: async (): Promise<DependencyGraph> => {
    const response = await api.get('/graph/');
    return response.data;
  },

  getForAmendment: async (id: string): Promise<DependencyGraph> => {
    const response = await api.get(`/graph/${id}`);
    return response.data;
  },

  getNode: async (nodeId: string) => {
    const response = await api.get(`/graph/node/${nodeId}`);
    return response.data;
  },

  search: async (params: { node_type?: string; search_term?: string }) => {
    const response = await api.get('/graph/search', { params });
    return response.data;
  },
};

export const reviewService = {
  generatePlan: async (id: string): Promise<{ tasks: ReviewTask[] }> => {
    const response = await api.post(`/review/${id}/plan`);
    return response.data;
  },

  getTasks: async (id: string): Promise<ReviewTask[]> => {
    const response = await api.get(`/review/${id}/tasks`);
    return response.data;
  },

  updateTaskStatus: async (taskId: string, status: string) => {
    const response = await api.patch(`/review/tasks/${taskId}`, { status });
    return response.data;
  },
};

export const auditService = {
  getTrail: async (id: string): Promise<AuditEntry[]> => {
    const response = await api.get(`/audit/${id}`);
    return response.data.entries;
  },

  list: async (params?: { 
    limit?: number; 
    start_date?: string; 
    end_date?: string;
  }): Promise<AuditEntry[]> => {
    const response = await api.get('/audit/', { params });
    return response.data.entries;
  },
};

// Simplified API object for component usage
export const api = {
  // Amendments
  uploadAmendment: async (data: { 
    old_text: string; 
    new_text: string; 
    change_type?: string;
    change_description?: string;
  }) => {
    const response = await api.post('/amendments/upload', data);
    return response.data;
  },

  compareAmendment: async (id: string) => {
    const response = await api.post(`/amendments/${id}/compare`);
    return response.data;
  },

  getAmendment: async (id: string) => {
    const response = await api.get(`/amendments/${id}`);
    return response.data;
  },

  listAmendments: async () => {
    const response = await api.get('/amendments/');
    return response.data;
  },

  // Impact Analysis
  analyzeImpact: async (id: string) => {
    const response = await api.get(`/impact/${id}`);
    return response.data;
  },

  // Graph
  getGraph: async (id: string) => {
    const response = await api.get(`/graph/${id}`);
    return response.data;
  },

  // Review Plan
  generateReviewPlan: async (id: string) => {
    const response = await api.post(`/review/plan/${id}`);
    return response.data;
  },

  updateTaskStatus: async (taskId: string, status: string) => {
    const response = await api.patch(`/review/tasks/${taskId}`, { status });
    return response.data;
  },

  // Audit
  getAuditTrail: async (id: string) => {
    const response = await api.get(`/audit/${id}`);
    return response.data;
  },

  getAuditHistory: async (limit = 50) => {
    const response = await api.get('/audit/', { params: { limit } });
    return response.data;
  },

  // Auth
  login: async (email: string, password: string) => {
    const response = await api.post('/auth/login', { email, password });
    if (response.data.access_token) {
      localStorage.setItem('auth_token', response.data.access_token);
    }
    return response.data;
  },

  logout: () => {
    localStorage.removeItem('auth_token');
  },
};

export default api;
