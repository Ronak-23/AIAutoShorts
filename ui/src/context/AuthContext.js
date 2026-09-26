/**
 * ui/src/context/AuthContext.js
 * =============================
 * Authentication state management and user session provider.
 */

import { html, createContext, useState, useEffect, useContext } from '../html.js';
import { api, authStorage } from '../api/client.js';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const checkAuth = async () => {
    try {
      const token = authStorage.getToken();
      if (!token) {
        setUser(null);
        return;
      }
      const me = await api.auth.getMe();
      setUser(me);
    } catch (e) {
      authStorage.clearToken();
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkAuth();
  }, []);

  const login = async (username, password) => {
    const res = await api.auth.login(username, password);
    authStorage.setToken(res.access_token);
    setUser(res.user);
    return res.user;
  };

  const register = async (username, password, email) => {
    const res = await api.auth.register(username, password, email);
    authStorage.setToken(res.access_token);
    setUser(res.user);
    return res.user;
  };

  const logout = () => {
    authStorage.clearToken();
    setUser(null);
  };

  return html`
    <${AuthContext.Provider} value=${{ user, loading, login, register, logout, checkAuth }}>
      ${children}
    <//>
  `;
}

export function useAuth() {
  return useContext(AuthContext);
}
