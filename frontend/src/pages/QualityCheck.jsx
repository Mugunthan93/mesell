import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import QualityScorecard from "../components/QualityScorecard";

export default function QualityCheck() {
  const { id } = useParams();
  const [report, setReport] = useState(null);
  const [busy, setBusy] = useState(true);
  const [error, setError] = useState(null);

  async function run() {
    setBusy(true);
    setError(null);
    try {
      const { data } = await api.post(`/catalogs/${id}/validate`);
      setReport(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Validation failed");
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    run();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">QualityGate</h1>
        <div className="flex gap-2">
          <button
            onClick={run}
            disabled={busy}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50"
          >
            Re-run
          </button>
          {report?.passed && (
            <Link
              to={`/export/${id}`}
              className="rounded-md bg-brand-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-600"
            >
              Export
            </Link>
          )}
        </div>
      </div>

      {busy && <p className="mt-4 text-sm text-slate-500">Running checks…</p>}
      {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}
      {report && <div className="mt-6"><QualityScorecard report={report} /></div>}
    </div>
  );
}
