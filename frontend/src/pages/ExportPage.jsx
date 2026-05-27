import { useState } from "react";
import { useParams } from "react-router-dom";
import { api } from "../api/client";

export default function ExportPage() {
  const { id } = useParams();
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const [urls, setUrls] = useState({ csv: null, zip: null });

  async function run(kind) {
    setBusy(kind);
    setError(null);
    try {
      const endpoint = kind === "csv" ? "meesho-csv" : "images-zip";
      const { data } = await api.post(`/catalogs/${id}/export/${endpoint}`);
      setUrls((u) => ({ ...u, [kind]: data.download_url }));
    } catch (err) {
      setError(err.response?.data?.detail || `Export ${kind} failed`);
    } finally {
      setBusy(null);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <h1 className="text-2xl font-bold">Export</h1>
      <p className="text-sm text-slate-500">Download Meesho-ready files for catalog {id}.</p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        <Card
          title="Meesho bulk-upload CSV"
          description="One row per SKU, AI titles + attributes, ready to import."
          busy={busy === "csv"}
          url={urls.csv}
          onClick={() => run("csv")}
        />
        <Card
          title="Processed images ZIP"
          description="All processed images, white BG, 1024×1024, named per SKU."
          busy={busy === "zip"}
          url={urls.zip}
          onClick={() => run("zip")}
        />
      </div>

      <div className="mt-8 rounded-xl bg-white p-6 ring-1 ring-slate-200">
        <h2 className="text-base font-semibold">Upload to Meesho</h2>
        <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-slate-600">
          <li>Log in to your Meesho Supplier Panel.</li>
          <li>Go to Catalogue → Bulk Upload.</li>
          <li>Upload the CSV first, then upload the image ZIP.</li>
          <li>Review and submit. Approval typically takes 24-48 hours.</li>
        </ol>
      </div>

      {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}
    </div>
  );
}

function Card({ title, description, busy, url, onClick }) {
  return (
    <div className="rounded-xl bg-white p-6 ring-1 ring-slate-200">
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="mt-1 text-sm text-slate-600">{description}</p>
      {url ? (
        <a
          href={url}
          target="_blank"
          rel="noreferrer"
          className="mt-4 inline-block rounded-md bg-emerald-500 px-4 py-2 text-sm font-medium text-white hover:bg-emerald-600"
        >
          Download
        </a>
      ) : (
        <button
          onClick={onClick}
          disabled={busy}
          className="mt-4 rounded-md bg-brand-500 px-4 py-2 text-sm font-medium text-white hover:bg-brand-600 disabled:opacity-60"
        >
          {busy ? "Generating…" : "Generate"}
        </button>
      )}
    </div>
  );
}
