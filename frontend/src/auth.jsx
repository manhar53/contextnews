import { createContext, useContext, useEffect, useState } from "react";
import { api, getToken, setToken } from "./api";

const AuthCtx = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null); // { email, onboarded }
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!getToken()) {
      setReady(true);
      return;
    }
    api
      .getPreferences()
      .then((p) =>
        setUser({ email: localStorage.getItem("cn_email") || "", onboarded: p.onboarded })
      )
      .catch(() => {
        setToken(null);
        setUser(null);
      })
      .finally(() => setReady(true));
  }, []);

  const persist = (tok) => {
    setToken(tok.access_token);
    localStorage.setItem("cn_email", tok.email);
    setUser({ email: tok.email, onboarded: tok.onboarded });
  };

  const login = async (email, password) => persist(await api.login(email, password));
  const signup = async (email, password) => persist(await api.signup(email, password));
  const logout = () => {
    setToken(null);
    localStorage.removeItem("cn_email");
    setUser(null);
  };
  const setOnboarded = (v) => setUser((u) => (u ? { ...u, onboarded: v } : u));

  return (
    <AuthCtx.Provider value={{ user, ready, login, signup, logout, setOnboarded }}>
      {children}
    </AuthCtx.Provider>
  );
}

export const useAuth = () => useContext(AuthCtx);
