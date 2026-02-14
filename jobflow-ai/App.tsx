import React, { useState, useEffect, useMemo } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { CheckCircle, X } from 'lucide-react';
import { ViewType, Application, Job, AppStatus } from './types';
import { SocketIOProvider } from './contexts/SocketIOContext';

const PATH_TO_VIEW: Record<string, ViewType> = {
  '/': 'dashboard',
  '/dashboard': 'dashboard',
  '/discovery': 'discovery',
  '/applications': 'manager',
  '/inbox': 'inbox',
  '/profile': 'profile',
  '/analytics': 'analytics',
  '/settings': 'settings',
};
import { MOCK_APPLICATIONS, MOCK_USER } from './constants';

// Layout Components
import { Sidebar } from './components/layout/Sidebar';
import { Header } from './components/layout/Header';

// View Components
import { AuthPage } from './components/views/AuthPage';
import { DashboardView } from './components/views/DashboardView';
import { JobDiscoveryView } from './components/views/JobDiscoveryView';
import { ManagerView } from './components/views/ManagerView';
import { ProfileView } from './components/views/ProfileView';
import InboxView from './components/views/InboxView';
import { ApplicationsView } from './components/views/ApplicationsView';

// Modals
import { GenerationModal } from './components/modals/GenerationModal';
import { authService } from './services/auth';

const AppContent = () => {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userId, setUserId] = useState<string>('');

  useEffect(() => {
    if (authService.isAuthenticated()) {
      setIsAuthenticated(true);
      const id = authService.getUserIdFromToken();
      if (id) setUserId(id);
    }
  }, []);

  const location = useLocation();
  const navigate = useNavigate();
  const currentView = useMemo(() => PATH_TO_VIEW[location.pathname] ?? 'dashboard', [location.pathname]);
  const [darkMode, setDarkMode] = useState(false); // Helper state for now, logic inside Header/Components needs to respect it if implemented fully
  const [apps, setApps] = useState<Application[]>(MOCK_APPLICATIONS);
  const [isApplying, setIsApplying] = useState<Job | null>(null);
  const [notifications, setNotifications] = useState<string[]>([]);

  const handleLogin = (id?: string) => {
    if (id) setUserId(id);
    setIsAuthenticated(true);
  };

  const handleApplyComplete = (newApp: Application) => {
    setApps(prev => [newApp, ...prev]);
    setIsApplying(null);
    setNotifications(prev => ["Application sent successfully via AI Agent!", ...prev]);

    // Simulate status updates
    setTimeout(() => {
      setNotifications(prev => ["Recruiter at TechCorp viewed your application", ...prev]);
    }, 5000);
  };

  if (!isAuthenticated) {
    return <AuthPage onLogin={handleLogin} />;
  }

  return (
    <div className={`flex min-h-screen ${darkMode ? 'dark bg-slate-900 text-white' : 'bg-slate-50'}`}>
      <Sidebar
        currentView={currentView}
        onLogout={() => {
          authService.logout();
          setIsAuthenticated(false);
        }}
      />

      <div className="flex-1 flex flex-col">
        <Header darkMode={darkMode} setDarkMode={setDarkMode} />

        <main className="flex-1 p-8 max-w-7xl mx-auto w-full overflow-x-hidden">
          {currentView === 'dashboard' && <DashboardView apps={apps} onAdd={() => navigate('/discovery')} />}
          {currentView === 'discovery' && <JobDiscoveryView onApply={(j) => setIsApplying(j)} />}
          {currentView === 'manager' && <ApplicationsView userId={userId} />}
          {currentView === 'profile' && <ProfileView userId={userId} />}
          {currentView === 'inbox' && <InboxView userId={userId} />}

          {/* Placeholders for unimplemented views */}
          {currentView === 'analytics' && (
            <div className="h-[600px] flex flex-col items-center justify-center text-slate-400">
              <h3 className="text-xl font-bold text-slate-600 mb-2">Analytics Dashboard</h3>
              <p>Coming soon in v2.0</p>
            </div>
          )}
          {currentView === 'settings' && (
            <div className="h-[600px] flex flex-col items-center justify-center text-slate-400">
              <h3 className="text-xl font-bold text-slate-600 mb-2">Settings</h3>
              <p>User preferences and account management</p>
            </div>
          )}
        </main>
      </div>

      {/* Notifications */}
      <div className="fixed bottom-8 right-8 flex flex-col gap-4 z-[100]">
        {notifications.map((n, i) => (
          <div key={i} className="bg-slate-900 text-white px-8 py-5 rounded-[24px] shadow-2xl border border-slate-700 flex items-center gap-4 animate-in slide-in-from-right-10 duration-500">
            <div className="w-10 h-10 bg-blue-600 rounded-xl flex items-center justify-center text-white shadow-lg">
              <CheckCircle size={22} />
            </div>
            <p className="text-sm font-bold">{n}</p>
            <button onClick={() => setNotifications(prev => prev.filter(m => m !== n))} className="ml-4 p-1 text-slate-500 hover:text-white transition-colors">
              <X size={20} />
            </button>
          </div>
        ))}
      </div>

      {/* Modals */}
      {isApplying && (
        <GenerationModal
          job={isApplying}
          user={MOCK_USER}
          onClose={() => setIsApplying(null)}
          onComplete={handleApplyComplete}
        />
      )}
    </div>
  );
};

const App = () => {
  return (
    <SocketIOProvider>
      <AppContent />
    </SocketIOProvider>
  );
};

export default App;
