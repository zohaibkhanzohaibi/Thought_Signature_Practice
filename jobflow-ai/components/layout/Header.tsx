import React, { useState, useEffect, useCallback } from 'react';
import { Sun, Moon, Bell } from 'lucide-react';
import { useSocketIO } from '../../contexts/SocketIOContext';

export const Header = ({ darkMode, setDarkMode }: { darkMode: boolean; setDarkMode: (d: boolean) => void }) => {
    const [userName, setUserName] = useState("Guest");
    // Default avatar
    const [avatarUrl, setAvatarUrl] = useState("https://picsum.photos/id/1012/64/64");
    const { socket } = useSocketIO();

    // 1. Define the fetch function so we can reuse it
    const fetchProfile = useCallback(async () => {
        const userId = localStorage.getItem('marathon_user_id');
        if (!userId) return;

        try {
            const response = await fetch(`http://localhost:8000/api/profiles/${userId}`);
            if (response.ok) {
                const data = await response.json();
                
                // Update Name
                if (data.full_name) {
                    setUserName(data.full_name);
                }

                // Update Avatar
                if (data.avatar_url) {
                    setAvatarUrl(data.avatar_url);
                } else {
                    // Generate avatar from ID if none exists
                    setAvatarUrl(`https://api.dicebear.com/7.x/avataaars/svg?seed=${userId}`);
                }
            }
        } catch (error) {
            console.error("Failed to fetch profile:", error);
        }
    }, []);

    // 2. Setup Effect: Fetch on mount AND listen for socket updates
    useEffect(() => {
        // Initial fetch
        fetchProfile();

        if (!socket) return;

        const userId = localStorage.getItem('marathon_user_id');
        if (!userId) return;

        // Listen for real-time updates (like Gmail connecting)
        socket.on(`gmail_update_${userId}`, (data) => {
            // If Gmail connects, re-fetch the profile to get the real name
            if (data.type === 'connected') {
                console.log("Gmail connected, refreshing profile...");
                fetchProfile();
            }
        });

        return () => {
            socket.off(`gmail_update_${userId}`);
        };
    }, [socket, fetchProfile]);

    return (
        <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-end sticky top-0 z-10">
            <div className="flex items-center gap-4">
                <button onClick={() => setDarkMode(!darkMode)} className="p-2 text-slate-500 hover:bg-slate-100 rounded-full transition-colors">
                    {darkMode ? <Sun size={20} /> : <Moon size={20} />}
                </button>
                <button className="p-2 text-slate-500 hover:bg-slate-100 rounded-full transition-colors relative">
                    <Bell size={20} />
                    <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-red-500 border-2 border-white rounded-full"></span>
                </button>
                <div className="h-8 w-px bg-slate-200 mx-2"></div>
                <div className="flex items-center gap-3">
                    <div className="text-right hidden sm:block">
                        <p className="text-sm font-bold text-slate-800 leading-none mb-1">
                            {userName}
                        </p>
                    </div>
                    <img 
                        src={avatarUrl} 
                        className="w-10 h-10 rounded-xl border-2 border-white shadow-sm bg-slate-100 object-cover" 
                        alt="User avatar" 
                    />
                </div>
            </div>
        </header>
    );
};