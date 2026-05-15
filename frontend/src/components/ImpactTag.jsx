const STYLES = {
  high: "bg-impactHigh/15 text-impactHigh border-impactHigh/40",
  medium: "bg-impactMedium/15 text-impactMedium border-impactMedium/40",
  low: "bg-impactLow/15 text-impactLow border-impactLow/40",
};

export default function ImpactTag({ level }) {
  const key = (level || "").toLowerCase();
  if (!STYLES[key]) {
    return (
      <span className="text-[11px] px-2 py-0.5 rounded-full border border-border text-muted">
        Unanalysed
      </span>
    );
  }
  return (
    <span
      className={`text-[11px] px-2 py-0.5 rounded-full border font-medium capitalize ${STYLES[key]}`}
    >
      {key} impact
    </span>
  );
}
