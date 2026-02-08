
import { AppStatus, Job, Application, UserProfile } from './types';

export const MOCK_USER: UserProfile = {
  name: "Muhammad Ahmed",
  title: "Software Engineer",
  experience: "5 years",
  skills: [
    { name: "Python", level: 90 },
    { name: "React", level: 95 },
    { name: "AWS", level: 75 },
    { name: "MongoDB", level: 80 },
    { name: "TypeScript", level: 85 }
  ],
  projects: [
    { name: "E-commerce API", tech: ["Python", "Flask", "PostgreSQL"], description: "Scalable backend for multi-vendor store." },
    { name: "ML Fraud Detection", tech: ["Python", "Scikit-Learn", "FastAPI"], description: "Real-time anomaly detection in financial tx." },
    { name: "Portfolio Website", tech: ["React", "Tailwind"], description: "Personal showcase with dark mode and animations." }
  ],
  githubConnected: true
};

export const MOCK_JOBS: Job[] = [
  {
    id: "j1",
    company: "TechCorp",
    position: "Senior Full Stack Developer",
    location: "San Francisco, CA (Remote)",
    salary: "$160k - $210k",
    matchScore: 92,
    description: "Join our core platform team to build the next generation of cloud solutions.",
    techStack: ["React", "Node.js", "TypeScript", "AWS"],
    requirements: ["5+ years experience", "Strong CSS skills", "Cloud architecture knowledge"],
    postedDate: "2 days ago",
    logo: "https://picsum.photos/id/1/64/64"
  },
  {
    id: "j2",
    company: "StartupXYZ",
    position: "ML Engineer",
    location: "New York, NY (Hybrid)",
    salary: "$140k - $180k",
    matchScore: 85,
    description: "Help us revolutionize the Al space with cutting edge models.",
    techStack: ["Python", "PyTorch", "GCP"],
    requirements: ["Strong math background", "3+ years ML experience"],
    postedDate: "5 hours ago",
    logo: "https://picsum.photos/id/2/64/64"
  },
  {
    id: "j3",
    company: "EnterpriseSolutions",
    position: "DevOps Specialist",
    location: "Austin, TX",
    salary: "$130k - $170k",
    matchScore: 78,
    description: "Automate everything and manage our global infrastructure.",
    techStack: ["Terraform", "Kubernetes", "AWS", "Go"],
    requirements: ["CI/CD expert", "Security mindset"],
    postedDate: "1 week ago",
    logo: "https://picsum.photos/id/3/64/64"
  }
];

export const MOCK_APPLICATIONS: Application[] = [
  {
    id: "a1",
    jobId: "j1",
    status: AppStatus.SENT,
    appliedDate: "2024-05-15",
    createdDate: "2024-05-10",
    lastUpdated: "2024-05-15",
    emailThread: [
      { id: "e1", sender: "Recruiter @ TechCorp", subject: "Application Received", content: "Hi Alex, thanks for applying. We'll be in touch soon.", timestamp: "2024-05-15 10:00", type: 'incoming' }
    ]
  },
  {
    id: "a2",
    jobId: "j2",
    status: AppStatus.INTERVIEW,
    appliedDate: "2024-05-01",
    createdDate: "2024-04-28",
    lastUpdated: "2024-05-18",
    emailThread: [
      { id: "e2", sender: "Engineering Manager", subject: "Next Steps: Technical Interview", content: "Hi Alex, your profile looks great. Can we chat tomorrow?", timestamp: "2024-05-18 09:30", type: 'incoming' }
    ]
  },
  {
    id: "a3",
    jobId: "j3",
    status: AppStatus.DRAFT,
    createdDate: "2024-05-19",
    lastUpdated: "2024-05-19"
  }
];

export const STATUS_COLORS = {
  [AppStatus.DRAFT]: "bg-gray-100 text-gray-700",
  [AppStatus.SENT]: "bg-blue-100 text-blue-700",
  [AppStatus.UNDER_REVIEW]: "bg-yellow-100 text-yellow-700",
  [AppStatus.INTERVIEW]: "bg-purple-100 text-purple-700",
  [AppStatus.OFFER]: "bg-green-100 text-green-700",
  [AppStatus.REJECTED]: "bg-red-100 text-red-700"
};
