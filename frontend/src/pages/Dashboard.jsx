import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAuthStore } from "../stores/authStore";
import CatalogCard from "../components/CatalogCard";

export default function Dashboard() {
  const user = useAuthStore((s) => s.user);
  const [catalogs, setCatalogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get("/catalogs");
        setCatalogs(data.data || []);
      } catch (err) {
        setError(err.response?.data?.detail || "Could not load catalogs");
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const avgScore =
    catalogs.length > 0
      ? Math.round(
          catalogs.filter((c) => c.quality_score).reduce((a, c) => a + c.quality_score, 0) /
            (catalogs.filter((c) => c.quality_score).length || 1),
        )
      : null;

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <h1 className="text-2xl font-bold">Welcome back{user?.name ? `, ${user.name}` : ""}</h1>
      <p className="text-sm text-slate-500">Plan: {user?.plan?.toUpperCase() || "FREE"}</p>

      <div className="mt-6 grid grid-cols-1 gap-4 sm:grid-cols-4">
        <Stat label="Catalogs" value={catalogs.length} />
        <Stat label="Avg score" value={avgScore ?? "—"} />
        <Stat label="Plan quota" value={`${user?.catalogs_used ?? 0}/${user?.catalogs_limit ?? 5}`} />
        <Stat label="Status" value={catalogs[0]?.status || "—"} />
      </div>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          to="/catalog/new"
          className="rounded-md bg-brand-500 px-4 py-2 font-medium text-white hover:bg-brand-600"
        >
          Create catalog
        </Link>
        <Link
          to="/pricing"
          className="rounded-md border border-slate-300 bg-white px-4 py-2 font-medium hover:bg-slate-50"
        >
          Price calculator
        </Link>
      </div>

      <h2 className="mt-10 text-lg font-semibold">Your catalogs</h2>
      {loading ? (
        <div className="mt-4 grid animate-pulse grid-cols-1 gap-3 sm:grid-cols-2">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-24 rounded-lg bg-slate-200" />
          ))}
        </div>
      ) : error ? (
        <p className="mt-4 text-sm text-rose-600">{error}</p>
      ) : catalogs.length === 0 ? (
        <p className="mt-4 text-sm text-slate-500">No catalogs yet — create your first one above.</p>
      ) : (
        <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
          {catalogs.map((c) => (
            <CatalogCard key={c.id} catalog={c} />
          ))}
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="rounded-lg bg-white p-4 shadow-sm ring-1 ring-slate-200">
      <p className="text-xs uppercase tracking-wide text-slate-500">{label}</p>
      <p className="mt-1 text-2xl font-semibold">{value}</p>
    </div>
  );
}
