# MeeSell — R&D Artifacts & Documentation

> All artifacts generated during the MeeSell R&D and planning phase.  
> Place this `docs/` folder inside your `meesell/` project root.

## Folder Structure

```
docs/
├── 01-rnd/                              # Market Research & Gap Analysis
│   ├── meesho-rnd-analysis.jsx          # 6 problem statements with opportunity scores
│   ├── catalog-solution-landscape.jsx   # Catalog problem: 9 approaches, 30+ players, pricing
│   ├── all-problems-map.jsx             # All 6 problems mapped with competitive landscape
│   └── unit-economics.jsx               # Partner costs, COGS per tier, margin analysis
│
├── 02-architecture/                     # Solution Design
│   ├── business-model-canvas.jsx        # Empty editable BMC template
│   ├── meesell-business-model-canvas.jsx # Populated BMC with all R&D data
│   ├── solution-architecture.jsx        # 6 modules, tech stack, pricing, roadmap, moat
│   └── meesho-integration-map.jsx       # 5 integration methods (CSV → Chrome Ext → API)
│
├── 03-wireframes/                       # UI Design
│   └── meesell-wireframes.jsx           # 7 interactive screens (onboarding → export)
│
├── 04-documents/                        # Single Source of Truth (Word docs)
│   ├── MeeSell_Product_Document.docx    # Vision, modules, user flows, roadmap
│   ├── MeeSell_Business_Document.docx   # BMC, competitive landscape, pricing, GTM
│   └── MeeSell_Technical_Document.docx  # Architecture, DB schema, API spec, K3s infra
│
└── 05-specs/                            # Technical Specifications (Markdown)
    ├── meesell-mvp-tech-spec.md         # Full MVP spec: DB, API, AI pipeline, QualityGate
    └── meesell-infra-spec-gcp-k3s.md    # GCP + K3s + Valkey infrastructure spec
```

## How to View Interactive Artifacts (.jsx)

The `.jsx` files are React components. To view them:

1. Open them in Claude.ai by uploading and asking "render this artifact"
2. Or paste into any React sandbox (CodeSandbox, StackBlitz)
3. Or integrate into a Vite + React project

## Key Artifacts by Purpose

| Need | File |
|------|------|
| What problems are we solving? | `01-rnd/meesho-rnd-analysis.jsx` |
| Who are the competitors? | `01-rnd/catalog-solution-landscape.jsx` + `all-problems-map.jsx` |
| What's the business model? | `02-architecture/meesell-business-model-canvas.jsx` |
| How does it connect to Meesho? | `02-architecture/meesho-integration-map.jsx` |
| What does the UI look like? | `03-wireframes/meesell-wireframes.jsx` |
| What are the costs? | `01-rnd/unit-economics.jsx` |
| Full product spec? | `04-documents/MeeSell_Product_Document.docx` |
| Full business spec? | `04-documents/MeeSell_Business_Document.docx` |
| Full tech spec? | `05-specs/meesell-mvp-tech-spec.md` |
| K3s deployment? | `05-specs/meesell-infra-spec-gcp-k3s.md` |
