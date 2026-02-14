import React, { useState, useEffect } from 'react';
import {
  ChevronDown,
  ChevronRight,
  Play,
  Pause,
  Plus,
  RefreshCw,
  Briefcase,
  MapPin,
  Calendar,
  ExternalLink,
  Clock,
  CheckCircle,
  AlertCircle,
  Send,
  Eye,
  FileText,
  X
} from 'lucide-react';
import { api, Campaign, JobApplication, CampaignRun, JobStatus, ProfileData } from '../../services/api';

// --- Types ---

interface ApplicationsViewProps {
  userId: string;
}

interface CreateCampaignModalProps {
  isOpen: boolean;
  onClose: () => void;
  userId: string;
  onCreated: () => void;
}

// --- Constants ---

const STATUS_COLORS: Record<JobStatus, string> = {
  scouted: 'bg-slate-100 text-slate-700 border-slate-200',
  analyzing: 'bg-amber-100 text-amber-700 border-amber-200',
  tailored: 'bg-blue-100 text-blue-700 border-blue-200',
  drafted: 'bg-indigo-100 text-indigo-700 border-indigo-200',
  sent: 'bg-cyan-100 text-cyan-700 border-cyan-200',
  replied: 'bg-purple-100 text-purple-700 border-purple-200',
  interview: 'bg-violet-100 text-violet-700 border-violet-200',
  offer: 'bg-green-100 text-green-700 border-green-200',
  rejected: 'bg-red-100 text-red-700 border-red-200',
  withdrawn: 'bg-gray-100 text-gray-500 border-gray-200',
};

const STATUS_ORDER: JobStatus[] = [
  'scouted', 'analyzing', 'tailored', 'drafted', 'sent', 'replied', 'interview', 'offer', 'rejected', 'withdrawn'
];

// --- Helper Components ---

const JobStatusBadge = ({ status }: { status: JobStatus }) => (
  <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-wider border ${STATUS_COLORS[status]}`}>
    {status}
  </span>
);

const JobRow = ({ job }: { job: JobApplication }) => {
  const [showDetails, setShowDetails] = useState(false);

  // Handlers must be defined BEFORE the return statement
  const [profile, setProfile] = useState<ProfileData | null>(null);

  useEffect(() => {
    // Fetch user profile for resume check
    api.getProfile(job.user_id).then(setProfile).catch(() => setProfile(null));
  }, [job.user_id]);

  const handleDownloadResume = async () => {
    if (!job.id) return;
    if (!job.job_description) {
      alert('Job description is missing. Please update the job before tailoring.');
      return;
    }
    if (!profile || (!profile.raw_text && !profile.parsed_resume)) {
      alert('Resume not found. Please upload your resume in your profile.');
      return;
    }
    try {
      // Only tailor if not already done or empty
      if (job.status === 'scouted' && (!job.tailored_resume || Object.keys(job.tailored_resume).length === 0)) {
        // Show loading state or toast here? For now just await.
        await api.tailorResume(job.id);
      }
      await api.generatePdf(job.id);
    } catch (err) {
      console.error(err);
      alert('Failed to tailor or download resume PDF.');
    }
  };

  const handleMarkAsApplied = async () => {
    if (!job.id) return;
    if (!['scouted', 'tailored', 'drafted'].includes(job.status)) {
      alert('Job cannot be marked as applied unless its status is scouted, tailored, or drafted.');
      return;
    }
    try {
      await api.markJobAsApplied(job.id);
      alert('Job marked as applied!');
    } catch (err) {
      alert('Failed to mark job as applied.');
    }
  };

  return (
    <div className="bg-slate-50 rounded-xl border border-slate-100 overflow-hidden">
      <div
        className="flex items-center justify-between px-4 py-3 cursor-pointer hover:bg-slate-100/50 transition-colors"
        onClick={() => setShowDetails(!showDetails)}
      >
        <div className="flex items-center gap-4">
          <div className="p-2 bg-white border border-slate-200 rounded-lg">
            <Briefcase size={18} className="text-slate-400" />
          </div>
          <div>
            <h4 className="font-bold text-slate-700">{job.job_title}</h4>
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <span>{job.company}</span>
              <span>•</span>
              <span className="flex items-center gap-1">
                <MapPin size={12} /> {job.location}
              </span>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {job.match_score && (
            <div className="text-right">
              <div className="text-sm font-bold text-slate-700">{job.match_score}%</div>
              <div className="text-[10px] text-slate-400 uppercase">Match</div>
            </div>
          )}
          {job.job_url && (
            <a
              href={job.job_url}
              target="_blank"
              rel="noopener noreferrer"
              className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 rounded-lg"
              onClick={e => e.stopPropagation()}
            >
              <ExternalLink size={16} />
            </a>
          )}
          <ChevronRight size={16} className={`text-slate-400 transition-transform ${showDetails ? 'rotate-90' : ''}`} />
        </div>
      </div>

      {showDetails && (
        <div className="border-t border-slate-100 p-4 bg-white space-y-3">
          {job.job_description && (
            <div>
              <h5 className="text-xs font-bold uppercase text-slate-400 mb-1">Description</h5>
              <p className="text-sm text-slate-600 line-clamp-3">{job.job_description}</p>
            </div>
          )}

          <div className="flex items-center gap-2 pt-2">
            {job.tailored_resume && Object.keys(job.tailored_resume).length > 0 && (
              <span className="flex items-center gap-1 text-xs text-green-600 bg-green-50 px-2 py-1 rounded-lg">
                <FileText size={12} /> Resume Tailored
              </span>
            )}
            {job.cover_email && (
              <span className="flex items-center gap-1 text-xs text-blue-600 bg-blue-50 px-2 py-1 rounded-lg">
                <Send size={12} /> Email Drafted
              </span>
            )}
            {job.applied_at && (
              <span className="text-xs text-slate-500">
                Applied: {new Date(job.applied_at).toLocaleDateString()}
              </span>
            )}
          </div>

          {/* Actions for scouted jobs */}
          {job.status === 'scouted' && !job.cover_email && (
            <div className="flex items-center gap-3 mt-3">
              <button
                className="px-4 py-2 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-700 text-sm"
                onClick={handleDownloadResume}
              >
                Tailor & Download Resume
              </button>
              <button
                className="px-4 py-2 bg-green-600 text-white font-bold rounded-xl hover:bg-green-700 text-sm"
                onClick={handleMarkAsApplied}
              >
                Mark as Applied
              </button>
            </div>
          )}

          {/* Download button for already tailored jobs */}
          {job.status !== 'scouted' && (job.tailored_resume || job.resume_pdf_path) && (
            <div className="mt-3">
              <button
                className="px-4 py-2 bg-slate-100 text-slate-700 font-bold rounded-xl hover:bg-slate-200 text-sm border border-slate-200 flex items-center gap-2"
                onClick={handleDownloadResume}
              >
                <FileText size={16} />
                Download Resume PDF
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

const CampaignCard = ({
  campaign,
  jobs,
  runs,
  onRun,
  onPauseResume,
  isRunning
}: {
  campaign: Campaign;
  jobs: JobApplication[];
  runs: CampaignRun[];
  onRun: () => void;
  onPauseResume: () => void;
  isRunning: boolean;
}) => {
  const [expanded, setExpanded] = useState(false);
  const [showRuns, setShowRuns] = useState(false);

  const campaignJobs = jobs.filter(j => j.campaign_id === campaign.id);

  const jobsByStatus = STATUS_ORDER.reduce((acc, status) => {
    acc[status] = campaignJobs.filter(j => j.status === status);
    return acc;
  }, {} as Record<JobStatus, JobApplication[]>);

  const isPaused = campaign.status === 'paused';
  const isCompleted = campaign.status === 'completed';

  // Day tracking
  const totalDays = campaign.config.total_days || 7;
  const currentDay = campaign.current_day || 1;
  const daysRemaining = campaign.days_remaining ?? totalDays;
  const jobsPerDay = campaign.config.jobs_per_day || 5;
  const jobsAppliedToday = campaign.jobs_applied_today || 0;

  return (
    <div className={`bg-white rounded-2xl border shadow-sm overflow-hidden ${isCompleted ? 'border-slate-200 opacity-75' : 'border-slate-100'}`}>
      {/* Campaign Header */}
      <div
        className="p-6 cursor-pointer hover:bg-slate-50/50 transition-colors"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <button className="p-1 text-slate-400">
              {expanded ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
            </button>
            <div>
              <div className="flex items-center gap-3">
                <h3 className="text-lg font-bold text-slate-800">{campaign.name}</h3>
                <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider ${isCompleted
                  ? 'bg-slate-100 text-slate-500 border border-slate-200'
                  : isPaused
                    ? 'bg-amber-100 text-amber-700 border border-amber-200'
                    : 'bg-green-100 text-green-700 border border-green-200'
                  }`}>
                  {campaign.status}
                </span>
              </div>
              <div className="flex items-center gap-4 mt-1 text-sm text-slate-500">
                <span className="flex items-center gap-1">
                  <Briefcase size={14} />
                  {campaign.config.job_titles.slice(0, 2).join(', ')}
                  {campaign.config.job_titles.length > 2 && ` +${campaign.config.job_titles.length - 2}`}
                </span>
                <span className="flex items-center gap-1">
                  <MapPin size={14} />
                  {campaign.config.locations.slice(0, 2).join(', ')}
                  {campaign.config.locations.length > 2 && ` +${campaign.config.locations.length - 2}`}
                </span>
                <span className="flex items-center gap-1">
                  <Calendar size={14} />
                  Day {currentDay}/{totalDays}
                </span>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3" onClick={e => e.stopPropagation()}>
            {/* Day Progress */}
            <div className="flex flex-col items-center bg-blue-50 rounded-xl px-4 py-2">
              <span className="text-xs font-bold text-blue-400">Days Left</span>
              <span className="text-lg font-bold text-blue-700">{daysRemaining}</span>
            </div>

            {/* Jobs Today */}
            <div className="flex flex-col items-center bg-slate-50 rounded-xl px-4 py-2">
              <span className="text-xs font-bold text-slate-400">Today</span>
              <span className="text-sm font-bold text-slate-700">{jobsAppliedToday}/{jobsPerDay}</span>
            </div>

            {/* Stats Summary */}
            <div className="flex flex-col items-center bg-slate-50 rounded-xl px-4 py-2">
              <span className="text-xs font-bold text-slate-400">Total Jobs</span>
              <span className="text-sm font-bold text-slate-700">{campaign.stats?.total_jobs || 0}</span>
            </div>

            {/* Run Button */}
            <button
              onClick={onRun}
              disabled={isRunning || isPaused || isCompleted}
              className={`p-2.5 rounded-xl transition-all ${isRunning
                ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                : (isPaused || isCompleted)
                  ? 'bg-slate-100 text-slate-400 cursor-not-allowed'
                  : 'bg-green-50 text-green-600 hover:bg-green-100'
                }`}
              title={isCompleted ? 'Campaign completed' : isPaused ? 'Resume campaign to run' : 'Run campaign now'}
            >
              {isRunning ? <RefreshCw size={18} className="animate-spin" /> : <Play size={18} />}
            </button>

            {/* Pause/Resume Button - hidden for completed */}
            {!isCompleted && (
              <button
                onClick={onPauseResume}
                className={`p-2.5 rounded-xl transition-all ${isPaused
                  ? 'bg-green-50 text-green-600 hover:bg-green-100'
                  : 'bg-amber-50 text-amber-600 hover:bg-amber-100'
                  }`}
                title={isPaused ? 'Resume campaign' : 'Pause campaign'}
              >
                {isPaused ? <Play size={18} /> : <Pause size={18} />}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {expanded && (
        <div className="border-t border-slate-100">
          {/* Run History Toggle */}
          <div className="px-6 py-3 bg-slate-50/50 border-b border-slate-100">
            <button
              onClick={() => setShowRuns(!showRuns)}
              className="text-sm font-medium text-slate-600 hover:text-blue-600 flex items-center gap-2"
            >
              <Clock size={14} />
              Run History ({runs.length})
              {showRuns ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
            </button>

            {showRuns && runs.length > 0 && (
              <div className="mt-3 space-y-2">
                {runs.slice(0, 5).map(run => (
                  <div key={run.id} className="flex items-center justify-between bg-white rounded-lg px-4 py-2 text-sm">
                    <div className="flex items-center gap-3">
                      {run.status === 'completed' ? (
                        <CheckCircle size={14} className="text-green-500" />
                      ) : run.status === 'running' ? (
                        <RefreshCw size={14} className="text-blue-500 animate-spin" />
                      ) : (
                        <AlertCircle size={14} className="text-red-500" />
                      )}
                      <span className="text-slate-600">
                        {new Date(run.started_at).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex items-center gap-4 text-slate-500">
                      <span>Found: <strong className="text-slate-700">{run.jobs_found}</strong></span>
                      <span>Applied: <strong className="text-slate-700">{run.jobs_applied}</strong></span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Jobs by Status */}
          <div className="p-6 space-y-4">
            {STATUS_ORDER.map(status => {
              const statusJobs = jobsByStatus[status];
              if (statusJobs.length === 0) return null;

              return (
                <div key={status} className="space-y-2">
                  <div className="flex items-center gap-2">
                    <JobStatusBadge status={status} />
                    <span className="text-sm font-medium text-slate-500">({statusJobs.length})</span>
                  </div>
                  <div className="grid gap-2">
                    {statusJobs.slice(0, 5).map(job => (
                      <div key={job.id}>
                        <JobRow job={job} />
                      </div>
                    ))}
                    {statusJobs.length > 5 && (
                      <button className="text-sm text-blue-600 hover:text-blue-700 font-medium pl-4">
                        Show {statusJobs.length - 5} more...
                      </button>
                    )}
                  </div>
                </div>
              );
            })}

            {campaignJobs.length === 0 && (
              <div className="text-center py-8 text-slate-400">
                <Eye size={32} className="mx-auto mb-2 opacity-50" />
                <p>No jobs found yet. Run the campaign to start scouting!</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const CreateCampaignModal = ({ isOpen, onClose, userId, onCreated }: CreateCampaignModalProps) => {
  const [name, setName] = useState('');
  const [jobTitles, setJobTitles] = useState('');
  const [locations, setLocations] = useState('');
  const [keywords, setKeywords] = useState('');
  const [totalDays, setTotalDays] = useState(7);
  const [jobsPerDay, setJobsPerDay] = useState(5);
  const [maxJobsPerRun, setMaxJobsPerRun] = useState(10);
  const [autoApply, setAutoApply] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      await api.createCampaign({
        user_id: userId,
        name,
        job_titles: jobTitles.split(',').map(s => s.trim()).filter(Boolean),
        locations: locations.split(',').map(s => s.trim()).filter(Boolean),
        keywords: keywords ? keywords.split(',').map(s => s.trim()).filter(Boolean) : undefined,
        total_days: totalDays,
        jobs_per_day: jobsPerDay,
        auto_apply: autoApply,
      });
      onCreated();
      onClose();
      // Reset form
      setName('');
      setJobTitles('');
      setLocations('');
    } catch (error) {
      console.error('Failed to create campaign:', error);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 animate-in fade-in duration-200">
      <div className="bg-white rounded-2xl w-full max-w-lg mx-4 animate-in slide-in-from-bottom-4 duration-300">
        <div className="flex items-center justify-between p-6 border-b border-slate-100">
          <h2 className="text-xl font-bold text-slate-800">Create Campaign</h2>
          <button onClick={onClose} className="p-2 text-slate-400 hover:text-slate-600 rounded-lg">
            <X size={20} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          <div>
            <label className="block text-sm font-bold text-slate-600 mb-1">Campaign Name</label>
            <input
              type="text"
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="My Job Search"
              className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-600 mb-1">Job Titles (comma separated)</label>
            <input
              type="text"
              value={jobTitles}
              onChange={e => setJobTitles(e.target.value)}
              placeholder="Software Engineer, Frontend Developer, Full Stack Developer"
              className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-600 mb-1">Locations (comma separated)</label>
            <input
              type="text"
              value={locations}
              onChange={e => setLocations(e.target.value)}
              placeholder="Remote, New York, San Francisco"
              className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-bold text-slate-600 mb-1">Keywords (optional)</label>
            <input
              type="text"
              value={keywords}
              onChange={e => setKeywords(e.target.value)}
              placeholder="React, TypeScript, Node.js"
              className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none"
            />
          </div>

          {/* Campaign Duration Settings */}
          <div className="flex items-center gap-4">
            <div className="flex-1">
              <label className="block text-sm font-bold text-slate-600 mb-1">Campaign Days</label>
              <input
                type="number"
                value={totalDays}
                onChange={e => setTotalDays(Number(e.target.value))}
                min={1}
                max={90}
                className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none"
              />
              <span className="text-xs text-slate-400 mt-1">Total days to run</span>
            </div>

            <div className="flex-1">
              <label className="block text-sm font-bold text-slate-600 mb-1">Jobs Per Day</label>
              <input
                type="number"
                value={jobsPerDay}
                onChange={e => setJobsPerDay(Number(e.target.value))}
                min={1}
                max={50}
                className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none"
              />
              <span className="text-xs text-slate-400 mt-1">Max applications/day</span>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex-1">
              <label className="block text-sm font-bold text-slate-600 mb-1">Jobs Per Run</label>
              <input
                type="number"
                value={maxJobsPerRun}
                onChange={e => setMaxJobsPerRun(Number(e.target.value))}
                min={1}
                max={50}
                className="w-full px-4 py-3 rounded-xl border border-slate-200 focus:border-blue-400 focus:ring-2 focus:ring-blue-100 outline-none"
              />
              <span className="text-xs text-slate-400 mt-1">Jobs to scout per run</span>
            </div>

            <div className="flex-1">
              <label className="block text-sm font-bold text-slate-600 mb-1">Auto Apply</label>
              <button
                type="button"
                onClick={() => setAutoApply(!autoApply)}
                className={`w-full px-4 py-3 rounded-xl border transition-colors ${autoApply
                  ? 'bg-green-50 border-green-300 text-green-700'
                  : 'bg-slate-50 border-slate-200 text-slate-500'
                  }`}
              >
                {autoApply ? 'Enabled' : 'Disabled'}
              </button>
              <span className="text-xs text-slate-400 mt-1">Auto-send applications</span>
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full py-3 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-4"
          >
            {isSubmitting ? 'Creating...' : 'Create Campaign'}
          </button>
        </form>
      </div>
    </div>
  );
};

// --- Main Component ---

export const ApplicationsView = ({ userId }: ApplicationsViewProps) => {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [jobs, setJobs] = useState<JobApplication[]>([]);
  const [campaignRuns, setCampaignRuns] = useState<Record<number, CampaignRun[]>>({});
  const [isLoading, setIsLoading] = useState(true);
  const [runningCampaigns, setRunningCampaigns] = useState<Set<number>>(new Set());
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchData = async () => {
    try {
      setIsLoading(true);
      setError(null);

      const [campaignsData, jobsData] = await Promise.all([
        api.getCampaigns(userId),
        api.getJobs(userId),
      ]);

      setCampaigns(campaignsData);
      setJobs(jobsData);

      // Fetch runs for each campaign
      const runsPromises = campaignsData.map(c =>
        api.getCampaignRuns(c.id).then(runs => ({ id: c.id, runs }))
      );
      const runsResults = await Promise.all(runsPromises);
      const runsMap: Record<number, CampaignRun[]> = {};
      runsResults.forEach(r => { runsMap[r.id] = r.runs; });
      setCampaignRuns(runsMap);

    } catch (err) {
      console.error('Failed to fetch data:', err);
      setError('Failed to load campaigns. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (userId) {
      fetchData();
    }
  }, [userId]);

  const handleRunCampaign = async (campaignId: number) => {
    setRunningCampaigns(prev => new Set(prev).add(campaignId));
    try {
      await api.runCampaign(String(campaignId));
      // Refresh after a delay to get updated data
      setTimeout(fetchData, 2000);
    } catch (err) {
      console.error('Failed to run campaign:', err);
    } finally {
      setRunningCampaigns(prev => {
        const next = new Set(prev);
        next.delete(campaignId);
        return next;
      });
    }
  };

  const handlePauseResume = async (campaign: Campaign) => {
    try {
      if (campaign.status === 'paused') {
        await api.resumeCampaign(campaign.id);
      } else {
        await api.pauseCampaign(campaign.id);
      }
      fetchData();
    } catch (err) {
      console.error('Failed to pause/resume campaign:', err);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw size={32} className="text-blue-500 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-6 animate-in slide-in-from-bottom-4 duration-500">
      {/* Header */}
      <div className="bg-white rounded-[32px] border border-slate-100 shadow-sm overflow-hidden">
        <div className="p-8 flex justify-between items-center">
          <div>
            <h3 className="text-xl font-bold text-slate-800">Job Campaigns</h3>
            <p className="text-sm font-medium text-slate-400 mt-1">
              {campaigns.length} campaign{campaigns.length !== 1 ? 's' : ''} · {jobs.length} job{jobs.length !== 1 ? 's' : ''} found
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={fetchData}
              className="px-4 py-2 bg-white border border-slate-200 text-slate-600 font-bold rounded-xl text-sm hover:bg-slate-50 shadow-sm flex items-center gap-2"
            >
              <RefreshCw size={16} />
              Refresh
            </button>
            <button
              onClick={() => setShowCreateModal(true)}
              className="px-4 py-2 bg-blue-600 text-white font-bold rounded-xl text-sm shadow-lg shadow-blue-100 hover:bg-blue-700 flex items-center gap-2"
            >
              <Plus size={16} />
              New Campaign
            </button>
          </div>
        </div>
      </div>

      {/* Error State */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-2xl p-4 text-red-700 text-sm">
          {error}
        </div>
      )}

      {/* Campaigns List */}
      {campaigns.length === 0 ? (
        <div className="bg-white rounded-[32px] border border-slate-100 shadow-sm p-12 text-center">
          <Briefcase size={48} className="mx-auto text-slate-300 mb-4" />
          <h3 className="text-lg font-bold text-slate-700 mb-2">No campaigns yet</h3>
          <p className="text-slate-500 mb-6">Create your first campaign to start finding jobs automatically</p>
          <button
            onClick={() => setShowCreateModal(true)}
            className="px-6 py-3 bg-blue-600 text-white font-bold rounded-xl hover:bg-blue-700 inline-flex items-center gap-2"
          >
            <Plus size={18} />
            Create Campaign
          </button>
        </div>
      ) : (
        <div className="space-y-4">
          {campaigns.map(campaign => (
            <div key={campaign.id}>
              <CampaignCard
                campaign={campaign}
                jobs={jobs}
                runs={campaignRuns[campaign.id] || []}
                onRun={() => handleRunCampaign(campaign.id)}
                onPauseResume={() => handlePauseResume(campaign)}
                isRunning={runningCampaigns.has(campaign.id)}
              />
            </div>
          ))}
        </div>
      )}

      {/* Create Campaign Modal */}
      <CreateCampaignModal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        userId={userId}
        onCreated={fetchData}
      />
    </div>
  );
};