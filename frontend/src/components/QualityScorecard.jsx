import { scoreColor } from "../utils/formatters";

const ICON = { pass: "✓", warn: "!", fail: "✕" };
const BADGE = {
  pass: "bg-emerald-100 text-emerald-700",
  warn: "bg-amber-100 text-amber-700",
  fail: "bg-rose-100 text-rose-700",
};

export default function QualityScorecard({ report }) {
  if (!report) return null;
  return (
    <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <div className="flex items-center gap-6">
        <div className={`text-6xl font-bold ${scoreColor(report.score)}`}>{report.score}</div>
        <div>
          <p className="text-sm uppercase tracking-wide text-slate-500">QualityGate score</p>
          <p className="font-medium">
            {report.passed ? "Catalog passed and is ready to export" : "Catalog has blocking issues"}
          </p>
          <p className="text-xs text-slate-500">
            {report.summary.passed_checks} passed · {report.summary.warned_checks} warnings ·{" "}
            {report.summary.failed_checks} failures
          </p>
        </div>
      </div>
      <ul className="mt-4 divide-y divide-slate-100">
        {report.checks.map((c) => (
          <li key={c.name} className="flex items-start gap-3 py-3">
            <span
              className={`mt-0.5 inline-flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold ${BADGE[c.status]}`}
            >
              {ICON[c.status]}
            </span>
            <div className="flex-1">
              <p className="text-sm font-medium capitalize">{c.name.replace(/_/g, " ")}</p>
              <p className="text-sm text-slate-600">{c.detail}</p>
              {c.fix && c.status !== "pass" ? (
                <p className="mt-1 text-xs italic text-slate-500">Fix: {c.fix}</p>
              ) : null}
            </div>
            <span className="text-xs text-slate-500">
              {c.score}/{c.weight}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}
