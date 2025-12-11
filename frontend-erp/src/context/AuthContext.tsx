import React, { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Usuario, LoginResponse, AuthState } from '@/types/auth'; // Asegúrate que Usuario tenga los campos necesarios
import { authService } from '@/services/authService';
import { message } from 'antd';

interface AuthContextType extends AuthState {
    login: (email: string, password: string) => Promise<void>;
    logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<Usuario | null>(null);
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const router = useRouter();

    // Función para cargar el usuario inicial desde el token
    useEffect(() => {
        const initAuth = async () => {
            const token = localStorage.getItem('token');
            if (token) {
                try {
                    const userData = await authService.getMe();
                    setUser(userData);
                    setIsAuthenticated(true);
                } catch (err) {
                    console.error("Error validando sesión:", err);
                    localStorage.removeItem('token');
                    setUser(null);
                    setIsAuthenticated(false);
                    // Opcional: router.push('/login');
                }
            }
            setIsLoading(false);
        };

        initAuth();
    }, []);

    const login = async (email: string, password: string) => {
        setIsLoading(true);
        setError(null);
        try {
            const response: LoginResponse = await authService.login(email, password);
            localStorage.setItem('token', response.access_token);

            const userData = await authService.getMe();
            setUser(userData);
            setIsAuthenticated(true);
            message.success('Bienvenido');

            // Redirección post-login
            router.push('/');
        } catch (err: any) {
            console.error("Login fallido:", err);
            const msg = err.response?.data?.detail || 'Credenciales inválidas';
            setError(msg);
            message.error(msg);
            throw err;
        } finally {
            setIsLoading(false);
        }
    };

    const logout = () => {
        localStorage.removeItem('token');
        setUser(null);
        setIsAuthenticated(false);
        router.push('/login');
        message.info('Sesión cerrada');
    };

    return (
        <AuthContext.Provider value={{ user, isAuthenticated, isLoading, error, login, logout }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
