import { useState } from "react";

const PROBLEMS = [
  {
    id: "catalog",
    title: "Catalog Creation & Optimization",
    severity: "HIGH", score: 95, status: "DEEP-DIVED",
    oneLiner: "No all-in-one AI tool for Meesho catalog at ₹500-2K/mo",
    approaches: [
      { type: "Premium Agency", players: "EcomSarthi, DigiCommerce, Seller Rocket", price: "₹8K–50K/mo", meeshoFit: "✓", gap: "Too expensive for small sellers" },
      { type: "Budget Agency", players: "Cruzen Digital, Technovita, OMM Digital", price: "₹2.5K–10K/mo", meeshoFit: "✓", gap: "Manual, no AI, slow" },
      { type: "Local/IndiaMART", players: "W2G Solutions, Uptech E-Com, local shops", price: "₹200/catalog–₹5K/yr", meeshoFit: "✓", gap: "Rock-bottom quality, copy-paste" },
      { type: "Freelancers", players: "Fiverr, Freelancer.com, Upwork", price: "₹300–3K/catalog", meeshoFit: "~", gap: "Inconsistent, no scale" },
      { type: "AI Text SaaS", players: "ListIQ, Sellermitra, DigiCommerce AI", price: "Free–₹500/mo", meeshoFit: "✓", gap: "TEXT ONLY — no images, no upload, no validation" },
      { type: "AI Image Tools", players: "PhotoRoom, Pixelcut, Remove.bg, Canva", price: "₹500–1K/mo", meeshoFit: "✗", gap: "Generic, no Meesho format, no text" },
      { type: "Multi-channel SaaS", players: "Unicommerce, Vinculum, EasyEcom", price: "₹5K–50K/mo", meeshoFit: "✓", gap: "Overkill OMS, catalog is minor feature" },
      { type: "Global AI Tools", players: "SellerApp, Helium 10, Jungle Scout", price: "₹2.4K–19K/mo", meeshoFit: "✗", gap: "Amazon-only, USD pricing" },
      { type: "Meesho Built-in", players: "Supplier Panel, Bulk CSV, Price Recommender", price: "Free", meeshoFit: "✓", gap: "No AI, no SEO, no image enhancement" },
    ],
    whitespace: "All-in-one: AI text + AI images + compliance check + Meesho export → ₹499-1,999/mo"
  },
  {
    id: "rto",
    title: "RTO & Return Reduction",
    severity: "CRITICAL", score: 92, status: "MAPPED",
    oneLiner: "RTO tools exist for D2C (₹10K+/mo) but ZERO for marketplace sellers like Meesho",
    approaches: [
      { type: "D2C RTO Suite", players: "Pragma (RTO Suite + 1Checkout)", price: "Custom (₹10K+/mo est.)", meeshoFit: "✗", gap: "Built for D2C checkout, not marketplace sellers" },
      { type: "AI Checkout Optimizer", players: "GoKwik", price: "Custom / % of GMV", meeshoFit: "✗", gap: "Shopify/D2C checkout — Meesho controls its own checkout" },
      { type: "Logistics + RTO", players: "Shiprocket (CORE engine), Delhivery RTO Predictor", price: "Per-shipment", meeshoFit: "~", gap: "Meesho handles its own logistics — sellers can't choose courier" },
      { type: "Courier Aggregator", players: "OrderzUp, iThink Logistics, Bombax", price: "Per-shipment", meeshoFit: "✗", gap: "Can't plug into Meesho's locked logistics" },
      { type: "Pin Code Blockers", players: "Manual seller lists, Shopify plugins", price: "Free–₹1K/mo", meeshoFit: "✗", gap: "Meesho doesn't allow sellers to block pin codes" },
      { type: "Free Tools", players: "EcomSarthi shipping reducer", price: "Free", meeshoFit: "✓", gap: "Shipping cost optimizer only, not RTO prediction" },
      { type: "Meesho Built-in", players: "Return dashboard, NDD program", price: "Free", meeshoFit: "✓", gap: "Reactive — shows returns AFTER they happen, no prediction" },
    ],
    whitespace: "Pin code risk intelligence + product-level return analytics + listing quality correlation → ₹499-999/mo. Can't control logistics, but CAN predict which SKUs/categories to avoid or fix."
  },
  {
    id: "pricing",
    title: "Dynamic Pricing & Margin Intelligence",
    severity: "HIGH", score: 88, status: "MAPPED",
    oneLiner: "Free static calculators exist, but no LIVE competitive pricing intelligence for Meesho",
    approaches: [
      { type: "Free Calculators", players: "DigiCommerce, Shiprocket, SellerShip, Ginesys", price: "Free", meeshoFit: "✓", gap: "Static — input-output, no live data, no competitor tracking" },
      { type: "Paid Calculator Sheet", players: "EcomSprint Calculator (Excel)", price: "₹499 one-time", meeshoFit: "✓", gap: "Offline Excel, no automation" },
      { type: "Meesho-specific SaaS", players: "VariantStudio (P&L tracker + shipping optimizer)", price: "Free to start", meeshoFit: "✓", gap: "NEW — P&L + Tally XML focus, no competitor intelligence" },
      { type: "All-in-one Free Tools", players: "SellerShip.in (15+ tools)", price: "Free (paid AI coming)", meeshoFit: "✓", gap: "Free tools live, AI features still 'Notify Me' — not launched" },
      { type: "Enterprise Pricing AI", players: "Flipkart Commerce Cloud, Prisync", price: "$99+/mo", meeshoFit: "✗", gap: "Enterprise pricing, not for Meesho small sellers" },
      { type: "Data Scraping", players: "Product Data Scrape (custom)", price: "Custom ($$$)", meeshoFit: "~", gap: "Custom project, not a SaaS tool" },
      { type: "Agency Service", players: "EcomSarthi, Gonukkad", price: "₹15K+/mo", meeshoFit: "✓", gap: "Manual pricing strategy, not automated tool" },
      { type: "Meesho Built-in", players: "Price Recommendation tool", price: "Free", meeshoFit: "✓", gap: "Basic suggestions, no per-SKU margin tracking, no return-cost factoring" },
    ],
    whitespace: "Live competitive price tracker + auto margin calculator (factoring returns, weight slabs, ads) + per-SKU P&L → ₹499-999/mo"
  },
  {
    id: "quality",
    title: "Pre-upload Quality Checks",
    severity: "HIGH", score: 85, status: "MAPPED",
    oneLiner: "40-60% first-time catalog rejection. No tool validates BEFORE upload.",
    approaches: [
      { type: "Image Compliance Tool", players: "EcomSarthi (1024×1024 white BG generator)", price: "Free", meeshoFit: "✓", gap: "Image-only, no title/description/attribute validation" },
      { type: "Generic Image Editor", players: "Canva, PhotoRoom, Pixelcut", price: "Free–₹1K/mo", meeshoFit: "✗", gap: "General purpose, no Meesho format rules built in" },
      { type: "VariantStudio", players: "VariantStudio.in (duplicate detection)", price: "Free to start", meeshoFit: "✓", gap: "Variant + duplicate check, but no full compliance suite" },
      { type: "SellerShip (coming)", players: "SellerShip.in (AI validation — not launched)", price: "TBD", meeshoFit: "✓", gap: "Still in 'Notify Me' stage — vaporware risk" },
      { type: "Agency QC", players: "All listing agencies do manual QC", price: "Bundled in ₹3K+/mo", meeshoFit: "✓", gap: "Human QC — slow, expensive, doesn't scale" },
      { type: "Meesho Built-in", players: "Post-upload rejection with error codes", price: "Free", meeshoFit: "✓", gap: "Tells you AFTER rejection — wastes 2-5 days per cycle" },
    ],
    whitespace: "Pre-upload validator: image specs + title rules + category mapping + attribute completeness → instant pass/fail BEFORE submitting. Can be a feature inside catalog tool."
  },
  {
    id: "payment",
    title: "Payment Reconciliation & GST",
    severity: "MEDIUM", score: 78, status: "MAPPED",
    oneLiner: "Specialized tools emerging but priced for mid-market (₹3K+/mo). Small sellers use Excel.",
    approaches: [
      { type: "Meesho-specific SaaS", players: "VariantStudio (Tally XML + P&L)", price: "Free to start", meeshoFit: "✓", gap: "Good start — Tally XML export, but no bank reconciliation" },
      { type: "Reconciliation SaaS", players: "ReconPe (AI matching), Recarya (cloud recon)", price: "₹2K–10K/mo (est.)", meeshoFit: "✓", gap: "Good for mid-market, may be overkill for <500 orders/mo" },
      { type: "Accounting Software", players: "Zoho Books, Tally Prime, Vyapar", price: "₹500–3K/mo", meeshoFit: "~", gap: "General accounting — no native Meesho settlement parsing" },
      { type: "GST Tools", players: "TaxBuddy, ClearTax, GST Tool", price: "₹500–5K/mo", meeshoFit: "~", gap: "GST filing focus, no per-SKU marketplace reconciliation" },
      { type: "CA/Accountant", players: "Freelance CAs, Patron Accounting", price: "₹2K–8K/mo", meeshoFit: "✓", gap: "Monthly, not real-time. Manual. Expensive for small sellers" },
      { type: "Multi-channel OMS", players: "Unicommerce, Vinculum (payment recon module)", price: "₹10K+/mo", meeshoFit: "✓", gap: "Bundled with full OMS — overkill" },
      { type: "Free Tools", players: "SellerShip (GST report + invoice generator)", price: "Free", meeshoFit: "✓", gap: "Basic reports, no full reconciliation" },
      { type: "Meesho Built-in", players: "Payment section in supplier panel", price: "Free", meeshoFit: "✓", gap: "Shows settlements but no per-SKU P&L, no auto ITC tracking" },
    ],
    whitespace: "Auto-parse Meesho settlement → per-SKU P&L → GST ITC tracking → Tally/Zoho export. Feature in unified platform, not standalone."
  },
  {
    id: "inventory",
    title: "Inventory & Stock Management",
    severity: "MEDIUM", score: 72, status: "MAPPED",
    oneLiner: "Solved by Unicommerce/EasyEcom at ₹5K+/mo. No affordable Meesho-first option.",
    approaches: [
      { type: "Multi-channel OMS", players: "Unicommerce, EasyEcom, Vinculum, Browntape", price: "₹3K–50K/mo", meeshoFit: "✓", gap: "Good solutions but expensive for Meesho-only sellers" },
      { type: "Generic Inventory", players: "Zoho Inventory, Sortly", price: "₹1K–3K/mo", meeshoFit: "✗", gap: "No native Meesho integration" },
      { type: "Meesho Built-in", players: "Stock management in supplier panel", price: "Free", meeshoFit: "✓", gap: "Basic — no forecasting, no multi-platform sync, no alerts" },
      { type: "Spreadsheet", players: "Excel/Google Sheets (manual)", price: "Free", meeshoFit: "~", gap: "Manual, error-prone, doesn't scale past 100 SKUs" },
    ],
    whitespace: "Lower priority — include basic stock alerts as a feature, not core differentiator. Multi-channel sync only if seller also sells on Flipkart/Amazon."
  },
];

const sevColors = { CRITICAL: "#ff4444", HIGH: "#ff8c42", MEDIUM: "#ffd166" };

function MiniBar({ score }) {
  const c = score >= 90 ? "#57cc99" : score >= 80 ? "#48bfe3" : "#ffd166";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 80 }}>
      <div style={{ flex: 1, height: 6, background: "rgba(255,255,255,0.06)", borderRadius: 3 }}>
        <div style={{ width: `${score}%`, height: "100%", background: c, borderRadius: 3 }} />
      </div>
      <span style={{ fontSize: 11, fontWeight: 700, color: c, fontFamily: "'JetBrains Mono', monospace" }}>{score}</span>
    </div>
  );
}

export default function AllProblemsMap() {
  const [expanded, setExpanded] = useState(new Set(["rto"]));

  const toggle = (id) => setExpanded(p => {
    const n = new Set(p); n.has(id) ? n.delete(id) : n.add(id); return n;
  });

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d10", color: "#e0e0e0", fontFamily: "'DM Sans', sans-serif", padding: "28px 20px 50px" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Playfair+Display:wght@700;800&display=swap" rel="stylesheet" />

      <div style={{ maxWidth: 1020, margin: "0 auto 20px" }}>
        <div style={{ fontSize: 10, letterSpacing: "0.15em", color: "#7b68ee", textTransform: "uppercase", fontWeight: 600, marginBottom: 6 }}>
          R&D Complete Map · All Problem Statements
        </div>
        <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: 26, fontWeight: 800, margin: "0 0 6px", color: "#eee" }}>
          Meesho Supplier Portal — 6 Problems, 50+ Solutions, 1 Gap
        </h1>
        <p style={{ color: "#777", fontSize: 13, margin: 0, lineHeight: 1.5 }}>
          Every problem, every existing approach, exact pricing, and the whitespace that remains.
        </p>
      </div>

      {/* Emerging competitors callout */}
      <div style={{ maxWidth: 1020, margin: "0 auto 18px", background: "#ff8c4210", border: "1px solid #ff8c4222", borderRadius: 10, padding: "14px 18px" }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "#ff8c42", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>
          ⚠️ Emerging Competitors Spotted
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 12, fontSize: 12, color: "#bbb", lineHeight: 1.5 }}>
          <div>
            <span style={{ color: "#ffd166", fontWeight: 700 }}>VariantStudio.in</span> — Meesho-specific. Image variants + Tally XML + P&L. Free to start. Live product, growing.
          </div>
          <div>
            <span style={{ color: "#ffd166", fontWeight: 700 }}>SellerShip.in</span> — 15+ free tools (calculators, image). AI catalog + validation = "coming soon" (not launched). Early adopter pricing.
          </div>
          <div>
            <span style={{ color: "#ffd166", fontWeight: 700 }}>ListIQ.in</span> — AI listing text for Meesho/Amazon/Flipkart. Credit-based from ₹49. 10K+ sellers. Text only.
          </div>
        </div>
      </div>

      {/* Summary row */}
      <div style={{ maxWidth: 1020, margin: "0 auto 16px", display: "grid", gridTemplateColumns: "repeat(6, 1fr)", gap: 8 }}>
        {PROBLEMS.map(p => (
          <div key={p.id} onClick={() => toggle(p.id)} style={{
            background: expanded.has(p.id) ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.02)",
            border: `1px solid ${expanded.has(p.id) ? "#7b68ee33" : "rgba(255,255,255,0.05)"}`,
            borderRadius: 10, padding: "12px", cursor: "pointer", transition: "all 0.2s"
          }}>
            <div style={{ fontSize: 9, fontWeight: 700, color: sevColors[p.severity], letterSpacing: "0.06em", marginBottom: 4 }}>{p.severity}</div>
            <div style={{ fontSize: 11, fontWeight: 600, color: "#ddd", marginBottom: 6, lineHeight: 1.3 }}>{p.title}</div>
            <MiniBar score={p.score} />
          </div>
        ))}
      </div>

      {/* Problem details */}
      <div style={{ maxWidth: 1020, margin: "0 auto", display: "flex", flexDirection: "column", gap: 8 }}>
        {PROBLEMS.map(p => {
          const open = expanded.has(p.id);
          return (
            <div key={p.id} style={{
              background: open ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.015)",
              border: `1px solid ${open ? sevColors[p.severity] + "33" : "rgba(255,255,255,0.05)"}`,
              borderRadius: 12, overflow: "hidden"
            }}>
              <div onClick={() => toggle(p.id)} style={{ padding: "14px 18px", cursor: "pointer", display: "flex", alignItems: "center", gap: 12 }}>
                <span style={{ fontSize: 10, fontWeight: 700, padding: "3px 8px", borderRadius: 4, background: sevColors[p.severity] + "18", color: sevColors[p.severity], fontFamily: "'JetBrains Mono', monospace" }}>
                  {p.severity}
                </span>
                <span style={{ flex: 1, fontSize: 14, fontWeight: 600, color: "#ddd" }}>{p.title}</span>
                <span style={{ fontSize: 11, color: "#888", fontFamily: "'JetBrains Mono', monospace" }}>{p.approaches.length} approaches</span>
                <MiniBar score={p.score} />
                <span style={{ fontSize: 16, color: "#555", transition: "transform 0.3s", transform: open ? "rotate(180deg)" : "rotate(0)" }}>▾</span>
              </div>

              {open && (
                <div style={{ padding: "0 18px 18px", borderTop: "1px solid rgba(255,255,255,0.04)" }}>
                  {/* One-liner */}
                  <div style={{ fontSize: 13, color: "#48bfe3", fontWeight: 600, margin: "12px 0 14px", lineHeight: 1.5 }}>
                    💡 {p.oneLiner}
                  </div>

                  {/* Approaches table */}
                  <div style={{ fontSize: 10, fontWeight: 700, color: "#888", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 6 }}>
                    Solution Approaches in Market
                  </div>
                  <div style={{ display: "grid", gap: 3, marginBottom: 14 }}>
                    {/* Header */}
                    <div style={{ display: "grid", gridTemplateColumns: "140px 1fr 120px 40px 1fr", gap: 8, padding: "6px 10px", fontSize: 9, color: "#666", fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase" }}>
                      <span>Type</span><span>Players</span><span>Price</span><span>Fit</span><span>Gap</span>
                    </div>
                    {p.approaches.map((a, i) => (
                      <div key={i} style={{
                        display: "grid", gridTemplateColumns: "140px 1fr 120px 40px 1fr",
                        gap: 8, padding: "7px 10px", fontSize: 11.5, alignItems: "start",
                        background: i % 2 === 0 ? "rgba(255,255,255,0.015)" : "transparent", borderRadius: 6
                      }}>
                        <span style={{ color: "#ccc", fontWeight: 600 }}>{a.type}</span>
                        <span style={{ color: "#999", fontSize: 11 }}>{a.players}</span>
                        <span style={{ color: "#ffd166", fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", fontSize: 10.5 }}>{a.price}</span>
                        <span style={{ fontSize: 12 }}>{a.meeshoFit}</span>
                        <span style={{ color: "#e07a5f", fontSize: 11 }}>{a.gap}</span>
                      </div>
                    ))}
                  </div>

                  {/* Whitespace */}
                  <div style={{ background: "#57cc9908", border: "1px solid #57cc9920", borderRadius: 8, padding: "10px 14px" }}>
                    <span style={{ fontSize: 10, fontWeight: 700, color: "#57cc99", letterSpacing: "0.06em", textTransform: "uppercase" }}>✅ WHITESPACE: </span>
                    <span style={{ fontSize: 12, color: "#ccc", lineHeight: 1.5 }}>{p.whitespace}</span>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Final unified insight */}
      <div style={{
        maxWidth: 1020, margin: "28px auto 0",
        background: "linear-gradient(135deg, #7b68ee08, #57cc9908)",
        border: "1px solid #7b68ee22", borderRadius: 12, padding: "22px 24px"
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "#7b68ee", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>
          🏗️ Unified Architecture Signal
        </div>
        <p style={{ fontSize: 14, color: "#ddd", lineHeight: 1.7, margin: "0 0 14px" }}>
          Across all 6 problems, <strong style={{ color: "#57cc99" }}>the same pattern repeats:</strong> solutions exist at ₹0 (basic/free) or ₹5K+ (agency/enterprise). 
          The ₹499–1,999/month zone is either empty or fragmented into single-feature tools.
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#7b68ee", marginBottom: 6 }}>Shared Infrastructure Across Problems:</div>
            <div style={{ fontSize: 12, color: "#aaa", lineHeight: 1.6 }}>
              → Meesho data pipeline (orders, returns, settlements)<br />
              → AI backbone (LLM for text, Vision for images)<br />
              → Seller dashboard (one login, unified view)<br />
              → Per-SKU analytics engine (connects catalog → pricing → returns → P&L)
            </div>
          </div>
          <div>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#57cc99", marginBottom: 6 }}>Nearest Competitors to Watch:</div>
            <div style={{ fontSize: 12, color: "#aaa", lineHeight: 1.6 }}>
              → <strong>VariantStudio</strong> — closest (Meesho-first, free, growing)<br />
              → <strong>SellerShip</strong> — ambitious roadmap but AI not live yet<br />
              → <strong>ListIQ</strong> — AI text only, credit-based, 10K users<br />
              → <strong>Unicommerce</strong> — enterprise OMS, wrong segment
            </div>
          </div>
        </div>
        <div style={{ marginTop: 16, padding: "14px 16px", background: "rgba(255,255,255,0.03)", borderRadius: 8, textAlign: "center" }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: "#eee", marginBottom: 4 }}>
            Ready for the next step: Unified Solution Architecture
          </div>
          <div style={{ fontSize: 12, color: "#888" }}>
            One platform. 6 problems. Modular features. ₹499–1,999/month. Meesho-first.
          </div>
        </div>
      </div>
    </div>
  );
}
