# Vendored third-party skills — attribution & notice

Six cross-cutting engineering-discipline skills in this directory are **vendored verbatim**
from [`addyosmani/agent-skills`](https://github.com/addyosmani/agent-skills) (by Addy Osmani),
cherry-picked because they fill documented gaps the MeeSell `meesell-*` convention skills and
SuperPowers do **not** already cover. They were selected from a 24-skill collection after an
evaluation that scored the full set 5/10 for MeeSell (stack-fit + overlap); see
`docs/CLAUDE_SKILLS_PRODUCTIVITY_REANALYSIS.md` → "Addendum: addyosmani/agent-skills".

## Vendored skills (source: `addyosmani/agent-skills` @ commit `17214a2`)

| Skill | Why cherry-picked |
|-------|-------------------|
| `security-and-hardening` | Only systematic OWASP/threat-model checklist; "treat LLM output as untrusted" covers the Gemini-output trust gap |
| `debugging-and-error-recovery` | Framework-agnostic 6-step layer-isolation triage (UI/API/DB/external) — matches the live-bug class (auth refresh storm, `size_in_ltrs` 422) |
| `observability-and-instrumentation` | RED/USE metrics + correlation IDs — fills the Langfuse/tracing gap on the Celery+FastAPI+Valkey stack |
| `context-engineering` | Context hygiene / progressive disclosure — load-bearing on the 8 GB dev box with multi-agent dispatch |
| `doubt-driven-development` | Adversarial fresh-context review — strengthens the coordinator merge-gate-review step |
| `source-driven-development` | DETECT→FETCH→IMPLEMENT→CITE — pairs with the Context7 MCP to kill stale-training-data hallucinations |

## Deliberately NOT vendored (from the same collection)
`git-workflow-and-versioning` (conflicts with MeeSell's squash→integration flow), `ci-cd-and-automation`
(GitHub Actions ≠ GitLab CI), `frontend-ui-engineering` (React-only), the 4 Personas (could be
dispatched instead of `meesell-*` agents), and all Define/Plan/TDD/review skills already covered by
SuperPowers + the `meesell-*` fleet.

## Precedence
CLAUDE.md Rule #1 still governs: **only `meesell-*` agents handle MeeSell work.** These vendored
skills are behavioural guidance loaded into context — they do NOT introduce new agents/personas and
do not override the fleet's routing, merge-gate, or locked-doc rules.

---

## License (MIT)

These files retain their original MIT license:

```
MIT License

Copyright (c) 2025 Addy Osmani

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```
