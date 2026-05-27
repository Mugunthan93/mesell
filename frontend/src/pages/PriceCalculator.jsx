import { useState } from "react";
import { api } from "../api/client";
import PnLBreakdown from "../components/PnLBreakdown";

const CATEGORIES = ["Kurtis", "Sarees", "Tops", "Dresses", "Jeans", "T-Shirts", "Bedsheets", "Earrings"];

export default function PriceCalculator() {
  const [form, setForm] = useState({
    selling_price: 599,
    cost_price: 250,
    weight_grams: 480,
    category: "Kurtis",
    ad_spend: 0,
    packaging: 12,
  });
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);

  async function compute() {
    setBusy(true);
    setError(null);
    try {
      const { data } = await api.post("/pricing/calculate", form);
      setResult(data);
    } catch (err) {
      setError(err.response?.data?.detail || "Calculation failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto grid max-w-4xl gap-6 px-4 py-6 md:grid-cols-2">
      <div className="rounded-xl bg-white p-6 ring-1 ring-slate-200">
        <h1 className="text-xl font-bold">PriceIntel</h1>
        <p className="text-sm text-slate-500">Public Meesho P&amp;L calculator — no login needed.</p>
        <div className="mt-4 space-y-3 text-sm">
          <Field label="Selling price (₹)">
            <Input form={form} setForm={setForm} field="selling_price" type="number" />
          </Field>
          <Field label="Cost price (₹)">
            <Input form={form} setForm={setForm} field="cost_price" type="number" />
          </Field>
          <Field label="Weight (g)">
            <Input form={form} setForm={setForm} field="weight_grams" type="number" />
          </Field>
          <Field label="Category">
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              className="w-full rounded-md border border-slate-300 px-3 py-2"
            >
              {CATEGORIES.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </Field>
          <Field label="Ad spend (₹)">
            <Input form={form} setForm={setForm} field="ad_spend" type="number" />
          </Field>
          <button
            onClick={compute}
            disabled={busy}
            className="w-full rounded-md bg-brand-500 px-4 py-2 font-medium text-white hover:bg-brand-600 disabled:opacity-60"
          >
            {busy ? "Calculating…" : "Calculate"}
          </button>
          {error && <p className="text-sm text-rose-600">{error}</p>}
        </div>
      </div>
      <PnLBreakdown result={result} />
    </div>
  );
}

function Field({ label, children }) {
  return (
    <label className="block">
      <span className="block text-xs font-medium uppercase tracking-wide text-slate-500">{label}</span>
      <div className="mt-1">{children}</div>
    </label>
  );
}

function Input({ form, setForm, field, type }) {
  return (
    <input
      type={type}
      value={form[field]}
      onChange={(e) => setForm({ ...form, [field]: type === "number" ? Number(e.target.value) : e.target.value })}
      className="w-full rounded-md border border-slate-300 px-3 py-2"
    />
  );
}
