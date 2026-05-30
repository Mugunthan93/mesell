import { useState, useRef, useEffect } from "react";

const SECTIONS = [
  { id: "partners", label: "Key Partners", icon: "🤝", hint: "Who are your key partners and suppliers?", row: "1/2", col: "1/2" },
  { id: "activities", label: "Key Activities", icon: "⚡", hint: "What key activities does your value proposition require?", row: "1/2", col: "2/3" },
  { id: "resources", label: "Key Resources", icon: "🧱", hint: "What key resources does your value proposition require?", row: "2/3", col: "2/3" },
  { id: "value", label: "Value Propositions", icon: "💎", hint: "What value do you deliver to the customer?", row: "1/3", col: "3/4" },
  { id: "relationships", label: "Customer Relationships", icon: "💬", hint: "What relationship does each customer segment expect?", row: "1/2", col: "4/5" },
  { id: "channels", label: "Channels", icon: "📡", hint: "Through which channels do your segments want to be reached?", row: "2/3", col: "4/5" },
  { id: "segments", label: "Customer Segments", icon: "👥", hint: "For whom are you creating value?", row: "1/3", col: "5/6" },
  { id: "costs", label: "Cost Structure", icon: "📉", hint: "What are the most important costs inherent in your model?", row: "3/4", col: "1/4" },
  { id: "revenue", label: "Revenue Streams", icon: "📈", hint: "For what value are your customers willing to pay?", row: "3/4", col: "4/6" },
];

const COLORS = {
  partners: "#E07A5F",
  activities: "#81B29A",
  resources: "#F2CC8F",
  value: "#3D405B",
  relationships: "#7B68EE",
  channels: "#F4845F",
  segments: "#48BFE3",
  costs: "#E56B6F",
  revenue: "#57CC99",
};

function SectionCard({ section, items, onAdd, onRemove, onEdit }) {
  const [input, setInput] = useState("");
  const [editIdx, setEditIdx] = useState(null);
  const [editVal, setEditVal] = useState("");
  const inputRef = useRef(null);
  const editRef = useRef(null);
  const color = COLORS[section.id];

  useEffect(() => {
    if (editIdx !== null && editRef.current) editRef.current.focus();
  }, [editIdx]);

  const handleAdd = () => {
    const v = input.trim();
    if (!v) return;
    onAdd(section.id, v);
    setInput("");
    inputRef.current?.focus();
  };

  const handleEditSave = (idx) => {
    const v = editVal.trim();
    if (v) onEdit(section.id, idx, v);
    setEditIdx(null);
  };

  return (
    <div
      style={{
        gridRow: section.row,
        gridColumn: section.col,
        background: "rgba(255,255,255,0.03)",
        borderRadius: 14,
        border: `1.5px solid ${color}22`,
        display: "flex",
        flexDirection: "column",
        overflow: "hidden",
        transition: "border-color 0.3s",
        position: "relative",
      }}
      onMouseEnter={(e) => (e.currentTarget.style.borderColor = color + "66")}
      onMouseLeave={(e) => (e.currentTarget.style.borderColor = color + "22")}
    >
      {/* Header */}
      <div
        style={{
          padding: "14px 16px 10px",
          display: "flex",
          alignItems: "center",
          gap: 8,
          borderBottom: `1px solid ${color}15`,
        }}
      >
        <span style={{ fontSize: 18 }}>{section.icon}</span>
        <span
          style={{
            fontFamily: "'DM Sans', sans-serif",
            fontWeight: 700,
            fontSize: 13,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
            color: color,
          }}
        >
          {section.label}
        </span>
        <span
          style={{
            marginLeft: "auto",
            fontSize: 11,
            color: "#888",
            fontFamily: "'JetBrains Mono', monospace",
            fontWeight: 500,
          }}
        >
          {items.length}
        </span>
      </div>

      {/* Items */}
      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: "8px 12px",
          display: "flex",
          flexDirection: "column",
          gap: 5,
          minHeight: 60,
        }}
      >
        {items.length === 0 && (
          <span
            style={{
              color: "#555",
              fontSize: 12,
              fontStyle: "italic",
              lineHeight: 1.5,
              padding: "4px 0",
              fontFamily: "'DM Sans', sans-serif",
            }}
          >
            {section.hint}
          </span>
        )}
        {items.map((item, idx) => (
          <div
            key={idx}
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 6,
              group: "item",
            }}
          >
            <span
              style={{
                width: 6, height: 6, minWidth: 6,
                borderRadius: "50%",
                background: color,
                marginTop: 6,
                opacity: 0.6,
              }}
            />
            {editIdx === idx ? (
              <input
                ref={editRef}
                value={editVal}
                onChange={(e) => setEditVal(e.target.value)}
                onBlur={() => handleEditSave(idx)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleEditSave(idx);
                  if (e.key === "Escape") setEditIdx(null);
                }}
                style={{
                  flex: 1,
                  background: "rgba(255,255,255,0.06)",
                  border: `1px solid ${color}44`,
                  borderRadius: 6,
                  color: "#e0e0e0",
                  fontSize: 13,
                  padding: "3px 8px",
                  fontFamily: "'DM Sans', sans-serif",
                  outline: "none",
                }}
              />
            ) : (
              <span
                onClick={() => {
                  setEditIdx(idx);
                  setEditVal(item);
                }}
                style={{
                  flex: 1,
                  color: "#ccc",
                  fontSize: 13,
                  lineHeight: 1.45,
                  cursor: "text",
                  fontFamily: "'DM Sans', sans-serif",
                  wordBreak: "break-word",
                }}
              >
                {item}
              </span>
            )}
            <button
              onClick={() => onRemove(section.id, idx)}
              style={{
                background: "none",
                border: "none",
                color: "#555",
                cursor: "pointer",
                fontSize: 14,
                lineHeight: 1,
                padding: "2px 4px",
                borderRadius: 4,
                transition: "color 0.2s",
              }}
              onMouseEnter={(e) => (e.target.style.color = "#e56b6f")}
              onMouseLeave={(e) => (e.target.style.color = "#555")}
              title="Remove"
            >
              ×
            </button>
          </div>
        ))}
      </div>

      {/* Input */}
      <div style={{ padding: "8px 12px 12px", display: "flex", gap: 6 }}>
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="Add item…"
          style={{
            flex: 1,
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.08)",
            borderRadius: 8,
            color: "#ddd",
            fontSize: 12,
            padding: "7px 10px",
            fontFamily: "'DM Sans', sans-serif",
            outline: "none",
            transition: "border-color 0.2s",
          }}
          onFocus={(e) => (e.target.style.borderColor = color + "55")}
          onBlur={(e) => (e.target.style.borderColor = "rgba(255,255,255,0.08)")}
        />
        <button
          onClick={handleAdd}
          style={{
            background: color + "22",
            border: `1px solid ${color}33`,
            borderRadius: 8,
            color: color,
            fontSize: 16,
            width: 32,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "all 0.2s",
            fontWeight: 700,
          }}
          onMouseEnter={(e) => {
            e.target.style.background = color + "44";
          }}
          onMouseLeave={(e) => {
            e.target.style.background = color + "22";
          }}
        >
          +
        </button>
      </div>
    </div>
  );
}

export default function BusinessModelCanvas() {
  const [title, setTitle] = useState("My New Business");
  const [editingTitle, setEditingTitle] = useState(false);
  const [data, setData] = useState(() => {
    const init = {};
    SECTIONS.forEach((s) => (init[s.id] = []));
    return init;
  });

  const addItem = (id, val) => setData((d) => ({ ...d, [id]: [...d[id], val] }));
  const removeItem = (id, idx) => setData((d) => ({ ...d, [id]: d[id].filter((_, i) => i !== idx) }));
  const editItem = (id, idx, val) =>
    setData((d) => ({ ...d, [id]: d[id].map((v, i) => (i === idx ? val : v)) }));

  const totalItems = Object.values(data).reduce((a, b) => a + b.length, 0);

  const handleExportJSON = () => {
    const blob = new Blob([JSON.stringify({ title, canvas: data }, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${title.replace(/\s+/g, "_")}_BMC.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const handleClear = () => {
    if (totalItems === 0) return;
    const init = {};
    SECTIONS.forEach((s) => (init[s.id] = []));
    setData(init);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "#111114",
        color: "#e0e0e0",
        fontFamily: "'DM Sans', sans-serif",
        padding: "24px 20px 40px",
      }}
    >
      <link
        href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=JetBrains+Mono:wght@500&family=Playfair+Display:wght@700;800&display=swap"
        rel="stylesheet"
      />

      {/* Header */}
      <div
        style={{
          maxWidth: 1200,
          margin: "0 auto 20px",
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 12,
        }}
      >
        <div>
          <div
            style={{
              fontSize: 10,
              letterSpacing: "0.15em",
              textTransform: "uppercase",
              color: "#666",
              marginBottom: 6,
              fontWeight: 500,
            }}
          >
            Business Model Canvas
          </div>
          {editingTitle ? (
            <input
              autoFocus
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              onBlur={() => setEditingTitle(false)}
              onKeyDown={(e) => e.key === "Enter" && setEditingTitle(false)}
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: 30,
                fontWeight: 800,
                background: "transparent",
                border: "none",
                borderBottom: "2px solid #7B68EE55",
                color: "#eee",
                outline: "none",
                padding: "0 0 4px",
                width: "100%",
                maxWidth: 500,
              }}
            />
          ) : (
            <h1
              onClick={() => setEditingTitle(true)}
              style={{
                fontFamily: "'Playfair Display', serif",
                fontSize: 30,
                fontWeight: 800,
                margin: 0,
                cursor: "text",
                color: "#eee",
                letterSpacing: "-0.01em",
              }}
              title="Click to edit"
            >
              {title}
            </h1>
          )}
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          <span
            style={{
              fontSize: 11,
              color: "#666",
              fontFamily: "'JetBrains Mono', monospace",
              marginRight: 6,
            }}
          >
            {totalItems} item{totalItems !== 1 ? "s" : ""}
          </span>
          <button
            onClick={handleClear}
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.08)",
              borderRadius: 8,
              color: "#888",
              fontSize: 12,
              padding: "7px 14px",
              cursor: "pointer",
              fontFamily: "'DM Sans', sans-serif",
              fontWeight: 500,
              transition: "all 0.2s",
            }}
            onMouseEnter={(e) => {
              e.target.style.borderColor = "#e56b6f55";
              e.target.style.color = "#e56b6f";
            }}
            onMouseLeave={(e) => {
              e.target.style.borderColor = "rgba(255,255,255,0.08)";
              e.target.style.color = "#888";
            }}
          >
            Clear All
          </button>
          <button
            onClick={handleExportJSON}
            style={{
              background: "linear-gradient(135deg, #7B68EE22, #48BFE322)",
              border: "1px solid #7B68EE33",
              borderRadius: 8,
              color: "#b8b0ff",
              fontSize: 12,
              padding: "7px 16px",
              cursor: "pointer",
              fontFamily: "'DM Sans', sans-serif",
              fontWeight: 600,
              transition: "all 0.2s",
            }}
            onMouseEnter={(e) => {
              e.target.style.background = "linear-gradient(135deg, #7B68EE33, #48BFE333)";
            }}
            onMouseLeave={(e) => {
              e.target.style.background = "linear-gradient(135deg, #7B68EE22, #48BFE322)";
            }}
          >
            Export JSON ↓
          </button>
        </div>
      </div>

      {/* Canvas Grid */}
      <div
        style={{
          maxWidth: 1200,
          margin: "0 auto",
          display: "grid",
          gridTemplateColumns: "repeat(5, 1fr)",
          gridTemplateRows: "minmax(180px, auto) minmax(180px, auto) minmax(160px, auto)",
          gap: 10,
        }}
      >
        {SECTIONS.map((s) => (
          <SectionCard
            key={s.id}
            section={s}
            items={data[s.id]}
            onAdd={addItem}
            onRemove={removeItem}
            onEdit={editItem}
          />
        ))}
      </div>

      {/* Footer */}
      <div
        style={{
          maxWidth: 1200,
          margin: "20px auto 0",
          textAlign: "center",
          fontSize: 11,
          color: "#444",
          fontFamily: "'JetBrains Mono', monospace",
        }}
      >
        Click any section title to add items · Click items to edit · Export when ready
      </div>
    </div>
  );
}
