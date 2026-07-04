// frontend/src/lib/api-client.ts

export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export class ApiError extends Error {
  constructor(public status: number, public data: any) {
    super(data?.detail || 'An API error occurred');
    this.name = 'ApiError';
  }
}

// Token Management
export const getToken = () => typeof window !== 'undefined' ? localStorage.getItem('token') : null;
export const setToken = (token: string) => typeof window !== 'undefined' && localStorage.setItem('token', token);
export const removeToken = () => typeof window !== 'undefined' && localStorage.removeItem('token');

async function fetchClient<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401) {
      removeToken();
      if (typeof window !== 'undefined' && window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    const data = await response.json().catch(() => null);
    throw new ApiError(response.status, data);
  }

  // Handle empty responses
  if (response.status === 204) {
    return {} as T;
  }

  return response.json();
}

// ==========================================
// Types (Derived from Backend Pydantic Models)
// ==========================================

export interface Token {
  access_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  is_active: boolean;
  tier: string;
}

export interface Probe {
  probe_id: number;
  asn?: number;
  country?: string;
  latitude?: number;
  longitude?: number;
  status?: string;
}

export interface BGPEvent {
  id: string;
  time: string;
  collector: string;
  event_type: string;
  prefix?: string;
  peer_asn?: number;
  origin_asn?: number;
}

export interface Incident {
  id: string;
  detected_at: string;
  severity: string;
  incident_type: string;
  affected_asns?: number[];
  affected_prefixes?: string[];
  prediction_score?: number;
  explanation?: string;
  resolved_at?: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// ==========================================
// API Services
// ==========================================

export const authApi = {
  login: async (data: FormData): Promise<Token> => {
    // OAuth2PasswordBearer expects form data
    const response = await fetch(`${API_BASE_URL}/token`, {
      method: 'POST',
      body: data,
    });
    if (!response.ok) {
      const errData = await response.json().catch(() => null);
      throw new ApiError(response.status, errData);
    }
    return response.json();
  },
  
  register: (data: any): Promise<User> => fetchClient('/users/register', {
    method: 'POST',
    body: JSON.stringify(data),
  }),

  me: (): Promise<User> => fetchClient('/users/me'),
};

export const measurementsApi = {
  getProbes: (country?: string): Promise<Paginated<Probe>> => {
    const params = new URLSearchParams();
    if (country) params.append('country', country);
    return fetchClient(`/measurements/probes?${params.toString()}`);
  }
};

export const incidentsApi = {
  list: (severity?: string, activeOnly = false, page = 1): Promise<Paginated<Incident>> => {
    const params = new URLSearchParams({ page: page.toString(), size: '20' });
    if (severity) params.append('severity', severity);
    if (activeOnly) params.append('active_only', 'true');
    return fetchClient(`/incidents/?${params.toString()}`);
  },
  
  get: (id: string): Promise<Incident> => fetchClient(`/incidents/${id}`),
};
