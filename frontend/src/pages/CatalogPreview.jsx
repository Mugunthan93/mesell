import { useEffect, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api/client";

export default function CatalogPreview() {
  const { id } = useParams();
  const [params] = useSearchParams();
  const jobId = params.get("job");
  const [catalog, setCatalog] = useState(null);
  const [jobStatus, setJobStatus] = useState(jobId ? "queued" : null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const { data } = await api.get(`/catalogs/${id}`);
        setCatalog(data);
      } finally {
        setLoading(false);
      }
    })();
  }, [id]);

  useEffect(() => {
    if (!jobId) return;
    const t = setInterval(async () => {
      try {
        const { data } = await api.get(`/jobs/${jobId}`);
        setJobStatus(data.status);
        if (["success", "failure"].includes(data.status)) {
          clearInterval(t);
          const refreshed = await api.get(`/catalogs/${id}`);
          setCatalog(refreshed.data);
        }
      } catch (e) {
        clearInterval(t);
      }
    }, 2000);
    return () => clearInterval(t);
  }, [jobId, id]);

  if (loading) return <div className="p-6">Loading…</div>;
  if (!catalog) return <div className="p-6">Catalog not found</div>;

  return (
    <div className="mx-auto max-w-5xl px-4 py-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{catalog.name}</h1>
          <p className="text-sm text-slate-500">
            {catalog.category || "Uncategorised"} · {catalog.status}
          </p>
        </div>
        <div className="flex gap-2">
          <Link
            to={`/quality/${catalog.id}`}
            className="rounded-md border border-slate-300 bg-white px-3 py-1.5 text-sm hover:bg-slate-50"
          >
            Validate
          </Link>
          <Link
            to={`/export/${catalog.id}`}
            className="rounded-md bg-brand-500 px-3 py-1.5 text-sm font-medium text-white hover:bg-brand-600"
          >
            Export
          </Link>
        </div>
      </div>

      {jobStatus && jobStatus !== "success" && (
        <div className="mt-4 rounded-md bg-amber-50 px-4 py-3 text-sm text-amber-700">
          AI generation: <strong>{jobStatus}</strong>… this page refreshes automatically.
        </div>
      )}

      <div className="mt-6 space-y-4">
        {catalog.skus.map((sku) => (
          <SKURow key={sku.id} sku={sku} />
        ))}
      </div>
    </div>
  );
}

function SKURow({ sku }) {
  return (
    <div className="grid grid-cols-1 gap-4 rounded-xl bg-white p-4 ring-1 ring-slate-200 sm:grid-cols-[180px_1fr]">
      <div className="flex flex-wrap gap-2">
        {(sku.images || []).slice(0, 4).map((img) => (
          <img
            key={img.id}
            src={img.processed_url || img.original_url}
            alt=""
            className="h-20 w-20 rounded-md object-cover ring-1 ring-slate-200"
          />
        ))}
        {(sku.images || []).length === 0 && (
          <div className="flex h-20 w-20 items-center justify-center rounded-md bg-slate-100 text-xs text-slate-400">
            No image
          </div>
        )}
      </div>
      <div>
        <p className="text-sm uppercase tracking-wide text-slate-500">{sku.product_name}</p>
        {sku.ai_title ? (
          <>
            <p className="mt-1 font-medium">{sku.ai_title}</p>
            <p className="mt-1 text-sm text-slate-600">{sku.ai_description}</p>
            <p className="mt-2 text-xs text-slate-500">Keywords: {sku.ai_keywords}</p>
          </>
        ) : (
          <p className="mt-1 text-sm italic text-slate-500">Waiting for AI…</p>
        )}
      </div>
    </div>
  );
}
