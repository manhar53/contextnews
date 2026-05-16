import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import ImpactTag from "./ImpactTag.jsx";

function timeAgo(iso) {
  if (!iso) return "";
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

function oneLine(text) {
  if (!text) return "";
  const t = text.trim();
  return t.length > 140 ? t.slice(0, 140).trimEnd() + "…" : t;
}

export default function NewsCard({ article }) {
  const [vote, setVote] = useState(null);

  const cast = (kind) => (e) => {
    e.preventDefault();
    e.stopPropagation();
    const prev = vote;
    setVote(kind); // optimistic; nothing is hidden
    const call = kind === "up" ? api.signalUp : api.signalDown;
    call(article.id).catch(() => setVote(prev));
  };

  return (
    <Link
      to={`/news/${article.id}`}
      className="block bg-surface border border-border rounded-xl p-4 hover:border-accent transition"
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <h3 className="font-semibold leading-snug min-w-0">
          {article.headline}
        </h3>
        <div className="flex items-center gap-2 shrink-0">
          {article.important && (
            <span
              title="Important SSB lecturette/GD topic"
              className="text-[10px] px-2 py-0.5 rounded border border-accent text-text whitespace-nowrap"
            >
              ★ Topic
            </span>
          )}
          <ImpactTag level={article.impact_level} />
        </div>
      </div>

      {article.description && (
        <p className="text-muted text-sm line-clamp-2 mb-3">
          {oneLine(article.description)}
        </p>
      )}

      <div className="flex items-center flex-wrap gap-x-2 gap-y-1 text-xs text-muted">
        <span className="inline-flex items-center justify-center w-5 h-5 rounded bg-surface2 text-[10px] font-bold text-text/80 shrink-0">
          {(article.source || "?").slice(0, 1).toUpperCase()}
        </span>
        <span className="font-medium text-text/80 truncate max-w-[55%]">
          {article.source || "Unknown source"}
        </span>
        <span aria-hidden>•</span>
        <span className="whitespace-nowrap">{timeAgo(article.published_at)}</span>
        {article.category && (
          <>
            <span aria-hidden>•</span>
            <span className="capitalize whitespace-nowrap">{article.category}</span>
          </>
        )}
        <span className="ml-auto flex items-center gap-2">
          <button
            onClick={cast("up")}
            title="Helpful"
            aria-label="Helpful"
            className={`text-xs leading-none ${
              vote === "up" ? "text-impactLow" : "text-muted hover:text-impactLow"
            }`}
          >
            👍
          </button>
          <button
            onClick={cast("down")}
            title="Not relevant"
            aria-label="Not relevant"
            className={`text-xs leading-none ${
              vote === "down"
                ? "text-impactHigh"
                : "text-muted hover:text-impactHigh"
            }`}
          >
            👎
          </button>
        </span>
      </div>
    </Link>
  );
}
