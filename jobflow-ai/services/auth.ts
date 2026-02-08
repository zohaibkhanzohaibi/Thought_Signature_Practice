import { UserProfile } from "../types";

const API_URL = "http://localhost:8000/auth";

export interface AuthResponse {
    access_token: string;
    token_type: string;
}

export interface User {
    id: string;
    email: string;
    full_name?: string;
}

export const authService = {
    async login(email: string, password: string): Promise<AuthResponse> {
        const formData = new FormData();
        formData.append("username", email);
        formData.append("password", password);

        const response = await fetch(`${API_URL}/login`, {
            method: "POST",
            body: formData,
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Login failed");
        }

        const data = await response.json();
        localStorage.setItem("token", data.access_token);
        return data;
    },

    async signup(email: string, password: string, fullName?: string): Promise<User> {
        const response = await fetch(`${API_URL}/signup`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ email, password, full_name: fullName }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Signup failed");
        }

        return response.json();
    },

    logout() {
        localStorage.removeItem("token");
    },

    getToken() {
        return localStorage.getItem("token");
    },

    isAuthenticated() {
        return !!localStorage.getItem("token");
    },

    async loginWithGoogle(token: string): Promise<AuthResponse> {
        const response = await fetch(`${API_URL}/google`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ token }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || "Google login failed");
        }

        const data = await response.json();
        localStorage.setItem("token", data.access_token);
        return data;
    },

    getUserIdFromToken(): string | null {
        const token = localStorage.getItem("token");
        if (!token) return null;
        try {
            const payload = JSON.parse(atob(token.split('.')[1]));
            return payload.sub;
        } catch (e) {
            return null;
        }
    }
};
