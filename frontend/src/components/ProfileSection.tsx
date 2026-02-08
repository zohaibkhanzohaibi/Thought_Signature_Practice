import { useState } from 'react';
import { api, Profile } from '../api';

interface Props {
  userId: string;
  profile: Profile | null;
  onUpdate: () => void;
  showToast: (message: string, type?: 'success' | 'error') => void;
}

export default function ProfileSection({ userId, profile, onUpdate, showToast }: Props) {
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    full_name: profile?.full_name || '',
    email: profile?.email || '',
    phone: profile?.phone || '',
    linkedin_url: profile?.linkedin_url || '',
    github_username: profile?.github_username || '',
    skills: profile?.skills?.join(', ') || '',
    experience_years: profile?.experience_years || 0,
    target_roles: profile?.target_roles?.join(', ') || '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      await api.createProfile(userId, {
        ...form,
        skills: form.skills.split(',').map(s => s.trim()).filter(Boolean),
        target_roles: form.target_roles.split(',').map(s => s.trim()).filter(Boolean),
      });
      showToast('Profile saved successfully!');
      onUpdate();
    } catch (err) {
      showToast(String(err), 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    try {
      const result = await api.uploadResume(userId, file);
      showToast(result.message);
      onUpdate();
    } catch (err) {
      showToast(String(err), 'error');
    } finally {
      setLoading(false);
    }
  };

  const handleGitHubSync = async () => {
    if (!form.github_username) {
      showToast('Enter a GitHub username first', 'error');
      return;
    }
    setLoading(true);
    try {
      const result = await api.syncGitHub(userId);
      showToast(result.message);
      onUpdate();
    } catch (err) {
      showToast(String(err), 'error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-gray-800">👤 Profile Management</h2>

      {/* Profile Form */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">
          {profile ? 'Update Profile' : 'Create Profile'}
        </h3>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="label">Full Name *</label>
              <input
                type="text"
                className="input"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                required
              />
            </div>
            <div>
              <label className="label">Email</label>
              <input
                type="email"
                className="input"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
            <div>
              <label className="label">Phone</label>
              <input
                type="text"
                className="input"
                value={form.phone}
                onChange={(e) => setForm({ ...form, phone: e.target.value })}
              />
            </div>
            <div>
              <label className="label">LinkedIn URL</label>
              <input
                type="url"
                className="input"
                value={form.linkedin_url}
                onChange={(e) => setForm({ ...form, linkedin_url: e.target.value })}
              />
            </div>
            <div>
              <label className="label">GitHub Username</label>
              <input
                type="text"
                className="input"
                value={form.github_username}
                onChange={(e) => setForm({ ...form, github_username: e.target.value })}
              />
            </div>
            <div>
              <label className="label">Years of Experience</label>
              <input
                type="number"
                className="input"
                min="0"
                value={form.experience_years}
                onChange={(e) => setForm({ ...form, experience_years: parseInt(e.target.value) || 0 })}
              />
            </div>
          </div>
          <div>
            <label className="label">Skills (comma-separated)</label>
            <input
              type="text"
              className="input"
              placeholder="Python, React, PostgreSQL..."
              value={form.skills}
              onChange={(e) => setForm({ ...form, skills: e.target.value })}
            />
          </div>
          <div>
            <label className="label">Target Roles (comma-separated)</label>
            <input
              type="text"
              className="input"
              placeholder="Software Engineer, Backend Developer..."
              value={form.target_roles}
              onChange={(e) => setForm({ ...form, target_roles: e.target.value })}
            />
          </div>
          <button type="submit" className="btn-primary" disabled={loading}>
            {loading ? 'Saving...' : 'Save Profile'}
          </button>
        </form>
      </div>

      {/* Resume Upload */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">📄 Upload Resume (PDF)</h3>
        <input
          type="file"
          accept=".pdf"
          onChange={handleResumeUpload}
          className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4
            file:rounded-lg file:border-0 file:text-sm file:font-medium
            file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          disabled={loading}
        />
        {profile?.parsed_resume && Object.keys(profile.parsed_resume).length > 0 && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-600">✅ Resume parsed and stored</p>
          </div>
        )}
      </div>

      {/* GitHub Sync */}
      <div className="card">
        <h3 className="text-lg font-semibold mb-4">🐙 Sync GitHub Portfolio</h3>
        <button onClick={handleGitHubSync} className="btn-secondary" disabled={loading}>
          {loading ? 'Syncing...' : '🔄 Sync GitHub'}
        </button>
        {profile?.portfolio_data && Object.keys(profile.portfolio_data).length > 0 && (
          <div className="mt-4 p-4 bg-gray-50 rounded-lg">
            <p className="text-sm text-gray-600">
              ✅ {(profile.portfolio_data as { repositories?: unknown[] }).repositories?.length || 0} repositories synced
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
