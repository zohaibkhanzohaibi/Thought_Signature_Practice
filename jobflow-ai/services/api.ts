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
// CAMPAIGN TYPES
// ============================================

export type JobStatus =
  | 'scouted'
  | 'analyzing'
  | 'tailored'
  | 'drafted'
  | 'sent'
  | 'replied'
  | 'interview'
  | 'offer'
  | 'rejected'
  | 'withdrawn';

export interface CampaignConfig {
  name: string;
  job_titles: string[];
  locations: string[];
  keywords?: string[];
  excluded_companies?: string[];
  total_days: number;
  jobs_per_day: number;
  auto_apply: boolean;
  started_at?: string;
  paused?: boolean;
  completed?: boolean;
  created_at?: string;
}

export interface Campaign {
  id: string;
  user_id: string;
  name: string;
  status: 'active' | 'paused' | 'completed';
  config: CampaignConfig;
  created_at: string;
  thought_signature?: any;
  last_run?: string;
  current_day?: number;
  days_remaining?: number;
  jobs_applied_today?: number;
  stats?: {
    total_jobs: number;
    by_status: Record<string, number>;
  };
}

export interface CampaignRun {
  id: string;
  agent_state_id: string;
  run_type: string;
  status: string;
  jobs_found: number;
  jobs_applied: number;
  summary?: string;
  started_at: string;
  completed_at?: string;
}

export interface CampaignCreateRequest {
  user_id: string;
  name: string;
  job_titles: string[];
  locations: string[];
  keywords?: string[];
  excluded_companies?: string[];
  total_days?: number;
  jobs_per_day?: number;
  auto_apply?: boolean;
}

// ============================================
// JOB TYPES
// ============================================

export interface JobApplication {
  id: number;
  user_id: string;
  job_title: string;
  company: string;
  location?: string;
  job_url?: string;
  job_description?: string;
  posted_date?: string;
  match_score?: number;
  status: JobStatus;
  jd_analysis?: Record<string, any>;
  tailored_resume?: Record<string, any>;
  cover_email?: string;
  resume_pdf_path?: string;
  gmail_draft_id?: string;
  company_email?: string;
  applied_at?: string;
  last_activity_at?: string;
  created_at: string;
  replies_log?: any[];
}

// ============================================
// API FUNCTIONS
// ============================================

class ApiService {
  async markJobAsApplied(jobId: number): Promise<any> {
    return this.request<any>(`/jobs/${jobId}/mark-applied`, {
      method: 'POST',
    });
  }
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

  async getCampaigns(userId: string): Promise<Campaign[]> {
    return this.request<Campaign[]>(`/campaigns/user/${userId}`);
  }

  async getCampaign(campaignId: string): Promise<Campaign> {
    return this.request<Campaign>(`/campaigns/${campaignId}`);
  }

  async createCampaign(campaign: CampaignCreateRequest): Promise<Campaign> {
    return this.request<Campaign>('/campaigns/', {
      method: 'POST',
      body: JSON.stringify(campaign),
    });
  }

  async runCampaign(campaignId: string): Promise<{ run_id: string; status: string; message: string }> {
    return this.request(`/campaigns/${campaignId}/run`, {
      method: 'POST',
    });
  }

  async getCampaignRuns(campaignId: string, limit: number = 10): Promise<CampaignRun[]> {
    return this.request<CampaignRun[]>(`/campaigns/${campaignId}/runs?limit=${limit}`);
  }

  async pauseCampaign(campaignId: string): Promise<{ status: string }> {
    return this.request(`/campaigns/${campaignId}/pause`, {
      method: 'PATCH',
    });
  }

  async resumeCampaign(campaignId: string): Promise<{ status: string }> {
    return this.request(`/campaigns/${campaignId}/resume`, {
      method: 'PATCH',
    });
  }

  async deleteCampaign(campaignId: string): Promise<{ status: string }> {
    return this.request(`/campaigns/${campaignId}`, {
      method: 'DELETE',
    });
  }

  // ============================================
  // JOBS ENDPOINTS
  // ============================================

  async getJobs(userId: string, status?: string): Promise<JobApplication[]> {
    const params = status ? `?status=${status}` : '';
    return this.request<JobApplication[]>(`/jobs/user/${userId}${params}`);
  }

  async searchJobs(userId: string, query: string, params: { location?: string, num_jobs?: number, days_limit?: number } = {}): Promise<any[]> {
    return this.request<any[]>(`/jobs/search?user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify({ query, ...params }),
    });
  }

  async manualExtract(userId: string, rawText: string): Promise<any> {
    return this.request<any>(`/jobs/manual-extract?user_id=${userId}`, {
      method: 'POST',
      body: JSON.stringify({ raw_text: rawText }),
    });
  }

  async getJob(jobId: number): Promise<JobApplication> {
    return this.request<JobApplication>(`/jobs/${jobId}`);
  }

  async updateJob(jobId: number, update: Partial<JobApplication>): Promise<JobApplication> {
    return this.request<JobApplication>(`/jobs/${jobId}`, {
      method: 'PATCH',
      body: JSON.stringify(update),
    });
  }

  async tailorResume(jobId: number): Promise<any> {
    return this.request<any>(`/jobs/${jobId}/tailor`, {
      method: 'POST',
    });
  }

  async generatePdf(jobId: number): Promise<void> {
    const response = await fetch(`${API_BASE}/jobs/${jobId}/generate-pdf`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Download failed' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `resume_job_${jobId}.pdf`; // Fallback name, browser might use header
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
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
