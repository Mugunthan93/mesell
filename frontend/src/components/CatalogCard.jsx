import { Link } from "react-router-dom";
import { scoreColor, shortDate } from "../utils/formatters";

export default function CatalogCard({ catalog }) {
  return (
    <Link
      to={`/catalog/${catalog.id}`}
      className="block rounded-lg bg-white p-4 shadow-sm ring-1 ring-slate-200 transition hover:shadow-md"
    >
      <div className="flex items-center justify-between">
        <p className="font-semibold">{catalog.name}</p>
        <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs uppercase tracking-wide text-slate-600">
          {catalog.status}
        </span>
      </div>
      <p className="mt-1 text-xs text-slate-500">
        {catalog.category || "Uncategorised"} · created {shortDate(catalog.created_at)}
      </p>
      {catalog.quality_score !== null && catalog.quality_score !== undefined ? (
        <p className={`mt-2 text-sm font-semibold ${scoreColor(catalog.quality_score)}`}>
          Score {catalog.quality_score}
        </p>
      ) : null}
    </Link>
  );
}
