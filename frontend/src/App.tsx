import { useState, useEffect } from 'react';
import { api, Profile, Campaign, Job } from './api';
import ProfileSection from './components/ProfileSection';
import CampaignsSection from './components/CampaignsSection';
import JobsSection from './components/JobsSection';
import GmailSection from './components/GmailSection';

type Section = 'profile' | 'campaigns' | 'jobs' | 'gmail';

function App() {
  const [activeSection, setActiveSection] = useState<Section>('profile');
  const [userId, setUserId] = useState<string>(() => localStorage.getItem('userId') || '');
  const [userIdInput, setUserIdInput] = useState(userId);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [toast, setToast] = useState<{ message: string; type: 'success' | 'error' } | null>(null);

  const showToast = (message: string, type: 'success' | 'error' = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  const handleSetUserId = () => {
    if (userIdInput.trim()) {
      setUserId(userIdInput.trim());
      localStorage.setItem('userId', userIdInput.trim());
      showToast('User ID set successfully');
    }
  };

  useEffect(() => {
    if (userId) {
      loadProfile();
    }
  }, [userId]);

  const loadProfile = async () => {
    if (!userId) return;
    try {
      const p = await api.getProfile(userId);
      setProfile(p);
    } catch {
      setProfile(null);
    }
  };

  const loadCampaigns = async () => {
    if (!userId) return;
    setLoading(true);
    try {
      const c = await api.getCampaigns(userId);
      setCampaigns(c);
    } catch (e) {
      showToast(String(e), 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadJobs = async (status?: string) => {
    if (!userId) return;
    setLoading(true);
    try {
      const j = await api.getJobs(userId, status);
      setJobs(j);
    } catch (e) {
      showToast(String(e), 'error');
    } finally {
      setLoading(false);
    }
  };

  const navItems: { id: Section; label: string; icon: string }[] = [
    { id: 'profile', label: 'Profile', icon: '👤' },
    { id: 'campaigns', label: 'Campaigns', icon: '📋' },
    { id: 'jobs', label: 'Jobs', icon: '💼' },
    { id: 'gmail', label: 'Gmail', icon: '📧' },
  ];

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-6 border-b border-gray-200">
          <h1 className="text-2xl font-bold text-blue-600">🏃 Marathon</h1>
          <p className="text-sm text-gray-500">Job Search Agent</p>
        </div>
        
        <nav className="flex-1 p-4">
          <ul className="space-y-2">
            {navItems.map(item => (
              <li key={item.id}>
                <button
                  onClick={() => setActiveSection(item.id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                    activeSection === item.id
                      ? 'bg-blue-50 text-blue-700 font-medium'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`}
                >
                  <span className="text-xl">{item.icon}</span>
                  <span>{item.label}</span>
                </button>
              </li>
            ))}
          </ul>
        </nav>

        {/* User ID Input */}
        <div className="p-4 border-t border-gray-200">
          <label className="label">User ID</label>
          <div className="flex gap-2">
            <input
              type="text"
              value={userIdInput}
              onChange={(e) => setUserIdInput(e.target.value)}
              placeholder="Enter User ID..."
              className="input flex-1 text-sm"
            />
            <button onClick={handleSetUserId} className="btn-primary text-sm px-3">
              Set
            </button>
          </div>
          {userId && (
            <p className="text-xs text-gray-500 mt-2 truncate">
              Current: {userId.slice(0, 8)}...
            </p>
          )}
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 overflow-auto">
        <div className="p-8">
          {!userId ? (
            <div className="card text-center py-12">
              <h2 className="text-xl font-semibold text-gray-700 mb-2">
                Welcome to Marathon Agent
              </h2>
              <p className="text-gray-500">
                Enter your User ID in the sidebar to get started.
              </p>
            </div>
          ) : (
            <>
              {activeSection === 'profile' && (
                <ProfileSection
                  userId={userId}
                  profile={profile}
                  onUpdate={loadProfile}
                  showToast={showToast}
                />
              )}
              {activeSection === 'campaigns' && (
                <CampaignsSection
                  userId={userId}
                  campaigns={campaigns}
                  loading={loading}
                  onLoad={loadCampaigns}
                  showToast={showToast}
                />
              )}
              {activeSection === 'jobs' && (
                <JobsSection
                  userId={userId}
                  jobs={jobs}
                  loading={loading}
                  onLoad={loadJobs}
                  showToast={showToast}
                />
              )}
              {activeSection === 'gmail' && (
                <GmailSection
                  userId={userId}
                  showToast={showToast}
                />
              )}
            </>
          )}
        </div>
      </main>

      {/* Toast */}
      {toast && (
        <div className={`fixed bottom-4 right-4 px-6 py-3 rounded-lg shadow-lg ${
          toast.type === 'success' ? 'bg-green-500' : 'bg-red-500'
        } text-white`}>
          {toast.message}
        </div>
      )}
    </div>
  );
}

export default App;
