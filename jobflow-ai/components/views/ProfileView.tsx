import React, { useState, useEffect, useRef } from 'react';
import { Github, Globe, Mail, Zap, Plus, Code, ArrowUpRight, Edit3, Save, X, Upload, RefreshCw, User, Briefcase, MapPin, Target, FileText, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { api, ProfileData, SkillsSummary, ResumeUploadResponse, GitHubSyncResponse } from '../../services/api';

interface ProfileViewProps {
    userId: string;
}

export const ProfileView: React.FC<ProfileViewProps> = ({ userId }) => {
    const [profile, setProfile] = useState<ProfileData | null>(null);
    const [skills, setSkills] = useState<SkillsSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [successMsg, setSuccessMsg] = useState<string | null>(null);
    const [isEditing, setIsEditing] = useState(false);
    const [editForm, setEditForm] = useState<Partial<ProfileData>>({});
    const [uploadingResume, setUploadingResume] = useState(false);
    const [syncingGithub, setSyncingGithub] = useState(false);
    const [githubInput, setGithubInput] = useState('');
    const fileInputRef = useRef<HTMLInputElement>(null);

    // Fetch profile on mount
    useEffect(() => {
        loadProfile();
    }, [userId]);

    const loadProfile = async () => {
        setLoading(true);
        setError(null);
        try {
            const [profileData, skillsData] = await Promise.all([
                api.getProfile(userId),
                api.getSkillsSummary(userId).catch(() => null)
            ]);
            setProfile(profileData);
            setSkills(skillsData);
            if (profileData) {
                setEditForm(profileData);
            }
        } catch (err: any) {
            setError(err.message || 'Failed to load profile');
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        setSaving(true);
        setError(null);
        try {
            const updated = await api.createOrUpdateProfile(userId, editForm);
            setProfile(updated);
            setIsEditing(false);
            showSuccess('Profile saved successfully!');
            // Refresh skills
            const skillsData = await api.getSkillsSummary(userId).catch(() => null);
            setSkills(skillsData);
        } catch (err: any) {
            setError(err.message || 'Failed to save profile');
        } finally {
            setSaving(false);
        }
    };

    const handleResumeUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;

        if (!file.name.toLowerCase().endsWith('.pdf')) {
            setError('Only PDF files are supported');
            return;
        }

        setUploadingResume(true);
        setError(null);
        try {
            // Create profile first if it doesn't exist
            if (!profile) {
                await api.createOrUpdateProfile(userId, { full_name: 'New User' });
            }
            
            const result = await api.uploadResume(userId, file);
            showSuccess(`Resume parsed! Found ${result.parsed_data.skills?.length || 0} skills`);
            await loadProfile();
        } catch (err: any) {
            setError(err.message || 'Failed to upload resume');
        } finally {
            setUploadingResume(false);
            if (fileInputRef.current) {
                fileInputRef.current.value = '';
            }
        }
    };

    const handleGitHubSync = async () => {
        const username = profile?.github_username || editForm.github_username;
        if (!username) {
            setError('Please enter a GitHub username first');
            return;
        }

        setSyncingGithub(true);
        setError(null);
        try {
            const result = await api.syncGitHub(userId, username);
            showSuccess(`Synced ${result.portfolio.repositories?.length || 0} repositories from GitHub!`);
            await loadProfile();
        } catch (err: any) {
            setError(err.message || 'Failed to sync GitHub');
        } finally {
            setSyncingGithub(false);
        }
    };

    const showSuccess = (msg: string) => {
        setSuccessMsg(msg);
        setTimeout(() => setSuccessMsg(null), 3000);
    };

    const handleFormChange = (field: keyof ProfileData, value: any) => {
        setEditForm(prev => ({ ...prev, [field]: value }));
    };

    const handleSkillsChange = (value: string) => {
        const skillsArray = value.split(',').map(s => s.trim()).filter(Boolean);
        handleFormChange('skills', skillsArray);
    };

    const handleLocationsChange = (value: string) => {
        const locationsArray = value.split(',').map(s => s.trim()).filter(Boolean);
        handleFormChange('preferred_locations', locationsArray);
    };

    const handleRolesChange = (value: string) => {
        const rolesArray = value.split(',').map(s => s.trim()).filter(Boolean);
        handleFormChange('target_roles', rolesArray);
    };

    // Loading state
    if (loading) {
        return (
            <div className="flex items-center justify-center h-[600px]">
                <div className="text-center">
                    <Loader2 className="w-12 h-12 text-blue-600 animate-spin mx-auto mb-4" />
                    <p className="text-slate-500 font-medium">Loading profile...</p>
                </div>
            </div>
        );
    }

    // No profile - show create form
    if (!profile && !isEditing) {
        return (
            <div className="max-w-2xl mx-auto animate-in slide-in-from-bottom-4 duration-500">
                <div className="bg-white rounded-[32px] p-12 border border-slate-100 shadow-sm text-center">
                    <div className="w-24 h-24 bg-blue-100 rounded-full flex items-center justify-center mx-auto mb-6">
                        <User size={48} className="text-blue-600" />
                    </div>
                    <h2 className="text-2xl font-bold text-slate-800 mb-2">Create Your Profile</h2>
                    <p className="text-slate-500 mb-8">Get started by uploading your resume or filling in your details</p>
                    
                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <label className="flex items-center gap-3 px-6 py-4 bg-blue-600 text-white rounded-2xl cursor-pointer hover:bg-blue-700 transition-colors font-bold">
                            <Upload size={20} />
                            {uploadingResume ? 'Uploading...' : 'Upload Resume (PDF)'}
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".pdf"
                                className="hidden"
                                onChange={handleResumeUpload}
                                disabled={uploadingResume}
                            />
                        </label>
                        <button
                            onClick={() => {
                                setEditForm({ full_name: '' });
                                setIsEditing(true);
                            }}
                            className="flex items-center gap-3 px-6 py-4 bg-slate-100 text-slate-700 rounded-2xl hover:bg-slate-200 transition-colors font-bold"
                        >
                            <Edit3 size={20} />
                            Fill Manually
                        </button>
                    </div>

                    {error && (
                        <div className="mt-6 p-4 bg-red-50 text-red-600 rounded-xl flex items-center gap-2">
                            <AlertCircle size={18} />
                            {error}
                        </div>
                    )}
                </div>
            </div>
        );
    }

    // Edit mode
    if (isEditing) {
        return (
            <div className="max-w-4xl mx-auto animate-in slide-in-from-bottom-4 duration-500">
                {/* Alerts */}
                {error && (
                    <div className="mb-6 p-4 bg-red-50 text-red-600 rounded-xl flex items-center gap-2">
                        <AlertCircle size={18} />
                        {error}
                        <button onClick={() => setError(null)} className="ml-auto"><X size={18} /></button>
                    </div>
                )}
                {successMsg && (
                    <div className="mb-6 p-4 bg-green-50 text-green-600 rounded-xl flex items-center gap-2">
                        <CheckCircle size={18} />
                        {successMsg}
                    </div>
                )}

                <div className="bg-white rounded-[32px] p-8 border border-slate-100 shadow-sm">
                    <div className="flex items-center justify-between mb-8">
                        <h3 className="text-xl font-bold text-slate-800">Edit Profile</h3>
                        <div className="flex gap-3">
                            <button
                                onClick={() => {
                                    setIsEditing(false);
                                    if (profile) setEditForm(profile);
                                }}
                                className="px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-xl transition-colors font-medium"
                            >
                                Cancel
                            </button>
                            <button
                                onClick={handleSave}
                                disabled={saving}
                                className="flex items-center gap-2 px-6 py-2 bg-blue-600 text-white rounded-xl hover:bg-blue-700 transition-colors font-bold disabled:opacity-50"
                            >
                                {saving ? <Loader2 size={18} className="animate-spin" /> : <Save size={18} />}
                                {saving ? 'Saving...' : 'Save'}
                            </button>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {/* Basic Info */}
                        <div className="space-y-4">
                            <h4 className="font-bold text-slate-700 flex items-center gap-2">
                                <User size={18} className="text-blue-600" /> Basic Information
                            </h4>
                            
                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-2">Full Name *</label>
                                <input
                                    type="text"
                                    value={editForm.full_name || ''}
                                    onChange={(e) => handleFormChange('full_name', e.target.value)}
                                    className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    placeholder="John Doe"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-2">Email</label>
                                <input
                                    type="email"
                                    value={editForm.email || ''}
                                    onChange={(e) => handleFormChange('email', e.target.value)}
                                    className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    placeholder="john@example.com"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-2">Phone</label>
                                <input
                                    type="tel"
                                    value={editForm.phone || ''}
                                    onChange={(e) => handleFormChange('phone', e.target.value)}
                                    className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    placeholder="+1 234 567 8900"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-2">Years of Experience</label>
                                <input
                                    type="number"
                                    value={editForm.experience_years || 0}
                                    onChange={(e) => handleFormChange('experience_years', parseInt(e.target.value) || 0)}
                                    className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    min="0"
                                    max="50"
                                />
                            </div>
                        </div>

                        {/* Links & Social */}
                        <div className="space-y-4">
                            <h4 className="font-bold text-slate-700 flex items-center gap-2">
                                <Globe size={18} className="text-blue-600" /> Links & Social
                            </h4>

                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-2">LinkedIn URL</label>
                                <input
                                    type="url"
                                    value={editForm.linkedin_url || ''}
                                    onChange={(e) => handleFormChange('linkedin_url', e.target.value)}
                                    className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    placeholder="https://linkedin.com/in/johndoe"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-2">GitHub Username</label>
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        value={editForm.github_username || ''}
                                        onChange={(e) => handleFormChange('github_username', e.target.value)}
                                        className="flex-1 px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        placeholder="johndoe"
                                    />
                                    <button
                                        onClick={handleGitHubSync}
                                        disabled={syncingGithub || !editForm.github_username}
                                        className="px-4 py-3 bg-slate-900 text-white rounded-xl hover:bg-slate-800 transition-colors disabled:opacity-50 flex items-center gap-2"
                                    >
                                        {syncingGithub ? <Loader2 size={18} className="animate-spin" /> : <RefreshCw size={18} />}
                                        Sync
                                    </button>
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-2">Professional Summary</label>
                                <textarea
                                    value={editForm.summary || ''}
                                    onChange={(e) => handleFormChange('summary', e.target.value)}
                                    className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 h-24 resize-none"
                                    placeholder="Brief overview of your experience and goals..."
                                />
                            </div>
                        </div>

                        {/* Skills & Preferences */}
                        <div className="space-y-4">
                            <h4 className="font-bold text-slate-700 flex items-center gap-2">
                                <Zap size={18} className="text-yellow-500" /> Skills
                            </h4>

                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-2">Skills (comma-separated)</label>
                                <textarea
                                    value={(editForm.skills || []).join(', ')}
                                    onChange={(e) => handleSkillsChange(e.target.value)}
                                    className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500 h-24 resize-none"
                                    placeholder="Python, React, AWS, Node.js..."
                                />
                            </div>
                        </div>

                        {/* Job Preferences */}
                        <div className="space-y-4">
                            <h4 className="font-bold text-slate-700 flex items-center gap-2">
                                <Target size={18} className="text-purple-600" /> Job Preferences
                            </h4>

                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-2">Preferred Locations (comma-separated)</label>
                                <input
                                    type="text"
                                    value={(editForm.preferred_locations || []).join(', ')}
                                    onChange={(e) => handleLocationsChange(e.target.value)}
                                    className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    placeholder="Remote, San Francisco, New York..."
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-slate-600 mb-2">Target Roles (comma-separated)</label>
                                <input
                                    type="text"
                                    value={(editForm.target_roles || []).join(', ')}
                                    onChange={(e) => handleRolesChange(e.target.value)}
                                    className="w-full px-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                                    placeholder="Software Engineer, Full Stack Developer..."
                                />
                            </div>
                        </div>
                    </div>

                    {/* Resume Upload Section */}
                    <div className="mt-8 pt-8 border-t border-slate-100">
                        <h4 className="font-bold text-slate-700 flex items-center gap-2 mb-4">
                            <FileText size={18} className="text-green-600" /> Resume
                        </h4>
                        <div className="flex items-center gap-4">
                            <label className="flex items-center gap-3 px-6 py-4 border-2 border-dashed border-slate-200 rounded-2xl cursor-pointer hover:border-blue-400 hover:bg-blue-50/50 transition-all">
                                <Upload size={20} className="text-slate-400" />
                                <span className="text-slate-600 font-medium">
                                    {uploadingResume ? 'Uploading...' : 'Upload New Resume (PDF)'}
                                </span>
                                <input
                                    ref={fileInputRef}
                                    type="file"
                                    accept=".pdf"
                                    className="hidden"
                                    onChange={handleResumeUpload}
                                    disabled={uploadingResume}
                                />
                            </label>
                            {profile?.parsed_resume && (
                                <span className="text-sm text-green-600 flex items-center gap-1">
                                    <CheckCircle size={16} />
                                    Resume on file
                                </span>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    // Display mode
    return (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 animate-in slide-in-from-bottom-4 duration-500">
            {/* Alerts */}
            {error && (
                <div className="lg:col-span-3 p-4 bg-red-50 text-red-600 rounded-xl flex items-center gap-2">
                    <AlertCircle size={18} />
                    {error}
                    <button onClick={() => setError(null)} className="ml-auto"><X size={18} /></button>
                </div>
            )}
            {successMsg && (
                <div className="lg:col-span-3 p-4 bg-green-50 text-green-600 rounded-xl flex items-center gap-2">
                    <CheckCircle size={18} />
                    {successMsg}
                </div>
            )}

            {/* Left Column - Profile Card */}
            <div className="lg:col-span-1 space-y-6">
                <div className="bg-white rounded-[32px] p-8 border border-slate-100 shadow-sm text-center relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-32 bg-gradient-to-br from-blue-500 to-purple-600"></div>
                    
                    {/* Edit Button */}
                    <button
                        onClick={() => setIsEditing(true)}
                        className="absolute top-4 right-4 z-20 p-2 bg-white/20 backdrop-blur-sm text-white rounded-xl hover:bg-white/30 transition-colors"
                    >
                        <Edit3 size={18} />
                    </button>

                    <div className="relative z-10 mt-12">
                        <div className="w-32 h-32 rounded-[32px] border-4 border-white shadow-2xl mx-auto mb-6 bg-gradient-to-br from-blue-400 to-purple-500 flex items-center justify-center text-white text-4xl font-bold">
                            {profile.full_name?.charAt(0)?.toUpperCase() || 'U'}
                        </div>
                        <h2 className="text-2xl font-bold text-slate-800">{profile.full_name}</h2>
                        <p className="text-slate-500 font-medium mb-2">
                            {profile.target_roles?.[0] || 'Software Engineer'}
                        </p>
                        {profile.email && (
                            <p className="text-sm text-slate-400 mb-6">{profile.email}</p>
                        )}
                        
                        <div className="flex justify-center gap-3 mb-8">
                            {profile.github_username && (
                                <a
                                    href={`https://github.com/${profile.github_username}`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="p-3 bg-slate-50 text-slate-600 rounded-2xl hover:bg-slate-100 hover:text-blue-600 transition-colors"
                                >
                                    <Github size={20} />
                                </a>
                            )}
                            {profile.linkedin_url && (
                                <a
                                    href={profile.linkedin_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="p-3 bg-slate-50 text-slate-600 rounded-2xl hover:bg-slate-100 hover:text-blue-600 transition-colors"
                                >
                                    <Globe size={20} />
                                </a>
                            )}
                            {profile.email && (
                                <a
                                    href={`mailto:${profile.email}`}
                                    className="p-3 bg-slate-50 text-slate-600 rounded-2xl hover:bg-slate-100 hover:text-blue-600 transition-colors"
                                >
                                    <Mail size={20} />
                                </a>
                            )}
                        </div>

                        <div className="grid grid-cols-2 gap-4 text-left">
                            <div className="p-4 bg-slate-50 rounded-2xl">
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Experience</p>
                                <p className="font-bold text-slate-700">{profile.experience_years || 0} years</p>
                            </div>
                            <div className="p-4 bg-slate-50 rounded-2xl">
                                <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1">Skills</p>
                                <p className="font-bold text-slate-700">{skills?.skills?.length || profile.skills?.length || 0}</p>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Skills Section */}
                <div className="bg-white rounded-[32px] p-8 border border-slate-100 shadow-sm">
                    <h4 className="font-bold text-slate-800 mb-6 flex items-center gap-2">
                        <Zap size={18} className="text-yellow-500" /> Skills
                        {skills?.sources && (
                            <span className="ml-auto text-xs text-slate-400">
                                {skills.sources.resume && '📄'} {skills.sources.github && '🐙'}
                            </span>
                        )}
                    </h4>
                    <div className="flex flex-wrap gap-2">
                        {(skills?.skills || profile.skills || []).slice(0, 15).map((skill, i) => (
                            <span
                                key={i}
                                className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-xl text-sm font-medium"
                            >
                                {skill}
                            </span>
                        ))}
                        {(skills?.skills || profile.skills || []).length === 0 && (
                            <p className="text-slate-400 text-sm">No skills added yet</p>
                        )}
                    </div>
                </div>

                {/* Preferred Locations */}
                {(profile.preferred_locations?.length ?? 0) > 0 && (
                    <div className="bg-white rounded-[32px] p-8 border border-slate-100 shadow-sm">
                        <h4 className="font-bold text-slate-800 mb-4 flex items-center gap-2">
                            <MapPin size={18} className="text-red-500" /> Preferred Locations
                        </h4>
                        <div className="flex flex-wrap gap-2">
                            {profile.preferred_locations?.map((loc, i) => (
                                <span
                                    key={i}
                                    className="px-3 py-1.5 bg-slate-100 text-slate-600 rounded-xl text-sm font-medium"
                                >
                                    {loc}
                                </span>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            {/* Right Column */}
            <div className="lg:col-span-2 space-y-6">
                {/* Summary */}
                {profile.summary && (
                    <div className="bg-white rounded-[32px] p-8 border border-slate-100 shadow-sm">
                        <h3 className="text-xl font-bold text-slate-800 mb-4">About</h3>
                        <p className="text-slate-600 leading-relaxed">{profile.summary}</p>
                    </div>
                )}

                {/* Connect GitHub - shows when no portfolio_data */}
                {!profile.portfolio_data && (
                    <div className="bg-white rounded-[32px] p-8 border border-slate-100 shadow-sm">
                        <div className="text-center">
                            <div className="w-16 h-16 bg-slate-100 rounded-full flex items-center justify-center mx-auto mb-4">
                                <Github size={32} className="text-slate-400" />
                            </div>
                            <h3 className="text-xl font-bold text-slate-800 mb-2">Connect GitHub</h3>
                            <p className="text-slate-500 mb-6">Sync your repositories to showcase your projects</p>
                            
                            <div className="max-w-sm mx-auto space-y-4">
                                <div className="flex gap-2">
                                    <div className="relative flex-1">
                                        <span className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">@</span>
                                        <input
                                            type="text"
                                            value={githubInput || profile.github_username || ''}
                                            onChange={(e) => setGithubInput(e.target.value)}
                                            placeholder="username"
                                            className="w-full pl-8 pr-4 py-3 border border-slate-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500"
                                        />
                                    </div>
                                </div>
                                <button
                                    onClick={async () => {
                                        const username = githubInput || profile.github_username;
                                        if (!username) {
                                            setError('Please enter a GitHub username');
                                            return;
                                        }
                                        setSyncingGithub(true);
                                        setError(null);
                                        try {
                                            // Backend auto-syncs GitHub when username is set
                                            await api.createOrUpdateProfile(userId, { github_username: username });
                                            showSuccess('GitHub synced!');
                                            await loadProfile();
                                        } catch (err: any) {
                                            setError(err.message || 'Failed to sync GitHub');
                                        } finally {
                                            setSyncingGithub(false);
                                        }
                                    }}
                                    disabled={syncingGithub || (!githubInput && !profile.github_username)}
                                    className="w-full flex items-center justify-center gap-2 px-6 py-3 bg-slate-900 text-white rounded-xl hover:bg-slate-800 transition-colors font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    {syncingGithub ? <Loader2 size={18} className="animate-spin" /> : <RefreshCw size={18} />}
                                    {syncingGithub ? 'Syncing...' : 'Sync Repositories'}
                                </button>
                            </div>
                        </div>
                    </div>
                )}

                {/* GitHub Portfolio */}
                {profile.portfolio_data && (
                    <div className="bg-white rounded-[32px] p-8 border border-slate-100 shadow-sm">
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-xl font-bold text-slate-800 flex items-center gap-2">
                                <Github size={24} /> GitHub Projects
                            </h3>
                            <button
                                onClick={handleGitHubSync}
                                disabled={syncingGithub}
                                className="flex items-center gap-2 px-4 py-2 text-slate-600 hover:bg-slate-100 rounded-xl transition-colors"
                            >
                                {syncingGithub ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                                Refresh
                            </button>
                        </div>
                        
                        {/* Change username option */}
                        <div className="flex items-center gap-2 mb-8 p-3 bg-slate-50 rounded-xl">
                            <span className="text-slate-400">@</span>
                            <input
                                type="text"
                                value={githubInput || profile.github_username || ''}
                                onChange={(e) => setGithubInput(e.target.value)}
                                placeholder="username"
                                className="flex-1 bg-transparent border-none focus:outline-none text-slate-700"
                            />
                            {githubInput && githubInput !== profile.github_username && (
                                <button
                                    onClick={async () => {
                                        setSyncingGithub(true);
                                        setError(null);
                                        try {
                                            // Backend auto-syncs GitHub when username changes
                                            await api.createOrUpdateProfile(userId, { github_username: githubInput });
                                            showSuccess('GitHub synced!');
                                            await loadProfile();
                                            setGithubInput('');
                                        } catch (err: any) {
                                            setError(err.message || 'Failed to sync');
                                        } finally {
                                            setSyncingGithub(false);
                                        }
                                    }}
                                    disabled={syncingGithub}
                                    className="px-3 py-1 bg-blue-600 text-white text-sm rounded-lg hover:bg-blue-700 transition-colors"
                                >
                                    {syncingGithub ? 'Syncing...' : 'Update'}
                                </button>
                            )}
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                            {(profile.portfolio_data as any)?.repositories?.slice(0, 6).map((repo: any, i: number) => (
                                <div key={i} className="group p-6 rounded-[24px] border border-slate-100 hover:border-blue-200 hover:bg-blue-50/30 transition-all cursor-pointer">
                                    <div className="flex justify-between items-start mb-4">
                                        <div className="w-12 h-12 bg-blue-100 text-blue-600 rounded-2xl flex items-center justify-center">
                                            <Code size={24} />
                                        </div>
                                        <a
                                            href={repo.url}
                                            target="_blank"
                                            rel="noopener noreferrer"
                                            onClick={(e) => e.stopPropagation()}
                                        >
                                            <ArrowUpRight size={20} className="text-slate-300 group-hover:text-blue-600 transition-colors transform group-hover:translate-x-1 group-hover:-translate-y-1" />
                                        </a>
                                    </div>
                                    <h4 className="font-bold text-lg text-slate-800 mb-2">{repo.name}</h4>
                                    <p className="text-sm text-slate-500 mb-4 line-clamp-2">{repo.description || 'No description'}</p>
                                    <div className="flex flex-wrap gap-2">
                                        {repo.language && (
                                            <span className="px-2.5 py-1 bg-white border border-slate-200 rounded-lg text-[10px] font-bold text-slate-600">
                                                {repo.language}
                                            </span>
                                        )}
                                        {repo.stars > 0 && (
                                            <span className="px-2.5 py-1 bg-yellow-50 border border-yellow-200 rounded-lg text-[10px] font-bold text-yellow-700">
                                                ⭐ {repo.stars}
                                            </span>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                        {!(profile.portfolio_data as any)?.repositories?.length && (
                            <p className="text-slate-400 text-center py-8">No repositories found. Click Refresh to sync.</p>
                        )}
                    </div>
                )}

                {/* Resume Data */}
                {profile.parsed_resume && Object.keys(profile.parsed_resume).length > 0 && (
                    <div className="bg-white rounded-[32px] p-8 border border-slate-100 shadow-sm">
                        <h3 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
                            <FileText size={24} className="text-green-600" /> Resume Highlights
                        </h3>
                        
                        {/* Experience from Resume */}
                        {(profile.parsed_resume as any)?.experience?.length > 0 && (
                            <div className="mb-6">
                                <h4 className="font-bold text-slate-700 mb-3 flex items-center gap-2">
                                    <Briefcase size={16} /> Experience
                                </h4>
                                <div className="space-y-4">
                                    {(profile.parsed_resume as any).experience.slice(0, 3).map((exp: any, i: number) => (
                                        <div key={i} className="p-4 bg-slate-50 rounded-xl">
                                            <p className="font-bold text-slate-800">{exp.title || exp.position}</p>
                                            <p className="text-sm text-slate-500">{exp.company} • {exp.duration}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}

                        {/* Education from Resume */}
                        {(profile.parsed_resume as any)?.education?.length > 0 && (
                            <div>
                                <h4 className="font-bold text-slate-700 mb-3">Education</h4>
                                <div className="space-y-2">
                                    {(profile.parsed_resume as any).education.map((edu: any, i: number) => (
                                        <div key={i} className="p-4 bg-slate-50 rounded-xl">
                                            <p className="font-bold text-slate-800">{edu.degree}</p>
                                            <p className="text-sm text-slate-500">{edu.school} • {edu.year}</p>
                                        </div>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                )}

                {/* Quick Actions */}
                <div className="bg-white rounded-[32px] p-8 border border-slate-100 shadow-sm">
                    <h3 className="text-xl font-bold text-slate-800 mb-6">Quick Actions</h3>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <label className="flex items-center gap-4 p-4 border border-slate-100 rounded-xl hover:border-blue-300 hover:bg-blue-50/50 cursor-pointer transition-all">
                            <div className="w-12 h-12 bg-green-100 text-green-600 rounded-xl flex items-center justify-center">
                                <Upload size={24} />
                            </div>
                            <div>
                                <p className="font-bold text-slate-800">Upload Resume</p>
                                <p className="text-sm text-slate-500">PDF to auto-extract details</p>
                            </div>
                            <input
                                ref={fileInputRef}
                                type="file"
                                accept=".pdf"
                                className="hidden"
                                onChange={handleResumeUpload}
                                disabled={uploadingResume}
                            />
                        </label>

                        <button
                            onClick={handleGitHubSync}
                            disabled={syncingGithub || !profile.github_username}
                            className="flex items-center gap-4 p-4 border border-slate-100 rounded-xl hover:border-purple-300 hover:bg-purple-50/50 transition-all disabled:opacity-50 text-left"
                        >
                            <div className="w-12 h-12 bg-purple-100 text-purple-600 rounded-xl flex items-center justify-center">
                                {syncingGithub ? <Loader2 size={24} className="animate-spin" /> : <Github size={24} />}
                            </div>
                            <div>
                                <p className="font-bold text-slate-800">Sync GitHub</p>
                                <p className="text-sm text-slate-500">Import your projects</p>
                            </div>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
};

