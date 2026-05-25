import React, { createContext, useContext, useEffect, useState } from 'react';
import { useRouter } from 'next/router';
import { Usuario, AuthState } from '@/types/auth';
import { authService } from '@/services/authService';
import { setAccessToken } from '@/lib/axios';
import { queryClient } from '@/lib/queryClient';
import { message } from 'antd';

const EMPRESA_STORAGE_KEY = 'ui.empresa.selected';

interface AuthContextType extends AuthState {
    login: (email: string, password: string) => Promise<void>;
    logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<Usuario | null>(null);
    const [isAuthenticated, setIsAuthenticated] = useState<boolean>(false);
    const [isLoading, setIsLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);
    const router = useRouter();

    // Restaurar sesión al cargar la app usando la cookie httpOnly del refresh token.
    // Si la cookie es válida, el backend devuelve un nuevo access token; si no, el
    // usuario no está autenticado y se redirigirá al login cuando sea necesario.
    useEffect(() => {
        const initAuth = async () => {
            try {
                const tokens = await authService.refreshToken();
                setAccessToken(tokens.access_token);
                const userData = await authService.getMe();
                setUser(userData);
                setIsAuthenticated(true);
            } catch {
                // Sin cookie válida → sesión inexistente o expirada
                setAccessToken(null);
                setUser(null);
                setIsAuthenticated(false);
            } finally {
                setIsLoading(false);
            }
        };

        initAuth();
    }, []);

    const login = async (email: string, password: string) => {
        setIsLoading(true);
        setError(null);
        try {
            const response = await authService.login(email, password);
            // access_token en memoria; refresh_token llegó como httpOnly cookie
            setAccessToken(response.access_token);

            const userData = await authService.getMe();
            setUser(userData);
            setIsAuthenticated(true);
            message.success('Bienvenido');

            router.push('/');
        } catch (err: any) {
            console.error('Login fallido:', err);
            const msg = err.response?.data?.detail || 'Credenciales inválidas';
            setError(msg);
            message.error(msg);
            throw err;
        } finally {
            setIsLoading(false);
        }
    };

    const logout = async () => {
        // El backend invalida el JTI y borra la cookie usando el refresh_token de la cookie
        await authService.logout();

        // Limpiar estado local
        setAccessToken(null);
        localStorage.removeItem(EMPRESA_STORAGE_KEY);
        queryClient.clear();
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
