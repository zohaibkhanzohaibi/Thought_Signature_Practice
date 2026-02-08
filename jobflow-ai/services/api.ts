/**
 * API Service for backend communication
 * Connects to marathon_backend FastAPI server
 */

const API_BASE = '/api';

// ============================================
// TYPES
// ============================================

export interface ProfileData {
  id?: string;
  full_name: string;
  email?: string;
  phone?: string;
  linkedin_url?: string;
  github_username?: string;
  summary?: string;
  skills?: string[];
  experience_years?: number;
  preferred_locations?: string[];
  target_roles?: string[];
  parsed_resume?: Record<string, any>;
  portfolio_data?: Record<string, any>;
  created_at?: string;
}

export interface ResumeUploadResponse {
  message: string;
  parsed_data: {
    name?: string;
    email?: string;
    phone?: string;
    linkedin?: string;
    github?: string;
    skills?: string[];
    experience?: any[];
    education?: any[];
    raw_text?: string;
  };
}

export interface GitHubSyncResponse {
  message: string;
  portfolio: {
    username: string;
    profile?: {
      name?: string;
      bio?: string;
      company?: string;
      location?: string;
      blog?: string;
      public_repos?: number;
      followers?: number;
    };
    repositories: Array<{
      name: string;
      description?: string;
      url: string;
      language?: string;
      stars: number;
      forks: number;
      tech_stack?: string[];
      updated_at?: string;
    }>;
    tech_stack: string[];
    languages: Record<string, number>;
  };
}

export interface SkillsSummary {
  skills: string[];
  sources: {
    resume: boolean;
    github: boolean;
  };
}

// ============================================
// API FUNCTIONS
// ============================================

class ApiService {
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE}${endpoint}`;
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Request failed' }));
      const err = new Error(error.detail || `HTTP ${response.status}`);
      (err as any).status = response.status;
      throw err;
    }

    return response.json();
  }

  // ============================================
  // PROFILE ENDPOINTS
  // ============================================

  async getProfile(userId: string): Promise<ProfileData | null> {
    try {
      return await this.request<ProfileData>(`/profile/${userId}`);
    } catch (error: any) {
      if (error.status === 404 || error.message.includes('not found')) {
        return null;
      }
      throw error;
    }
  }

  async createOrUpdateProfile(userId: string, profile: Partial<ProfileData>): Promise<ProfileData> {
    return this.request<ProfileData>(`/profile/${userId}`, {
      method: 'POST',
      body: JSON.stringify(profile),
    });
  }

  async uploadResume(userId: string, file: File): Promise<ResumeUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE}/profile/${userId}/resume/upload`, {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  async syncGitHub(userId: string, username?: string): Promise<GitHubSyncResponse> {
    const params = username ? `?github_username=${encodeURIComponent(username)}` : '';
    return this.request<GitHubSyncResponse>(`/profile/${userId}/github/sync${params}`, {
      method: 'POST',
    });
  }

  async getSkillsSummary(userId: string): Promise<SkillsSummary> {
    return this.request<SkillsSummary>(`/profile/${userId}/skills`);
  }

  // ============================================
  // CAMPAIGNS ENDPOINTS
  // ============================================

  async getCampaigns(userId: string): Promise<any[]> {
    return this.request<any[]>(`/campaigns/${userId}`);
  }

  async createCampaign(campaign: any): Promise<any> {
    return this.request<any>('/campaigns', {
      method: 'POST',
      body: JSON.stringify(campaign),
    });
  }

  // ============================================
  // JOBS ENDPOINTS
  // ============================================

  async getJobs(userId: string, status?: string): Promise<any[]> {
    const params = status ? `?status=${status}` : '';
    return this.request<any[]>(`/jobs/${userId}${params}`);
  }

  async getJob(userId: string, jobId: string): Promise<any> {
    return this.request<any>(`/jobs/${userId}/${jobId}`);
  }

  async tailorResume(userId: string, jobId: string): Promise<any> {
    return this.request<any>(`/jobs/${userId}/${jobId}/tailor`, {
      method: 'POST',
    });
  }

  async generateCoverLetter(userId: string, jobId: string): Promise<any> {
    return this.request<any>(`/jobs/${userId}/${jobId}/cover-letter`, {
      method: 'POST',
    });
  }

  // ============================================
  // GMAIL ENDPOINTS
  // ============================================

  async getGmailAuthUrl(userId: string): Promise<{ auth_url: string }> {
    return this.request<{ auth_url: string }>(`/gmail/${userId}/auth-url`);
  }

  async getEmailThreads(userId: string): Promise<any[]> {
    return this.request<any[]>(`/gmail/${userId}/threads`);
  }

  async generateReply(userId: string, threadId: string): Promise<any> {
    return this.request<any>(`/gmail/${userId}/threads/${threadId}/generate-reply`, {
      method: 'POST',
    });
  }

  // ============================================
  // HEALTH CHECK
  // ============================================

  async healthCheck(): Promise<{ status: string }> {
    return this.request<{ status: string }>('/health');
  }
}

export const api = new ApiService();
