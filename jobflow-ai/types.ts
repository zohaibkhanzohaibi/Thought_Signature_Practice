
export enum AppStatus {
  DRAFT = 'Draft',
  SENT = 'Sent',
  UNDER_REVIEW = 'Under Review',
  INTERVIEW = 'Interview',
  OFFER = 'Offer',
  REJECTED = 'Rejected'
}

export interface Job {
  id: string;
  company: string;
  position: string;
  location: string;
  salary: string;
  matchScore: number;
  description: string;
  techStack: string[];
  requirements: string[];
  postedDate: string;
  logo: string;
}

export interface Application {
  id: string;
  jobId: string;
  status: AppStatus;
  appliedDate?: string;
  createdDate: string;
  lastUpdated: string;
  notes?: string;
  resumeUrl?: string;
  coverLetter?: string;
  emailThread?: EmailMessage[];
}

export interface EmailMessage {
  id: string;
  sender: string;
  subject: string;
  content: string;
  timestamp: string;
  isAiGenerated?: boolean;
  type: 'incoming' | 'outgoing';
}

export interface UserProfile {
  name: string;
  title: string;
  experience: string;
  skills: { name: string; level: number }[];
  projects: { name: string; tech: string[]; description: string; githubUrl?: string }[];
  githubConnected: boolean;
}

export type ViewType = 'dashboard' | 'profile' | 'discovery' | 'manager' | 'inbox' | 'analytics' | 'settings';
