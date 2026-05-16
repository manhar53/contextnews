import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

const WEAK_AREAS = [
  "Lecturette Topics",
  "Current Affairs Depth",
  "Defence News",
  "International Relations",
  "Geopolitics",
  "Indian Economy",
];
const SCOPES = [
  { key: "global", label: "Global", desc: "Worldwide geopolitics & economy" },
  { key: "national", label: "National", desc: "India-focused defence & policy" },
  { key: "local", label: "Local", desc: "Your city & state developments" },
];
const COMING_SOON = ["Business Owner", "Student", "Professional"];

function Stepper({ step }) {
  return (
    <div className="flex gap-2 mb-8">
      {[1, 2, 3].map((s) => (
        <div
          key={s}
          className={`h-1.5 flex-1 rounded-full ${
            s <= step ? "bg-accent" : "bg-border"
          }`}
        />
      ))}
    </div>
  );
}

export default function Onboarding({ onDone }) {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    profile: "defence_aspirant",
    city: "",
    state: "",
    weak_areas: [],
    news_scopes: ["national"],
    notifications: { breaking: true, daily_digest: true },
  });

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const toggleIn = (key, val) =>
    setForm((f) => ({
      ...f,
      [key]: f[key].includes(val)
        ? f[key].filter((x) => x !== val)
        : [...f[key], val],
    }));
  const toggleNotif = (k) =>
    setForm((f) => ({
      ...f,
      notifications: { ...f.notifications, [k]: !f.notifications[k] },
    }));

  const finish = async () => {
    setSaving(true);
    try {
      await api.savePreferences({ ...form, onboarded: true });
      onDone?.();
      navigate("/", { replace: true });
    } catch (e) {
      alert("Could not save preferences: " + e.message);
    } finally {
      setSaving(false);
    }
  };

  const canNext =
    step === 1
      ? form.profile === "defence_aspirant"
      : step === 2
      ? true
      : form.news_scopes.length > 0;

  return (
    <div className="min-h-screen bg-bg text-text px-5 py-10">
      <div className="max-w-md mx-auto">
        <h1 className="text-2xl font-bold mb-1">ContextNews</h1>
        <p className="text-muted text-sm mb-6">Let's personalise your feed.</p>
        <Stepper step={step} />

        {step === 1 && (
          <div>
            <h2 className="text-lg font-semibold mb-4">Select your profile</h2>
            <button
              onClick={() => set("profile", "defence_aspirant")}
              className={`w-full text-left p-4 rounded-xl border mb-3 transition ${
                form.profile === "defence_aspirant"
                  ? "border-accent bg-surface2"
                  : "border-border bg-surface"
              }`}
            >
              <div className="font-semibold">Defence Aspirant</div>
              <div className="text-muted text-sm">
                NDA, CDS, SSB, AFCAT, Territorial Army — defence current affairs.
              </div>
            </button>
            {COMING_SOON.map((p) => (
              <div
                key={p}
                className="w-full p-4 rounded-xl border border-border bg-surface mb-3 opacity-40 cursor-not-allowed"
              >
                <div className="font-semibold">{p}</div>
                <div className="text-sm">Coming soon</div>
              </div>
            ))}
          </div>
        )}

        {step === 2 && (
          <div className="space-y-6">
            <div>
              <h2 className="text-lg font-semibold mb-1">Your location</h2>
              <p className="text-muted text-xs mb-3">
                Used only for Local news.
              </p>
              <div className="grid grid-cols-2 gap-3">
                <input
                  placeholder="City"
                  value={form.city}
                  onChange={(e) => set("city", e.target.value)}
                  className="bg-surface border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-accent"
                />
                <input
                  placeholder="State"
                  value={form.state}
                  onChange={(e) => set("state", e.target.value)}
                  className="bg-surface border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-accent"
                />
              </div>
            </div>
            <div>
              <h2 className="text-lg font-semibold mb-3">
                Weak areas{" "}
                <span className="text-muted text-xs font-normal">
                  (optional)
                </span>
              </h2>
              <div className="flex flex-wrap gap-2">
                {WEAK_AREAS.map((w) => (
                  <button
                    key={w}
                    onClick={() => toggleIn("weak_areas", w)}
                    className={`px-3 py-2 rounded-lg border text-sm ${
                      form.weak_areas.includes(w)
                        ? "border-accent bg-surface2"
                        : "border-border bg-surface"
                    }`}
                  >
                    {w}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {step === 3 && (
          <div className="space-y-8">
            <div>
              <h2 className="text-lg font-semibold mb-1">News scope</h2>
              <p className="text-muted text-xs mb-3">
                Pick one or more — your feed blends all selected.
              </p>
              <div className="space-y-3">
                {SCOPES.map((s) => {
                  const on = form.news_scopes.includes(s.key);
                  return (
                    <button
                      key={s.key}
                      onClick={() => toggleIn("news_scopes", s.key)}
                      className={`w-full text-left p-4 rounded-xl border transition flex items-center justify-between ${
                        on
                          ? "border-accent bg-surface2"
                          : "border-border bg-surface"
                      }`}
                    >
                      <span>
                        <span className="font-semibold block">{s.label}</span>
                        <span className="text-muted text-sm">{s.desc}</span>
                      </span>
                      <span
                        className={`w-5 h-5 rounded border flex items-center justify-center text-xs ${
                          on
                            ? "bg-accent border-accent text-white"
                            : "border-border"
                        }`}
                      >
                        {on ? "✓" : ""}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>
            <div>
              <h2 className="text-lg font-semibold mb-3">Notifications</h2>
              {[
                { k: "breaking", label: "Breaking defence news alerts" },
                { k: "daily_digest", label: "Daily current-affairs digest" },
              ].map((n) => (
                <label
                  key={n.k}
                  className="flex items-center justify-between p-3 rounded-lg border border-border bg-surface mb-2 cursor-pointer"
                >
                  <span className="text-sm">{n.label}</span>
                  <input
                    type="checkbox"
                    checked={!!form.notifications[n.k]}
                    onChange={() => toggleNotif(n.k)}
                    className="accent-accent w-4 h-4"
                  />
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="flex gap-3 mt-10">
          {step > 1 && (
            <button
              onClick={() => setStep((s) => s - 1)}
              className="px-5 py-2.5 rounded-lg border border-border text-sm"
            >
              Back
            </button>
          )}
          {step < 3 ? (
            <button
              disabled={!canNext}
              onClick={() => setStep((s) => s + 1)}
              className="flex-1 px-5 py-2.5 rounded-lg bg-accent text-white text-sm font-semibold disabled:opacity-40"
            >
              Continue
            </button>
          ) : (
            <button
              disabled={saving || !canNext}
              onClick={finish}
              className="flex-1 px-5 py-2.5 rounded-lg bg-accent text-white text-sm font-semibold disabled:opacity-50"
            >
              {saving ? "Saving…" : "Finish"}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
