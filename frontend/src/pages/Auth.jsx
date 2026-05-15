import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function Auth() {
  const navigate = useNavigate();
  const { login, signup } = useAuth();
  const [mode, setMode] = useState("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      if (mode === "login") await login(email, password);
      else await signup(email, password);
      navigate("/", { replace: true });
    } catch (e2) {
      setErr(e2.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg text-text flex items-center justify-center px-5">
      <div className="w-full max-w-sm">
        <h1 className="text-2xl font-bold">ContextNews</h1>
        <p className="text-muted text-sm mb-8">
          Causal context for defence aspirants.
        </p>

        <div className="flex gap-2 mb-6">
          {["login", "signup"].map((m) => (
            <button
              key={m}
              onClick={() => {
                setMode(m);
                setErr("");
              }}
              className={`flex-1 py-2 rounded-lg text-sm font-medium border ${
                mode === m
                  ? "border-accent bg-surface2"
                  : "border-border bg-surface text-muted"
              }`}
            >
              {m === "login" ? "Log in" : "Sign up"}
            </button>
          ))}
        </div>

        <form onSubmit={submit} className="space-y-3">
          <input
            type="email"
            required
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-surface border border-border rounded-lg px-3 py-2.5 text-sm outline-none focus:border-accent"
          />
          <input
            type="password"
            required
            minLength={6}
            placeholder="Password (min 6 chars)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-surface border border-border rounded-lg px-3 py-2.5 text-sm outline-none focus:border-accent"
          />
          {err && <p className="text-impactHigh text-sm">{err}</p>}
          <button
            disabled={busy}
            className="w-full py-2.5 rounded-lg bg-accent text-white text-sm font-semibold disabled:opacity-50"
          >
            {busy ? "Please wait…" : mode === "login" ? "Log in" : "Create account"}
          </button>
        </form>
      </div>
    </div>
  );
}
