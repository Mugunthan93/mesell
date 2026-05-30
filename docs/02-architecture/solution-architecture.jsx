import { useState } from "react";

const TABS = ["Architecture", "Modules", "Tech Stack", "Pricing", "MVP Roadmap", "Moat"];

const MODULES = [
  {
    id: "catalog-ai",
    name: "CatalogAI",
    icon: "📦",
    solves: "#1 Catalog Creation",
    color: "#57cc99",
    features: [
      "AI title + description generator (Meesho SEO-optimized)",
      "AI image enhancement (background removal, white BG, 1024×1024 resize)",
      "Bulk catalog generation from product photos + basic details",
      "Category auto-mapping with attribute suggestions",
      "Meesho-format CSV/Excel export (ready to upload)",
      "Multi-language support (Hindi product titles)",
    ],
    aiModel: "Gemini Flash (text) + Vision API (images)",
    dataNeeded: "Product photos + basic details (name, material, size)",
    output: "Meesho-ready catalog file with images + metadata",
  },
  {
    id: "quality-gate",
    name: "QualityGate",
    icon: "✅",
    solves: "#4 Pre-upload Checks",
    color: "#48bfe3",
    features: [
      "Image compliance checker (size, format, white BG, watermark detection)",
      "Title rule validator (character limits, banned words, SEO score)",
      "Attribute completeness checker (required fields per category)",
      "Duplicate catalog detection (avoid rejection for similar listings)",
      "Pass/Fail scorecard with fix suggestions before upload",
      "Category-specific rule engine (fashion vs electronics vs home)",
    ],
    aiModel: "Vision AI + Rule Engine",
    dataNeeded: "Draft catalog (images + text)",
    output: "Compliance report with auto-fix suggestions",
  },
  {
    id: "price-intel",
    name: "PriceIntel",
    icon: "💰",
    solves: "#3 Pricing & Margins",
    color: "#ffd166",
    features: [
      "Smart pricing calculator (auto-factors GST, weight slab, return cost, ad spend)",
      "Per-SKU P&L tracker (true profit after all deductions)",
      "Shipping weight slab optimizer (flag when close to slab jump)",
      "Competitor price monitoring (same category products on Meesho)",
      "Margin alert system (flag when margin drops below threshold)",
      "What-if simulator (change price → see impact on margin + competitiveness)",
    ],
    aiModel: "Rule Engine + Scheduled Scraping",
    dataNeeded: "Seller's catalog data + Meesho public pricing data",
    output: "Recommended price per SKU + P&L dashboard",
  },
  {
    id: "return-shield",
    name: "ReturnShield",
    icon: "🛡️",
    solves: "#2 RTO & Returns",
    color: "#e07a5f",
    features: [
      "Per-SKU return rate tracker (which products get returned most)",
      "Return reason analytics (size mismatch, quality, expectation gap)",
      "Listing quality ↔ return correlation (flag bad descriptions causing returns)",
      "Category-level benchmarking (your return rate vs category average)",
      "Auto-suggestions to fix high-return SKUs (improve images, add size chart)",
      "Pin code analytics (which zones have highest returns for YOUR products)",
    ],
    aiModel: "Analytics Engine + Pattern Detection",
    dataNeeded: "Seller's order + return data from Meesho panel",
    output: "Return reduction action plan per SKU",
  },
  {
    id: "recon-flow",
    name: "ReconFlow",
    icon: "📊",
    solves: "#5 Payment Reconciliation",
    color: "#7b68ee",
    features: [
      "Auto-parse Meesho settlement reports (CSV/PDF)",
      "Per-order deduction breakdown (commission, shipping GST, ad charges, penalties)",
      "GST ITC tracker (match GSTR-2B with Meesho commission invoices)",
      "Bank settlement matcher (expected vs received)",
      "Tally XML / Zoho export for CA filing",
      "Monthly P&L summary with trend charts",
    ],
    aiModel: "Document Parser + Matching Engine",
    dataNeeded: "Meesho settlement reports + bank statements",
    output: "Reconciled P&L + GST-ready exports",
  },
  {
    id: "stock-pulse",
    name: "StockPulse",
    icon: "📈",
    solves: "#6 Inventory",
    color: "#888",
    features: [
      "Stock level alerts (low stock, out of stock)",
      "Sales velocity tracker (fast-moving vs dead stock)",
      "Restock reminders based on sell-through rate",
      "Basic multi-platform view (if selling on Flipkart/Amazon too)",
    ],
    aiModel: "Rule Engine",
    dataNeeded: "Catalog + order data",
    output: "Stock alerts + restock recommendations",
  },
];

const TIERS = [
  {
    name: "Free",
    price: "₹0",
    period: "forever",
    color: "#888",
    target: "Try before you buy",
    features: [
      "5 AI catalog generations/month",
      "Profit calculator (unlimited)",
      "Basic QualityGate checks (3/day)",
      "Shipping slab optimizer",
    ],
    limits: "Watermarked exports, no bulk, no analytics",
  },
  {
    name: "Starter",
    price: "₹499",
    period: "/month",
    color: "#48bfe3",
    target: "New sellers (<100 orders/mo)",
    features: [
      "50 AI catalog generations/month",
      "Full QualityGate (unlimited checks)",
      "Per-SKU P&L tracker (up to 200 SKUs)",
      "Return rate dashboard",
      "Basic settlement parser",
      "Meesho CSV export",
    ],
    limits: "No competitor pricing, no bulk generation",
  },
  {
    name: "Pro",
    price: "₹999",
    period: "/month",
    color: "#57cc99",
    target: "Growing sellers (100-500 orders/mo)",
    features: [
      "200 AI catalog generations/month",
      "Bulk catalog generation (upload Excel → get catalogs)",
      "Competitor price monitoring (50 tracked SKUs)",
      "Full return analytics with fix suggestions",
      "Auto settlement reconciliation",
      "Tally XML + Zoho export",
      "Priority support (WhatsApp)",
    ],
    limits: "Standard AI quality",
  },
  {
    name: "Growth",
    price: "₹1,999",
    period: "/month",
    color: "#ffd166",
    target: "Scale sellers (500+ orders/mo)",
    features: [
      "Unlimited AI catalog generations",
      "Premium AI (better titles, lifestyle images)",
      "Competitor tracking (200 SKUs)",
      "Multi-platform view (Meesho + Flipkart + Amazon)",
      "Full reconciliation with bank matching",
      "API access for automation",
      "Dedicated account support",
    ],
    limits: "None",
  },
];

const MVP_PHASES = [
  {
    phase: "MVP (Month 1-3)",
    color: "#57cc99",
    modules: ["CatalogAI (basic)", "QualityGate", "Profit Calculator"],
    milestones: [
      "AI title + description generator (Gemini Flash API)",
      "Image background removal + 1024×1024 resize",
      "Pre-upload compliance checker (image + title rules)",
      "Meesho profit calculator with weight slab optimization",
      "Meesho-format CSV export",
      "Landing page + waitlist + early adopter pricing",
    ],
    metric: "100 beta users, 1,000 catalogs generated",
    techFocus: "FastAPI backend, React frontend, Gemini API, basic Vision AI",
  },
  {
    phase: "Phase 2 (Month 4-6)",
    color: "#48bfe3",
    modules: ["PriceIntel", "ReturnShield (basic)", "Bulk generation"],
    milestones: [
      "Per-SKU P&L tracker (parse Meesho settlement CSVs)",
      "Return rate dashboard (manual data upload initially)",
      "Bulk catalog generation (Excel → multi-catalog output)",
      "Competitor price monitoring (scheduled scraping)",
      "Shipping slab optimizer with visual weight alerts",
      "Payment gateway integration (Razorpay for subscriptions)",
    ],
    metric: "500 paid users, ₹2.5L MRR",
    techFocus: "PostgreSQL analytics, scheduled scrapers, Razorpay billing",
  },
  {
    phase: "Phase 3 (Month 7-12)",
    color: "#7b68ee",
    modules: ["ReconFlow", "StockPulse", "Multi-platform"],
    milestones: [
      "Auto settlement reconciliation (CSV upload → matched P&L)",
      "Tally XML + Zoho Books export",
      "GST ITC tracking with GSTR-2B matching",
      "Stock alerts + restock reminders",
      "Flipkart/Amazon basic support (catalog generation)",
      "WhatsApp bot for daily alerts (sales, returns, stock)",
      "Mobile-responsive PWA",
    ],
    metric: "2,000 paid users, ₹15L MRR",
    techFocus: "Document parsing, WhatsApp Business API, PWA, multi-marketplace adapters",
  },
];

const TECH_STACK = [
  { layer: "Frontend", tech: "React + Tailwind CSS, PWA for mobile", why: "Fast, mobile-first, installable on phone" },
  { layer: "Backend API", tech: "FastAPI (Python)", why: "Async, fast, great for AI/ML integration" },
  { layer: "AI — Text", tech: "Gemini Flash API (Google)", why: "Cheapest quality LLM, ₹0.075/1M input tokens, India-optimized" },
  { layer: "AI — Vision", tech: "Google Vision AI + rembg (open source)", why: "Background removal, image analysis, compliance checking" },
  { layer: "Database", tech: "PostgreSQL + Redis", why: "Relational for orders/SKUs, Redis for caching/sessions" },
  { layer: "File Storage", tech: "AWS S3 / Cloudflare R2", why: "Product images, generated catalogs, settlement files" },
  { layer: "Scraping", tech: "Playwright + Celery (scheduled)", why: "Competitor price monitoring from Meesho public pages" },
  { layer: "Auth", tech: "Phone OTP (MSG91) + Google OAuth", why: "Indian sellers prefer phone login, no password" },
  { layer: "Payments", tech: "Razorpay Subscriptions", why: "Indian payment methods, auto-renewal, GST invoicing" },
  { layer: "Hosting", tech: "AWS ap-south-1 (Mumbai) / Railway", why: "Low latency for Indian users, cost-effective" },
  { layer: "Notifications", tech: "WhatsApp Business API (via Gupshup/Wati)", why: "Sellers live on WhatsApp — daily alerts, support" },
  { layer: "Analytics", tech: "PostHog (self-hosted) + Metabase", why: "Product analytics + internal dashboards, privacy-first" },
];

export default function SolutionArchitecture() {
  const [activeTab, setActiveTab] = useState("Architecture");

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0f", color: "#e0e0e0", fontFamily: "'DM Sans', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&family=Instrument+Serif&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{ padding: "28px 24px 0", maxWidth: 1060, margin: "0 auto" }}>
        <div style={{ fontSize: 10, letterSpacing: "0.2em", color: "#57cc99", textTransform: "uppercase", fontWeight: 600, marginBottom: 8 }}>
          Solution Architecture · Unified Platform
        </div>
        <h1 style={{ fontFamily: "'Instrument Serif', serif", fontSize: 36, fontWeight: 400, margin: "0 0 4px", color: "#fff", lineHeight: 1.1 }}>
          MeeSell<span style={{ color: "#57cc99" }}>.</span>
        </h1>
        <p style={{ color: "#666", fontSize: 13, margin: "0 0 20px", lineHeight: 1.5 }}>
          The AI-powered operating system for Meesho suppliers. 6 modules. 1 platform. ₹499–1,999/month.
        </p>

        {/* Tabs */}
        <div style={{ display: "flex", gap: 4, borderBottom: "1px solid rgba(255,255,255,0.06)", marginBottom: 0 }}>
          {TABS.map(t => (
            <button key={t} onClick={() => setActiveTab(t)} style={{
              padding: "10px 18px", fontSize: 12, fontWeight: 600,
              background: activeTab === t ? "rgba(255,255,255,0.05)" : "transparent",
              border: "none", borderBottom: activeTab === t ? "2px solid #57cc99" : "2px solid transparent",
              color: activeTab === t ? "#eee" : "#666", cursor: "pointer",
              fontFamily: "'DM Sans', sans-serif", transition: "all 0.2s",
            }}>
              {t}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding: "24px", maxWidth: 1060, margin: "0 auto" }}>

        {/* ===== ARCHITECTURE TAB ===== */}
        {activeTab === "Architecture" && (
          <div>
            {/* Visual Architecture */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 14, padding: "24px", marginBottom: 20 }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#57cc99", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 16 }}>
                System Architecture
              </div>

              {/* Layer 1: User */}
              <div style={{ textAlign: "center", marginBottom: 8 }}>
                <div style={{ display: "inline-block", padding: "8px 24px", background: "#ffd16615", border: "1px solid #ffd16633", borderRadius: 8, fontSize: 12, fontWeight: 600, color: "#ffd166" }}>
                  👤 Meesho Supplier (Mobile / Desktop)
                </div>
              </div>
              <div style={{ textAlign: "center", fontSize: 18, color: "#333", marginBottom: 8 }}>↓</div>

              {/* Layer 2: Frontend */}
              <div style={{ textAlign: "center", marginBottom: 8 }}>
                <div style={{ display: "inline-block", padding: "8px 24px", background: "#48bfe310", border: "1px solid #48bfe333", borderRadius: 8, fontSize: 12, fontWeight: 600, color: "#48bfe3" }}>
                  🌐 React PWA + WhatsApp Bot
                </div>
              </div>
              <div style={{ textAlign: "center", fontSize: 18, color: "#333", marginBottom: 8 }}>↓</div>

              {/* Layer 3: API Gateway */}
              <div style={{ textAlign: "center", marginBottom: 8 }}>
                <div style={{ display: "inline-block", padding: "8px 24px", background: "#7b68ee10", border: "1px solid #7b68ee33", borderRadius: 8, fontSize: 12, fontWeight: 600, color: "#7b68ee" }}>
                  ⚡ FastAPI Gateway (Auth · Rate Limit · Routing)
                </div>
              </div>
              <div style={{ textAlign: "center", fontSize: 18, color: "#333", marginBottom: 8 }}>↓</div>

              {/* Layer 4: Modules */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 6, marginBottom: 12 }}>
                {MODULES.map(m => (
                  <div key={m.id} style={{
                    background: m.color + "10", border: `1px solid ${m.color}33`,
                    borderRadius: 8, padding: "10px 8px", textAlign: "center"
                  }}>
                    <div style={{ fontSize: 20, marginBottom: 4 }}>{m.icon}</div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: m.color, letterSpacing: "0.04em" }}>{m.name}</div>
                  </div>
                ))}
              </div>
              <div style={{ textAlign: "center", fontSize: 18, color: "#333", marginBottom: 8 }}>↓</div>

              {/* Layer 5: Shared Services */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 6, marginBottom: 12 }}>
                {[
                  { name: "AI Engine", sub: "Gemini + Vision AI", color: "#57cc99" },
                  { name: "Data Pipeline", sub: "Meesho CSV Parser", color: "#48bfe3" },
                  { name: "Analytics DB", sub: "PostgreSQL + Redis", color: "#7b68ee" },
                  { name: "File Store", sub: "S3 / Cloudflare R2", color: "#ffd166" },
                ].map((s, i) => (
                  <div key={i} style={{
                    background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: 8, padding: "10px", textAlign: "center"
                  }}>
                    <div style={{ fontSize: 11, fontWeight: 700, color: s.color }}>{s.name}</div>
                    <div style={{ fontSize: 10, color: "#666", marginTop: 2 }}>{s.sub}</div>
                  </div>
                ))}
              </div>
              <div style={{ textAlign: "center", fontSize: 18, color: "#333", marginBottom: 8 }}>↓</div>

              {/* Layer 6: External */}
              <div style={{ display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 6 }}>
                {["Meesho Supplier Panel", "Razorpay", "WhatsApp API", "Google Cloud", "Tally/Zoho"].map((e, i) => (
                  <div key={i} style={{
                    background: "rgba(255,255,255,0.015)", border: "1px dashed rgba(255,255,255,0.1)",
                    borderRadius: 6, padding: "8px", textAlign: "center", fontSize: 10, color: "#777"
                  }}>{e}</div>
                ))}
              </div>
            </div>

            {/* Data Flow */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 14, padding: "20px 24px" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#48bfe3", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 12 }}>
                Core Data Flow
              </div>
              <div style={{ fontSize: 13, color: "#aaa", lineHeight: 2 }}>
                <span style={{ color: "#ffd166", fontWeight: 600 }}>Input:</span> Seller uploads product photos + basic details (or Meesho settlement CSV)
                <br />
                <span style={{ color: "#57cc99", fontWeight: 600 }}>Process:</span> AI generates catalog → QualityGate validates → PriceIntel optimizes price → Export ready
                <br />
                <span style={{ color: "#48bfe3", fontWeight: 600 }}>Output:</span> Meesho-ready catalog file + per-SKU P&L + compliance scorecard + return risk flags
                <br />
                <span style={{ color: "#7b68ee", fontWeight: 600 }}>Loop:</span> After sales, seller uploads settlement data → ReconFlow reconciles → ReturnShield identifies problem SKUs → CatalogAI suggests fixes → cycle repeats
              </div>
            </div>
          </div>
        )}

        {/* ===== MODULES TAB ===== */}
        {activeTab === "Modules" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
            {MODULES.map(m => (
              <div key={m.id} style={{
                background: "rgba(255,255,255,0.02)", border: `1px solid ${m.color}22`,
                borderRadius: 12, padding: "18px 20px"
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 12 }}>
                  <span style={{ fontSize: 24 }}>{m.icon}</span>
                  <div>
                    <div style={{ fontSize: 16, fontWeight: 700, color: m.color }}>{m.name}</div>
                    <div style={{ fontSize: 11, color: "#888" }}>Solves: {m.solves}</div>
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#888", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>Features</div>
                    {m.features.map((f, i) => (
                      <div key={i} style={{ fontSize: 12, color: "#bbb", marginBottom: 4, display: "flex", gap: 6, lineHeight: 1.4 }}>
                        <span style={{ color: m.color, minWidth: 8 }}>→</span> {f}
                      </div>
                    ))}
                  </div>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#888", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>Technical</div>
                    <div style={{ fontSize: 12, color: "#999", marginBottom: 8 }}>
                      <span style={{ color: "#666" }}>AI Model:</span> <span style={{ color: "#ddd" }}>{m.aiModel}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "#999", marginBottom: 8 }}>
                      <span style={{ color: "#666" }}>Input:</span> <span style={{ color: "#ddd" }}>{m.dataNeeded}</span>
                    </div>
                    <div style={{ fontSize: 12, color: "#999" }}>
                      <span style={{ color: "#666" }}>Output:</span> <span style={{ color: "#ddd" }}>{m.output}</span>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ===== TECH STACK TAB ===== */}
        {activeTab === "Tech Stack" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div style={{ display: "grid", gridTemplateColumns: "140px 1fr 1fr", gap: 8, padding: "8px 14px", fontSize: 10, color: "#555", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase" }}>
              <span>Layer</span><span>Technology</span><span>Why</span>
            </div>
            {TECH_STACK.map((t, i) => (
              <div key={i} style={{
                display: "grid", gridTemplateColumns: "140px 1fr 1fr", gap: 8,
                padding: "10px 14px", fontSize: 12, alignItems: "start",
                background: i % 2 === 0 ? "rgba(255,255,255,0.02)" : "transparent", borderRadius: 8
              }}>
                <span style={{ color: "#57cc99", fontWeight: 700, fontSize: 11 }}>{t.layer}</span>
                <span style={{ color: "#ddd", fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{t.tech}</span>
                <span style={{ color: "#888" }}>{t.why}</span>
              </div>
            ))}
            <div style={{ marginTop: 16, background: "#ffd16608", border: "1px solid #ffd16622", borderRadius: 10, padding: "14px 18px" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#ffd166", marginBottom: 6 }}>💡 Cost Estimate (MVP)</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, fontSize: 12, color: "#bbb" }}>
                <div><span style={{ color: "#ddd" }}>Gemini Flash API:</span> ~₹500-2K/mo (pay per use)</div>
                <div><span style={{ color: "#ddd" }}>AWS Hosting:</span> ~₹3K-5K/mo (t3.small + S3)</div>
                <div><span style={{ color: "#ddd" }}>Total Infra:</span> ~₹5K-10K/mo for first 500 users</div>
              </div>
            </div>
          </div>
        )}

        {/* ===== PRICING TAB ===== */}
        {activeTab === "Pricing" && (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 20 }}>
              {TIERS.map((t, i) => (
                <div key={i} style={{
                  background: i === 2 ? "#57cc9908" : "rgba(255,255,255,0.02)",
                  border: `1px solid ${i === 2 ? "#57cc9933" : "rgba(255,255,255,0.06)"}`,
                  borderRadius: 12, padding: "20px 16px", position: "relative"
                }}>
                  {i === 2 && <div style={{ position: "absolute", top: -10, left: "50%", transform: "translateX(-50%)", fontSize: 9, fontWeight: 700, color: "#0a0a0f", background: "#57cc99", padding: "2px 10px", borderRadius: 10, letterSpacing: "0.06em" }}>RECOMMENDED</div>}
                  <div style={{ fontSize: 12, fontWeight: 700, color: t.color, marginBottom: 4 }}>{t.name}</div>
                  <div style={{ display: "flex", alignItems: "baseline", gap: 2, marginBottom: 4 }}>
                    <span style={{ fontSize: 28, fontWeight: 800, color: "#eee", fontFamily: "'JetBrains Mono', monospace" }}>{t.price}</span>
                    <span style={{ fontSize: 11, color: "#666" }}>{t.period}</span>
                  </div>
                  <div style={{ fontSize: 11, color: "#888", marginBottom: 12, fontStyle: "italic" }}>{t.target}</div>
                  {t.features.map((f, j) => (
                    <div key={j} style={{ fontSize: 11.5, color: "#bbb", marginBottom: 4, display: "flex", gap: 6, lineHeight: 1.4 }}>
                      <span style={{ color: t.color }}>✓</span> {f}
                    </div>
                  ))}
                  <div style={{ fontSize: 10, color: "#555", marginTop: 8, fontStyle: "italic" }}>{t.limits}</div>
                </div>
              ))}
            </div>
            {/* Revenue model */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: "18px 20px" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#ffd166", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 10 }}>Revenue Projections</div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, fontSize: 12, color: "#bbb" }}>
                <div>
                  <div style={{ color: "#57cc99", fontWeight: 700, marginBottom: 4 }}>Month 6</div>
                  500 paid users × ₹750 ARPU = <strong style={{ color: "#eee" }}>₹3.75L MRR</strong>
                </div>
                <div>
                  <div style={{ color: "#48bfe3", fontWeight: 700, marginBottom: 4 }}>Month 12</div>
                  2,000 paid users × ₹900 ARPU = <strong style={{ color: "#eee" }}>₹18L MRR</strong>
                </div>
                <div>
                  <div style={{ color: "#ffd166", fontWeight: 700, marginBottom: 4 }}>Month 18</div>
                  5,000 paid users × ₹1,100 ARPU = <strong style={{ color: "#eee" }}>₹55L MRR</strong>
                </div>
              </div>
              <div style={{ fontSize: 11, color: "#555", marginTop: 10 }}>
                TAM: 400K+ active Meesho suppliers. Even 1% penetration = 4,000 users. Market expanding as Meesho post-IPO adds more sellers.
              </div>
            </div>
          </div>
        )}

        {/* ===== MVP ROADMAP TAB ===== */}
        {activeTab === "MVP Roadmap" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {MVP_PHASES.map((p, i) => (
              <div key={i} style={{
                background: "rgba(255,255,255,0.02)", border: `1px solid ${p.color}22`,
                borderRadius: 12, padding: "18px 20px"
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 14 }}>
                  <div style={{ width: 36, height: 36, borderRadius: "50%", background: p.color + "20", border: `2px solid ${p.color}44`, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14, fontWeight: 800, color: p.color, fontFamily: "'JetBrains Mono', monospace" }}>
                    {i + 1}
                  </div>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 700, color: p.color }}>{p.phase}</div>
                    <div style={{ fontSize: 11, color: "#888" }}>Modules: {p.modules.join(" · ")}</div>
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#888", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>Deliverables</div>
                    {p.milestones.map((m, j) => (
                      <div key={j} style={{ fontSize: 12, color: "#bbb", marginBottom: 4, display: "flex", gap: 6, lineHeight: 1.4 }}>
                        <span style={{ color: p.color }}>▸</span> {m}
                      </div>
                    ))}
                  </div>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#888", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>Success Metric</div>
                    <div style={{ fontSize: 13, color: "#eee", fontWeight: 600, marginBottom: 12 }}>{p.metric}</div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#888", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>Tech Focus</div>
                    <div style={{ fontSize: 12, color: "#aaa" }}>{p.techFocus}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* ===== MOAT TAB ===== */}
        {activeTab === "Moat" && (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 20 }}>
              {/* vs competitors */}
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: "18px 20px" }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#e07a5f", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 12 }}>
                  vs Nearest Competitors
                </div>
                {[
                  { name: "VariantStudio", diff: "They do variants + Tally. We do full AI catalog + pricing + returns + reconciliation. They're a feature, we're a platform." },
                  { name: "SellerShip", diff: "They have free tools + coming-soon AI. We ship AI first. Their vaporware is our MVP." },
                  { name: "ListIQ", diff: "They do text-only listing. We do text + images + compliance + upload format. They're 1 module, we're 6." },
                  { name: "Unicommerce", diff: "They cost ₹10K+ and solve multi-channel OMS. We cost ₹499-1,999 and solve Meesho-specific pain." },
                ].map((c, i) => (
                  <div key={i} style={{ marginBottom: 10, fontSize: 12 }}>
                    <span style={{ color: "#ffd166", fontWeight: 700 }}>{c.name}:</span>
                    <span style={{ color: "#aaa" }}> {c.diff}</span>
                  </div>
                ))}
              </div>

              {/* Defensibility */}
              <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: "18px 20px" }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#57cc99", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 12 }}>
                  Competitive Moats (Over Time)
                </div>
                {[
                  { moat: "Data Network Effect", desc: "More sellers → more catalog data → better AI models → better titles/images → more sellers" },
                  { moat: "Meesho-Specific Intelligence", desc: "Category-specific rules, return patterns, pricing data that generic tools can't replicate" },
                  { moat: "Workflow Lock-in", desc: "Once seller's catalog + P&L + GST flows through us, switching cost is high" },
                  { moat: "WhatsApp Distribution", desc: "Daily alerts via WhatsApp = habitual engagement. Indian sellers check WhatsApp 50x/day" },
                  { moat: "Price Advantage", desc: "Gemini Flash is 10x cheaper than GPT-4. We pass savings to sellers at ₹499/mo" },
                ].map((m, i) => (
                  <div key={i} style={{ marginBottom: 10, fontSize: 12 }}>
                    <span style={{ color: "#57cc99", fontWeight: 700 }}>{m.moat}:</span>
                    <span style={{ color: "#aaa" }}> {m.desc}</span>
                  </div>
                ))}
              </div>
            </div>

            {/* GTM */}
            <div style={{ background: "#7b68ee08", border: "1px solid #7b68ee22", borderRadius: 12, padding: "18px 20px" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#7b68ee", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 10 }}>
                🚀 Go-to-Market Strategy
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 16, fontSize: 12, color: "#bbb", lineHeight: 1.6 }}>
                <div>
                  <div style={{ color: "#7b68ee", fontWeight: 700, marginBottom: 4 }}>Channel 1: YouTube</div>
                  Meesho seller tutorials in Hindi. "How to create catalog in 30 seconds" demos. Target the 500K+ sellers watching Meesho videos.
                </div>
                <div>
                  <div style={{ color: "#7b68ee", fontWeight: 700, marginBottom: 4 }}>Channel 2: WhatsApp Groups</div>
                  Meesho seller WhatsApp communities are massive. Free tool → share link → viral loop. Offer free P&L calculator as lead magnet.
                </div>
                <div>
                  <div style={{ color: "#7b68ee", fontWeight: 700, marginBottom: 4 }}>Channel 3: Meesho Seller Forums</div>
                  Engage in seller communities, provide value. Partner with existing Meesho training channels. No paid ads initially.
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
