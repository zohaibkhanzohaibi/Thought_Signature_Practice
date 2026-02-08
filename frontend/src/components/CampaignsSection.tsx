import { useState, useEffect } from 'react';
import { api, Campaign, CampaignCreate } from '../api';

interface Props {
  userId: string;
  campaigns: Campaign[];
  loading: boolean;
  onLoad: () => void;
  showToast: (message: string, type?: 'success' | 'error') => void;
}

export default function CampaignsSection({ userId, campaigns, loading, onLoad, showToast }: Props) {
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<Omit<CampaignCreate, 'user_id'>>({
    name: '',
    job_titles: [],
    locations: [],
    keywords: [],
    max_jobs_per_run: 5,
    auto_apply: false,
  });
  const [jobTitlesInput, setJobTitlesInput] = useState('');
  const [locationsInput, setLocationsInput] = useState('Remote');

  useEffect(() => {
    onLoad();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      await api.createCampaign({
        user_id: userId,
        name: form.name,
        job_titles: jobTitlesInput.split(',').map(s => s.trim()).filter(Boolean),
        locations: locationsInput.split(',').map(s => s.trim()).filter(Boolean),
        max_jobs_per_run: form.max_jobs_per_run,
        auto_apply: form.auto_apply,
      });
      showToast('Campaign created successfully!');
      setForm({ name: '', job_titles: [], locations: [], max_jobs_per_run: 5, auto_apply: false });
      setJobTitlesInput('');
      setLocationsInput('Remote');
      onLoad();
    } catch (err) {
      showToast(String(err), 'error');
    } finally {
      setCreating(false);
    }
  };

  const handleRun = async (campaignId: number) => {
    try {
      await api.runCampaign(campaignId);
      showToast('Campaign run started!');
    } catch (err) {
      showToast(String(err), 'error');
    }
  };

  const handlePause = async (campaignId: number) => {
    try {
      await api.pauseCampaign(campaignId);
      showToast('Campaign paused');
      onLoad();
    } catch (err) {
      showToast(String(err), 'error');
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">📋 Campaigns</h2>

      {/* Create Campaign */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">Create New Campaign</h3>
        <form onSubmit={handleCreate} className="space-y-4">
          <div>
            <label className="label">Campaign Name *</label>
            <input
              type="text"
              className="input"
              placeholder="My Job Search Campaign"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Job Titles (comma-separated)</label>
              <input
                type="text"
                className="input"
                placeholder="Software Engineer, Python Developer"
                value={jobTitlesInput}
                onChange={(e) => setJobTitlesInput(e.target.value)}
              />
            </div>
            <div>
              <label className="label">Locations (comma-separated)</label>
              <input
                type="text"
                className="input"
                placeholder="Remote, New York"
                value={locationsInput}
                onChange={(e) => setLocationsInput(e.target.value)}
              />
            </div>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Max Jobs Per Run</label>
              <input
                type="number"
                className="input"
                min="1"
                max="20"
                value={form.max_jobs_per_run}
                onChange={(e) => setForm({ ...form, max_jobs_per_run: parseInt(e.target.value) || 5 })}
              />
            </div>
            <div className="flex items-center gap-2 pt-6">
              <input
                type="checkbox"
                id="auto-apply"
                checked={form.auto_apply}
                onChange={(e) => setForm({ ...form, auto_apply: e.target.checked })}
                className="w-4 h-4 text-blue-600 rounded focus:ring-blue-500"
              />
              <label htmlFor="auto-apply" className="text-sm text-gray-700">
                Auto-create Gmail drafts
              </label>
            </div>
          </div>
          <button type="submit" className="btn-primary" disabled={creating}>
            {creating ? 'Creating...' : 'Create Campaign'}
          </button>
        </form>
      </div>

      {/* Campaign List */}
      <div className="card">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-semibold">Your Campaigns</h3>
          <button onClick={onLoad} className="btn-secondary text-sm" disabled={loading}>
            🔄 Refresh
          </button>
        </div>

        {loading ? (
          <p className="text-gray-500 text-center py-8">Loading...</p>
        ) : campaigns.length === 0 ? (
          <p className="text-gray-500 text-center py-8">No campaigns yet. Create one above!</p>
        ) : (
          <div className="space-y-4">
            {campaigns.map((campaign) => (
              <div
                key={campaign.id}
                className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors"
              >
                <div className="flex justify-between items-start">
                  <div>
                    <h4 className="font-medium text-gray-800">{campaign.name}</h4>
                    <p className="text-sm text-gray-500 mt-1">
                      ID: {campaign.id} • Status: 
                      <span className={`ml-1 ${
                        campaign.status === 'active' ? 'text-green-600' : 'text-yellow-600'
                      }`}>
                        {campaign.status}
                      </span>
                    </p>
                    {campaign.config && (
                      <p className="text-sm text-gray-500">
                        Targets: {(campaign.config as { job_titles?: string[] }).job_titles?.join(', ') || 'Any'}
                      </p>
                    )}
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleRun(campaign.id)}
                      className="btn-primary text-sm px-3 py-1"
                    >
                      ▶️ Run
                    </button>
                    <button
                      onClick={() => handlePause(campaign.id)}
                      className="btn-secondary text-sm px-3 py-1"
                    >
                      ⏸️ Pause
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
