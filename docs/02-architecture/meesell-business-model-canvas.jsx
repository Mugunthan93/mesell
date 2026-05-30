import { useState } from "react";

const CANVAS = {
  partners: {
    label: "Key Partners",
    icon: "🤝",
    color: "#E07A5F",
    items: [
      { title: "Google Cloud (Gemini AI)", detail: "AI text generation — titles, descriptions, SEO keywords. Gemini 2.5 Flash at $0.30/1M input tokens. Cheapest quality LLM. ~₹0.12/catalog." },
      { title: "rembg (Open Source) + FAPIhub", detail: "Image background removal. Self-hosted rembg = FREE. FAPIhub API fallback at ₹0.08/image. Avoids remove.bg at ₹8-16/image." },
      { title: "Razorpay", detail: "Subscription billing. UPI, cards, auto-renewal, GST invoicing. 2% + ₹3 per transaction. Industry standard for Indian SaaS." },
      { title: "Gupshup / Meta WhatsApp API", detail: "WhatsApp Business notifications — daily alerts, return warnings, stock alerts. ₹0.50/message via Gupshup. Sellers live on WhatsApp." },
      { title: "AWS (ap-south-1 Mumbai)", detail: "Hosting infrastructure. t3.small + RDS + S3 + CloudFront. ~₹7,800/month fixed. Lowest latency for Indian users." },
      { title: "Meesho (Future — Phase 3+)", detail: "Official Supplier API partnership after 2,000+ active users. Until then: CSV bridge (MVP) → Chrome extension (Phase 2) → Session cookie (Phase 2-3)." },
    ],
  },
  activities: {
    label: "Key Activities",
    icon: "⚡",
    color: "#81B29A",
    items: [
      { title: "AI Catalog Generation Pipeline", detail: "Product photos + basic details → AI titles/descriptions + image enhancement + compliance validation → Meesho-ready CSV export." },
      { title: "Meesho Data Parsing Engine", detail: "Parse seller's settlement CSVs, order reports, TCS exports → per-SKU P&L, return analytics, GST reconciliation." },
      { title: "Chrome Extension Development (Phase 2)", detail: "Extension augments supplier.meesho.com — reads DOM data, injects quality scores, pricing alerts, optimization buttons." },
      { title: "Competitive Price Scraping (Phase 2)", detail: "Scheduled Playwright scrapers on public Meesho pages for competitor pricing intelligence. Rotating proxies." },
      { title: "Product-Led Growth Marketing", detail: "Hindi YouTube tutorials, WhatsApp seller community engagement, free tool lead magnets (profit calculator), Meesho forum presence." },
      { title: "Platform Maintenance & AI Model Tuning", detail: "Track Meesho format/rule changes. Fine-tune AI prompts per category (fashion vs electronics vs home). Update compliance rules." },
    ],
  },
  resources: {
    label: "Key Resources",
    icon: "🧱",
    color: "#F2CC8F",
    items: [
      { title: "Meesho Category Knowledge Base", detail: "Category-specific rules: image specs, title formats, required attributes, banned words, SEO patterns. Updated as Meesho changes rules." },
      { title: "AI Prompt Library", detail: "Fine-tuned prompts for each product category — fashion titles differ from electronics descriptions. Built from testing 10K+ generations." },
      { title: "Seller Data Flywheel", detail: "More sellers → more catalog data → better AI models → better output quality → more sellers. Network effect on data." },
      { title: "Engineering Team", detail: "MVP: 1-2 full-stack devs (FastAPI + React). Phase 2: add 1 ML/AI engineer + 1 Chrome extension specialist." },
      { title: "Pin Code & Return Pattern Database", detail: "Aggregated anonymized return data by category/pin code. Powers ReturnShield's predictive analytics." },
    ],
  },
  value: {
    label: "Value Propositions",
    icon: "💎",
    color: "#3D405B",
    items: [
      { title: "30-second catalog creation vs 30-minute manual", detail: "Upload product photos → get Meesho-ready catalog with AI titles, optimized descriptions, compliant images, correct attributes. 60x faster." },
      { title: "40-60% rejection rate → near-zero", detail: "QualityGate validates everything BEFORE upload — image size, white BG, title rules, attribute completeness. No more 'submit and pray'." },
      { title: "₹499/month vs ₹5K-50K/month agencies", detail: "Same output (catalog creation + pricing + analytics) at 10-100x lower cost. AI replaces manual agency labor." },
      { title: "Know your TRUE profit per SKU", detail: "Most Meesho sellers don't know real margins after returns, weight slab costs, GST, ad spend. PriceIntel shows per-SKU P&L in real-time." },
      { title: "One platform, not 5 fragmented tools", detail: "Replaces: ListIQ (text) + PhotoRoom (images) + EcomSarthi (QC tool) + Excel (P&L) + CA (GST). Everything in one login." },
      { title: "Meesho-first, not marketplace-generic", detail: "Every feature built specifically for Meesho's format, rules, and seller dynamics. Not a repurposed Amazon tool." },
    ],
  },
  relationships: {
    label: "Customer Relationships",
    icon: "💬",
    color: "#7B68EE",
    items: [
      { title: "Self-serve SaaS (Primary)", detail: "Sign up → free tier → upgrade. No sales calls needed. Seller onboards in <5 minutes." },
      { title: "WhatsApp Daily Alerts", detail: "Automated daily digest: yesterday's sales, returns, margin alerts, stock warnings. Keeps seller engaged without opening dashboard." },
      { title: "YouTube Tutorial Community", detail: "Hindi video tutorials: 'How to create perfect Meesho catalog in 30 seconds'. Builds trust + drives organic signups." },
      { title: "WhatsApp Support Group", detail: "Pro/Growth tier sellers get access to community group. Peer support + MeeSell team responds. Reduces support cost." },
      { title: "Onboarding Wizard", detail: "First-time flow: upload 1 product photo → see AI magic → wow moment → convert to paid. Time to value < 2 minutes." },
    ],
  },
  channels: {
    label: "Channels",
    icon: "📡",
    color: "#F4845F",
    items: [
      { title: "YouTube (Primary — Hindi tutorials)", detail: "500K+ Meesho sellers watch Hindi tutorials. 'How to sell on Meesho' videos get 100K-1M views. Create AI demo content." },
      { title: "WhatsApp Seller Groups", detail: "Massive Meesho seller WhatsApp communities. Share free profit calculator → viral loop. Word-of-mouth in seller networks." },
      { title: "Meesho Seller Forums & Facebook Groups", detail: "Engage in seller communities. Provide value (free tools, tips). No hard selling — utility-first approach." },
      { title: "Chrome Web Store (Phase 2)", detail: "Chrome extension listed on Web Store. Sellers searching 'Meesho tools' find us. Extension acts as acquisition channel." },
      { title: "SEO — Long-tail seller queries", detail: "Blog targeting: 'Meesho catalog rejection fix', 'Meesho profit calculator', 'how to reduce returns on Meesho'. Low competition, high intent." },
    ],
  },
  segments: {
    label: "Customer Segments",
    icon: "👥",
    color: "#48BFE3",
    items: [
      { title: "New Meesho Sellers (0-100 orders/mo)", detail: "Just registered on Meesho. Struggling with first catalog. High rejection rates. Need hand-holding. Target for Starter plan (₹499)." },
      { title: "Growing Sellers (100-500 orders/mo)", detail: "Established but scaling. Need bulk catalog, pricing optimization, return analysis. Can't afford ₹10K+ agency. Target for Pro plan (₹999)." },
      { title: "Scale Sellers (500+ orders/mo)", detail: "High volume, multi-category. Need automation, competitor intelligence, reconciliation, multi-platform. Target for Growth plan (₹1,999)." },
      { title: "Meesho-only Manufacturers", detail: "Small manufacturers (Surat textiles, Jaipur crafts) who produce and sell directly. Need catalog creation from raw product photos." },
      { title: "Multi-platform Sellers (Phase 3)", detail: "Sell on Meesho + Flipkart + Amazon. Need cross-platform catalog, pricing, inventory. Target for future Enterprise tier." },
    ],
  },
  costs: {
    label: "Cost Structure",
    icon: "📉",
    color: "#E56B6F",
    items: [
      { title: "AI API Costs (Variable — largest COGS)", detail: "Gemini Flash: ₹0.12/catalog + Image processing: ₹0.04-0.08/image. At 500 users × Pro plan: ~₹12,500/month. Scales with usage." },
      { title: "Infrastructure (Fixed — shared)", detail: "AWS Mumbai: ₹7,800/month (server + DB + storage + CDN + GPU instance). Handles up to ~500 concurrent users." },
      { title: "WhatsApp Messaging (Variable)", detail: "₹0.50/message via Gupshup. At 500 users × 30 msgs: ₹7,500/month." },
      { title: "Payment Gateway (Variable)", detail: "Razorpay: 2% + ₹3 per subscription payment. At 500 users × ₹900 avg: ~₹12,000/month." },
      { title: "Engineering Team (Fixed)", detail: "MVP: 2 full-stack devs. Phase 2: +1 ML engineer +1 extension dev. Biggest fixed cost." },
      { title: "Scraping Infrastructure (Phase 2)", detail: "Rotating proxies: ₹2,000-5,000/month. Playwright on existing server. Competitor pricing intelligence." },
      { title: "Gross Margin: 83-85% across all tiers", detail: "Starter ₹499: COGS ₹77, margin ₹422 (85%). Pro ₹999: COGS ₹150, margin ₹849 (85%). Growth ₹1,999: COGS ₹330, margin ₹1,669 (83%)." },
    ],
  },
  revenue: {
    label: "Revenue Streams",
    icon: "📈",
    color: "#57CC99",
    items: [
      { title: "SaaS Subscriptions (Primary — 90%+)", detail: "Free (₹0) → Starter (₹499/mo) → Pro (₹999/mo) → Growth (₹1,999/mo). Monthly recurring. Auto-renewal via Razorpay." },
      { title: "Revenue Projections", detail: "Month 6: 500 paid × ₹750 ARPU = ₹3.75L MRR. Month 12: 2,000 × ₹900 = ₹18L MRR. Month 18: 5,000 × ₹1,100 = ₹55L MRR." },
      { title: "TAM / SAM / SOM", detail: "TAM: 400K+ active Meesho suppliers. SAM: ~100K who need catalog/pricing tools. SOM Year 1: 2,000 paid (2% of SAM)." },
      { title: "Future: Enterprise Tier (₹4,999+/mo)", detail: "Multi-platform sellers, white-label for agencies. Phase 3+ after official Meesho API access." },
      { title: "Future: Marketplace Data Insights (B2B)", detail: "Aggregated, anonymized category trends, pricing benchmarks, return rate data. Sold to brands/investors. Phase 3+." },
    ],
  },
};

const GRID_MAP = {
  partners: { row: "1 / 3", col: "1 / 2" },
  activities: { row: "1 / 2", col: "2 / 3" },
  resources: { row: "2 / 3", col: "2 / 3" },
  value: { row: "1 / 3", col: "3 / 4" },
  relationships: { row: "1 / 2", col: "4 / 5" },
  channels: { row: "2 / 3", col: "4 / 5" },
  segments: { row: "1 / 3", col: "5 / 6" },
  costs: { row: "3 / 4", col: "1 / 4" },
  revenue: { row: "3 / 4", col: "4 / 6" },
};

function CanvasBlock({ id, data, isExpanded, onToggle }) {
  const grid = GRID_MAP[id];
  return (
    <div
      onClick={() => onToggle(id)}
      style={{
        gridRow: grid.row,
        gridColumn: grid.col,
        background: isExpanded ? `${data.color}10` : "rgba(255,255,255,0.02)",
        border: `1.5px solid ${isExpanded ? data.color + "44" : data.color + "18"}`,
        borderRadius: 12,
        padding: "14px 16px",
        cursor: "pointer",
        overflow: "hidden",
        transition: "all 0.3s",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8, flexShrink: 0 }}>
        <span style={{ fontSize: 16 }}>{data.icon}</span>
        <span style={{
          fontSize: 11, fontWeight: 700, letterSpacing: "0.05em",
          textTransform: "uppercase", color: data.color,
          fontFamily: "'DM Sans', sans-serif",
        }}>
          {data.label}
        </span>
        <span style={{
          marginLeft: "auto", fontSize: 10, color: "#666",
          fontFamily: "'JetBrains Mono', monospace",
        }}>
          {data.items.length}
        </span>
      </div>

      {/* Items */}
      <div style={{ flex: 1, overflowY: "auto", display: "flex", flexDirection: "column", gap: 6 }}>
        {data.items.map((item, i) => (
          <div key={i}>
            <div style={{ display: "flex", gap: 6, alignItems: "flex-start" }}>
              <span style={{
                width: 5, height: 5, minWidth: 5, borderRadius: "50%",
                background: data.color, marginTop: 5, opacity: 0.6,
              }} />
              <div>
                <div style={{
                  fontSize: 12, fontWeight: 600, color: "#ddd",
                  lineHeight: 1.3, fontFamily: "'DM Sans', sans-serif",
                }}>
                  {item.title}
                </div>
                {isExpanded && (
                  <div style={{
                    fontSize: 11, color: "#888", lineHeight: 1.5,
                    marginTop: 2, fontFamily: "'DM Sans', sans-serif",
                  }}>
                    {item.detail}
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function BusinessModelCanvas() {
  const [expanded, setExpanded] = useState(new Set(["value"]));

  const toggle = (id) => {
    setExpanded(prev => {
      const n = new Set(prev);
      n.has(id) ? n.delete(id) : n.add(id);
      return n;
    });
  };

  const expandAll = () => setExpanded(new Set(Object.keys(CANVAS)));
  const collapseAll = () => setExpanded(new Set());

  return (
    <div style={{
      minHeight: "100vh", background: "#0a0a0f", color: "#e0e0e0",
      fontFamily: "'DM Sans', sans-serif", padding: "24px 20px 40px",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&family=Instrument+Serif&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{ maxWidth: 1200, margin: "0 auto 16px", display: "flex", alignItems: "flex-end", justifyContent: "space-between", flexWrap: "wrap", gap: 12 }}>
        <div>
          <div style={{ fontSize: 10, letterSpacing: "0.2em", color: "#57cc99", textTransform: "uppercase", fontWeight: 600, marginBottom: 6 }}>
            Business Model Canvas · Final
          </div>
          <h1 style={{ fontFamily: "'Instrument Serif', serif", fontSize: 34, fontWeight: 400, margin: 0, color: "#fff", lineHeight: 1.1 }}>
            MeeSell<span style={{ color: "#57cc99" }}>.</span>
          </h1>
          <p style={{ color: "#666", fontSize: 12, margin: "4px 0 0" }}>
            AI-powered operating system for Meesho suppliers · 6 modules · ₹499-1,999/mo · Meesho-first
          </p>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <button onClick={expandAll} style={{
            padding: "6px 12px", fontSize: 11, fontWeight: 600, borderRadius: 6,
            background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
            color: "#888", cursor: "pointer", fontFamily: "'DM Sans', sans-serif",
          }}>
            Expand All
          </button>
          <button onClick={collapseAll} style={{
            padding: "6px 12px", fontSize: 11, fontWeight: 600, borderRadius: 6,
            background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)",
            color: "#888", cursor: "pointer", fontFamily: "'DM Sans', sans-serif",
          }}>
            Collapse All
          </button>
        </div>
      </div>

      {/* Canvas Grid */}
      <div style={{
        maxWidth: 1200, margin: "0 auto",
        display: "grid",
        gridTemplateColumns: "repeat(5, 1fr)",
        gridTemplateRows: "minmax(200px, auto) minmax(200px, auto) minmax(180px, auto)",
        gap: 8,
      }}>
        {Object.entries(CANVAS).map(([id, data]) => (
          <CanvasBlock
            key={id}
            id={id}
            data={data}
            isExpanded={expanded.has(id)}
            onToggle={toggle}
          />
        ))}
      </div>

      {/* Integration Strategy */}
      <div style={{
        maxWidth: 1200, margin: "16px auto 0",
        background: "rgba(255,255,255,0.02)",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 12, padding: "16px 20px",
      }}>
        <div style={{ fontSize: 10, fontWeight: 700, color: "#48bfe3", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8 }}>
          Meesho Integration Roadmap
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
          {[
            { phase: "MVP (M1-3)", method: "CSV Bridge", desc: "Seller downloads/uploads CSVs. MeeSell generates Meesho-format files. Zero API dependency.", color: "#57cc99", modules: "CatalogAI + QualityGate + Calculator" },
            { phase: "Phase 2 (M4-6)", method: "Chrome Extension", desc: "Extension reads supplier panel DOM. Injects features into Meesho UI. Auto-data sync.", color: "#48bfe3", modules: "+ PriceIntel + ReturnShield + Bulk Gen" },
            { phase: "Phase 3 (M7-12)", method: "Session Cookie + Scraping", desc: "Auto-pull seller data. Scrape public Meesho for competitor pricing. Full automation.", color: "#ffd166", modules: "+ ReconFlow + StockPulse + Multi-platform" },
            { phase: "Phase 4 (M12+)", method: "Official API Partner", desc: "2,000+ active users → approach Meesho for sanctioned API credentials.", color: "#7b68ee", modules: "Full automation + Enterprise tier" },
          ].map((p, i) => (
            <div key={i} style={{ background: `${p.color}08`, border: `1px solid ${p.color}22`, borderRadius: 8, padding: "10px 12px" }}>
              <div style={{ fontSize: 9, fontWeight: 700, color: p.color, letterSpacing: "0.06em", marginBottom: 3 }}>{p.phase}</div>
              <div style={{ fontSize: 12, fontWeight: 700, color: "#ddd", marginBottom: 4 }}>{p.method}</div>
              <div style={{ fontSize: 10, color: "#888", lineHeight: 1.4, marginBottom: 4 }}>{p.desc}</div>
              <div style={{ fontSize: 9, color: p.color, fontFamily: "'JetBrains Mono', monospace" }}>{p.modules}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <div style={{
        maxWidth: 1200, margin: "12px auto 0", textAlign: "center",
        fontSize: 11, color: "#333", fontFamily: "'JetBrains Mono', monospace",
      }}>
        Click any section to expand details · Built from R&D analysis of 6 problems, 50+ competitors, 30+ players
      </div>
    </div>
  );
}
