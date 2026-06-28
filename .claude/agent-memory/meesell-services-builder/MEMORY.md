# Memory — meesell-services-builder

## Agent Identity
Business-logic specialist for MeeSell. Owns service layer (ai_engine call site, image_processor, quality_engine, pricing_engine, export_service, otp_service MSG91 portion, storage) + Celery workers. Decentralized memory ecosystem.

---

## Index
> Bodies live in `mem/`. ⭐ = contains reusable pattern / gotcha / ground-truth.

- ⭐ [Export validation aggregation — fail-fast → collect-all (2026-06-18, PR #291, branch feat/export-validation-aggregation, worktree /private/tmp/mesell-wt/export-validation off origin/develop@86dfb86)](mem/mem_01_export-validation-aggregation-fail-fast-collect-all-2026-06.md)
- ⭐ [Razorpay DEV-MOCK mode (2026-06-20, branch feature/razorpay-dev-mock, worktree /tmp/mesell-wt/razorpay-dev-mock off develop@8b5dce2 — the #323 merge that HAS create_subscription; commit 66ecf0d)](mem/mem_02_razorpay-dev-mock-mode-2026-06-20-branch-feature-razorpay-de.md)
- ⭐ [google-auth account-link audit_events.user_id NULL fix (2026-06-20, branch fix/google-link-audit-userid, worktree /private/tmp/mesell-wt/google-link-audit-fix off develop@fa61a61, PR #324 → develop)](mem/mem_03_google-auth-account-link-audit-events-user-id-null-fix-2026.md)
- [PR #285 gate R1/R2 doc reconciliation (2026-06-18, branch fix/pricing-engine-rework, worktree /private/tmp/mesell-wt/pricing-rework, commit 74ade7c)](mem/mem_04_pr-285-gate-r1-r2-doc-reconciliation-2026-06-18-branch-fix-p.md)
- [i18n #280 LOCAL HOT-PATCH applied to master tree (2026-06-18, dev-only bridge)](mem/mem_05_i18n-280-local-hot-patch-applied-to-master-tree-2026-06-18-d.md)
- [i18n generic-missing fallback (2026-06-18, branch fix/i18n-generic-missing, PR #280, worktree /private/tmp/mesell-wt/i18n-missing off develop@0087562)](mem/mem_06_i18n-generic-missing-fallback-2026-06-18-branch-fix-i18n-gen.md)
- ⭐ [catalog-form schema DTO mapper (2026-06-16, branch feature/catalog-form-fix, worktree /tmp/mesell-wt/catalog-form-fix)](mem/mem_07_catalog-form-schema-dto-mapper-2026-06-16-branch-feature-cat.md)
- ⭐ [MS-D Phase B — svc-pricing extraction (2026-06-13, branch feature/microservices-pricing/backend)](mem/mem_08_ms-d-phase-b-svc-pricing-extraction-2026-06-13-branch-featur.md)
- [D4 §20.5 CI YAML CONSTRUCTED (2026-06-09, .gitlab-ci.yml)](mem/mem_09_d4-20-5-ci-yaml-constructed-2026-06-09-gitlab-ci-yml.md)
- ⭐ [§19 CI gates CONSTRUCTED (2026-06-08, Wave 7 step 2)](mem/mem_10_19-ci-gates-constructed-2026-06-08-wave-7-step-2.md)
- ⭐ [§5 shared CONSTRUCTED (2026-06-06)](mem/mem_11_5-shared-constructed-2026-06-06.md)
- ⭐ [Session: 2026-06-05 — Final Gap Purge (workers + leftover tests) COMPLETE](mem/mem_12_session-2026-06-05-final-gap-purge-workers-leftover-tests-co.md)
- ⭐ [§4 core/ services slice CONSTRUCTED (2026-06-06)](mem/mem_13_4-core-services-slice-constructed-2026-06-06.md)
- ⭐ [Memory index](mem/mem_14_memory-index.md)
- ⭐ [§4 cross-test pollution fix (2026-06-06 follow-up)](mem/mem_15_4-cross-test-pollution-fix-2026-06-06-follow-up.md)
- ⭐ [§5A i18n CONSTRUCTED (2026-06-06)](mem/mem_16_5a-i18n-constructed-2026-06-06.md)
- ⭐ [§6 adapters CONSTRUCTED (2026-06-06)](mem/mem_17_6-adapters-constructed-2026-06-06.md)
- ⭐ [§6A ai_ops CONSTRUCTED (2026-06-06)](mem/mem_18_6a-ai-ops-constructed-2026-06-06.md)
- ⭐ [§8 customer service layer CONSTRUCTED (2026-06-07)](mem/mem_19_8-customer-service-layer-constructed-2026-06-07.md)
- ⭐ [§9 category services slice CONSTRUCTED (2026-06-07)](mem/mem_20_9-category-services-slice-constructed-2026-06-07.md)
- [§10 catalog — CONSTRUCTED 2026-06-07 (sub-session 1)](mem/mem_21_10-catalog-constructed-2026-06-07-sub-session-1.md)
- ⭐ [§11 image — CONSTRUCTED 2026-06-07 (sub-session: meesell-backend-construction-11-image-1)](mem/mem_22_11-image-constructed-2026-06-07-sub-session-meesell-backend.md)
- ⭐ [§12 pricing — CONSTRUCTED 2026-06-07 (sub-session: meesell-backend-construction-12-pricing-1)](mem/mem_23_12-pricing-constructed-2026-06-07-sub-session-meesell-backen.md)
- ⭐ [§13 dashboard — CONSTRUCTED 2026-06-07 (sub-session: meesell-backend-construction-13-dashboard-1)](mem/mem_24_13-dashboard-constructed-2026-06-07-sub-session-meesell-back.md)
- ⭐ [§14 export — CONSTRUCTED 2026-06-08 (sub-session: meesell-backend-construction-14-export-1)](mem/mem_25_14-export-constructed-2026-06-08-sub-session-meesell-backend.md)
- ⭐ [§18 Celery wiring CONSTRUCTED (2026-06-08)](mem/mem_26_18-celery-wiring-constructed-2026-06-08.md)
- ⭐ [F-15-1 export worker terminal audit rows IMPLEMENTED (2026-06-09)](mem/mem_27_f-15-1-export-worker-terminal-audit-rows-implemented-2026-06.md)
- ⭐ [V0 ARTIFACT DELETE + V0-ROT TEST CLEANUP + COMMIT (2026-06-09, branch claude/meesell-project-setup-Tl7DS)](mem/mem_28_v0-artifact-delete-v0-rot-test-cleanup-commit-2026-06-09-bra.md)
- ⭐ [Session mesell-housekeeping-v1-backend-session-1 — 2026-06-10](mem/mem_29_session-mesell-housekeeping-v1-backend-session-1-2026-06-10.md)
- ⭐ [MS-C B1 — svc-image service layer EXTRACTED (2026-06-13)](mem/mem_30_ms-c-b1-svc-image-service-layer-extracted-2026-06-13.md)
- ⭐ [MS-B svc-dashboard extraction CONSTRUCTED (2026-06-13, services-builder Phase B heavy lift)](mem/mem_31_ms-b-svc-dashboard-extraction-constructed-2026-06-13-service.md)
- [Section-2 (smart-picker) Plan 2-W1 — i18n error message contract (2026-06-15, branch feature/section-2/backend)](mem/mem_32_section-2-smart-picker-plan-2-w1-i18n-error-message-contract.md)
- ⭐ [section-3 Wave 1.1 — catalog.service.get_product_detail (2026-06-15, branch feature/section-3/backend)](mem/mem_33_section-3-wave-1-1-catalog-service-get-product-detail-2026-0.md)
- [catalog-form merge-gate D1 fix — M10 local-var rename (2026-06-16, branch feature/catalog-form-fix)](mem/mem_34_catalog-form-merge-gate-d1-fix-m10-local-var-rename-2026-06.md)
- [catalog-form CI Gate-4 (integration) RED — scope-reduction fix (2026-06-16, branch feature/catalog-form-fix)](mem/mem_35_catalog-form-ci-gate-4-integration-red-scope-reduction-fix-2.md)
- ⭐ [Cross-field validation rule engine (2026-06-18, branch feat/catalog-field-dependency-rules, worktree /private/tmp/mesell-wt/field-dep-rules off develop@fd4331d)](mem/mem_36_cross-field-validation-rule-engine-2026-06-18-branch-feat-ca.md)
- ⭐ [Price Calculator forward-estimator rework §12.M (2026-06-18, branch fix/pricing-engine-rework, PR #285, worktree /private/tmp/mesell-wt/pricing-rework off origin/develop@da588f3)](mem/mem_37_price-calculator-forward-estimator-rework-12-m-2026-06-18-br.md)
