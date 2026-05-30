import { useState } from "react";

const APPROACHES = [
  {
    id: "agency-premium",
    category: "Full-Service Agency",
    approach: "Managed Catalog Service (Premium)",
    players: [
      { name: "EcomSarthi", price: "₹15,000–50,000/mo", model: "Monthly retainer", meesho: true },
      { name: "DigiCommerce", price: "₹10,000–30,000/mo", model: "Monthly retainer", meesho: true },
      { name: "Seller Rocket", price: "₹10,000–25,000/mo", model: "Monthly retainer", meesho: true },
      { name: "Novel Web Solution", price: "₹8,000–20,000/mo", model: "Monthly retainer", meesho: true },
    ],
    whatTheyDo: "End-to-end catalog management — creation, SEO optimization, image editing, pricing strategy, ad management, returns handling, weekly analytics reports. Dedicated account manager assigned.",
    strengths: ["Human-quality output", "Complete hands-off for seller", "Includes ads + pricing + catalog holistically", "Relationship with marketplace SPNs"],
    weaknesses: ["Extremely expensive for small sellers", "Minimum 3-month lock-in typical", "Doesn't scale linearly — more SKUs = more cost", "Overkill for sellers doing <200 orders/month"],
    targetUser: "D2C brands, high-volume sellers (500+ orders/month)",
    priceRange: "₹8K–50K/month",
    affordableForSmall: false,
  },
  {
    id: "agency-budget",
    category: "Budget Agency",
    approach: "Catalog Listing Service (Budget)",
    players: [
      { name: "Cruzen Digital", price: "₹3,999–7,999/mo", model: "Tiered plans", meesho: true },
      { name: "Technovita Solution", price: "₹3,000–10,000/mo", model: "Per project", meesho: true },
      { name: "OMM Digital", price: "₹2,500–8,000/mo", model: "Per project", meesho: true },
      { name: "Ecom Advisors", price: "₹3,000–7,000/mo", model: "Monthly retainer", meesho: true },
      { name: "InfoBeam Solutions", price: "Custom quotes", model: "Per project", meesho: true },
    ],
    whatTheyDo: "Catalog creation, bulk upload, basic SEO titles, image formatting, category mapping. Standard/Premium tiers with fixed SKU limits per month.",
    strengths: ["Cheaper than premium agencies", "Know Meesho-specific guidelines", "Handle bulk uploads", "Good for initial catalog setup"],
    weaknesses: ["Quality varies wildly", "No AI or automation — pure manual labor", "No ongoing optimization after upload", "No analytics or performance tracking", "Slow turnaround (2-5 days per catalog)"],
    targetUser: "New sellers, small manufacturers launching on Meesho",
    priceRange: "₹2.5K–10K/month",
    affordableForSmall: false,
  },
  {
    id: "indiamart-local",
    category: "IndiaMART / Local Services",
    approach: "Local Listing Shops & IndiaMART Providers",
    players: [
      { name: "W2G Solutions (Delhi)", price: "₹5,000/year", model: "Annual plan", meesho: true },
      { name: "Uptech E-Com (Dhanbad)", price: "₹1,999–3,499/mo", model: "Bronze/Silver/Gold", meesho: true },
      { name: "Local shops (various)", price: "₹200–500/catalog", model: "Per catalog", meesho: true },
    ],
    whatTheyDo: "Basic catalog upload — seller provides product photos and details, they format and upload to Meesho supplier panel. Often run from small towns, listed on IndiaMART.",
    strengths: ["Cheapest human option", "Available in tier-2/3 cities", "Simple per-catalog pricing", "No tech barrier"],
    weaknesses: ["Rock-bottom quality — copy-paste titles, no SEO", "No image enhancement", "No compliance checks — high rejection rates", "Zero optimization or follow-up", "No scalability"],
    targetUser: "First-time sellers who don't understand the panel",
    priceRange: "₹200/catalog – ₹5K/year",
    affordableForSmall: true,
  },
  {
    id: "freelancer",
    category: "Freelancer Marketplace",
    approach: "Fiverr / Freelancer / Upwork Gigs",
    players: [
      { name: "Fiverr gigs", price: "₹500–3,000/catalog", model: "Per catalog/batch", meesho: true },
      { name: "Freelancer.com", price: "₹300–2,000/project", model: "Per project", meesho: true },
      { name: "Upwork", price: "$5–20/hr", model: "Hourly/project", meesho: false },
    ],
    whatTheyDo: "Individual freelancers who list products, write descriptions, do basic image editing. Quality depends entirely on the person hired.",
    strengths: ["Pay per task — no commitment", "Can find good talent occasionally", "Flexible scope"],
    weaknesses: ["Extremely inconsistent quality", "No Meesho-specific expertise guaranteed", "Communication overhead", "No bulk/ongoing workflow", "Seller has to QC everything themselves"],
    targetUser: "Occasional sellers needing one-time listing help",
    priceRange: "₹300–3K/catalog",
    affordableForSmall: true,
  },
  {
    id: "ai-listing",
    category: "AI Listing Generator (SaaS)",
    approach: "AI-Powered Text Generation for Listings",
    players: [
      { name: "ListIQ", price: "₹49+ (credits)", model: "Credit-based", meesho: true },
      { name: "Sellermitra", price: "Free credits + paid", model: "Credit-based", meesho: true },
      { name: "DigiCommerce AI Tool", price: "Free (web tool)", model: "Free with limits", meesho: true },
    ],
    whatTheyDo: "AI generates SEO-optimized product titles, bullet points, descriptions, and backend keywords. Seller inputs product name + features, gets marketplace-formatted listing text.",
    strengths: ["Instant output — seconds vs days", "Very affordable (some free)", "Supports multiple marketplaces", "Scales to any catalog size", "India-focused, understands Meesho format"],
    weaknesses: ["TEXT ONLY — no image processing", "No catalog upload to Meesho", "No compliance/format validation", "No image editing, background removal, or resize", "No pricing intelligence", "No performance tracking after listing", "Seller still does 70% of the work manually"],
    targetUser: "Tech-savvy sellers who want title/description help",
    priceRange: "Free – ₹500/month",
    affordableForSmall: true,
  },
  {
    id: "image-tools",
    category: "AI Image Editing Tools",
    approach: "Product Photo Enhancement & Background Removal",
    players: [
      { name: "PhotoRoom", price: "$9.99/mo (₹850+)", model: "Subscription", meesho: false },
      { name: "Pixelcut", price: "$9.99/mo (₹850+)", model: "Subscription", meesho: false },
      { name: "Remove.bg", price: "$0.90/image or $0.18/img bulk", model: "Pay-per-use", meesho: false },
      { name: "Canva Pro", price: "₹500/mo (India)", model: "Subscription", meesho: false },
      { name: "EcomSarthi Image Tool", price: "Free", model: "Free web tool", meesho: true },
    ],
    whatTheyDo: "Background removal, white background generation, image resize to marketplace specs (1024×1024 for Meesho), image enhancement, lifestyle scene generation.",
    strengths: ["Good AI quality for backgrounds", "Fast processing", "Some have batch processing", "Mobile-friendly (PhotoRoom, Pixelcut)"],
    weaknesses: ["NOT Meesho-specific — generic tools", "No title/description generation", "No catalog upload integration", "No compliance validation beyond image size", "International pricing — expensive for Indian sellers", "Seller must use SEPARATE tools for text + images"],
    targetUser: "Sellers who need better product photos",
    priceRange: "Free – ₹1,000/month",
    affordableForSmall: true,
  },
  {
    id: "multichannel-saas",
    category: "Multi-channel OMS/SaaS",
    approach: "Enterprise Catalog + Order Management",
    players: [
      { name: "Unicommerce", price: "₹10,000–50,000+/mo", model: "Subscription + per-order", meesho: true },
      { name: "Vinculum (Vin eRetail)", price: "₹15,000+/mo", model: "Enterprise subscription", meesho: true },
      { name: "EasyEcom", price: "₹5,000–25,000/mo", model: "Subscription", meesho: true },
      { name: "Browntape", price: "₹3,000–15,000/mo", model: "Subscription", meesho: true },
    ],
    whatTheyDo: "Full multi-channel management — inventory sync, order processing, catalog management, payment reconciliation, shipping integration. Catalog management is ONE feature in a massive platform.",
    strengths: ["Complete solution if you sell on 3+ platforms", "Real-time inventory sync", "Payment reconciliation", "Enterprise-grade reliability"],
    weaknesses: ["MASSIVE overkill for Meesho-only sellers", "Catalog creation is basic — no AI optimization", "Pricing starts at ₹5K minimum", "Complex setup, steep learning curve", "Designed for brands, not small Meesho suppliers", "No Meesho-specific SEO or listing intelligence"],
    targetUser: "Multi-channel D2C brands doing ₹10L+ monthly revenue",
    priceRange: "₹5K–50K+/month",
    affordableForSmall: false,
  },
  {
    id: "global-ai",
    category: "Global AI Seller Tools",
    approach: "AI-Powered Amazon/eBay Seller Platforms",
    players: [
      { name: "SellerApp", price: "$42–199/mo (₹3,500–16,500)", model: "Subscription", meesho: false },
      { name: "Helium 10", price: "$29–229/mo (₹2,400–19,000)", model: "Subscription", meesho: false },
      { name: "Jungle Scout", price: "$49–399/mo", model: "Subscription", meesho: false },
      { name: "SmartScout", price: "$29–97/mo", model: "Subscription", meesho: false },
    ],
    whatTheyDo: "Full seller toolkit — product research, keyword research, listing optimization, PPC automation, competitor tracking, profit analytics. Primarily Amazon-focused.",
    strengths: ["Powerful AI and data intelligence", "Keyword research + competitor tracking", "Listing quality scoring", "Proven results on Amazon"],
    weaknesses: ["ZERO Meesho support", "Amazon/US-centric — irrelevant algorithms", "USD pricing — very expensive for Indian sellers", "Overkill features that don't apply to Meesho's model", "No understanding of Meesho's reseller dynamics"],
    targetUser: "Amazon sellers (US/Global), not Meesho",
    priceRange: "₹2,400–19,000/month",
    affordableForSmall: false,
  },
  {
    id: "meesho-builtin",
    category: "Meesho Built-in Tools",
    approach: "Meesho's Own Supplier Panel Tools",
    players: [
      { name: "Meesho Supplier Panel", price: "Free", model: "Built-in", meesho: true },
      { name: "Meesho Product Recommendations", price: "Free", model: "Built-in", meesho: true },
      { name: "Meesho Catalog Upload (Single/Bulk)", price: "Free", model: "Built-in", meesho: true },
      { name: "Meesho Ads (Boost)", price: "Pay-per-click", model: "Ad spend", meesho: true },
    ],
    whatTheyDo: "Basic catalog creation within the supplier panel — manual title entry, image upload, category selection, variant management. Product recommendation tool suggests trending items. Bulk upload via CSV templates.",
    strengths: ["Free", "Native to the platform", "Improving gradually with AI features", "Product recommendation helps with what to sell"],
    weaknesses: ["NO AI title or description generation", "NO image enhancement or compliance checking", "NO SEO keyword suggestions", "NO competitor analysis", "Bulk CSV template is confusing for new sellers", "NO listing quality score or optimization tips", "NO pre-upload validation — submit and pray"],
    targetUser: "All Meesho suppliers (default tool)",
    priceRange: "Free",
    affordableForSmall: true,
  },
];

const catColors = {
  "Full-Service Agency": "#e07a5f",
  "Budget Agency": "#f4845f",
  "IndiaMART / Local Services": "#ffd166",
  "Freelancer Marketplace": "#f2cc8f",
  "AI Listing Generator (SaaS)": "#57cc99",
  "AI Image Editing Tools": "#48bfe3",
  "Multi-channel OMS/SaaS": "#7b68ee",
  "Global AI Seller Tools": "#b388ff",
  "Meesho Built-in Tools": "#888",
};

export default function CatalogLandscape() {
  const [expanded, setExpanded] = useState(new Set(["ai-listing"]));
  const [view, setView] = useState("list");

  const toggle = (id) => setExpanded(prev => {
    const n = new Set(prev);
    n.has(id) ? n.delete(id) : n.add(id);
    return n;
  });

  return (
    <div style={{ minHeight: "100vh", background: "#0d0d10", color: "#e0e0e0", fontFamily: "'DM Sans', sans-serif", padding: "28px 20px 50px" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&family=Playfair+Display:wght@700;800&display=swap" rel="stylesheet" />

      {/* Header */}
      <div style={{ maxWidth: 1000, margin: "0 auto 20px" }}>
        <div style={{ fontSize: 10, letterSpacing: "0.15em", color: "#57cc99", textTransform: "uppercase", fontWeight: 600, marginBottom: 6 }}>
          R&D Deep Dive · Problem #1
        </div>
        <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: 26, fontWeight: 800, margin: "0 0 6px", color: "#eee" }}>
          Catalog Creation & Optimization
        </h1>
        <p style={{ color: "#777", fontSize: 13, margin: 0, lineHeight: 1.5 }}>
          Every solution approach that exists in the market — who built it, how they charge, and where they fall short.
        </p>
      </div>

      {/* Price Spectrum */}
      <div style={{ maxWidth: 1000, margin: "0 auto 20px", background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)", borderRadius: 12, padding: "16px 20px" }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "#ffd166", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 12 }}>
          💰 Price Spectrum — Monthly Cost to Seller
        </div>
        <div style={{ position: "relative", height: 60, marginBottom: 8 }}>
          {/* Scale bar */}
          <div style={{ position: "absolute", top: 24, left: 0, right: 0, height: 4, background: "linear-gradient(90deg, #57cc99, #ffd166, #e07a5f, #ff4444)", borderRadius: 2, opacity: 0.5 }} />
          {/* Labels */}
          {[
            { label: "Free", left: "0%", color: "#57cc99" },
            { label: "₹500", left: "10%", color: "#57cc99" },
            { label: "₹2K", left: "25%", color: "#ffd166" },
            { label: "₹5K", left: "40%", color: "#ffd166" },
            { label: "₹10K", left: "55%", color: "#e07a5f" },
            { label: "₹25K", left: "75%", color: "#e07a5f" },
            { label: "₹50K+", left: "95%", color: "#ff4444" },
          ].map((m, i) => (
            <div key={i} style={{ position: "absolute", left: m.left, top: 0, transform: "translateX(-50%)" }}>
              <div style={{ fontSize: 10, fontWeight: 700, color: m.color, fontFamily: "'JetBrains Mono', monospace", textAlign: "center" }}>{m.label}</div>
              <div style={{ width: 2, height: 10, background: m.color, margin: "4px auto 0", opacity: 0.4 }} />
            </div>
          ))}
          {/* Zone labels */}
          <div style={{ position: "absolute", bottom: 0, left: "5%", fontSize: 9, color: "#57cc99", fontFamily: "'JetBrains Mono', monospace", opacity: 0.7 }}>AFFORDABLE</div>
          <div style={{ position: "absolute", bottom: 0, left: "35%", fontSize: 9, color: "#ffd166", fontFamily: "'JetBrains Mono', monospace", opacity: 0.7 }}>MID-RANGE</div>
          <div style={{ position: "absolute", bottom: 0, left: "70%", fontSize: 9, color: "#e07a5f", fontFamily: "'JetBrains Mono', monospace", opacity: 0.7 }}>PREMIUM</div>
        </div>
        <div style={{ fontSize: 11, color: "#666", textAlign: "center", marginTop: 4, fontStyle: "italic" }}>
          The ₹500–2,000/month zone has NO comprehensive tool. This is the gap.
        </div>
      </div>

      {/* Summary count */}
      <div style={{ maxWidth: 1000, margin: "0 auto 16px", display: "flex", gap: 8, flexWrap: "wrap" }}>
        <div style={{ fontSize: 11, color: "#888", padding: "6px 12px", background: "rgba(255,255,255,0.03)", borderRadius: 8, fontFamily: "'JetBrains Mono', monospace" }}>
          {APPROACHES.length} approaches · {APPROACHES.reduce((a, b) => a + b.players.length, 0)} players mapped
        </div>
        <div style={{ fontSize: 11, color: "#57cc99", padding: "6px 12px", background: "#57cc9910", borderRadius: 8, fontFamily: "'JetBrains Mono', monospace" }}>
          {APPROACHES.filter(a => a.affordableForSmall).length} affordable for small sellers
        </div>
        <div style={{ fontSize: 11, color: "#e07a5f", padding: "6px 12px", background: "#e07a5f10", borderRadius: 8, fontFamily: "'JetBrains Mono', monospace" }}>
          {APPROACHES.filter(a => !a.affordableForSmall).length} out of reach for small sellers
        </div>
      </div>

      {/* Approach Cards */}
      <div style={{ maxWidth: 1000, margin: "0 auto", display: "flex", flexDirection: "column", gap: 8 }}>
        {APPROACHES.map((a) => {
          const isOpen = expanded.has(a.id);
          const color = catColors[a.category] || "#888";
          return (
            <div key={a.id} style={{
              background: isOpen ? "rgba(255,255,255,0.03)" : "rgba(255,255,255,0.015)",
              border: `1px solid ${isOpen ? color + "33" : "rgba(255,255,255,0.05)"}`,
              borderRadius: 12, overflow: "hidden", transition: "all 0.3s"
            }}>
              {/* Header row */}
              <div onClick={() => toggle(a.id)} style={{ padding: "14px 18px", cursor: "pointer", display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ width: 10, height: 10, borderRadius: "50%", background: color, flexShrink: 0 }} />
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "#ddd" }}>{a.approach}</div>
                  <div style={{ fontSize: 11, color: "#777", marginTop: 2 }}>{a.category}</div>
                </div>
                <span style={{
                  fontSize: 11, fontWeight: 700, color: a.affordableForSmall ? "#57cc99" : "#e07a5f",
                  padding: "3px 8px", borderRadius: 4,
                  background: a.affordableForSmall ? "#57cc9915" : "#e07a5f15",
                  fontFamily: "'JetBrains Mono', monospace",
                }}>
                  {a.priceRange}
                </span>
                <span style={{ fontSize: 16, color: "#555", transition: "transform 0.3s", transform: isOpen ? "rotate(180deg)" : "rotate(0)" }}>▾</span>
              </div>

              {isOpen && (
                <div style={{ padding: "0 18px 18px", borderTop: "1px solid rgba(255,255,255,0.04)" }}>
                  {/* What they do */}
                  <p style={{ fontSize: 13, color: "#aaa", lineHeight: 1.6, margin: "12px 0 16px" }}>{a.whatTheyDo}</p>

                  {/* Players table */}
                  <div style={{ fontSize: 11, fontWeight: 700, color, letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 8 }}>
                    Players & Pricing
                  </div>
                  <div style={{ display: "grid", gap: 4, marginBottom: 16 }}>
                    {a.players.map((p, i) => (
                      <div key={i} style={{
                        display: "grid", gridTemplateColumns: "180px 180px 140px auto",
                        gap: 8, alignItems: "center", fontSize: 12,
                        padding: "8px 12px", background: "rgba(255,255,255,0.02)", borderRadius: 8
                      }}>
                        <span style={{ color: "#ddd", fontWeight: 600 }}>{p.name}</span>
                        <span style={{ color: "#ffd166", fontWeight: 600, fontFamily: "'JetBrains Mono', monospace", fontSize: 11 }}>{p.price}</span>
                        <span style={{ color: "#888", fontFamily: "'JetBrains Mono', monospace", fontSize: 10 }}>{p.model}</span>
                        <span style={{
                          fontSize: 9, padding: "2px 6px", borderRadius: 3, fontWeight: 600,
                          background: p.meesho ? "#57cc9915" : "#ff444415",
                          color: p.meesho ? "#57cc99" : "#ff6b6b",
                          justifySelf: "end",
                        }}>
                          {p.meesho ? "MEESHO ✓" : "NO MEESHO"}
                        </span>
                      </div>
                    ))}
                  </div>

                  {/* Strengths & Weaknesses side by side */}
                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 700, color: "#57cc99", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>Strengths</div>
                      {a.strengths.map((s, i) => (
                        <div key={i} style={{ fontSize: 12, color: "#aaa", marginBottom: 4, display: "flex", gap: 6, lineHeight: 1.4 }}>
                          <span style={{ color: "#57cc99" }}>+</span> {s}
                        </div>
                      ))}
                    </div>
                    <div>
                      <div style={{ fontSize: 10, fontWeight: 700, color: "#e07a5f", letterSpacing: "0.06em", textTransform: "uppercase", marginBottom: 6 }}>Weaknesses</div>
                      {a.weaknesses.map((w, i) => (
                        <div key={i} style={{ fontSize: 12, color: "#aaa", marginBottom: 4, display: "flex", gap: 6, lineHeight: 1.4 }}>
                          <span style={{ color: "#e07a5f" }}>−</span> {w}
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Target */}
                  <div style={{ fontSize: 11, color: "#777", fontFamily: "'JetBrains Mono', monospace" }}>
                    TARGET → {a.targetUser}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Bottom Insight */}
      <div style={{
        maxWidth: 1000, margin: "28px auto 0",
        background: "linear-gradient(135deg, #57cc9910, #48bfe310)",
        border: "1px solid #57cc9922", borderRadius: 12, padding: "20px 24px"
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, color: "#57cc99", letterSpacing: "0.08em", textTransform: "uppercase", marginBottom: 10 }}>
          🔑 Key Finding
        </div>
        <p style={{ fontSize: 14, color: "#ccc", lineHeight: 1.7, margin: "0 0 12px" }}>
          <strong style={{ color: "#eee" }}>9 approaches, 30+ players, and yet the gap persists:</strong>
        </p>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, fontSize: 13, color: "#bbb", lineHeight: 1.6 }}>
          <div>
            <div style={{ color: "#e07a5f", fontWeight: 700, fontSize: 12, marginBottom: 4 }}>❌ What exists but fails small sellers:</div>
            <div>• Agencies (₹3K-50K/mo) — too expensive, manual, no AI</div>
            <div>• Multi-channel SaaS (₹5K-50K) — overkill for Meesho-only</div>
            <div>• Global AI tools ($29-229/mo) — no Meesho support, USD pricing</div>
          </div>
          <div>
            <div style={{ color: "#ffd166", fontWeight: 700, fontSize: 12, marginBottom: 4 }}>⚠️ What exists but is incomplete:</div>
            <div>• ListIQ/Sellermitra — text only, no images, no upload</div>
            <div>• PhotoRoom/Pixelcut — images only, no text, no Meesho format</div>
            <div>• EcomSarthi free tools — one feature each, fragmented</div>
          </div>
        </div>
        <div style={{ marginTop: 16, padding: "14px 16px", background: "rgba(255,255,255,0.04)", borderRadius: 8 }}>
          <div style={{ color: "#57cc99", fontWeight: 700, fontSize: 12, marginBottom: 4 }}>✅ The whitespace opportunity:</div>
          <div style={{ fontSize: 13, color: "#ddd", lineHeight: 1.6 }}>
            An <strong>all-in-one AI tool at ₹499-1,999/month</strong> that combines: AI title/description generation (ListIQ's job) + image compliance/enhancement (PhotoRoom's job) + pre-upload validation (nobody's job) + direct Meesho catalog format export (nobody's job) + listing performance tracking (nobody's job for Meesho). One tool replacing 4-5 fragmented solutions.
          </div>
        </div>
      </div>
    </div>
  );
}
