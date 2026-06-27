# Headroom — Token Optimization R&D Brief
**Date:** 2026-06-27  
**Author:** Director R&D session  
**Sources:** GitHub repo + 8 official documentation pages (all fetched live)  
**Purpose:** Evaluate Headroom for MeeSell Gemini cost reduction (category-picker at ₹0.09–0.20/call vs ≤₹0.05 ceiling)

---

## Table of Contents

1. [What is Headroom?](#1-what-is-headroom)
2. [Architecture Deep-Dive](#2-architecture-deep-dive)
3. [Token Optimization Techniques](#3-token-optimization-techniques)
4. [Installation & Setup](#4-installation--setup)
5. [Integration Methods](#5-integration-methods)
6. [CLI Reference](#6-cli-reference)
7. [Benchmarks & Performance](#7-benchmarks--performance)
8. [Deployment Options](#8-deployment-options)
9. [MeeSell Evaluation & Recommendation](#9-mesell-evaluation--recommendation)

---

## 1. What is Headroom?

Headroom is an open-source **context compression middleware** that reduces token usage by **60–95%** for AI agents and LLMs while maintaining answer accuracy. It operates between your application and the LLM provider, intercepting API calls, compressing the content, and forwarding the optimized request.

**Core problem it solves:** LLM token costs scale linearly with input size. Tool outputs, RAG chunks, logs, category trees, and conversation history bloat every prompt. Headroom strips this down using deterministic statistical compression — no LLM-based summarization, no hallucination risk, no extra API cost.

**Project vitals (as of 2026-06-27):**
- GitHub: https://github.com/headroomlabs-ai/headroom
- Stars: 52,300 | Forks: 3,700 | Releases: 157 | Commits: 1,763
- License: Apache 2.0
- Language split: Python 79.5%, Rust 15.8%, TypeScript 2.6%
- Requires: Python 3.10+

**Four deployment modes:**

| Mode | Description | Code changes required |
|------|-------------|----------------------|
| Library | `compress()` function in Python/TypeScript | Yes (minimal — 2 lines) |
| Proxy | Drop-in HTTP proxy server | None |
| Agent wrapper | CLI `headroom wrap claude` | None |
| MCP server | Model Context Protocol integration | None |

---

## 2. Architecture Deep-Dive

### 2.1 High-Level Request Flow

```
Your Application (FastAPI / Angular / CLI)
          │
          ▼
  ┌──────────────────────────────────────┐
  │           Headroom Layer             │
  │                                      │
  │  Step 1: Parse messages              │
  │    └─ Decompose into semantic blocks │
  │    └─ Count tokens per block         │
  │    └─ Detect waste signals           │
  │                                      │
  │  Step 2: Route content               │
  │    └─ ContentRouter picks compressor │
  │    └─ JSON → SmartCrusher           │
  │    └─ Code → CodeCompressor          │
  │    └─ Images → MiniLM router         │
  │                                      │
  │  Step 3: Transform pipeline          │
  │    └─ Cache Aligner                  │
  │    └─ Smart Crusher (default)        │
  │    └─ ML Compressor (optional)       │
  │    └─ Rolling Window                 │
  │    └─ Intelligent Context Manager    │
  │                                      │
  │  Step 4: Cache check                 │
  │    └─ Semantic cache (LRU + TTL)     │
  │                                      │
  │  Step 5: Budget enforcement          │
  │    └─ Daily USD spend limit check    │
  └──────────────────────────────────────┘
          │  Optimized request (60–95% fewer tokens)
          ▼
  LLM Provider API
  (Anthropic / OpenAI / Gemini)
          │
          ▼
  Response (unchanged) → back to your application
```

### 2.2 Core Components

| Component | Location | Role |
|-----------|----------|------|
| `HeadroomClient` | `client.py` | Transparent wrapper around native LLM clients; orchestrates pipeline |
| `Providers` | `providers/` | Provider-specific token counting (tiktoken for OpenAI, custom for Anthropic/Google); context window limits |
| `Parser` | `parser.py` | Decomposes messages into blocks (system, user, tool_call, tool_result); counts tokens; detects waste signals (JSON >500 tokens, base64, HTML tags) |
| `ContentRouter` | `transforms/` | Detects content type; routes to appropriate compressor per content |
| `SmartCrusher` | `transforms/smart_crusher.py` | **Default** statistical JSON compressor — the workhorse |
| `CodeCompressor` | `transforms/code.py` | AST-aware compression for Python, JS, Go, Rust, Java, C++ |
| `Kompress-base` | HuggingFace model | ModernBERT ML token classifier (optional, higher compression, higher latency) |
| `CacheAligner` | `transforms/cache_aligner.py` | Stabilizes system prompt prefixes for provider KV cache hits |
| `CCR` | `storage/` | Reversible compression with local SHA256-indexed retrieval (5-min TTL default) |
| `Storage` | SQLite / JSON Lines | Request logging: tokens before/after, transforms applied, savings |

### 2.3 Transform Pipeline (Sequential, Fixed Order)

```
Transform 1: Cache Aligner  [ALWAYS ON]
  ├─ Extracts dynamic content (dates, UUIDs, auth tokens) from system prompts
  ├─ Creates stable prefixes → enables provider-level KV cache hits
  └─ Moves temporal data to message end (preserved, just repositioned)

Transform 2: Tool Crusher  [DISABLED by default]
  ├─ Naive approach: keeps first N items only
  └─ Disabled: discards potentially important tail data

Transform 3: Smart Crusher  [DEFAULT — main token reducer]
  ├─ Field Analysis: calculates unique ratios + variance per JSON field
  ├─ Pattern Detection: classifies arrays as:
  │   - time_series → preserve change points, compress stable regions
  │   - logs → cluster similar messages
  │   - search_results → rank by score, drop lower-ranked duplicates
  │   - generic → factor out constant fields
  └─ Result: 70–95% reduction on JSON arrays

Transform 4: ML Compressor (Kompress)  [OPTIONAL — install: headroom-ai[ml]]
  ├─ ModernBERT token classifier
  ├─ Higher compression than SmartCrusher
  └─ Higher latency (~200ms vs ~10ms for SmartCrusher)

Transform 5: Rolling Window  [CONTEXT LIMIT ENFORCER]
  ├─ Enforces model context window limits
  ├─ Drops oldest messages first
  └─ Atomic: tool_call + tool_result always drop together

Transform 6: Intelligent Context Manager  [SMART DROPPER]
  ├─ Semantic importance scoring per message:
  │   - Recency: 20%
  │   - Semantic similarity to recent context: 20%
  │   - TOIN learned importance: 25%
  │   - Error indicators: 15%
  │   - Forward references: 15%
  │   - Token density: 5%
  └─ Drops lowest-scored messages; always preserves critical errors
```

### 2.4 CCR — Compress-Cache-Retrieve (Reversible Compression)

Six-phase system allowing the LLM to recover full content on demand:

1. **Compression Store** — Original content stored locally, SHA256-hashed, 5-min TTL (configurable)
2. **Retrieval API** — `POST /v1/retrieve` returns original by hash; BM25 search within cache
3. **Tool Injection** — LLM told about retrieval via system message; compressed JSON embeds `__headroom_hash` markers
4. **Feedback Loop** — Tracks per-tool retrieval rate (>50% = too aggressive; auto-tunes)
5. **Response Handler** — Intercepts LLM responses with `headroom_retrieve` tool calls; auto-executes; continues up to 3 iterations
6. **Context Tracker** — Multi-turn awareness; proactively expands relevant compressed data on keyword match

### 2.5 Image Compression Pipeline

A trained MiniLM router (93.7% classification accuracy) selects technique per provider:

| Provider | Technique | Token Savings |
|----------|-----------|---------------|
| OpenAI | `detail="low"` parameter | ~87% |
| Anthropic | PIL resize to 512px | ~75% |
| Google (Gemini) | PIL resize to 768px | ~75% |

Image compression runs **before** text compression in the pipeline.

### 2.6 Key Design Principles

| Principle | What it means for reliability |
|-----------|-------------------------------|
| **Deterministic** | No LLM calls for compression; ~10ms overhead; zero extra API cost |
| **Provider-agnostic** | Works with OpenAI, Anthropic, Groq, local models; Google via adapters |
| **Safety-first** | Never modifies user/assistant message text; only compresses tool outputs and injected context |
| **Atomic tool handling** | tool_call + tool_result always drop together, never split |

---

## 3. Token Optimization Techniques

Complete list of all techniques documented:

| Technique | When Triggered | Typical Savings |
|-----------|----------------|-----------------|
| **Cache Aligner** | Always; system prompt stabilization | 10–30% (via provider KV cache hits) |
| **Smart Crusher** | JSON arrays, log arrays, search result arrays | 70–95% |
| **Code Compressor** | Python/JS/Go/Rust/Java/C++ AST content | Variable |
| **ML Compressor (Kompress)** | Optional; maximum compression mode | Higher than SmartCrusher |
| **Rolling Window** | Context limit enforcement | Drops tail messages |
| **Intelligent Context Manager** | Long multi-turn conversations | Preserves critical, drops low-importance |
| **CCR** | Reversible compression for agentic loops | Aggressive; LLM can retrieve originals |
| **Image Compression** | Image inputs (Vision models) | 75–87% |
| **Output Token Reduction** | LLM response verbosity trimming | Variable |
| **Semantic Caching** | Repeat/similar queries | 100% for cache hits |

---

## 4. Installation & Setup

### 4.1 Python Installation

```bash
# Core library only
pip install headroom-ai

# With proxy server (recommended for MeeSell backend integration)
pip install "headroom-ai[proxy]"

# With ML compressor (higher compression, higher latency)
pip install "headroom-ai[ml]"

# With image compression
pip install "headroom-ai[image]"

# Everything
pip install "headroom-ai[all]"
```

**All available extras:** `[proxy]`, `[mcp]`, `[ml]`, `[code]`, `[memory]`, `[image]`, `[langchain]`, `[agno]`, `[pytorch-mps]`

### 4.2 Node.js / TypeScript

```bash
npm install headroom-ai
```

### 4.3 Docker / Script Install

```bash
# One-line script installer (binary + dependencies)
curl -fsSL https://raw.githubusercontent.com/chopratejas/headroom/main/scripts/install.sh | bash

# Deploy as persistent background service
headroom install apply --preset persistent-service --providers auto

# Deploy as Docker container
headroom install apply --preset persistent-docker
```

### 4.4 Starting the Proxy

```bash
headroom proxy --port 8787
```

**All proxy configuration flags:**

| Flag | Default | Purpose |
|------|---------|---------|
| `--host` | `127.0.0.1` | Binding address |
| `--port` | `8787` | Server port |
| `--mode` | `token` | Optimization strategy: `token` (reduce tokens) or `cache` (prefix cache stability) |
| `--no-cache` | `false` | Disable semantic caching |
| `--budget` | `None` | Daily USD spending limit (enforced per session) |
| `--backend` | auto | Target LLM provider |
| `--memory` | auto | Memory backend |
| `--verbose` | false | Verbose logging |
| `--learn` | false | Enable failure learning |

### 4.5 Verification Commands

```bash
# Health check
curl http://localhost:8787/health
# → {"status": "healthy"}

# Compression stats for current session
curl http://localhost:8787/stats

# Durable compression history
curl http://localhost:8787/stats-history

# Prometheus metrics
curl http://localhost:8787/metrics

# Check savings via CLI
headroom perf
```

---

## 5. Integration Methods

### 5.1 Method A: Proxy Mode — Zero Code Changes (Anthropic/OpenAI)

```bash
# Terminal 1: start proxy
headroom proxy --port 8787

# Terminal 2: point your SDK to the proxy
export ANTHROPIC_BASE_URL=http://localhost:8787
# All your existing code is unchanged
```

For Claude Code agents:
```bash
ANTHROPIC_BASE_URL=http://localhost:8787 claude
```

### 5.2 Method B: Proxy Mode — OpenAI SDK Clients

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8787/v1",
    api_key="your-api-key"
)
# Use identically to the normal OpenAI client
```

### 5.3 Method C: `compress()` SDK Function — Universal (ANY LLM including Gemini)

```python
from headroom import compress

# Before calling your LLM
optimized_messages, metrics = compress(messages, model="gemini-2.5-flash")

print(f"Tokens saved: {metrics.tokens_saved}")
print(f"Compression ratio: {metrics.compression_ratio}")
print(f"Transforms applied: {metrics.transforms_applied}")

# Then call your LLM with the optimized messages
response = await gemini_client.generate_content_async(optimized_messages)
```

Source: "Works with any LLM client." — Integration Guide

### 5.4 Method D: HeadroomClient Wrapper (Python SDK)

```python
from headroom import HeadroomClient, AnthropicProvider
from anthropic import Anthropic

client = HeadroomClient(
    original_client=Anthropic(),
    provider=AnthropicProvider(),
    default_mode="optimize",
)

# Use identically to the standard Anthropic client
response = client.messages.create(...)
stats = client.get_stats()          # token savings metrics
client.validate_setup()             # verify configuration
```

### 5.5 Method E: FastAPI ASGI Middleware

```python
from headroom.middleware import CompressionMiddleware
from fastapi import FastAPI

app = FastAPI()
app.add_middleware(CompressionMiddleware)

# Response headers will include:
# x-headroom-compressed: true
# x-headroom-tokens-saved: 1842
```

### 5.6 Method F: LiteLLM Callback (100+ providers, including Gemini)

```python
import litellm
from headroom.callbacks import HeadroomCallback

litellm.callbacks = [HeadroomCallback()]

# All litellm calls now auto-compressed
# Works with Gemini, OpenAI, Anthropic, Groq, etc.
response = litellm.completion(model="gemini/gemini-2.5-flash", messages=messages)
```

### 5.7 Method G: LangChain Integration

```python
from headroom.langchain import HeadroomChatModel

model = HeadroomChatModel(base_model=your_chat_model)
```

### 5.8 Method H: TypeScript/Node.js

```typescript
import { compress } from 'headroom-ai';

const [optimizedMessages, metrics] = await compress(messages, {
  model: 'gpt-4o'
});
```

### 5.9 Compression Tuning Options

```python
# From quickstart guide — configuration parameters

# Adjust compression aggressiveness
compress(messages, model="...", max_items_after_crush=50)

# Skip compression for specific tools
compress(messages, model="...", headroom_tool_profiles={"my_tool": "skip"})

# Target minimum items retained
compress(messages, model="...", min_items_to_retain=10)
```

### 5.10 Latency Impact

Source: Integration Guide
> "15–200ms depending on content size"

Source: Benchmarks Page
- P50 (median): **52ms**
- P90: **309ms**
- P99: **4,172ms**

Pipeline breakdown at P50:
- Content routing: 11.7ms
- SmartCrusher JSON: 50.1ms

---

## 6. CLI Reference

### 6.1 Proxy & Agent Commands

```bash
# Start proxy
headroom proxy [--port 8787] [--host 127.0.0.1] [--mode token|cache] [--budget USD] [--verbose]

# Wrap an agent through the proxy (zero config required)
headroom wrap claude           # Claude Code
headroom wrap codex            # Codex CLI
headroom wrap copilot          # GitHub Copilot CLI
headroom wrap aider            # Aider
headroom wrap cursor           # Cursor editor
headroom wrap openclaw         # OpenClaw plugin
headroom unwrap openclaw       # Remove OpenClaw integration

# View performance metrics
headroom perf [--window 24h|7d|30d]

# Analyze tool failures → write corrections to agent config files
headroom learn [--agent claude] [--project /path/to/project]
```

### 6.2 Memory Management

```bash
headroom memory list [--session X] [--scope X] [--age Xd] [--search "query"]
headroom memory show <id>
headroom memory edit <id>
headroom memory delete <id1> [<id2> ...]
headroom memory prune [--age Xd] [--scope X] [--importance X]
headroom memory purge          # Delete ALL memories (requires confirmation)
headroom memory export > backup.json
headroom memory import < backup.json
```

### 6.3 Persistent Deployment

```bash
# Deploy
headroom install apply --preset persistent-service --providers auto
headroom install apply --preset persistent-task
headroom install apply --preset persistent-docker

# Lifecycle management
headroom install status
headroom install start
headroom install stop
headroom install restart
headroom install remove
```

### 6.4 Evaluation / Benchmarking

```bash
# Run LoCoMo memory benchmark
headroom evals memory [--conversations N] [--categories X] [--judge-model Y]
headroom evals memory-v2       # V2 with LLM-controlled memory tools
```

### 6.5 MCP Integration (Claude Code)

```bash
headroom mcp install           # Install as MCP tool in Claude Code
headroom mcp uninstall
headroom mcp status
headroom mcp serve             # Run MCP server
```

### 6.6 Proxy API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/livez` | GET | Liveness probe (K8s compatible) |
| `/readyz` | GET | Readiness with subsystem checks |
| `/health` | GET | Aggregate health status |
| `/stats` | GET | Session compression metrics |
| `/stats-history` | GET | Durable compression history |
| `/metrics` | GET | Prometheus-format metrics |
| `/v1/messages` | POST | Anthropic-format LLM requests |
| `/v1/chat/completions` | POST | OpenAI-format LLM requests |
| `/v1/compress` | POST | Compression-only (no LLM call) |
| `/v1/retrieve` | POST | Retrieve compressed content by hash |

---

## 7. Benchmarks & Performance

*Source: https://headroomlabs-ai.github.io/headroom/benchmarks/ — fetched 2026-06-27*

### 7.1 Token Reduction by Content Type

| Content Type | Compression Rate | Notes |
|---|---|---|
| JSON arrays (100 items) | **90.6%** | Production log entries; 4/4 correct answers maintained |
| JSON arrays (500 items) | **83.1%** | Larger arrays; slightly less efficient |
| Build logs | **93.9%** | Very high repetition |
| Shell output | **85.5%** | Mixed content |
| HTML extraction | **94.9%** | Scrapinghub benchmark, 181 pages |
| Long agent sessions | **40–80%** | Mix of JSON, logs, history |
| Short conversations | **4.8%** | Minimal value on brief exchanges |
| Source code (raw) | **0%** | Passed through unchanged by default |

**Fleet-wide results:** 1.4 billion tokens saved across 249 opt-in instances; ~$4,000 USD saved.

### 7.2 Accuracy (Quality Preservation)

| Benchmark | Task | Result |
|---|---|---|
| GSM8K | Mathematical reasoning | Maintains baseline |
| TruthfulQA | Factual accuracy | Maintains baseline |
| BFCL | Function/tool calling | Maintains baseline |
| HTML Extraction | F1 score | **0.919** |
| HTML Extraction | Recall | **0.982** |
| HTML Extraction | Precision | **0.879** |
| JSON QA (100-item array) | Answer correctness | **4/4 (100%)** at 87.6% compression |

### 7.3 Latency Overhead

| Percentile | Added Latency |
|---|---|
| P50 (median) | **52ms** |
| P90 | **309ms** |
| P99 | **4,172ms** |

SmartCrusher P50 breakdown: content routing 11.7ms + JSON compression 50.1ms.

### 7.4 Real-World Case Results

| Use Case | Before | After | Reduction | Quality |
|---|---|---|---|---|
| Code search (100 results) | 17,765 tokens | 1,408 tokens | **92%** | Maintained |
| GitHub issue triage | 54,174 tokens | 14,761 tokens | **73%** | Maintained |
| SRE incident (5 tool calls) | 22,048 tokens | 2,190 tokens | **90%** | 5.0/5 |

### 7.5 Benchmark Caveats

- Source code compression is **0%** by default (code semantics are brittle under compression)
- Short conversations (<5 turns, no tool outputs) show only ~4.8% savings
- P99 latency of 4.1s is an occasional spike, not sustained degradation
- Fleet data from 50,000+ proxy sessions with telemetry opt-in (default: off)

---

## 8. Deployment Options

### 8.1 macOS (Development — LaunchAgent with auto-restart)

```bash
# Automated installer
cd examples/deployment/macos-launchagent
./install.sh --port 8787

# Service management
launchctl print gui/$(id -u)/com.headroom.proxy   # status
tail -f ~/Library/Logs/headroom/proxy.log           # logs
launchctl kickstart -k gui/$(id -u)/com.headroom.proxy  # restart

# Uninstall
./uninstall.sh
```

**Shell auto-integration** (sets `ANTHROPIC_BASE_URL` when proxy is running):
```bash
source /path/to/headroom/examples/deployment/macos-launchagent/shell-integration.sh
```

### 8.2 Docker

```bash
headroom install apply --preset persistent-docker
```

### 8.3 Kubernetes / K3s (MeeSell's production platform — no official chart)

The proxy is a stateless HTTP server — deployable as a standard K8s Deployment:

```yaml
# headroom-proxy-deployment.yaml (draft for MeeSell)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: headroom-proxy
  namespace: mesell-dev
spec:
  replicas: 1
  selector:
    matchLabels:
      app: headroom-proxy
  template:
    metadata:
      labels:
        app: headroom-proxy
    spec:
      containers:
      - name: headroom
        image: python:3.12-slim
        command:
        - sh
        - -c
        - "pip install 'headroom-ai[proxy]' && headroom proxy --port 8787 --host 0.0.0.0"
        ports:
        - containerPort: 8787
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: mesell-secrets
              key: anthropic_api_key
        readinessProbe:
          httpGet:
            path: /readyz
            port: 8787
        livenessProbe:
          httpGet:
            path: /livez
            port: 8787
---
apiVersion: v1
kind: Service
metadata:
  name: headroom-proxy-svc
  namespace: mesell-dev
spec:
  selector:
    app: headroom-proxy
  ports:
  - port: 8787
    targetPort: 8787
```

### 8.4 Cloud (ECS / Cloud Run)

Docs explicitly recommend for production: "Cloud-native solutions (ECS, Cloud Run)."  
GCP Cloud Run in `asia-south1` = same region as MeeSell's K3s cluster → minimal network latency.

### 8.5 Monitoring Integration

- `/metrics` → Prometheus scrape (MeeSell already has Prometheus in K3s)
- `/stats` → per-session compression dashboard
- `/stats-history` → durable history for cost auditing

### 8.6 Apple Silicon GPU Optimization (macOS dev machines)

```bash
pip install 'headroom-ai[pytorch-mps]'
export HEADROOM_EMBEDDER_RUNTIME=pytorch_mps
```

---

## 9. MeeSell Evaluation & Recommendation

### 9.1 The Problem Being Solved

MeeSell's AI category-picker (Feature 2) uses Gemini 2.5 Flash to suggest top-3 leaf categories from a 3,772-node Meesho category tree. Current cost: **₹0.09–0.20 per call** vs ceiling of **≤₹0.05 per call** (2–4× over budget).

Root cause: each call serializes a large JSON structure (the full tree or a pre-filtered subset) as context. This is the dominant token consumer.

### 9.2 Can Headroom Proxy Gemini 2.5 Flash?

**Direct proxy support: No (Gemini format not natively supported by the HTTP proxy).**

The Headroom proxy natively handles:
- `POST /v1/messages` → Anthropic SDK format
- `POST /v1/chat/completions` → OpenAI SDK format

Gemini's native API uses `generateContent` — a different format.

**However, three paths work for Gemini:**

| Path | Mechanism | Gemini Support | Effort |
|------|-----------|----------------|--------|
| **`compress()` SDK function** | Call in `ai_engine.py` before Gemini call | ✅ Yes — universal, provider-agnostic | 2–4 hrs |
| **LiteLLM + HeadroomCallback** | Route Gemini through LiteLLM; add callback | ✅ Yes — LiteLLM covers Gemini | 8–12 hrs (adds dependency) |
| **ASGI CompressionMiddleware** | Intercepts message content at FastAPI layer | ✅ Yes — compresses content, not protocol | 4–8 hrs |

**Recommended path for MeeSell: `compress()` SDK function in `ai_engine.py`.**

### 9.3 Realistic Token Savings for Category-Picker

The category tree that goes into each Gemini call is a JSON array. Based on Headroom benchmarks on JSON arrays:

| Array Size | Documented Compression |
|---|---|
| 100 items | 90.6% |
| 500 items | 83.1% |
| ~3,772 nodes (estimated) | **~75–85%** |

The existing smart-picker ML pre-filter already trims the 3,772-node tree before calling Gemini. If the filtered candidate set is 50–200 nodes (likely), SmartCrusher compresses it by **83–91%**.

**Cost projection:**

| Scenario | Current Cost | After Compression | vs Ceiling |
|---|---|---|---|
| Full tree (3,772 nodes) | ₹0.20/call | ₹0.03–0.05 | ✅ At or under |
| Pre-filtered (50–200 nodes) | ₹0.09/call | ₹0.01–0.02 | ✅ Well under |

**Conclusion: The ≤₹0.05 ceiling is achievable.** This is the single most impactful optimization available without changing the LLM or prompt strategy.

### 9.4 Additional MeeSell Use Cases Beyond Category-Picker

| Feature | Content Type | Expected Savings |
|---|---|---|
| **Catalog autofill** (Feature 4) | Repeating product description prompts + category schema context | 60–80% |
| **Image precheck** (Feature 5) | Gemini Vision calls with base64 image data | 75% (native Google PIL resize) |
| **Quality gate** | Repeated rule evaluation with JSON attribute sets | 70–85% |
| **Cross-session memory** | `headroom memory` for agent memory persistence | Built-in feature |

### 9.5 Integration Effort Estimate

| Approach | Files Changed | Dev Effort | Risk |
|---|---|---|---|
| **`compress()` in `ai_engine.py`** | 1 file | **2–4 hrs** | Low |
| **ASGI `CompressionMiddleware`** | 1 file (`main.py`) | **4–8 hrs** | Low–Medium |
| **K3s sidecar proxy** | New K8s manifest + env vars | **8–16 hrs** | Medium (no Gemini native format) |
| **LiteLLM + HeadroomCallback** | requirements.txt + ai_engine.py | **8–12 hrs** | Medium (adds LiteLLM dependency) |

### 9.6 Latency Assessment for Real-Time Category-Suggest

| Latency | Assessment for MeeSell |
|---|---|
| P50: **52ms** | ✅ Negligible — Gemini call itself takes 800ms–2s |
| P90: **309ms** | ✅ Acceptable — total response under 2.5s |
| P99: **4,172ms** | ⚠️ Borderline — rare spikes could hurt interactive UX |

**Mitigation:** Call `compress()` with an async timeout (e.g., 500ms). On timeout → send uncompressed (cost impact) rather than blocking the user. Log timeout events to tune the threshold.

### 9.7 Deployment Strategy for MeeSell

**Simplest (recommended first step):** No separate service — `pip install "headroom-ai"` + call `compress()` inline in `ai_engine.py`. Runs in-process. No K8s changes, no new secrets.

**If expanding to proxy mode later:**
- Deploy as a K3s Deployment in `mesell-dev` namespace (manifest draft in §8.3)
- Use LiteLLM as intermediary to handle Gemini format conversion
- Hook `/metrics` into existing Prometheus scraping config
- No Traefik ingress needed (internal cluster traffic only)

### 9.8 Risks & Limitations

| Risk | Severity | Mitigation |
|---|---|---|
| SmartCrusher strips category node attributes needed for accurate suggestion | 🔴 High | **Run golden eval fixtures before shipping**; tune `max_items_after_crush` |
| Pre-filtered candidate set may already be small enough that further compression yields diminishing returns | 🟡 Medium | Measure actual savings with `metrics.compression_ratio` after integration |
| CCR retrieval adds Gemini API calls (Gemini calls `headroom_retrieve`) | 🟡 Medium | **Disable CCR for category-picker** — it's a single-turn call, not an agentic loop |
| No official Gemini provider for token counting in Providers module | 🟢 Low | `compress()` still works — falls back to character-based token estimation |
| P99 latency spikes (4.1s) | 🟡 Medium | Async compress + timeout + fallback to uncompressed |
| Source code is passed through at 0% compression | 🟢 Low | Category tree is JSON, not code — SmartCrusher handles it |

### 9.9 What Headroom Does NOT Do

- Does **not** cache Gemini responses (compresses inputs; semantic cache is only for repeat identical queries)
- Does **not** batch multiple user requests into one API call
- Does **not** replace prompt engineering (category tree pre-filtering still needed and still valuable)
- Does **not** guarantee Gemini-native HTTP proxy support without LiteLLM as intermediary
- Does **not** help with short conversations or pure code sessions (minimal or 0% savings there)

### 9.10 Recommended Action Plan

**Verdict: INTEGRATE NOW — SDK path, one sprint.**

| Step | Owner | Effort | Success Criteria |
|---|---|---|---|
| 1. Add `headroom-ai` to `backend/requirements.txt` | meesell-backend-coordinator | 30 min | Package installs cleanly |
| 2. Add `compress(messages, model="gemini-2.5-flash")` call in `ai_engine.py` before each Gemini invocation | meesell-services-builder | 2–3 hrs | Compression metrics logging in backend logs |
| 3. Log `metrics.tokens_saved` and `metrics.compression_ratio` per AI call type | meesell-services-builder | 1 hr | Cost dashboard shows savings |
| 4. Run category-picker golden eval with compressed vs uncompressed inputs | meesell-qa-coordinator | 2–3 hrs | Top-3 accuracy ≥ baseline |
| 5. Measure cost/call delta across 100 representative calls | Director | 30 min | ≤₹0.05/call confirmed |
| 6. If accuracy drop: tune `max_items_after_crush` or disable SmartCrusher for this call site | meesell-ai-coordinator | 1–2 hrs | Accuracy restored |
| 7. Roll out to catalog-autofill and image-precheck AI calls | meesell-services-builder | 2–3 hrs | Full AI fleet compressed |

**Total estimate: 10–13 hours end-to-end.**

**Fallback:** If SmartCrusher hurts accuracy, use **CacheAligner-only** mode (removes dynamic date/UUID churn from prompts → 10–30% savings with zero accuracy risk, free speedup via provider KV cache).

---

## Sources

All pages fetched live on 2026-06-27. No training-data assumptions used.

| Page | URL |
|---|---|
| GitHub Repo | https://github.com/headroomlabs-ai/headroom |
| Homepage | https://headroomlabs-ai.github.io/headroom/ |
| Quickstart | https://headroomlabs-ai.github.io/headroom/quickstart/ |
| User Guide / Proxy | https://headroomlabs-ai.github.io/headroom/proxy/ |
| Integration Guide | https://headroomlabs-ai.github.io/headroom/integration-guide/ |
| Architecture | https://headroomlabs-ai.github.io/headroom/ARCHITECTURE/ |
| Benchmarks | https://headroomlabs-ai.github.io/headroom/benchmarks/ |
| CLI Reference | https://headroomlabs-ai.github.io/headroom/cli/ |
| macOS Deployment | https://headroomlabs-ai.github.io/headroom/macos-deployment/ |
