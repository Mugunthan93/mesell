import { useState } from "react";

const PROBLEM_STATEMENTS = [
  {
    id: "catalog",
    title: "Catalog Creation & Optimization",
    severity: "HIGH",
    description: "Sellers struggle with product listing quality — poor images, weak titles, missing SEO keywords, incorrect categorization. Meesho's bulk upload templates are confusing for non-tech sellers.",
    userSegment: "New & small sellers (80% of Meesho suppliers)",
    evidence: [
      "20%+ returns caused by product expectation mismatch",
      "Catalog rejection rates high due to image/format non-compliance",
      "Manual listing = 15-30 min per SKU, unscalable"
    ],
    existingSolutions: [
      { name: "DigiCommerce", type: "Agency", price: "₹5K-20K/month", gap: "Too expensive for small sellers doing <200 orders" },
      { name: "Markzmania", type: "Agency", price: "₹3K-15K per catalog batch", gap: "One-time, no ongoing optimization" },
      { name: "EcomSarthi", type: "Agency", price: "₹15K-50K/month", gap: "Enterprise-grade, overkill for Meesho beginners" },
      { name: "Meesho's own tools", type: "Built-in", price: "Free", gap: "Basic — no AI titles, no image enhancement, no SEO" }
    ],
    solved: false,
    affordableExists: false,
    opportunityScore: 95
  },
  {
    id: "rto",
    title: "RTO & Return Reduction",
    severity: "CRITICAL",
    description: "Meesho's COD-heavy user base causes massive RTO rates (25-40%). Sellers lose shipping costs on returns. Fake delivery attempts by couriers add to losses. No pin code intelligence available to small sellers.",
    userSegment: "All sellers, especially COD-heavy categories",
    evidence: [
      "COD = 70%+ of Meesho orders → impulse buying → high RTO",
      "Sellers report 30-40% fake RTOs by courier partners",
      "₹120 minimum penalty per customer return",
      "High RTO reduces seller score → less visibility → death spiral"
    ],
    existingSolutions: [
      { name: "Shiprocket", type: "Logistics SaaS", price: "Per-shipment", gap: "Logistics only, no predictive RTO intelligence" },
      { name: "WareIQ", type: "3PL + Tech", price: "% of order value", gap: "Fulfillment-focused, not Meesho-specific" },
      { name: "Unicommerce", type: "OMS SaaS", price: "₹10K-50K/month", gap: "Multi-channel OMS, no pin code risk scoring for Meesho" },
      { name: "Manual pin code blocking", type: "DIY", price: "Free", gap: "No data, guesswork, misses good customers" }
    ],
    solved: false,
    affordableExists: false,
    opportunityScore: 92
  },
  {
    id: "pricing",
    title: "Dynamic Pricing & Margin Calculator",
    severity: "HIGH",
    description: "90% of Meesho sellers make pricing mistakes. They don't account for GST, shipping weight slabs, return costs, and ad spend. No tool gives real-time competitive pricing intelligence at Meesho scale.",
    userSegment: "All sellers, especially multi-category",
    evidence: [
      "Sellers either underprice (no profit) or overprice (no orders)",
      "Shipping weight slab jumps can eat entire margin",
      "Free calculators exist but are static — no live competitor data",
      "No tool auto-adjusts pricing based on return rate per SKU"
    ],
    existingSolutions: [
      { name: "DigiCommerce Calculator", type: "Free Tool", price: "Free", gap: "Static calculator, no competitor intelligence" },
      { name: "EcomSarthi Shipping Tool", type: "Free Tool", price: "Free", gap: "Only shipping optimization, not full pricing" },
      { name: "EcomSprint Calculator", type: "Paid Sheet", price: "₹499 one-time", gap: "Excel sheet, no automation or live data" },
      { name: "SellerApp", type: "SaaS", price: "₹2K+/month", gap: "Amazon-focused, minimal Meesho support" }
    ],
    solved: false,
    affordableExists: false,
    opportunityScore: 88
  },
  {
    id: "inventory",
    title: "Inventory & Stock Management",
    severity: "MEDIUM",
    description: "Sellers managing stock across Meesho + other platforms (Flipkart, Amazon) face overselling and stockouts. Meesho's built-in inventory is basic with no cross-platform sync.",
    userSegment: "Multi-platform sellers (growing segment)",
    evidence: [
      "Stockouts lead to cancelled orders and score drops",
      "No auto-restock alerts on Meesho supplier panel",
      "Multi-channel sellers manually update stock on each platform"
    ],
    existingSolutions: [
      { name: "Unicommerce", type: "SaaS", price: "₹10K-50K/month", gap: "Too expensive for sellers with <500 orders/month" },
      { name: "EasyEcom", type: "SaaS", price: "₹5K-25K/month", gap: "Good but still premium for Meesho's price-sensitive sellers" },
      { name: "Vinculum", type: "Enterprise SaaS", price: "₹15K+/month", gap: "Enterprise-grade, not for individual sellers" },
      { name: "Zoho Inventory", type: "SaaS", price: "₹2K+/month", gap: "No native Meesho integration" }
    ],
    solved: true,
    affordableExists: false,
    opportunityScore: 72
  },
  {
    id: "payment",
    title: "Payment Reconciliation & GST",
    severity: "MEDIUM",
    description: "Meesho's 7-day payment cycle with various deductions (GST on shipping, ad charges, return adjustments) makes it hard for sellers to track actual earnings. ITC claims are complex.",
    userSegment: "All GST-registered sellers",
    evidence: [
      "Sellers can't easily match settlements to individual orders",
      "GST ITC on shipping fee requires cross-referencing GSTR-2B",
      "No automated profit/loss per SKU tracking",
      "Manual reconciliation takes 2-4 hours/week for active sellers"
    ],
    existingSolutions: [
      { name: "Unicommerce", type: "SaaS", price: "₹10K+/month", gap: "Has reconciliation but bundled with full OMS — overkill" },
      { name: "Tally + Manual", type: "DIY", price: "₹5K+/year", gap: "Manual data entry, error-prone, no Meesho API" },
      { name: "CA/Accountant", type: "Service", price: "₹2K-5K/month", gap: "Monthly, not real-time; no per-SKU insights" }
    ],
    solved: false,
    affordableExists: false,
    opportunityScore: 78
  },
  {
    id: "quality",
    title: "Pre-upload Quality Checks",
    severity: "HIGH",
    description: "Catalog rejections waste time. Image compliance (1024×1024, white background, no watermarks), description quality, and attribute accuracy are not validated before upload.",
    userSegment: "New sellers and bulk uploaders",
    evidence: [
      "First-time sellers face 40-60% catalog rejection rate",
      "Re-submission cycle adds 2-5 days per catalog",
      "No tool pre-validates against Meesho's specific format rules",
      "Image non-compliance is the #1 rejection reason"
    ],
    existingSolutions: [
      { name: "EcomSarthi Image Tool", type: "Free Tool", price: "Free", gap: "Image-only, no description/attribute validation" },
      { name: "Canva / PhotoRoom", type: "Generic Tool", price: "Free-₹1K/month", gap: "General image editing, not Meesho-compliant output" },
      { name: "Agency services", type: "Agency", price: "₹500-2K/catalog", gap: "Per-catalog cost adds up fast for scaling sellers" }
    ],
    solved: false,
    affordableExists: false,
    opportunityScore: 85
  }
];

const severityColor = { CRITICAL: "#ff4444", HIGH: "#ff8c42", MEDIUM: "#ffd166" };
const severityBg = { CRITICAL: "#ff444418", HIGH: "#ff8c4218", MEDIUM: "#ffd16618" };

function OpportunityBar({ score }) {
  const color = score >= 90 ? "#57cc99" : score >= 80 ? "#48bfe3" : score >= 70 ? "#ffd166" : "#aaa";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
      <div style={{ flex: 1, height: 8, background: "rgba(255,255,255,0.06)", borderRadius: 4, overflow: "hidden" }}>
        <div style={{ width: `${score}%`, height: "100%", background: color, borderRadius: 4, transition: "width 0.6s ease" }} />
      </div>
      <span style={{ fontSize: 13, fontWeight: 700, color, fontFamily: "'JetBrains Mono', monospace", minWidth: 30 }}>{score}</span>
    </div>
  );
}

function ProblemCard({ problem, isExpanded, onToggle }) {
  return (
    <div
      style={{
        background: isExpanded ? "rgba(255,255,255,0.04)" : "rgba(255,255,255,0.02)",
        border: `1px solid ${isExpanded ? "rgba(255,255,255,0.12)" : "rgba(255,255,255,0.06)"}`,
        borderRadius: 12,
        transition: "all 0.3s",
        overflow: "hidden",
      }}
    >
      <div
        onClick={onToggle}
        style={{
          padding: "16px 20px",
          cursor: "pointer",
          display: "flex",
          alignItems: "center",
          gap: 14,
        }}
      >
        <span style={{
          fontSize: 10, fontWeight: 700, letterSpacing: "0.08em",
          padding: "3px 8px", borderRadius: 4,
          background: severityBg[problem.severity],
          color: severityColor[problem.severity],
          fontFamily: "'JetBrains Mono', monospace",
        }}>
          {problem.severity}
        </span>
        <span style={{ flex: 1, fontSize: 15, fontWeight: 600, color: "#e0e0e0", fontFamily: "'DM Sans', sans-serif" }}>
          {problem.title}
        </span>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          {!problem.affordableExists && (
            <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 4, background: "#57cc9920", color: "#57cc99", fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>
              NO AFFORDABLE SOLUTION
            </span>
          )}
          {!problem.solved && (
            <span style={{ fontSize: 10, padding: "2px 8px", borderRadius: 4, background: "#ff444420", color: "#ff6b6b", fontWeight: 600, fontFamily: "'JetBrains Mono', monospace" }}>
              UNSOLVED
            </span>
          )}
        </div>
        <span style={{ fontSize: 18, color: "#666", transition: "transform 0.3s", transform: isExpanded ? "rotate(180deg)" : "rotate(0)" }}>▾</span>
      </div>

      {isExpanded && (
        <div style={{ padding: "0 20px 20px", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
          <p style={{ color: "#aaa", fontSize: 13, lineHeight: 1.6, margin: "14px 0", fontFamily: "'DM Sans', sans-serif" }}>
            {problem.description}
          </p>
          <div style={{ fontSize: 11, color: "#888", marginBottom: 12, fontFamily: "'JetBrains Mono', monospace" }}>
            TARGET: {problem.userSegment}
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#7b68ee", letterSpacing: "0.06em", marginBottom: 8, textTransform: "uppercase" }}>Evidence</div>
            {problem.evidence.map((e, i) => (
              <div key={i} style={{ display: "flex", gap: 8, marginBottom: 5, fontSize: 12, color: "#bbb", lineHeight: 1.5, fontFamily: "'DM Sans', sans-serif" }}>
                <span style={{ color: "#7b68ee", minWidth: 8 }}>→</span>
                {e}
              </div>
            ))}
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#e07a5f", letterSpacing: "0.06em", marginBottom: 8, textTransform: "uppercase" }}>Existing Solutions & Gaps</div>
            <div style={{ display: "grid", gap: 8 }}>
              {problem.existingSolutions.map((s, i) => (
                <div key={i} style={{ display: "grid", gridTemplateColumns: "140px 90px 100px 1fr", gap: 8, alignItems: "start", fontSize: 12, padding: "8px 12px", background: "rgba(255,255,255,0.02)", borderRadius: 8 }}>
                  <div style={{ color: "#ddd", fontWeight: 600, fontFamily: "'DM Sans', sans-serif" }}>{s.name}</div>
                  <div style={{ color: "#888", fontFamily: "'JetBrains Mono', monospace", fontSize: 10 }}>{s.type}</div>
                  <div style={{ color: "#ffd166", fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{s.price}</div>
                  <div style={{ color: "#e07a5f", fontSize: 11, fontFamily: "'DM Sans', sans-serif" }}>⚠ {s.gap}</div>
                </div>
              ))}
            </div>
          </div>

          <div>
            <div style={{ fontSize: 11, fontWeight: 700, color: "#57cc99", letterSpacing: "0.06em", marginBottom: 8, textTransform: "uppercase" }}>Opportunity Score</div>
            <OpportunityBar score={problem.opportunityScore} />
          </div>
        </div>
      )}
    </div>
  );
}

export default function MeeshoRnD() {
  const [expanded, setExpanded] = useState(new Set(["catalog"]));
  const [filter, setFilter] = useState("all");

  const toggle = (id) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const filtered = PROBLEM_STATEMENTS
    .filter((p) => {
      if (filter === "unsolved") return !p.solved;
      if (filter === "noaffordable") return !p.affordableExists;
      if (filter === "critical") return p.severity === "CRITICAL" || p.severity === "HIGH";
      return true;
    })
    .sort((a, b) => b.opportunityScore - a.opportunityScore);

  const topOpportunities = [...PROBLEM_STATEMENTS].sort((a, b) => b.opportunityScore - a.opportunityScore).slice(0, 3);

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d10", color: "#e0e0e0", fontFamily: "'DM Sans', sans-serif", padding: "28px 24px 50px" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Playfair+Display:wght@700;800&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{ maxWidth: 960, margin: "0 auto 28px" }}>
        <div style={{ fontSize: 10, letterSpacing: "0.15em", color: "#7b68ee", textTransform: "uppercase", fontWeight: 600, marginBottom: 6 }}>
          R&D · Market Gap Analysis
        </div>
        <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: 28, fontWeight: 800, margin: "0 0 8px", color: "#eee" }}>
          Meesho Supplier Portal
        </h1>
        <p style={{ color: "#777", fontSize: 14, margin: 0, maxWidth: 600, lineHeight: 1.5 }}>
          Problem statements, existing solutions, pricing gaps, and opportunity scoring for building an affordable SaaS targeting Meesho's 400K+ active suppliers.
        </p>
      </div>

      {/* Summary Cards */}
      <div style={{ maxWidth: 960, margin: "0 auto 24px", display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12 }}>
        {[
          { label: "Problem Areas", value: PROBLEM_STATEMENTS.length, color: "#7b68ee" },
          { label: "Unsolved", value: PROBLEM_STATEMENTS.filter(p => !p.solved).length, color: "#ff6b6b" },
          { label: "No Affordable Tool", value: PROBLEM_STATEMENTS.filter(p => !p.affordableExists).length, color: "#ffd166" },
          { label: "Top Opportunity", value: topOpportunities[0]?.opportunityScore, color: "#57cc99" },
        ].map((card, i) => (
          <div key={i} style={{
            background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.06)",
            borderRadius: 10, padding: "14px 16px", textAlign: "center"
          }}>
            <div style={{ fontSize: 24, fontWeight: 800, color: card.color, fontFamily: "'JetBrains Mono', monospace" }}>{card.value}</div>
            <div style={{ fontSize: 10, color: "#666", letterSpacing: "0.06em", textTransform: "uppercase", marginTop: 4 }}>{card.label}</div>
          </div>
        ))}
      </div>

      {/* Top 3 Opportunities */}
      <div style={{ maxWidth: 960, margin: "0 auto 24px" }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "#57cc99", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>
          🎯 Top 3 Opportunity Zones
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
          {topOpportunities.map((p, i) => (
            <div key={p.id} style={{
              background: i === 0 ? "linear-gradient(135deg, #57cc9910, #48bfe310)" : "rgba(255,255,255,0.02)",
              border: `1px solid ${i === 0 ? "#57cc9933" : "rgba(255,255,255,0.06)"}`,
              borderRadius: 10, padding: "14px 16px"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 6 }}>
                <span style={{ fontSize: 18, fontWeight: 800, color: i === 0 ? "#57cc99" : "#888", fontFamily: "'JetBrains Mono', monospace" }}>#{i + 1}</span>
                <span style={{ fontSize: 12, fontWeight: 700, color: i === 0 ? "#57cc99" : "#aaa", fontFamily: "'JetBrains Mono', monospace" }}>{p.opportunityScore}/100</span>
              </div>
              <div style={{ fontSize: 13, fontWeight: 600, color: "#ddd", marginBottom: 4 }}>{p.title}</div>
              <div style={{ fontSize: 11, color: "#888", lineHeight: 1.4 }}>
                {p.solved ? "Solved but expensive" : "Unsolved"} · {p.affordableExists ? "Affordable exists" : "No affordable tool"}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Filters */}
      <div style={{ maxWidth: 960, margin: "0 auto 16px", display: "flex", gap: 8 }}>
        {[
          { key: "all", label: "All Problems" },
          { key: "unsolved", label: "Unsolved" },
          { key: "noaffordable", label: "No Affordable Solution" },
          { key: "critical", label: "High / Critical" },
        ].map((f) => (
          <button
            key={f.key}
            onClick={() => setFilter(f.key)}
            style={{
              padding: "7px 14px", fontSize: 12, fontWeight: 600,
              borderRadius: 8, cursor: "pointer",
              fontFamily: "'DM Sans', sans-serif",
              background: filter === f.key ? "#7b68ee22" : "rgba(255,255,255,0.03)",
              border: `1px solid ${filter === f.key ? "#7b68ee44" : "rgba(255,255,255,0.06)"}`,
              color: filter === f.key ? "#b8b0ff" : "#888",
              transition: "all 0.2s",
            }}
          >
            {f.label}
          </button>
        ))}
      </div>

      {/* Problem List */}
      <div style={{ maxWidth: 960, margin: "0 auto", display: "flex", flexDirection: "column", gap: 10 }}>
        {filtered.map((p) => (
          <ProblemCard
            key={p.id}
            problem={p}
            isExpanded={expanded.has(p.id)}
            onToggle={() => toggle(p.id)}
          />
        ))}
      </div>

      {/* Bottom Insight */}
      <div style={{
        maxWidth: 960, margin: "32px auto 0",
        background: "linear-gradient(135deg, #7b68ee10, #57cc9910)",
        border: "1px solid #7b68ee22",
        borderRadius: 12, padding: "20px 24px"
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "#7b68ee", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 8 }}>
          💡 Key Insight
        </div>
        <p style={{ fontSize: 14, color: "#ccc", lineHeight: 1.7, margin: 0 }}>
          <strong style={{ color: "#eee" }}>The gap is clear:</strong> Existing solutions are either free-but-basic (Meesho's own tools, static calculators) or premium-but-overkill (₹10K-50K/month agency/SaaS aimed at multi-channel D2C brands). There is <strong style={{ color: "#57cc99" }}>no affordable AI-powered SaaS (₹499-1999/month range)</strong> built specifically for Meesho's 400K+ small suppliers who need catalog optimization, RTO prediction, smart pricing, and payment reconciliation — all in one place.
        </p>
      </div>
    </div>
  );
}
