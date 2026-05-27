import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import ImageUploader from "../components/ImageUploader";

export default function CatalogCreate() {
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [category, setCategory] = useState("Kurtis");
  const [productName, setProductName] = useState("");
  const [material, setMaterial] = useState("");
  const [sizes, setSizes] = useState("");
  const [colors, setColors] = useState("");
  const [costPrice, setCostPrice] = useState("");
  const [sellingPrice, setSellingPrice] = useState("");
  const [weight, setWeight] = useState("");
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function submit() {
    setError(null);
    setBusy(true);
    try {
      const { data: catalog } = await api.post("/catalogs", { name, category });
      const { data: sku } = await api.post(`/catalogs/${catalog.id}/skus`, {
        product_name: productName,
        material,
        sizes,
        colors,
        cost_price: costPrice ? Number(costPrice) : null,
        selling_price: sellingPrice ? Number(sellingPrice) : null,
        weight_grams: weight ? Number(weight) : null,
      });
      for (const file of files) {
        const fd = new FormData();
        fd.append("file", file);
        await api.post(`/skus/${sku.id}/images`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }
      const { data: job } = await api.post(`/catalogs/${catalog.id}/generate`);
      navigate(`/catalog/${catalog.id}?job=${job.job_id}`);
    } catch (err) {
      setError(err.response?.data?.detail || "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl px-4 py-6">
      <h1 className="text-2xl font-bold">New catalog</h1>

      <section className="mt-6 space-y-4 rounded-xl bg-white p-6 ring-1 ring-slate-200">
        <h2 className="text-base font-semibold">1. Catalog basics</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Catalog name">
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </Field>
          <Field label="Category">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2"
            >
              {["Kurtis", "Sarees", "Tops", "Dresses", "T-Shirts", "Jeans", "Bedsheets", "Earrings"].map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </Field>
        </div>
      </section>

      <section className="mt-6 space-y-4 rounded-xl bg-white p-6 ring-1 ring-slate-200">
        <h2 className="text-base font-semibold">2. Product details</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <Field label="Product name">
            <input
              value={productName}
              onChange={(e) => setProductName(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </Field>
          <Field label="Material">
            <input
              value={material}
              onChange={(e) => setMaterial(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </Field>
          <Field label="Sizes">
            <input
              value={sizes}
              onChange={(e) => setSizes(e.target.value)}
              placeholder="S, M, L, XL"
              className="w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </Field>
          <Field label="Colors">
            <input
              value={colors}
              onChange={(e) => setColors(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </Field>
          <Field label="Cost price (₹)">
            <input
              type="number"
              value={costPrice}
              onChange={(e) => setCostPrice(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </Field>
          <Field label="Selling price (₹)">
            <input
              type="number"
              value={sellingPrice}
              onChange={(e) => setSellingPrice(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </Field>
          <Field label="Weight (g)">
            <input
              type="number"
              value={weight}
              onChange={(e) => setWeight(e.target.value)}
              className="w-full rounded-md border border-slate-300 px-3 py-2"
            />
          </Field>
        </div>
      </section>

      <section className="mt-6 space-y-4 rounded-xl bg-white p-6 ring-1 ring-slate-200">
        <h2 className="text-base font-semibold">3. Upload photos</h2>
        <ImageUploader onSelect={setFiles} max={9} />
      </section>

      {error && <p className="mt-4 text-sm text-rose-600">{error}</p>}

      <button
        disabled={busy || !name || !productName || files.length === 0}
        onClick={submit}
        className="mt-6 w-full rounded-md bg-brand-500 px-4 py-3 font-medium text-white hover:bg-brand-600 disabled:opacity-50"
      >
        {busy ? "Creating & generating…" : "Generate with AI"}
      </button>
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="block text-sm font-medium text-slate-700">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  );
}
