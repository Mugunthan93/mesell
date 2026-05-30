import { useState } from "react";

const SCREENS = {
  flow: "User Flow",
  onboard: "Onboarding",
  dashboard: "Dashboard",
  catalog: "CatalogAI",
  quality: "QualityGate",
  pricing: "PriceIntel",
  export: "Export",
};

function Dot({ color = "#57cc99" }) {
  return <span style={{ width: 6, height: 6, borderRadius: "50%", background: color, display: "inline-block" }} />;
}

function WireBox({ children, label, style = {} }) {
  return (
    <div style={{ border: "1px dashed rgba(255,255,255,0.12)", borderRadius: 10, padding: "12px 14px", position: "relative", ...style }}>
      {label && (
        <div style={{ position: "absolute", top: -9, left: 12, background: "#0e0e14", padding: "0 6px", fontSize: 9, color: "#666", fontWeight: 600, letterSpacing: "0.06em", textTransform: "uppercase" }}>
          {label}
        </div>
      )}
      {children}
    </div>
  );
}

function Btn({ children, primary, color = "#57cc99", onClick, small, style = {} }) {
  return (
    <button onClick={onClick} style={{
      padding: small ? "5px 12px" : "8px 18px",
      fontSize: small ? 10 : 12,
      fontWeight: 600,
      borderRadius: 8,
      cursor: "pointer",
      fontFamily: "'DM Sans', sans-serif",
      background: primary ? color : "transparent",
      border: `1.5px solid ${color}`,
      color: primary ? "#0e0e14" : color,
      transition: "all 0.2s",
      ...style,
    }}>
      {children}
    </button>
  );
}

function InputMock({ placeholder, icon, wide }) {
  return (
    <div style={{
      display: "flex", alignItems: "center", gap: 8,
      padding: "9px 14px", background: "rgba(255,255,255,0.04)",
      border: "1px solid rgba(255,255,255,0.08)", borderRadius: 8,
      width: wide ? "100%" : "auto",
    }}>
      {icon && <span style={{ fontSize: 14, opacity: 0.5 }}>{icon}</span>}
      <span style={{ fontSize: 12, color: "#555" }}>{placeholder}</span>
    </div>
  );
}

function ScreenAnnotation({ text, color = "#7b68ee" }) {
  return (
    <div style={{
      fontSize: 10, color, fontWeight: 600, fontFamily: "'JetBrains Mono', monospace",
      padding: "4px 10px", background: color + "10", border: `1px solid ${color}22`,
      borderRadius: 6, display: "inline-block", marginBottom: 8,
    }}>
      {text}
    </div>
  );
}

/* ============ SCREEN: USER FLOW ============ */
function FlowScreen({ goTo }) {
  const steps = [
    { id: "onboard", label: "Sign Up\n(Phone OTP)", icon: "📱", color: "#ffd166", note: "< 60 seconds", screen: "onboard" },
    { id: "upload", label: "Upload\nProduct Photos", icon: "📷", color: "#48bfe3", note: "Drag & drop or camera", screen: "catalog" },
    { id: "ai", label: "AI Generates\nCatalog", icon: "🧠", color: "#57cc99", note: "~30 seconds", screen: "catalog" },
    { id: "quality", label: "QualityGate\nValidation", icon: "✅", color: "#7b68ee", note: "Auto pass/fail", screen: "quality" },
    { id: "price", label: "PriceIntel\nOptimize Price", icon: "💰", color: "#ffd166", note: "Per-SKU P&L", screen: "pricing" },
    { id: "export", label: "Export\nMeesho CSV", icon: "📤", color: "#e07a5f", note: "Ready to upload", screen: "export" },
    { id: "meesho", label: "Upload to\nMeesho Panel", icon: "🛒", color: "#888", note: "Manual (MVP)", screen: null },
  ];

  return (
    <div>
      <ScreenAnnotation text="MVP USER FLOW — 7 STEPS FROM PHOTO TO MEESHO LISTING" />
      <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 24, flexWrap: "wrap" }}>
        {steps.map((s, i) => (
          <div key={s.id} style={{ display: "flex", alignItems: "center", gap: 4 }}>
            <div
              onClick={() => s.screen && goTo(s.screen)}
              style={{
                background: s.color + "12", border: `1.5px solid ${s.color}33`,
                borderRadius: 10, padding: "12px 14px", textAlign: "center",
                cursor: s.screen ? "pointer" : "default",
                minWidth: 100, transition: "all 0.2s",
              }}
            >
              <div style={{ fontSize: 22, marginBottom: 4 }}>{s.icon}</div>
              <div style={{ fontSize: 11, fontWeight: 600, color: s.color, whiteSpace: "pre-line", lineHeight: 1.3 }}>{s.label}</div>
              <div style={{ fontSize: 9, color: "#666", marginTop: 4, fontFamily: "'JetBrains Mono', monospace" }}>{s.note}</div>
            </div>
            {i < steps.length - 1 && <span style={{ fontSize: 16, color: "#333" }}>→</span>}
          </div>
        ))}
      </div>

      <ScreenAnnotation text="SECONDARY FLOWS — ANALYTICS & RECONCILIATION" color="#e07a5f" />
      <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
        {[
          { label: "Upload Settlement CSV", desc: "Seller downloads from Meesho → uploads to MeeSell", icon: "📊", color: "#7b68ee" },
          { label: "Per-SKU P&L Dashboard", desc: "True profit after returns, shipping, GST", icon: "💹", color: "#57cc99" },
          { label: "Return Analytics", desc: "Which SKUs get returned most & why", icon: "🛡️", color: "#e07a5f" },
          { label: "WhatsApp Daily Digest", desc: "Auto daily alert: sales, returns, margins", icon: "💬", color: "#48bfe3" },
        ].map((f, i) => (
          <div key={i} style={{
            background: f.color + "08", border: `1px solid ${f.color}22`,
            borderRadius: 8, padding: "10px 14px", flex: "1 1 200px",
          }}>
            <span style={{ fontSize: 16 }}>{f.icon}</span>
            <div style={{ fontSize: 11, fontWeight: 700, color: f.color, marginTop: 4 }}>{f.label}</div>
            <div style={{ fontSize: 10, color: "#777", marginTop: 2 }}>{f.desc}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ============ SCREEN: ONBOARDING ============ */
function OnboardScreen() {
  const [step, setStep] = useState(0);
  return (
    <div>
      <ScreenAnnotation text="ONBOARDING — TIME TO VALUE < 2 MINUTES" />
      <div style={{ maxWidth: 400, margin: "0 auto" }}>
        <WireBox label="Onboarding Card" style={{ background: "rgba(255,255,255,0.02)", padding: "24px 20px" }}>
          {step === 0 && (
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>📱</div>
              <div style={{ fontSize: 18, fontWeight: 700, color: "#eee", marginBottom: 4 }}>Welcome to MeeSell</div>
              <div style={{ fontSize: 12, color: "#777", marginBottom: 16 }}>AI-powered catalog creator for Meesho sellers</div>
              <InputMock placeholder="+91 98765 43210" icon="📱" wide />
              <div style={{ marginTop: 12 }}><Btn primary onClick={() => setStep(1)} style={{ width: "100%" }}>Send OTP</Btn></div>
              <div style={{ fontSize: 10, color: "#555", marginTop: 10 }}>No password needed. Login with phone OTP.</div>
            </div>
          )}
          {step === 1 && (
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>🔢</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#eee", marginBottom: 4 }}>Enter OTP</div>
              <div style={{ fontSize: 12, color: "#777", marginBottom: 16 }}>Sent to +91 98765 43210</div>
              <div style={{ display: "flex", gap: 8, justifyContent: "center", marginBottom: 16 }}>
                {[1,2,3,4].map(i => (
                  <div key={i} style={{ width: 44, height: 48, background: "rgba(255,255,255,0.06)", border: "1px solid rgba(255,255,255,0.12)", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 20, color: "#57cc99", fontWeight: 700 }}>
                    {i < 4 ? "•" : ""}
                  </div>
                ))}
              </div>
              <Btn primary onClick={() => setStep(2)} style={{ width: "100%" }}>Verify & Continue</Btn>
            </div>
          )}
          {step === 2 && (
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 32, marginBottom: 8 }}>🎉</div>
              <div style={{ fontSize: 16, fontWeight: 700, color: "#57cc99", marginBottom: 4 }}>You're in!</div>
              <div style={{ fontSize: 12, color: "#777", marginBottom: 16 }}>Let's create your first catalog in 30 seconds</div>
              <div style={{ background: "#57cc9910", border: "1px solid #57cc9922", borderRadius: 10, padding: "16px", marginBottom: 16 }}>
                <div style={{ fontSize: 40, marginBottom: 6 }}>📷</div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "#ddd" }}>Upload a product photo</div>
                <div style={{ fontSize: 11, color: "#888", marginTop: 4 }}>We'll show you the AI magic ✨</div>
              </div>
              <Btn primary onClick={() => setStep(0)} style={{ width: "100%" }}>Upload Photo →</Btn>
              <div style={{ fontSize: 10, color: "#555", marginTop: 8 }}>Free tier — no card needed</div>
            </div>
          )}
        </WireBox>
        <div style={{ display: "flex", justifyContent: "center", gap: 6, marginTop: 12 }}>
          {[0,1,2].map(i => (
            <div key={i} onClick={() => setStep(i)} style={{
              width: i === step ? 20 : 8, height: 8, borderRadius: 4,
              background: i === step ? "#57cc99" : "rgba(255,255,255,0.1)",
              cursor: "pointer", transition: "all 0.3s",
            }} />
          ))}
        </div>
      </div>
    </div>
  );
}

/* ============ SCREEN: DASHBOARD ============ */
function DashboardScreen({ goTo }) {
  return (
    <div>
      <ScreenAnnotation text="DASHBOARD — SELLER'S HOME SCREEN" />
      {/* Top bar */}
      <WireBox label="Top Nav" style={{ marginBottom: 12, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <div style={{ fontSize: 16, fontWeight: 800, color: "#57cc99", fontFamily: "'Instrument Serif', serif" }}>MeeSell<span style={{ color: "#57cc99" }}>.</span></div>
        <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
          <span style={{ fontSize: 10, padding: "3px 8px", background: "#57cc9915", color: "#57cc99", borderRadius: 4, fontWeight: 600 }}>PRO PLAN</span>
          <div style={{ width: 28, height: 28, borderRadius: "50%", background: "rgba(255,255,255,0.08)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 12 }}>👤</div>
        </div>
      </WireBox>

      {/* Stats row */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8, marginBottom: 12 }}>
        {[
          { label: "Catalogs", value: "142", change: "+12 this week", color: "#57cc99" },
          { label: "Avg Margin", value: "32%", change: "↑ 4% vs last month", color: "#48bfe3" },
          { label: "Return Rate", value: "18%", change: "↓ 6% improved", color: "#ffd166" },
          { label: "Revenue (est)", value: "₹2.4L", change: "This month", color: "#7b68ee" },
        ].map((s, i) => (
          <WireBox key={i} style={{ textAlign: "center" }}>
            <div style={{ fontSize: 20, fontWeight: 800, color: s.color, fontFamily: "'JetBrains Mono', monospace" }}>{s.value}</div>
            <div style={{ fontSize: 10, color: "#888", marginTop: 2 }}>{s.label}</div>
            <div style={{ fontSize: 9, color: s.color, marginTop: 4, opacity: 0.7 }}>{s.change}</div>
          </WireBox>
        ))}
      </div>

      {/* Quick actions */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 8, marginBottom: 12 }}>
        {[
          { label: "Create Catalog", icon: "📦", desc: "AI-powered", color: "#57cc99", screen: "catalog" },
          { label: "Check Quality", icon: "✅", desc: "Pre-upload validation", color: "#48bfe3", screen: "quality" },
          { label: "Price Calculator", icon: "💰", desc: "Per-SKU P&L", color: "#ffd166", screen: "pricing" },
        ].map((a, i) => (
          <WireBox key={i} label="Quick Action" style={{ cursor: "pointer", textAlign: "center" }} onClick={() => goTo(a.screen)}>
            <div style={{ fontSize: 28, marginBottom: 4 }}>{a.icon}</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: a.color }}>{a.label}</div>
            <div style={{ fontSize: 10, color: "#666", marginTop: 2 }}>{a.desc}</div>
          </WireBox>
        ))}
      </div>

      {/* Recent catalogs */}
      <WireBox label="Recent Catalogs">
        {[
          { name: "Cotton Kurti Collection", skus: 6, status: "Live", score: 92, margin: "34%" },
          { name: "Silk Saree Premium", skus: 4, status: "Live", score: 88, margin: "28%" },
          { name: "Men's Casual Shirt", skus: 8, status: "Draft", score: null, margin: "—" },
        ].map((c, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "8px 0", borderBottom: i < 2 ? "1px solid rgba(255,255,255,0.04)" : "none" }}>
            <div style={{ width: 36, height: 36, borderRadius: 6, background: "rgba(255,255,255,0.06)", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 14 }}>📦</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#ddd" }}>{c.name}</div>
              <div style={{ fontSize: 10, color: "#666" }}>{c.skus} SKUs · Margin: {c.margin}</div>
            </div>
            <span style={{ fontSize: 9, padding: "2px 8px", borderRadius: 4, background: c.status === "Live" ? "#57cc9915" : "#ffd16615", color: c.status === "Live" ? "#57cc99" : "#ffd166", fontWeight: 600 }}>
              {c.status}
            </span>
            {c.score && <span style={{ fontSize: 10, color: "#48bfe3", fontFamily: "'JetBrains Mono', monospace", fontWeight: 700 }}>Q:{c.score}</span>}
          </div>
        ))}
      </WireBox>
    </div>
  );
}

/* ============ SCREEN: CATALOG AI ============ */
function CatalogScreen() {
  const [stage, setStage] = useState(0);
  return (
    <div>
      <ScreenAnnotation text="CATALOG AI — THE HERO FEATURE (WOW MOMENT)" />
      {/* Progress */}
      <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
        {["Upload", "Generate", "Preview", "Export"].map((s, i) => (
          <div key={i} style={{ flex: 1, textAlign: "center" }}>
            <div style={{ height: 3, background: i <= stage ? "#57cc99" : "rgba(255,255,255,0.06)", borderRadius: 2, marginBottom: 4, transition: "all 0.3s" }} />
            <span style={{ fontSize: 9, color: i <= stage ? "#57cc99" : "#555", fontWeight: 600 }}>{s}</span>
          </div>
        ))}
      </div>

      {stage === 0 && (
        <div>
          <WireBox label="Upload Zone" style={{ textAlign: "center", padding: "30px 20px", marginBottom: 12 }}>
            <div style={{ fontSize: 48, marginBottom: 8, opacity: 0.6 }}>📷</div>
            <div style={{ fontSize: 14, fontWeight: 600, color: "#ddd", marginBottom: 4 }}>Drop product photos here</div>
            <div style={{ fontSize: 11, color: "#666", marginBottom: 12 }}>JPG, PNG · Up to 9 images per catalog · Any size (we'll resize to 1024×1024)</div>
            <Btn primary onClick={() => setStage(1)}>Upload Photos</Btn>
          </WireBox>
          <WireBox label="Product Details">
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 8 }}>
              <InputMock placeholder="Product name (e.g. Cotton Kurti)" icon="✏️" wide />
              <InputMock placeholder="Category (auto-suggest)" icon="📂" wide />
              <InputMock placeholder="Material / Fabric" icon="🧵" wide />
              <InputMock placeholder="Price (₹)" icon="💰" wide />
            </div>
          </WireBox>
        </div>
      )}

      {stage === 1 && (
        <div>
          <WireBox label="AI Processing" style={{ textAlign: "center", padding: "24px 20px", marginBottom: 12 }}>
            <div style={{ fontSize: 40, marginBottom: 8 }}>🧠</div>
            <div style={{ fontSize: 14, fontWeight: 700, color: "#57cc99", marginBottom: 8 }}>AI is generating your catalog...</div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, maxWidth: 300, margin: "0 auto" }}>
              {[
                { task: "Background removal & white BG", done: true },
                { task: "Resize to 1024×1024", done: true },
                { task: "SEO title generation", done: true },
                { task: "Description & keywords", done: false },
                { task: "Category mapping", done: false },
              ].map((t, i) => (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12 }}>
                  <span style={{ color: t.done ? "#57cc99" : "#555" }}>{t.done ? "✓" : "○"}</span>
                  <span style={{ color: t.done ? "#aaa" : "#555" }}>{t.task}</span>
                </div>
              ))}
            </div>
            <div style={{ marginTop: 14 }}><Btn primary onClick={() => setStage(2)}>See Results →</Btn></div>
          </WireBox>
        </div>
      )}

      {stage === 2 && (
        <div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <WireBox label="Generated Images">
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
                {[1,2,3,4].map(i => (
                  <div key={i} style={{ aspectRatio: "1", background: "rgba(255,255,255,0.04)", borderRadius: 8, display: "flex", alignItems: "center", justifyContent: "center", border: "1px solid rgba(255,255,255,0.08)" }}>
                    <div style={{ textAlign: "center" }}>
                      <div style={{ fontSize: 24, opacity: 0.3 }}>🖼️</div>
                      <div style={{ fontSize: 8, color: "#57cc99", marginTop: 2 }}>1024×1024 ✓</div>
                      <div style={{ fontSize: 8, color: "#57cc99" }}>White BG ✓</div>
                    </div>
                  </div>
                ))}
              </div>
            </WireBox>
            <WireBox label="AI Generated Text">
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 9, color: "#57cc99", fontWeight: 700, letterSpacing: "0.06em", marginBottom: 3 }}>SEO TITLE</div>
                <div style={{ fontSize: 12, color: "#ddd", lineHeight: 1.4, padding: "6px 10px", background: "rgba(255,255,255,0.03)", borderRadius: 6 }}>
                  Women Cotton Kurti Straight Fit Casual Wear Printed A-Line Kurta for Daily Office Ethnic
                </div>
              </div>
              <div style={{ marginBottom: 10 }}>
                <div style={{ fontSize: 9, color: "#48bfe3", fontWeight: 700, letterSpacing: "0.06em", marginBottom: 3 }}>DESCRIPTION</div>
                <div style={{ fontSize: 11, color: "#aaa", lineHeight: 1.5, padding: "6px 10px", background: "rgba(255,255,255,0.03)", borderRadius: 6 }}>
                  This premium cotton kurti features a comfortable straight fit design perfect for daily and office wear. Made with breathable fabric...
                </div>
              </div>
              <div>
                <div style={{ fontSize: 9, color: "#ffd166", fontWeight: 700, letterSpacing: "0.06em", marginBottom: 3 }}>ATTRIBUTES</div>
                <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                  {["Fabric: Cotton", "Fit: Straight", "Occasion: Casual", "Sleeve: 3/4", "Neck: Round"].map((a, i) => (
                    <span key={i} style={{ fontSize: 10, padding: "2px 8px", background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.08)", borderRadius: 4, color: "#bbb" }}>{a}</span>
                  ))}
                </div>
              </div>
            </WireBox>
          </div>
          <div style={{ display: "flex", gap: 8, marginTop: 12, justifyContent: "flex-end" }}>
            <Btn onClick={() => setStage(1)}>↻ Regenerate</Btn>
            <Btn primary onClick={() => setStage(3)}>✓ Approve & Export →</Btn>
          </div>
        </div>
      )}

      {stage === 3 && (
        <WireBox label="Export Options" style={{ textAlign: "center", padding: "24px" }}>
          <div style={{ fontSize: 40, marginBottom: 8 }}>📤</div>
          <div style={{ fontSize: 16, fontWeight: 700, color: "#57cc99", marginBottom: 12 }}>Catalog Ready!</div>
          <div style={{ display: "flex", gap: 10, justifyContent: "center", marginBottom: 16 }}>
            <Btn primary color="#57cc99">Download Meesho CSV</Btn>
            <Btn primary color="#48bfe3">Download Images (ZIP)</Btn>
          </div>
          <div style={{ fontSize: 11, color: "#888", lineHeight: 1.6 }}>
            Upload the CSV to Meesho Supplier Panel → Catalog → Bulk Upload
          </div>
          <div style={{ marginTop: 12 }}><Btn small onClick={() => setStage(0)}>Create Another Catalog</Btn></div>
        </WireBox>
      )}
    </div>
  );
}

/* ============ SCREEN: QUALITY GATE ============ */
function QualityScreen() {
  return (
    <div>
      <ScreenAnnotation text="QUALITY GATE — PRE-UPLOAD VALIDATION" />
      <WireBox label="Quality Scorecard" style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 14 }}>
          <div style={{ width: 64, height: 64, borderRadius: "50%", border: "3px solid #57cc99", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <span style={{ fontSize: 22, fontWeight: 800, color: "#57cc99", fontFamily: "'JetBrains Mono', monospace" }}>92</span>
          </div>
          <div>
            <div style={{ fontSize: 16, fontWeight: 700, color: "#57cc99" }}>PASS — Ready to Upload</div>
            <div style={{ fontSize: 11, color: "#888" }}>Cotton Kurti Collection · 6 SKUs · 24 images</div>
          </div>
        </div>

        {[
          { check: "Image Size (1024×1024)", status: "pass", detail: "All 24 images meet size requirement" },
          { check: "White Background", status: "pass", detail: "All images have clean white backgrounds" },
          { check: "No Watermarks", status: "pass", detail: "No watermarks or text overlays detected" },
          { check: "Title Length (< 200 chars)", status: "pass", detail: "All titles within Meesho character limits" },
          { check: "Required Attributes", status: "warn", detail: "Missing 'wash care' for 2 SKUs — recommended but optional" },
          { check: "Duplicate Check", status: "pass", detail: "No similar catalogs found in your account" },
          { check: "Banned Words Check", status: "pass", detail: "No prohibited terms in titles or descriptions" },
          { check: "Category Mapping", status: "pass", detail: "Category: Women > Ethnic Wear > Kurtis — correct" },
        ].map((c, i) => (
          <div key={i} style={{ display: "flex", alignItems: "center", gap: 10, padding: "7px 0", borderBottom: i < 7 ? "1px solid rgba(255,255,255,0.03)" : "none" }}>
            <span style={{ fontSize: 14 }}>
              {c.status === "pass" ? "✅" : c.status === "warn" ? "⚠️" : "❌"}
            </span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: "#ddd" }}>{c.check}</div>
              <div style={{ fontSize: 10, color: "#777" }}>{c.detail}</div>
            </div>
          </div>
        ))}
      </WireBox>
      <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
        <Btn>Fix Warnings</Btn>
        <Btn primary>Export Catalog →</Btn>
      </div>
    </div>
  );
}

/* ============ SCREEN: PRICE INTEL ============ */
function PricingScreen() {
  return (
    <div>
      <ScreenAnnotation text="PRICE INTEL — PER-SKU P&L CALCULATOR" />
      <WireBox label="Input" style={{ marginBottom: 12 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 8 }}>
          <InputMock placeholder="Selling Price ₹599" icon="💰" wide />
          <InputMock placeholder="Cost Price ₹220" icon="🏭" wide />
          <InputMock placeholder="Weight 350g" icon="⚖️" wide />
          <InputMock placeholder="Category: Kurtis" icon="📂" wide />
        </div>
      </WireBox>

      <WireBox label="P&L Breakdown" style={{ marginBottom: 12 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
          {[
            { item: "Selling Price", value: "₹599", color: "#57cc99", bold: true },
            { item: "Cost Price", value: "- ₹220", color: "#e07a5f" },
            { item: "Meesho Commission (0%)", value: "- ₹0", color: "#888" },
            { item: "Shipping (350g, Zone B)", value: "- ₹58", color: "#e07a5f" },
            { item: "GST on Shipping (18%)", value: "- ₹10.44", color: "#e07a5f" },
            { item: "Payment Processing (2%)", value: "- ₹11.98", color: "#e07a5f" },
            { item: "Packaging", value: "- ₹12", color: "#e07a5f" },
            { item: "Return Cost Provision (18% rate × ₹58)", value: "- ₹10.44", color: "#ffd166" },
          ].map((r, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", padding: "5px 0", borderBottom: "1px solid rgba(255,255,255,0.03)", fontSize: 12 }}>
              <span style={{ color: "#aaa" }}>{r.item}</span>
              <span style={{ color: r.color, fontWeight: r.bold ? 800 : 600, fontFamily: "'JetBrains Mono', monospace" }}>{r.value}</span>
            </div>
          ))}
          <div style={{ display: "flex", justifyContent: "space-between", padding: "8px 0", fontSize: 14, borderTop: "2px solid rgba(255,255,255,0.1)", marginTop: 4 }}>
            <span style={{ color: "#eee", fontWeight: 700 }}>Net Profit per Order</span>
            <span style={{ color: "#57cc99", fontWeight: 800, fontFamily: "'JetBrains Mono', monospace" }}>₹276.14 (46.1%)</span>
          </div>
        </div>
      </WireBox>

      <WireBox label="Alerts">
        <div style={{ display: "flex", gap: 8, alignItems: "center", padding: "4px 0" }}>
          <span style={{ fontSize: 14 }}>⚠️</span>
          <span style={{ fontSize: 11, color: "#ffd166" }}>Weight is 350g — close to 500g slab jump. At 500g shipping jumps to ₹82 (+₹24). Consider lighter packaging.</span>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "center", padding: "4px 0" }}>
          <span style={{ fontSize: 14 }}>📊</span>
          <span style={{ fontSize: 11, color: "#48bfe3" }}>Similar kurtis in your category sell at ₹499-649. Your ₹599 is competitive.</span>
        </div>
      </WireBox>
    </div>
  );
}

/* ============ SCREEN: EXPORT ============ */
function ExportScreen() {
  return (
    <div>
      <ScreenAnnotation text="EXPORT — MEESHO-READY FILES" />
      <WireBox label="Export Package" style={{ textAlign: "center", padding: "24px" }}>
        <div style={{ fontSize: 48, marginBottom: 8 }}>📤</div>
        <div style={{ fontSize: 18, fontWeight: 700, color: "#eee", marginBottom: 4 }}>Your Meesho catalog is ready</div>
        <div style={{ fontSize: 12, color: "#777", marginBottom: 20 }}>Quality Score: 92/100 · 6 SKUs · 24 images</div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, maxWidth: 400, margin: "0 auto 20px" }}>
          <div style={{ background: "#57cc9910", border: "1px solid #57cc9922", borderRadius: 10, padding: "16px" }}>
            <div style={{ fontSize: 24, marginBottom: 4 }}>📄</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#57cc99" }}>Meesho CSV</div>
            <div style={{ fontSize: 10, color: "#888", marginTop: 2 }}>Bulk upload format</div>
            <div style={{ marginTop: 8 }}><Btn small primary color="#57cc99">Download</Btn></div>
          </div>
          <div style={{ background: "#48bfe310", border: "1px solid #48bfe322", borderRadius: 10, padding: "16px" }}>
            <div style={{ fontSize: 24, marginBottom: 4 }}>🖼️</div>
            <div style={{ fontSize: 12, fontWeight: 700, color: "#48bfe3" }}>Images ZIP</div>
            <div style={{ fontSize: 10, color: "#888", marginTop: 2 }}>24 images · 1024×1024</div>
            <div style={{ marginTop: 8 }}><Btn small primary color="#48bfe3">Download</Btn></div>
          </div>
        </div>
        <div style={{ background: "rgba(255,255,255,0.03)", borderRadius: 8, padding: "12px 16px", fontSize: 11, color: "#888", lineHeight: 1.6, maxWidth: 440, margin: "0 auto" }}>
          <strong style={{ color: "#ddd" }}>Next steps:</strong> Go to supplier.meesho.com → Catalog → Bulk Upload → Upload the CSV file → Upload images when prompted → Submit for review
        </div>
      </WireBox>
    </div>
  );
}

/* ============ MAIN APP ============ */
export default function Wireframes() {
  const [screen, setScreen] = useState("flow");

  const renderScreen = () => {
    switch (screen) {
      case "flow": return <FlowScreen goTo={setScreen} />;
      case "onboard": return <OnboardScreen />;
      case "dashboard": return <DashboardScreen goTo={setScreen} />;
      case "catalog": return <CatalogScreen />;
      case "quality": return <QualityScreen />;
      case "pricing": return <PricingScreen />;
      case "export": return <ExportScreen />;
      default: return <FlowScreen goTo={setScreen} />;
    }
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0e0e14", color: "#e0e0e0", fontFamily: "'DM Sans', sans-serif" }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;700&family=Instrument+Serif&display=swap" rel="stylesheet" />

      {/* Screen nav */}
      <div style={{ borderBottom: "1px solid rgba(255,255,255,0.06)", padding: "12px 20px", position: "sticky", top: 0, background: "#0e0e14", zIndex: 10 }}>
        <div style={{ maxWidth: 900, margin: "0 auto", display: "flex", alignItems: "center", gap: 6, overflowX: "auto" }}>
          <span style={{ fontSize: 14, fontWeight: 800, color: "#57cc99", fontFamily: "'Instrument Serif', serif", marginRight: 12 }}>MeeSell</span>
          {Object.entries(SCREENS).map(([key, label]) => (
            <button key={key} onClick={() => setScreen(key)} style={{
              padding: "5px 12px", fontSize: 11, fontWeight: 600, borderRadius: 6,
              background: screen === key ? "#57cc9918" : "transparent",
              border: `1px solid ${screen === key ? "#57cc9933" : "transparent"}`,
              color: screen === key ? "#57cc99" : "#666",
              cursor: "pointer", fontFamily: "'DM Sans', sans-serif",
              whiteSpace: "nowrap", transition: "all 0.2s",
            }}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Screen content */}
      <div style={{ maxWidth: 900, margin: "0 auto", padding: "20px" }}>
        {renderScreen()}
      </div>
    </div>
  );
}
