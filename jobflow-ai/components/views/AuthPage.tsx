import React, { useState } from 'react';
import { User, Mail as MailIcon, Lock, Eye, EyeOff, LogIn, UserPlus, Chrome, Github } from 'lucide-react';

export const AuthPage = ({ onLogin }: { onLogin: () => void }) => {
    const [isLogin, setIsLogin] = useState(true);
    const [showPassword, setShowPassword] = useState(false);
    const [loading, setLoading] = useState(false);

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        // Simulate API call
        setTimeout(() => {
            setLoading(false);
            onLogin();
        }, 1200);
    };

    return (
        <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6 relative overflow-hidden">
            {/* Decorative background elements */}
            <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-blue-100 rounded-full blur-[120px] opacity-50"></div>
            <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-purple-100 rounded-full blur-[120px] opacity-50"></div>

            <div className="w-full max-w-5xl bg-white rounded-[40px] shadow-2xl border border-slate-100 overflow-hidden flex flex-col md:flex-row relative z-10 animate-in zoom-in-95 duration-500">
                {/* Branding/Illustration Side */}
                <div className="w-full md:w-1/2 bg-blue-600 p-12 text-white flex flex-col justify-between relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>

                    <div>
                        <div className="flex items-center gap-3 mb-12">
                            <div className="w-10 h-10 bg-white rounded-xl flex items-center justify-center text-blue-600 font-bold text-xl">J</div>
                            <span className="text-2xl font-bold tracking-tight">JobFlow AI</span>
                        </div>
                        <h1 className="text-4xl lg:text-5xl font-bold leading-tight mb-6">
                            Accelerate Your Career with AI
                        </h1>
                        <p className="text-blue-100 text-lg max-w-md leading-relaxed">
                            Automate your applications, track your pipeline, and land your dream role with intelligent insights.
                        </p>
                    </div>

                    <div className="space-y-6 relative z-10">
                        <div className="flex items-center gap-4 bg-white/10 p-4 rounded-2xl backdrop-blur-md">
                            <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
                                <CheckCircle size={20} />
                            </div>
                            <p className="text-sm font-medium">Auto-generate tailored cover letters in seconds.</p>
                        </div>
                        <div className="flex items-center gap-4 bg-white/10 p-4 rounded-2xl backdrop-blur-md">
                            <div className="w-10 h-10 bg-blue-500 rounded-lg flex items-center justify-center">
                                <BarChart2 size={20} />
                            </div>
                            <p className="text-sm font-medium">Real-time tracking of every application status.</p>
                        </div>
                    </div>
                </div>

                {/* Form Side */}
                <div className="w-full md:w-1/2 p-12 lg:p-16 flex flex-col justify-center">
                    <div className="mb-10 text-center md:text-left">
                        <h2 className="text-3xl font-bold text-slate-800 mb-2">
                            {isLogin ? 'Welcome back' : 'Create an account'}
                        </h2>
                        <p className="text-slate-500">
                            {isLogin ? 'Enter your details to access your dashboard.' : 'Join thousands of developers scaling their careers.'}
                        </p>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-5">
                        {!isLogin && (
                            <div className="space-y-2">
                                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Full Name</label>
                                <div className="relative">
                                    <User className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                                    <input
                                        type="text"
                                        placeholder="Muhammad Ahmed"
                                        className="w-full pl-12 pr-4 py-3.5 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none transition-all"
                                        required
                                    />
                                </div>
                            </div>
                        )}

                        <div className="space-y-2">
                            <label className="text-xs font-bold text-slate-400 uppercase tracking-widest ml-1">Email Address</label>
                            <div className="relative">
                                <MailIcon className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                                <input
                                    type="email"
                                    placeholder="ahmed@example.com"
                                    className="w-full pl-12 pr-4 py-3.5 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none transition-all"
                                    required
                                />
                            </div>
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between items-center ml-1">
                                <label className="text-xs font-bold text-slate-400 uppercase tracking-widest">Password</label>
                                {isLogin && <button type="button" className="text-xs font-bold text-blue-600 hover:underline">Forgot?</button>}
                            </div>
                            <div className="relative">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400" size={18} />
                                <input
                                    type={showPassword ? "text" : "password"}
                                    placeholder="••••••••"
                                    className="w-full pl-12 pr-12 py-3.5 bg-slate-50 border border-slate-200 rounded-2xl text-sm focus:ring-2 focus:ring-blue-500 focus:bg-white outline-none transition-all"
                                    required
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                                >
                                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                                </button>
                            </div>
                        </div>

                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full py-4 bg-blue-600 text-white font-bold rounded-2xl shadow-xl shadow-blue-100 hover:bg-blue-700 transition-all flex items-center justify-center gap-2 group disabled:opacity-70 disabled:cursor-not-allowed"
                        >
                            {loading ? (
                                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                            ) : (
                                <>
                                    {isLogin ? (
                                        <>Sign In <LogIn size={20} className="group-hover:translate-x-1 transition-transform" /></>
                                    ) : (
                                        <>Create Account <UserPlus size={20} className="group-hover:translate-x-1 transition-transform" /></>
                                    )}
                                </>
                            )}
                        </button>
                    </form>

                    <div className="my-8 flex items-center gap-4">
                        <div className="flex-1 h-px bg-slate-100"></div>
                        <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">or continue with</span>
                        <div className="flex-1 h-px bg-slate-100"></div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <button className="flex items-center justify-center gap-3 py-3 border border-slate-200 rounded-2xl font-bold text-slate-600 hover:bg-slate-50 transition-colors text-sm">
                            <Chrome size={18} /> Google
                        </button>
                        <button className="flex items-center justify-center gap-3 py-3 border border-slate-200 rounded-2xl font-bold text-slate-600 hover:bg-slate-50 transition-colors text-sm">
                            <Github size={18} /> GitHub
                        </button>
                    </div>

                    <p className="mt-10 text-center text-sm text-slate-500">
                        {isLogin ? "Don't have an account?" : "Already have an account?"}{' '}
                        <button
                            onClick={() => setIsLogin(!isLogin)}
                            className="text-blue-600 font-bold hover:underline"
                        >
                            {isLogin ? 'Sign up free' : 'Log in here'}
                        </button>
                    </p>
                </div>
            </div>
        </div>
    );
};

// Add missing imports for icons used in the illustration side
import { CheckCircle, BarChart2 } from 'lucide-react';
