import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api";
import { useAuth } from "../auth";
import NewsCard from "../components/NewsCard.jsx";
import { CardSkeleton } from "../components/Skeleton.jsx";

const TABS = [
  { key: "top", label: "Top Stories" },
  { key: "defence", label: "Defence Specific" },
  { key: "personalised", label: "Personalised For You" },
];
const PAGE = 20;

export default function Home() {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [tab, setTab] = useState("top");
  const [search, setSearch] = useState("");
  const [q, setQ] = useState("");
  const [period, setPeriod] = useState("30d");
  const [lect, setLect] = useState(""); // "" | security | economic | social
  const [stats, setStats] = useState(null); // owner-only
  const [items, setItems] = useState([]);
  const [offset, setOffset] = useState(0);
  const [loading, setLoading] = useState(true);
  const [more, setMore] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [usage, setUsage] = useState(null);
  const sentinel = useRef(null);

  const loadPage = useCallback(
    async (reset) => {
      const off = reset ? 0 : offset;
      if (reset) setLoading(true);
      try {
        const batch = await api.listNews({
          tab, q, period, lecturette: lect, limit: PAGE, offset: off,
        });
        setItems((prev) => (reset ? batch : [...prev, ...batch]));
        setOffset(off + batch.length);
        setMore(batch.length === PAGE);
      } catch (e) {
        if (e.status === 401) logout();
      } finally {
        setLoading(false);
      }
    },
    [tab, q, period, lect, offset, logout]
  );

  // reset feed when tab, query, period or lecturette filter changes
  useEffect(() => {
    setItems([]);
    setOffset(0);
    setMore(true);
    loadPage(true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab, q, period, lect]);

  useEffect(() => {
    api.usage().then(setUsage).catch(() => {});
  }, []);

  // infinite scroll
  useEffect(() => {
    if (!sentinel.current || !more || loading) return;
    const obs = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) loadPage(false);
      },
      { rootMargin: "300px" }
    );
    obs.observe(sentinel.current);
    return () => obs.disconnect();
  }, [more, loading, loadPage]);

  const refresh = async () => {
    setRefreshing(true);
    try {
      await api.refreshNews();
      setItems([]);
      setOffset(0);
      setMore(true);
      loadPage(true);
    } catch (e) {
      alert("Refresh failed: " + e.message);
    } finally {
      setRefreshing(false);
    }
  };

  return (
    <div className="min-h-screen bg-bg text-text">
      <header className="sticky top-0 z-10 bg-bg border-b border-border">
        <div className="max-w-3xl mx-auto px-5 py-4">
          <div className="flex items-start justify-between mb-3 gap-3 flex-wrap">
            <div className="min-w-0">
              <h1 className="text-xl font-bold">ContextNews</h1>
              {usage && (
                <p className="text-xs text-muted">
                  {usage.unlimited
                    ? "Unlimited analyses (owner)"
                    : `${usage.remaining} of ${usage.limit} analyses remaining today`}
                </p>
              )}
            </div>
            <div className="flex gap-2 flex-wrap justify-end">
              <button
                onClick={refresh}
                disabled={refreshing}
                className="text-sm px-3 py-1.5 rounded-lg border border-border hover:border-accent disabled:opacity-50"
              >
                {refreshing ? "Refreshing…" : "Refresh"}
              </button>
              {usage?.unlimited && (
                <button
                  onClick={async () => {
                    if (
                      !confirm(
                        "One-time historic backfill: pulls ~12 months of older related coverage from GDELT so causal timelines have more depth. Only visible in the feed when 'All time' or a year filter is set. Run now?"
                      )
                    )
                      return;
                    setRefreshing(true);
                    try {
                      await api.backfill();
                      setItems([]);
                      setOffset(0);
                      setMore(true);
                      loadPage(true);
                    } catch (e) {
                      alert("Backfill failed: " + e.message);
                    } finally {
                      setRefreshing(false);
                    }
                  }}
                  disabled={refreshing}
                  title="Owner-only: one-shot historic depth load"
                  className="text-sm px-3 py-1.5 rounded-lg border border-border hover:border-accent disabled:opacity-50"
                >
                  Backfill
                </button>
              )}
              {usage?.unlimited && (
                <button
                  onClick={async () => {
                    try {
                      setStats(await api.adminStats());
                    } catch (e) {
                      alert("Stats failed: " + e.message);
                    }
                  }}
                  className="text-sm px-3 py-1.5 rounded-lg border border-border hover:border-accent"
                  title="Owner-only operational stats"
                >
                  Stats
                </button>
              )}
              <button
                onClick={() => navigate("/onboarding")}
                className="text-sm px-3 py-1.5 rounded-lg border border-border hover:border-accent"
              >
                Preferences
              </button>
              <button
                onClick={logout}
                className="text-sm px-3 py-1.5 rounded-lg border border-border hover:border-accent text-muted"
              >
                Log out
              </button>
            </div>
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              setQ(search.trim());
            }}
            className="mb-3 flex flex-col sm:flex-row gap-2"
          >
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search headlines… (searches all dates)"
              className="flex-1 min-w-0 bg-surface border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-accent"
            />
            <div className="flex gap-2">
              <select
                value={period}
                onChange={(e) => setPeriod(e.target.value)}
                title="Time range"
                className="flex-1 sm:flex-none bg-surface border border-border rounded-lg px-2 py-2 text-sm outline-none focus:border-accent"
              >
              <option value="24h">24 hours</option>
              <option value="7d">This week</option>
              <option value="30d">This month</option>
              <option value="90d">3 months</option>
              <option value="1y">This year</option>
              <option value="all">All time (incl. historic)</option>
              </select>
              <button
                type="submit"
                className="px-4 py-2 rounded-lg bg-accent text-white text-sm font-semibold"
              >
                Search
              </button>
              {q && (
                <button
                  type="button"
                  onClick={() => {
                    setSearch("");
                    setQ("");
                  }}
                  className="text-sm px-3 rounded-lg border border-border text-muted"
                >
                  Clear
                </button>
              )}
            </div>
          </form>

          <div className="flex gap-5 overflow-x-auto no-scrollbar border-b border-border">
            {TABS.map((t) => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`whitespace-nowrap text-sm pb-2 -mb-px border-b-2 ${
                  tab === t.key
                    ? "border-accent text-text"
                    : "border-transparent text-muted hover:text-text"
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          <div className="flex items-center gap-1 mt-3 text-xs">
            <span className="text-muted mr-1">Lecturette:</span>
            {[
              ["", "All"],
              ["security", "Security"],
              ["economic", "Economic"],
              ["social", "Social"],
            ].map(([key, label]) => (
              <button
                key={key || "all"}
                onClick={() => setLect(key)}
                className={`px-2 py-1 border ${
                  lect === key
                    ? "border-accent text-text"
                    : "border-border text-muted hover:text-text"
                }`}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-5 py-6">
        {loading ? (
          <div className="grid gap-3 md:grid-cols-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <CardSkeleton key={i} />
            ))}
          </div>
        ) : items.length === 0 ? (
          <div className="text-muted text-sm border border-dashed border-border rounded-xl p-8 text-center">
            No articles yet. Hit “Refresh” to ingest the latest RSS + NewsAPI feeds.
          </div>
        ) : (
          <>
            <div className="grid gap-3 md:grid-cols-2">
              {items.map((a) => (
                <NewsCard key={a.id} article={a} />
              ))}
            </div>
            <div ref={sentinel} className="h-10" />
            {more && (
              <p className="text-center text-muted text-xs py-4">Loading more…</p>
            )}
          </>
        )}
      </main>

      {stats && (
        <div
          className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-5"
          onClick={() => setStats(null)}
        >
          <div
            className="bg-surface border border-border rounded-xl max-w-md w-full p-5 text-sm"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between mb-3">
              <h2 className="font-bold">Operational stats</h2>
              <button
                onClick={() => setStats(null)}
                className="text-muted hover:text-text"
              >
                ✕
              </button>
            </div>
            <div className="grid grid-cols-2 gap-y-1 gap-x-3 mb-4">
              <div className="text-muted">Users</div>
              <div className="text-right">{stats.users}</div>
              <div className="text-muted">Articles ingested</div>
              <div className="text-right">{stats.articles}</div>
              <div className="text-muted">Analyses total</div>
              <div className="text-right">{stats.analyses_total}</div>
              <div className="text-muted">Analyses last 24h</div>
              <div className="text-right">{stats.analyses_24h}</div>
              <div className="text-muted">Users at daily limit (today)</div>
              <div className="text-right">{stats.users_at_daily_limit_today}</div>
              <div className="text-muted">Daily limit / user</div>
              <div className="text-right">{stats.daily_limit_per_user}</div>
              <div className="text-muted">Auto-analyse / 30 min</div>
              <div className="text-right">{stats.auto_analyse_per_run}</div>
            </div>
            <div className="mb-3">
              <div className="text-muted text-xs mb-1">LLM providers today</div>
              {stats.providers_today.length === 0 ? (
                <div className="text-muted text-xs">No LLM calls yet today.</div>
              ) : (
                <table className="w-full text-xs">
                  <thead className="text-muted">
                    <tr>
                      <th className="text-left font-normal">provider</th>
                      <th className="text-right font-normal">attempts</th>
                      <th className="text-right font-normal">ok</th>
                      <th className="text-right font-normal">429</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats.providers_today.map((p) => (
                      <tr key={p.provider}>
                        <td>{p.provider}</td>
                        <td className="text-right">{p.attempts}</td>
                        <td className="text-right">{p.successes}</td>
                        <td className="text-right">{p.rate_limits}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
            <div className="text-xs text-muted">
              Configured:&nbsp;
              {["gemini", "groq", "openrouter"].map((k) => (
                <span key={k} className="mr-2">
                  {k} {stats.configured[k] ? "✓" : "✗"}
                </span>
              ))}
            </div>
            {stats.last_analysis_at && (
              <div className="text-xs text-muted mt-1">
                Last analysis: {new Date(stats.last_analysis_at).toLocaleString()}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
