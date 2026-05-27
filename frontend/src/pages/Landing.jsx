import { Link } from "react-router-dom";

const FEATURES = [
  {
    title: "CatalogAI",
    body: "Upload photos and product details — Gemini-powered text and clean white-BG images come out the other side.",
  },
  {
    title: "QualityGate",
    body: "9 checks per catalog (size, watermark, banned words, attributes...) flag every issue before Meesho does.",
  },
  {
    title: "PriceIntel",
    body: "Meesho-aware P&L per SKU, with weight-slab and low-margin alerts so you don't ship at a loss.",
  },
];

const TIERS = [
  { name: "Free", price: "₹0", limit: "5 catalogs / month" },
  { name: "Starter", price: "₹499", limit: "50 catalogs / month" },
  { name: "Pro", price: "₹999", limit: "200 catalogs / month" },
  { name: "Growth", price: "₹1,999", limit: "1000 catalogs / month" },
];

export default function Landing() {
  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <section className="text-center">
        <p className="text-sm font-medium uppercase tracking-widest text-brand-500">For Meesho sellers</p>
        <h1 className="mt-2 text-4xl font-bold sm:text-5xl">
          Create Meesho catalogs in 30 seconds with AI
        </h1>
        <p className="mx-auto mt-3 max-w-2xl text-slate-600">
          MeeSell handles your product photos, copy, quality checks, and Meesho P&amp;L — so you ship
          listings faster, with fewer rejections.
        </p>
        <div className="mt-6 flex justify-center gap-3">
          <Link
            to="/onboarding"
            className="rounded-md bg-brand-500 px-5 py-2.5 text-sm font-medium text-white hover:bg-brand-600"
          >
            Start free
          </Link>
          <Link
            to="/pricing"
            className="rounded-md border border-slate-300 bg-white px-5 py-2.5 text-sm font-medium hover:bg-slate-50"
          >
            Try the price calculator
          </Link>
        </div>
      </section>

      <section className="mt-16 grid gap-4 md:grid-cols-3">
        {FEATURES.map((f) => (
          <div key={f.title} className="rounded-xl bg-white p-6 ring-1 ring-slate-200">
            <h3 className="text-base font-semibold">{f.title}</h3>
            <p className="mt-2 text-sm text-slate-600">{f.body}</p>
          </div>
        ))}
      </section>

      <section className="mt-16">
        <h2 className="text-2xl font-bold">Pricing</h2>
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {TIERS.map((t) => (
            <div key={t.name} className="rounded-xl bg-white p-6 ring-1 ring-slate-200">
              <p className="text-xs uppercase tracking-wide text-slate-500">{t.name}</p>
              <p className="mt-1 text-3xl font-bold">{t.price}</p>
              <p className="text-xs text-slate-500">per month</p>
              <p className="mt-3 text-sm text-slate-600">{t.limit}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
