import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";

const EXAMS = ["NDA", "CDS", "SSB Direct Entry", "AFCAT", "Territorial Army"];
const STAGES = ["Just Starting", "Written Cleared SSB Pending", "Repeater"];
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
    preparing_for: "",
    journey_stage: "",
    city: "",
    state: "",
    weak_areas: [],
    news_scope: "national",
    notifications: { breaking: true, daily_digest: true },
  });

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const toggleWeak = (w) =>
    setForm((f) => ({
      ...f,
      weak_areas: f.weak_areas.includes(w)
        ? f.weak_areas.filter((x) => x !== w)
        : [...f.weak_areas, w],
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
      ? form.preparing_for && form.journey_stage
      : true;

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
                NDA, CDS, SSB, AFCAT & more — tailored defence affairs.
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
              <h2 className="text-lg font-semibold mb-3">
                What are you preparing for?
              </h2>
              <div className="flex flex-wrap gap-2">
                {EXAMS.map((e) => (
                  <button
                    key={e}
                    onClick={() => set("preparing_for", e)}
                    className={`px-3 py-2 rounded-lg border text-sm ${
                      form.preparing_for === e
                        ? "border-accent bg-surface2"
                        : "border-border bg-surface"
                    }`}
                  >
                    {e}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <h2 className="text-lg font-semibold mb-3">
                Where are you in your journey?
              </h2>
              <div className="flex flex-col gap-2">
                {STAGES.map((s) => (
                  <button
                    key={s}
                    onClick={() => set("journey_stage", s)}
                    className={`px-3 py-2 rounded-lg border text-sm text-left ${
                      form.journey_stage === s
                        ? "border-accent bg-surface2"
                        : "border-border bg-surface"
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
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
            <div>
              <h2 className="text-lg font-semibold mb-3">Weak areas</h2>
              <div className="flex flex-wrap gap-2">
                {WEAK_AREAS.map((w) => (
                  <button
                    key={w}
                    onClick={() => toggleWeak(w)}
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
              <h2 className="text-lg font-semibold mb-4">News preferences</h2>
              <div className="space-y-3">
                {SCOPES.map((s) => (
                  <button
                    key={s.key}
                    onClick={() => set("news_scope", s.key)}
                    className={`w-full text-left p-4 rounded-xl border transition ${
                      form.news_scope === s.key
                        ? "border-accent bg-surface2"
                        : "border-border bg-surface"
                    }`}
                  >
                    <div className="font-semibold">{s.label}</div>
                    <div className="text-muted text-sm">{s.desc}</div>
                  </button>
                ))}
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
              disabled={saving}
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
