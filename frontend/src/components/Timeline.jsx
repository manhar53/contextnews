import { useMemo, useState } from "react";

const TYPE_META = {
  root_cause: { label: "Root Cause", tone: "past" },
  development: { label: "Key Development", tone: "past" },
  current: { label: "Current Event", tone: "current" },
  consequence: { label: "Projected", tone: "future" },
};

function nodeClasses(tone, active) {
  if (tone === "future")
    return `border-dashed border-nodeFuture/70 bg-surface/60 text-muted ${
      active ? "ring-2 ring-nodeFuture" : ""
    }`;
  if (tone === "current")
    return `border-nodeCurrent bg-nodeCurrent/15 ${
      active ? "ring-2 ring-nodeCurrent" : ""
    }`;
  return `border-nodePast bg-nodePast/10 ${active ? "ring-2 ring-nodePast" : ""}`;
}

function dotClass(tone) {
  if (tone === "future") return "bg-nodeFuture";
  if (tone === "current") return "bg-nodeCurrent";
  return "bg-nodePast";
}

export default function Timeline({ timeline = [], future = [] }) {
  const nodes = useMemo(() => {
    const past = (timeline || []).map((t) => {
      const meta = TYPE_META[t.type] || TYPE_META.development;
      return {
        tone: meta.tone,
        label: meta.label,
        date: t.date,
        title: t.event,
        detail: t.detail || t.significance || "",
      };
    });
    const projected = (future || []).map((f) => ({
      tone: "future",
      label: "Projected Consequence",
      date: f.timeframe || "Projected",
      title: f.consequence || (typeof f === "string" ? f : ""),
      detail: f.likelihood ? `Likelihood: ${f.likelihood}` : "",
    }));
    return [...past, ...projected];
  }, [timeline, future]);

  const [popup, setPopup] = useState(null);

  if (nodes.length === 0)
    return <p className="text-muted text-sm">No timeline available.</p>;

  return (
    <div>
      <div className="overflow-x-auto no-scrollbar pb-2">
        <div className="flex items-stretch min-w-max md:min-w-0 md:w-full">
          {nodes.map((n, i) => (
            <div key={i} className="flex items-center">
              <button
                onClick={() => setPopup(n)}
                className={`w-44 md:flex-1 text-left p-3 rounded-xl border-2 transition mr-1 ${nodeClasses(
                  n.tone
                )}`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <span className={`w-2.5 h-2.5 rounded-full ${dotClass(n.tone)}`} />
                  <span className="text-[10px] text-muted">
                    {n.label}
                  </span>
                </div>
                <div className="text-xs text-muted">{n.date}</div>
                <div
                  className={`text-sm line-clamp-3 ${
                    n.tone === "current" ? "font-bold" : "font-medium"
                  }`}
                >
                  {n.title}
                </div>
              </button>
              {i < nodes.length - 1 && (
                <div className="w-6 h-px bg-border shrink-0" />
              )}
            </div>
          ))}
        </div>
      </div>

      {popup && (
        <div
          className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-5"
          onClick={() => setPopup(null)}
        >
          <div
            className="bg-surface border border-border rounded-2xl max-w-md w-full p-5"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center gap-2 mb-2">
              <span className={`w-3 h-3 rounded-full ${dotClass(popup.tone)}`} />
              <span className="text-xs text-muted">
                {popup.label} · {popup.date}
              </span>
            </div>
            <h3 className="text-lg font-bold mb-2">{popup.title}</h3>
            <p className="text-sm text-muted leading-relaxed">
              {popup.detail || "No further detail."}
            </p>
            <button
              onClick={() => setPopup(null)}
              className="mt-5 w-full py-2 rounded-lg border border-border text-sm"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
