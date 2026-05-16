import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api";
import Timeline from "../components/Timeline.jsx";
import ImpactTag from "../components/ImpactTag.jsx";
import { DetailSkeleton } from "../components/Skeleton.jsx";

const RELEVANCE_COLOR = {
  high: "text-impactHigh",
  medium: "text-impactMedium",
  low: "text-impactLow",
};

export default function NewsDetail() {
  const { id } = useParams();
  const [vote, setVote] = useState(null); // 'up' | 'down'
  const [article, setArticle] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  useEffect(() => {
    setLoading(true);
    api.signalClick(id).catch(() => {}); // layer 3: opening = interest
    api
      .getNewsDetail(id)
      .then(setArticle)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const runAnalysis = async () => {
    setAnalyzing(true);
    setError("");
    try {
      const updated = await api.analyze(id);
      setArticle(updated);
    } catch (e) {
      setError(e.message);
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-bg">
        <DetailSkeleton />
      </div>
    );
  }

  if (error && !article) {
    return (
      <div className="min-h-screen bg-bg text-text p-6">
        <Link to="/" className="text-accent text-sm">
          ← Back
        </Link>
        <p className="mt-4 text-impactHigh">{error}</p>
      </div>
    );
  }

  const a = article.analysis;
  const lec = a?.lecturette_structure || {};
  const dai = a?.defence_aspirant_impact || {};

  return (
    <div className="min-h-screen bg-bg text-text">
      <div className="max-w-3xl mx-auto px-5 py-6">
        <div className="flex items-center justify-between">
          <Link to="/" className="text-accent text-sm">
            ← Back to feed
          </Link>
          <div className="flex items-center gap-2 print:hidden">
            <button
              onClick={() => {
                setVote("up");
                api.signalUp(id).catch(() => setVote(null));
              }}
              className={`text-xs px-3 py-1.5 rounded-lg border ${
                vote === "up"
                  ? "border-impactLow text-impactLow"
                  : "border-border text-muted hover:text-impactLow"
              }`}
            >
              👍 Helpful
            </button>
            <button
              onClick={() => {
                setVote("down");
                api.signalDown(id).catch(() => setVote(null));
              }}
              className={`text-xs px-3 py-1.5 rounded-lg border ${
                vote === "down"
                  ? "border-impactHigh text-impactHigh"
                  : "border-border text-muted hover:text-impactHigh"
              }`}
            >
              👎 Not relevant
            </button>
          </div>
        </div>

        <div className="mt-4 flex items-start justify-between gap-3">
          <h1 className="text-2xl font-bold leading-tight">{article.headline}</h1>
          <ImpactTag level={article.impact_level} />
        </div>
        <div className="text-muted text-xs mt-2">
          {article.source}
          {article.author ? ` · ${article.author}` : ""}
          {article.published_at
            ? ` · ${new Date(article.published_at).toLocaleString()}`
            : ""}{" "}
          ·{" "}
          <a
            href={article.url}
            target="_blank"
            rel="noreferrer"
            className="text-accent"
          >
            Original ↗
          </a>
        </div>

        {article.analysed && (
          <div className="mt-4 flex gap-2 print:hidden">
            <button
              onClick={() => api.exportAnalysis(id).catch((e) => setError(e.message))}
              className="text-sm px-3 py-1.5 rounded-lg border border-border hover:border-accent"
            >
              Export .md
            </button>
            <button
              onClick={() => window.print()}
              className="text-sm px-3 py-1.5 rounded-lg border border-border hover:border-accent"
            >
              Print / Save as PDF
            </button>
          </div>
        )}

        <section className="mt-6 bg-surface border border-border rounded-xl p-4">
          <h2 className="text-sm font-semibold text-muted mb-2">Summary</h2>
          <p className="text-[15px] leading-relaxed">
            {a?.summary || article.description || "No summary yet."}
          </p>
        </section>

        {!article.analysed && (
          <div className="mt-6 bg-surface2 border border-border rounded-xl p-5 text-center">
            <p className="text-sm text-muted mb-3">
              Deep AI analysis (causal timeline, impact, lecturette) hasn't been
              run for this article yet. This uses one of your daily analyses.
            </p>
            {error && <p className="text-impactHigh text-sm mb-3">{error}</p>}
            <button
              onClick={runAnalysis}
              disabled={analyzing}
              className="px-5 py-2.5 rounded-lg bg-accent text-white text-sm font-semibold disabled:opacity-50"
            >
              {analyzing ? "Analysing with Gemini…" : "Run AI deep analysis"}
            </button>
          </div>
        )}

        {article.analysed && a && (
          <>
            <section className="mt-8">
              <h2 className="text-lg font-bold mb-4">Causal Timeline</h2>
              <Timeline
                timeline={a.causal_timeline || []}
                future={a.future_consequences || []}
              />
            </section>

            <section className="mt-8 bg-surface border border-border rounded-xl p-5">
              <div className="flex items-center justify-between mb-2">
                <h2 className="text-lg font-bold">What this means for you</h2>
                {dai.relevance && (
                  <span
                    className={`text-xs font-semibold capitalize ${
                      RELEVANCE_COLOR[dai.relevance] || "text-muted"
                    }`}
                  >
                    {dai.relevance} relevance
                  </span>
                )}
              </div>
              <p className="text-[15px] leading-relaxed text-text/90">
                {dai.explanation || "No personalised impact available."}
              </p>
              {dai.lecturette_worthy && (
                <p className="mt-3 text-xs text-impactLow">
                  ★ Marked lecturette-worthy
                </p>
              )}
            </section>

            <section className="mt-8 bg-surface2 border border-border rounded-xl p-5">
              <div className="flex items-center justify-between mb-1">
                <h2 className="text-lg font-bold">Lecturette Ready</h2>
                <div className="flex items-center gap-2 text-xs text-muted">
                  {a.lecturette_category && (
                    <span className="px-2 py-0.5 border border-border capitalize">
                      {a.lecturette_category}
                    </span>
                  )}
                  <span>~{lec.estimated_minutes || 3} min</span>
                </div>
              </div>
              <div className="space-y-4 text-sm mt-3">
                {[
                  ["Opening", lec.opening],
                  ["Point 1", lec.point_one],
                  ["Point 2", lec.point_two],
                  ["Point 3", lec.point_three],
                  ["Conclusion", lec.conclusion],
                ].map(([label, val]) => (
                  <div key={label}>
                    <div className="text-xs font-medium text-muted mb-1">
                      {label}
                    </div>
                    <p>{val || "—"}</p>
                  </div>
                ))}
              </div>
            </section>

            {a.key_terms?.length > 0 && (
              <section className="mt-8 bg-surface border border-border rounded-xl p-5">
                <h2 className="text-lg font-bold mb-3">Key Terms</h2>
                <ul className="space-y-2 text-sm">
                  {a.key_terms.map((kt, i) => (
                    <li key={i}>
                      <span className="font-semibold">
                        {typeof kt === "string" ? kt : kt.term}
                      </span>
                      {typeof kt === "object" && kt.definition && (
                        <span className="text-muted"> — {kt.definition}</span>
                      )}
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </>
        )}
      </div>
    </div>
  );
}
