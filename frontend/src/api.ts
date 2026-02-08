const API_BASE = '/api';

export interface Profile {
  id: string;
  full_name: string;
  email?: string;
  phone?: string;
  linkedin_url?: string;
  github_username?: string;
  summary?: string;
  skills: string[];
  experience_years: number;
  preferred_locations: string[];
  target_roles: string[];
  parsed_resume?: Record<string, unknown>;
  portfolio_data?: Record<string, unknown>;
}

export interface Campaign {
  id: number;
  user_id: string;
  name: string;
  status: string;
  config: Record<string, unknown>;
  created_at?: string;
}

export interface Job {
  id: string;
  user_id: string;
  job_title: string;
  company_name: string;
  location?: string;
  source_url?: string;
  job_description?: string;
  match_score?: number;
  status: string;
  jd_analysis?: Record<string, unknown>;
  tailored_resume?: Record<string, unknown>;
  cover_email?: string;
  created_at?: string;
}

export interface CampaignCreate {
  user_id: string;
  name: string;
  job_titles: string[];
  locations: string[];
  keywords?: string[];
  max_jobs_per_run?: number;
  auto_apply?: boolean;
}

class ApiService {
  // Profile
  async getProfile(userId: string): Promise<Profile | null> {
    const res = await fetch(`${API_BASE}/profile/${userId}`);
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async createProfile(userId: string, data: Partial<Profile>): Promise<Profile> {
    const res = await fetch(`${API_BASE}/profile/${userId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async uploadResume(userId: string, file: File): Promise<{ message: string; parsed: Record<string, unknown> }> {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/profile/${userId}/resume/upload`, {
      method: 'POST',
      body: formData
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async syncGitHub(userId: string): Promise<{ message: string; data: Record<string, unknown> }> {
    const res = await fetch(`${API_BASE}/profile/${userId}/github/sync`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  // Campaigns
  async getCampaigns(userId: string): Promise<Campaign[]> {
    const res = await fetch(`${API_BASE}/campaigns/user/${userId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async createCampaign(data: CampaignCreate): Promise<Campaign> {
    const res = await fetch(`${API_BASE}/campaigns/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async runCampaign(campaignId: number): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE}/campaigns/${campaignId}/run`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async pauseCampaign(campaignId: number): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE}/campaigns/${campaignId}/pause`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  // Jobs
  async getJobs(userId: string, status?: string): Promise<Job[]> {
    const url = status 
      ? `${API_BASE}/jobs/user/${userId}?status=${status}`
      : `${API_BASE}/jobs/user/${userId}`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async getJob(jobId: string): Promise<Job> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async tailorResume(jobId: string): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/tailor`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async generatePDF(jobId: string): Promise<{ message: string; path: string }> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/generate-pdf`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async createDraft(jobId: string, recipientEmail: string): Promise<{ message: string }> {
    const res = await fetch(`${API_BASE}/jobs/${jobId}/create-draft`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ recipient_email: recipientEmail })
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  // Gmail
  async getGmailAuthUrl(userId: string): Promise<{ auth_url: string }> {
    const res = await fetch(`${API_BASE}/gmail/auth?user_id=${userId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async checkEmails(userId: string): Promise<{ message: string; results: Record<string, unknown>[] }> {
    const res = await fetch(`${API_BASE}/gmail/${userId}/check-emails`, { method: 'POST' });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  async getEmailThreads(userId: string): Promise<Record<string, unknown>[]> {
    const res = await fetch(`${API_BASE}/gmail/${userId}/threads`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }

  // Stats
  async getJobStats(userId: string): Promise<Record<string, number>> {
    const res = await fetch(`${API_BASE}/jobs/stats/${userId}`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }
}

export const api = new ApiService();
