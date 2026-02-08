import { useState, useEffect } from 'react';
import { api, Job } from '../api';

interface Props {
  userId: string;
  jobs: Job[];
  loading: boolean;
  onLoad: (status?: string) => void;
  showToast: (message: string, type?: 'success' | 'error') => void;
}

export default function JobsSection({ userId, jobs, loading, onLoad, showToast }: Props) {
  const [statusFilter, setStatusFilter] = useState('');
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [actionLoading, setActionLoading] = useState(false);
  const [recipientEmail, setRecipientEmail] = useState('');

  useEffect(() => {
    onLoad(statusFilter || undefined);
  }, [statusFilter]);

  const handleTailor = async () => {
    if (!selectedJob) return;
    setActionLoading(true);
    try {
      await api.tailorResume(selectedJob.id);
      showToast('Resume tailored successfully!');
      onLoad(statusFilter || undefined);
    } catch (err) {
      showToast(String(err), 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleGeneratePDF = async () => {
    if (!selectedJob) return;
    setActionLoading(true);
    try {
      const result = await api.generatePDF(selectedJob.id);
      showToast(`PDF generated: ${result.path}`);
    } catch (err) {
      showToast(String(err), 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleCreateDraft = async () => {
    if (!selectedJob || !recipientEmail) {
      showToast('Enter recipient email', 'error');
      return;
    }
    setActionLoading(true);
    try {
      await api.createDraft(selectedJob.id, recipientEmail);
      showToast('Gmail draft created!');
      onLoad(statusFilter || undefined);
    } catch (err) {
      showToast(String(err), 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      scouted: 'bg-blue-100 text-blue-800',
      tailored: 'bg-purple-100 text-purple-800',
      drafted: 'bg-yellow-100 text-yellow-800',
      sent: 'bg-green-100 text-green-800',
      interview: 'bg-orange-100 text-orange-800',
      offer: 'bg-emerald-100 text-emerald-800',
      rejected: 'bg-red-100 text-red-800',
    };
    return colors[status] || 'bg-gray-100 text-gray-800';
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">💼 Job Applications</h2>

      {/* Filter */}
      <div className="card">
        <div className="flex gap-4 items-center">
          <label className="text-sm font-medium text-gray-700">Filter by status:</label>
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="input w-48"
          >
            <option value="">All Statuses</option>
            <option value="scouted">Scouted</option>
            <option value="tailored">Tailored</option>
            <option value="drafted">Drafted</option>
            <option value="sent">Sent</option>
            <option value="interview">Interview</option>
            <option value="offer">Offer</option>
          </select>
          <button onClick={() => onLoad(statusFilter || undefined)} className="btn-secondary">
            🔄 Refresh
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Job List */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Jobs ({jobs.length})</h3>
          
          {loading ? (
            <p className="text-gray-500 text-center py-8">Loading...</p>
          ) : jobs.length === 0 ? (
            <p className="text-gray-500 text-center py-8">No jobs found. Run a campaign to scout jobs!</p>
          ) : (
            <div className="space-y-3 max-h-[600px] overflow-auto">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  onClick={() => setSelectedJob(job)}
                  className={`border rounded-lg p-3 cursor-pointer transition-all ${
                    selectedJob?.id === job.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex justify-between items-start">
                    <div>
                      <h4 className="font-medium text-gray-800">{job.job_title}</h4>
                      <p className="text-sm text-gray-600">{job.company_name}</p>
                      {job.location && (
                        <p className="text-xs text-gray-500">📍 {job.location}</p>
                      )}
                    </div>
                    <span className={`text-xs px-2 py-1 rounded-full ${getStatusBadge(job.status)}`}>
                      {job.status}
                    </span>
                  </div>
                  {job.match_score !== undefined && job.match_score > 0 && (
                    <div className="mt-2 flex items-center gap-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div
                          className="bg-blue-500 h-2 rounded-full"
                          style={{ width: `${job.match_score}%` }}
                        />
                      </div>
                      <span className="text-xs text-gray-500">{job.match_score}%</span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Job Details */}
        <div className="card">
          <h3 className="text-lg font-semibold mb-4">Job Details</h3>
          
          {!selectedJob ? (
            <p className="text-gray-500 text-center py-8">Select a job to view details</p>
          ) : (
            <div className="space-y-4">
              <div>
                <h4 className="text-xl font-bold text-gray-800">{selectedJob.job_title}</h4>
                <p className="text-lg text-gray-600">{selectedJob.company_name}</p>
                {selectedJob.location && (
                  <p className="text-sm text-gray-500">📍 {selectedJob.location}</p>
                )}
              </div>

              {selectedJob.source_url && (
                <a
                  href={selectedJob.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline text-sm"
                >
                  🔗 View Original Posting
                </a>
              )}

              {selectedJob.job_description && (
                <div>
                  <h5 className="font-medium text-gray-700 mb-1">Description</h5>
                  <p className="text-sm text-gray-600 whitespace-pre-wrap line-clamp-6">
                    {selectedJob.job_description}
                  </p>
                </div>
              )}

              {selectedJob.tailored_resume && Object.keys(selectedJob.tailored_resume).length > 0 && (
                <div className="p-3 bg-green-50 rounded-lg">
                  <p className="text-sm text-green-700">✅ Resume tailored</p>
                </div>
              )}

              {selectedJob.cover_email && (
                <div className="p-3 bg-blue-50 rounded-lg">
                  <p className="text-sm text-blue-700">✅ Cover email generated</p>
                </div>
              )}

              {/* Actions */}
              <div className="border-t pt-4 space-y-3">
                <h5 className="font-medium text-gray-700">Actions</h5>
                
                <button
                  onClick={handleTailor}
                  disabled={actionLoading || selectedJob.status !== 'scouted'}
                  className="btn-primary w-full"
                >
                  ✍️ Tailor Resume
                </button>

                <button
                  onClick={handleGeneratePDF}
                  disabled={actionLoading || !selectedJob.tailored_resume}
                  className="btn-secondary w-full"
                >
                  📄 Generate PDF
                </button>

                <div className="flex gap-2">
                  <input
                    type="email"
                    placeholder="Recipient email..."
                    value={recipientEmail}
                    onChange={(e) => setRecipientEmail(e.target.value)}
                    className="input flex-1"
                  />
                  <button
                    onClick={handleCreateDraft}
                    disabled={actionLoading || !selectedJob.tailored_resume}
                    className="btn-secondary"
                  >
                    📧 Draft
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
