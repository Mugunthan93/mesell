import { useState } from "react";

const PARTNERS = [
  {
    id: "gemini",
    name: "Google Gemini 2.5 Flash",
    what: "AI text generation — titles, descriptions, keywords, SEO optimization",
    icon: "🧠",
    pricing: "$0.30/1M input tokens · $2.50/1M output tokens",
    perCatalog: "~₹0.12 per catalog (800 input + 500 output tokens)",
    alternatives: ["Gemini 2.5 Flash-Lite ($0.10/1M) — cheaper but lower quality", "DeepSeek V3 ($0.14/1M) — cheapest but China-hosted", "Claude Haiku ($0.25/1M) — good but more expensive"],
    chosen: "Gemini 2.5 Flash",
    reason: "Best price-to-quality ratio. ₹0.12/catalog = negligible cost even at scale.",
  },
  {
    id: "image",
    name: "Image Processing (Background Removal + Resize)",
    what: "Background removal, white BG, 1024×1024 resize, image enhancement",
    icon: "🖼️",
    pricing: "Option A: rembg (open source, self-hosted) = FREE but needs GPU\nOption B: FAPIhub API = ₹0.08/image\nOption C: remove.bg = ₹8-16/image (10-200x more expensive!)",
    perCatalog: "~₹0.32/catalog (4 images × ₹0.08) using FAPIhub",
    alternatives: ["rembg self-hosted — FREE but needs GPU server (~₹3K/mo)", "RemoveBG API — ₹0.08/image at scale", "FAPIhub — ₹0.08/image, rembg-based", "PhotoRoom API — ₹1.50/image (expensive)", "remove.bg — ₹8-16/image (way too expensive)"],
    chosen: "Self-hosted rembg (MVP) → FAPIhub API (scale)",
    reason: "rembg is FREE and open source. Run on a GPU instance for ₹3K/mo, handles thousands of images. At scale, FAPIhub at ₹0.08/image as fallback.",
  },
  {
    id: "hosting",
    name: "AWS Hosting (ap-south-1 Mumbai)",
    what: "App server, database, file storage, CDN",
    icon: "☁️",
    pricing: "t3.small: ~₹1,500/mo · RDS PostgreSQL: ~₹2,500/mo · S3: ~₹500/mo · CloudFront: ~₹300/mo",
    perCatalog: "Shared cost — decreases per user as you scale",
    alternatives: ["Railway — simpler but more expensive at scale", "DigitalOcean — $12-48/mo, good middle ground", "Hetzner — cheapest EU option but no India region", "Self-managed VPS — cheapest but ops overhead"],
    chosen: "AWS ap-south-1",
    reason: "Lowest latency for Indian users. Free tier for first 12 months. Pay-as-you-grow. Industry standard for VC fundraising.",
  },
  {
    id: "whatsapp",
    name: "WhatsApp Business API (Notifications)",
    what: "Daily sales alerts, return notifications, stock alerts, support",
    icon: "💬",
    pricing: "Gupshup: ₹0.50-0.85/message · Wati: ₹0.50-1.00/message · Meta direct: ₹0.47/marketing msg",
    perCatalog: "Not per-catalog — per user: ~30 msgs/mo = ₹15-25/user/mo",
    alternatives: ["Gupshup — ₹0.50/msg, most popular in India", "Wati — ₹0.50-1.00/msg, easier dashboard", "Interakt — ₹0.60/msg + ₹999/mo base", "Meta Cloud API direct — cheapest but more dev work"],
    chosen: "Gupshup (MVP) → Meta Cloud API (scale)",
    reason: "Gupshup is fastest to integrate. At scale, Meta direct API saves 30-40% on message costs.",
  },
  {
    id: "razorpay",
    name: "Razorpay (Payment Gateway)",
    what: "Subscription billing, UPI, cards, auto-renewal, GST invoicing",
    icon: "💳",
    pricing: "2% + ₹3 per transaction (standard) · Subscription add-on: no extra fee",
    perCatalog: "Not per-catalog — per subscription: ₹13 (on ₹499) to ₹43 (on ₹1,999)",
    alternatives: ["Cashfree — 1.9% + ₹3 (slightly cheaper)", "PayU — 2% + ₹3 (same)", "Stripe India — 2% + ₹7 (more expensive but better DX)"],
    chosen: "Razorpay",
    reason: "Best subscription management for India. Auto-GST invoicing. Sellers trust Razorpay. 95%+ UPI success rate.",
  },
  {
    id: "scraping",
    name: "Proxy Infrastructure (Competitor Scraping)",
    what: "Scrape public Meesho pages for competitor pricing intelligence",
    icon: "🕷️",
    pricing: "Residential proxies: ₹2,000-5,000/mo · Apify actors: $49/mo · Self-hosted Playwright: server cost only",
    perCatalog: "Not per-catalog — shared infra: ₹4-10/user/mo at 500 users",
    alternatives: ["Bright Data — best quality, expensive ($500+/mo)", "Apify — $49/mo for hosted actors", "Self-hosted Playwright + free proxies — cheapest but less reliable", "ScrapingBee — $49/mo for 150K requests"],
    chosen: "Self-hosted Playwright + rotating proxies (Phase 2)",
    reason: "Phase 2 feature. Start with Playwright on existing server. Add proxy service only when scraping volume justifies it.",
  },
];

const TIERS = [
  {
    name: "Starter",
    price: 499,
    color: "#48bfe3",
    usage: { catalogs: 50, images: 200, whatsapp: 20, scraping: false },
    costs: [
      { item: "Gemini AI (50 catalogs)", cost: 6 },
      { item: "Image processing (200 imgs, self-hosted)", cost: 8 },
      { item: "Hosting share (at 200 users)", cost: 25 },
      { item: "WhatsApp (20 msgs)", cost: 10 },
      { item: "Razorpay (2% + ₹3)", cost: 13 },
      { item: "Support / ops overhead", cost: 15 },
    ],
  },
  {
    name: "Pro",
    price: 999,
    color: "#57cc99",
    recommended: true,
    usage: { catalogs: 200, images: 800, whatsapp: 40, scraping: true },
    costs: [
      { item: "Gemini AI (200 catalogs)", cost: 25 },
      { item: "Image processing (800 imgs)", cost: 32 },
      { item: "Hosting share (at 500 users)", cost: 15 },
      { item: "WhatsApp (40 msgs)", cost: 20 },
      { item: "Competitor scraping share", cost: 10 },
      { item: "Razorpay (2% + ₹3)", cost: 23 },
      { item: "Support / ops overhead", cost: 25 },
    ],
  },
  {
    name: "Growth",
    price: 1999,
    color: "#ffd166",
    usage: { catalogs: 500, images: 2000, whatsapp: 60, scraping: true },
    costs: [
      { item: "Gemini AI (500 catalogs, premium model)", cost: 80 },
      { item: "Image processing (2000 imgs)", cost: 80 },
      { item: "Hosting share (at 500 users)", cost: 12 },
      { item: "WhatsApp (60 msgs)", cost: 30 },
      { item: "Competitor scraping (200 SKU tracking)", cost: 25 },
      { item: "Razorpay (2% + ₹3)", cost: 43 },
      { item: "Multi-platform adapters", cost: 20 },
      { item: "Priority support / ops overhead", cost: 40 },
    ],
  },
];

export default function UnitEconomics() {
  const [activeSection, setActiveSection] = useState("costs");

  return (
    <div style={{ minHeight: "100vh", background: "#0a0a0f", color: "#e0e0e0", fontFamily: "'DM Sans', sans-serif", padding: "28px 20px 50px" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&family=Instrument+Serif&display=swap" rel="stylesheet" />

      <div style={{ maxWidth: 1020, margin: "0 auto 20px" }}>
        <div style={{ fontSize: 10, letterSpacing: "0.15em", color: "#ffd166", textTransform: "uppercase", fontWeight: 600, marginBottom: 6 }}>
          Unit Economics · Partner Cost Analysis
        </div>
        <h1 style={{ fontFamily: "'Instrument Serif', serif", fontSize: 28, fontWeight: 400, margin: "0 0 6px", color: "#fff" }}>
          What does each partner cost, and why does the plan price go up?
        </h1>
      </div>

      {/* Section toggle */}
      <div style={{ maxWidth: 1020, margin: "0 auto 16px", display: "flex", gap: 6 }}>
        {[
          { key: "costs", label: "Partner Costs" },
          { key: "unit", label: "Unit Economics Per Tier" },
          { key: "why", label: "Why Plan Value Increases" },
        ].map(s => (
          <button key={s.key} onClick={() => setActiveSection(s.key)} style={{
            padding: "8px 16px", fontSize: 12, fontWeight: 600, borderRadius: 8, cursor: "pointer",
            background: activeSection === s.key ? "#ffd16622" : "rgba(255,255,255,0.03)",
            border: `1px solid ${activeSection === s.key ? "#ffd16644" : "rgba(255,255,255,0.06)"}`,
            color: activeSection === s.key ? "#ffd166" : "#888",
            fontFamily: "'DM Sans', sans-serif",
          }}>{s.label}</button>
        ))}
      </div>

      <div style={{ maxWidth: 1020, margin: "0 auto" }}>

        {/* PARTNER COSTS */}
        {activeSection === "costs" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
            {PARTNERS.map(p => (
              <div key={p.id} style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: "16px 20px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 10 }}>
                  <span style={{ fontSize: 22 }}>{p.icon}</span>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: "#eee" }}>{p.name}</div>
                    <div style={{ fontSize: 11, color: "#888" }}>{p.what}</div>
                  </div>
                </div>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, fontSize: 12 }}>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#ffd166", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 }}>Pricing</div>
                    <div style={{ color: "#bbb", lineHeight: 1.6, whiteSpace: "pre-line" }}>{p.pricing}</div>
                    <div style={{ marginTop: 8 }}>
                      <span style={{ fontSize: 10, fontWeight: 700, color: "#57cc99", letterSpacing: "0.06em" }}>COST PER CATALOG: </span>
                      <span style={{ color: "#57cc99", fontWeight: 600 }}>{p.perCatalog}</span>
                    </div>
                  </div>
                  <div>
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#7b68ee", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 4 }}>Our Choice & Why</div>
                    <div style={{ color: "#ddd", fontWeight: 600, marginBottom: 4 }}>→ {p.chosen}</div>
                    <div style={{ color: "#999", lineHeight: 1.5 }}>{p.reason}</div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* UNIT ECONOMICS */}
        {activeSection === "unit" && (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14, marginBottom: 20 }}>
              {TIERS.map(t => {
                const totalCost = t.costs.reduce((a, c) => a + c.cost, 0);
                const margin = t.price - totalCost;
                const marginPct = Math.round((margin / t.price) * 100);
                return (
                  <div key={t.name} style={{
                    background: t.recommended ? "#57cc9908" : "rgba(255,255,255,0.02)",
                    border: `1px solid ${t.recommended ? "#57cc9933" : "rgba(255,255,255,0.06)"}`,
                    borderRadius: 12, padding: "18px", position: "relative"
                  }}>
                    {t.recommended && <div style={{ position: "absolute", top: -9, left: "50%", transform: "translateX(-50%)", fontSize: 9, fontWeight: 700, color: "#0a0a0f", background: "#57cc99", padding: "2px 10px", borderRadius: 10 }}>SWEET SPOT</div>}

                    <div style={{ fontSize: 12, fontWeight: 700, color: t.color, marginBottom: 2 }}>{t.name}</div>
                    <div style={{ fontSize: 24, fontWeight: 800, color: "#eee", fontFamily: "'JetBrains Mono', monospace", marginBottom: 12 }}>
                      ₹{t.price}<span style={{ fontSize: 11, color: "#666" }}>/mo</span>
                    </div>

                    {/* Cost breakdown */}
                    <div style={{ fontSize: 10, fontWeight: 700, color: "#888", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>COGS Breakdown</div>
                    {t.costs.map((c, i) => (
                      <div key={i} style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "#aaa", marginBottom: 3, lineHeight: 1.4 }}>
                        <span>{c.item}</span>
                        <span style={{ color: "#e07a5f", fontFamily: "'JetBrains Mono', monospace", fontWeight: 600 }}>₹{c.cost}</span>
                      </div>
                    ))}

                    <div style={{ borderTop: "1px solid rgba(255,255,255,0.08)", marginTop: 10, paddingTop: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4 }}>
                        <span style={{ color: "#e07a5f", fontWeight: 600 }}>Total COGS</span>
                        <span style={{ color: "#e07a5f", fontWeight: 700, fontFamily: "'JetBrains Mono', monospace" }}>₹{totalCost}</span>
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 13 }}>
                        <span style={{ color: "#57cc99", fontWeight: 700 }}>Gross Margin</span>
                        <span style={{ color: "#57cc99", fontWeight: 800, fontFamily: "'JetBrains Mono', monospace" }}>₹{margin} ({marginPct}%)</span>
                      </div>
                    </div>

                    {/* Margin bar */}
                    <div style={{ marginTop: 8, height: 8, background: "rgba(255,255,255,0.06)", borderRadius: 4, overflow: "hidden" }}>
                      <div style={{ display: "flex", height: "100%" }}>
                        <div style={{ width: `${100 - marginPct}%`, background: "#e07a5f", borderRadius: "4px 0 0 4px" }} />
                        <div style={{ width: `${marginPct}%`, background: "#57cc99", borderRadius: "0 4px 4px 0" }} />
                      </div>
                    </div>
                    <div style={{ display: "flex", justifyContent: "space-between", fontSize: 9, color: "#666", marginTop: 3 }}>
                      <span>COGS</span><span>MARGIN</span>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* Infrastructure costs */}
            <div style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: "16px 20px" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#48bfe3", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 10 }}>
                Fixed Infrastructure Costs (Shared Across All Users)
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
                {[
                  { item: "AWS Server (t3.small)", cost: "₹1,500/mo", note: "Handles up to ~500 concurrent users" },
                  { item: "PostgreSQL (RDS db.t3.micro)", cost: "₹2,500/mo", note: "Managed DB, auto-backups" },
                  { item: "S3 + CloudFront", cost: "₹800/mo", note: "Image storage + CDN" },
                  { item: "GPU instance (for rembg)", cost: "₹3,000/mo", note: "g4dn.xlarge spot instance" },
                ].map((c, i) => (
                  <div key={i} style={{ fontSize: 12 }}>
                    <div style={{ color: "#ddd", fontWeight: 600, marginBottom: 2 }}>{c.item}</div>
                    <div style={{ color: "#48bfe3", fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", fontSize: 13, marginBottom: 2 }}>{c.cost}</div>
                    <div style={{ color: "#666", fontSize: 10 }}>{c.note}</div>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 12, fontSize: 13, color: "#aaa" }}>
                <strong style={{ color: "#eee" }}>Total fixed infra: ~₹7,800/month.</strong> At 100 paid users = ₹78/user. At 500 users = ₹15.6/user. At 2000 users = ₹3.9/user. <span style={{ color: "#57cc99" }}>Infrastructure cost per user drops as you scale.</span>
              </div>
            </div>
          </div>
        )}

        {/* WHY PLAN VALUE INCREASES */}
        {activeSection === "why" && (
          <div>
            <div style={{ background: "#57cc9908", border: "1px solid #57cc9922", borderRadius: 12, padding: "20px 24px", marginBottom: 16 }}>
              <div style={{ fontSize: 13, color: "#ddd", lineHeight: 1.8 }}>
                <strong style={{ color: "#57cc99", fontSize: 15 }}>Core answer:</strong> Each plan tier costs MORE to serve because it uses MORE of each partner's resources. Higher plans unlock features that consume expensive partner services (AI, scraping, WhatsApp). The pricing increase is directly proportional to the value delivered.
              </div>
            </div>

            {/* Value chain breakdown */}
            <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
              {[
                {
                  from: "Free → Starter (₹0 → ₹499)",
                  delta: "+₹499",
                  partnerCostJump: "₹0 → ₹77",
                  color: "#48bfe3",
                  whyMore: [
                    "50 AI catalog generations vs 5 → 10x more Gemini API calls (+₹6)",
                    "200 image processing vs 15 → 13x more rembg compute (+₹8)",
                    "WhatsApp alerts activated → new partner cost (+₹10)",
                    "Full QualityGate (unlimited) vs basic (3/day) → more server compute",
                    "Per-SKU P&L tracker → needs settlement CSV parsing engine",
                  ],
                  sellerValue: "Seller saves 10+ hours/month on manual catalog work. At ₹200/hr minimum wage, that's ₹2,000+ value for ₹499 cost. 4x ROI.",
                },
                {
                  from: "Starter → Pro (₹499 → ₹999)",
                  delta: "+₹500",
                  partnerCostJump: "₹77 → ₹150",
                  color: "#57cc99",
                  whyMore: [
                    "200 catalogs vs 50 → 4x more Gemini API calls (+₹19)",
                    "800 images vs 200 → 4x more image processing (+₹24)",
                    "Competitor price monitoring activated → scraping infra cost (+₹10)",
                    "Full return analytics → needs more compute for pattern detection",
                    "Tally XML + Zoho export → additional parser development",
                    "WhatsApp doubled (40 vs 20 msgs) → +₹10 more messaging cost",
                  ],
                  sellerValue: "Seller with 100-500 orders/month saves ₹5,000-15,000/month on agency fees + catches pricing mistakes worth ₹3,000-8,000/month. 10-20x ROI.",
                },
                {
                  from: "Pro → Growth (₹999 → ₹1,999)",
                  delta: "+₹1,000",
                  partnerCostJump: "₹150 → ₹330",
                  color: "#ffd166",
                  whyMore: [
                    "Unlimited catalogs → uncapped Gemini API usage (+₹55)",
                    "Premium AI model (better titles) → costs more per generation",
                    "2000 images vs 800 → 2.5x image processing (+₹48)",
                    "200 SKU competitor tracking vs 50 → 4x scraping (+₹15)",
                    "Multi-platform adapters (Flipkart/Amazon) → new parser dev",
                    "API access → infrastructure for external integrations",
                    "Dedicated support → human time cost (+₹15)",
                  ],
                  sellerValue: "Scale seller replacing ₹15K-30K/month agency. Full automation = 15-30x ROI. Also prevents ₹10K-50K/month in pricing mistakes and unreconciled payments.",
                },
              ].map((tier, i) => (
                <div key={i} style={{ background: "rgba(255,255,255,0.02)", border: `1px solid ${tier.color}22`, borderRadius: 12, padding: "18px 20px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 12, marginBottom: 12 }}>
                    <div style={{ fontSize: 14, fontWeight: 700, color: tier.color }}>{tier.from}</div>
                    <div style={{ fontSize: 12, fontWeight: 800, color: "#eee", fontFamily: "'JetBrains Mono', monospace", background: tier.color + "22", padding: "3px 10px", borderRadius: 6 }}>
                      {tier.delta}/mo
                    </div>
                    <div style={{ fontSize: 11, color: "#e07a5f", fontFamily: "'JetBrains Mono', monospace" }}>
                      Partner COGS: {tier.partnerCostJump}
                    </div>
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 700, color: "#e07a5f", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>Why partner costs increase</div>
                      {tier.whyMore.map((w, j) => (
                        <div key={j} style={{ fontSize: 11.5, color: "#aaa", marginBottom: 3, display: "flex", gap: 6, lineHeight: 1.4 }}>
                          <span style={{ color: "#e07a5f" }}>↑</span> {w}
                        </div>
                      ))}
                    </div>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 700, color: "#57cc99", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>Value delivered to seller</div>
                      <div style={{ fontSize: 12, color: "#ccc", lineHeight: 1.6, padding: "10px 14px", background: "#57cc9908", borderRadius: 8, border: "1px solid #57cc9915" }}>
                        {tier.sellerValue}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            {/* Bottom line */}
            <div style={{ marginTop: 16, background: "linear-gradient(135deg, #ffd16608, #57cc9908)", border: "1px solid #ffd16622", borderRadius: 12, padding: "18px 22px" }}>
              <div style={{ fontSize: 11, fontWeight: 700, color: "#ffd166", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 8 }}>
                💡 The Formula
              </div>
              <div style={{ fontSize: 14, color: "#ddd", lineHeight: 1.8 }}>
                <strong style={{ color: "#eee" }}>Plan Price = Partner COGS + Infra Share + Margin</strong>
                <br /><br />
                Each tier unlocks <strong style={{ color: "#57cc99" }}>more AI calls, more images, more scraping, more WhatsApp</strong> → each of these has a real per-unit cost from the technology partner → so the COGS goes up → so the plan price goes up.
                <br /><br />
                But the <strong style={{ color: "#ffd166" }}>value to the seller grows FASTER than the cost</strong>. Starter delivers 4x ROI. Pro delivers 10-20x ROI. Growth delivers 15-30x ROI. The more they pay, the more they save — which is exactly why they'll upgrade.
                <br /><br />
                <strong style={{ color: "#eee" }}>Gross margins stay healthy across all tiers:</strong> Starter = 85%, Pro = 85%, Growth = 83%. The business is highly profitable even at MVP scale.
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
