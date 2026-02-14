import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { io, Socket } from 'socket.io-client';

type SocketContextType = {
    socket: Socket | null;
    connected: boolean;
};

const SocketIOContext = createContext<SocketContextType>({ socket: null, connected: false });

export const SocketIOProvider = ({ children }: { children: ReactNode }) => {
    const [socket, setSocket] = useState<Socket | null>(null);
    const [connected, setConnected] = useState(false);

    useEffect(() => {
        const userId = localStorage.getItem('marathon_user_id');
        const base = (import.meta as any).env?.VITE_API_URL ?? 'http://localhost:8000';
        const url = userId ? `${base}/socket.io/?userId=${encodeURIComponent(userId)}` : `${base}/socket.io/`;

        const s: Socket = io(url, {
            path: '/socket.io',
            transports: ['websocket', 'polling'],
            upgrade: true,
            autoConnect: true,
            reconnection: true,
            reconnectionAttempts: Infinity,
            reconnectionDelay: 1000,
        });

        const onConnect = () => setConnected(true);
        const onDisconnect = () => setConnected(false);

        s.on('connect', onConnect);
        s.on('disconnect', onDisconnect);
        s.on('connect_error', (err: any) => console.error('Socket connect_error', err));

        setSocket(s);

        return () => {
            s.off('connect', onConnect);
            s.off('disconnect', onDisconnect);
            s.off('connect_error');
            try {
                s.disconnect();
            } catch (e) {
                // ignore
            }
            setSocket(null);
        };
    }, []);

    return <SocketIOContext.Provider value={{ socket, connected }}>{children}</SocketIOContext.Provider>;
};

export const useSocketIO = () => useContext(SocketIOContext);
