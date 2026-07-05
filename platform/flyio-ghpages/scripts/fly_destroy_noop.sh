#!/usr/bin/env bash
# fly_destroy_noop.sh — the destroy provisioner for the Fly app shim.
#
# DELIBERATELY DELETES NOTHING. Tearing down the live Fly app also destroys its
# attached Postgres (meesell-db) + all ~40 secrets — that must be a conscious human
# act, never a `terraform destroy` side effect. This prints the manual runbook and
# exits 0 so `terraform destroy` can remove the state entry without touching live infra.
set -euo pipefail
FLY_APP="${FLY_APP:-meesell-api}"
cat >&2 <<MSG
[fly_destroy_noop] Terraform is removing the fly_app shim from STATE ONLY.
[fly_destroy_noop] NO Fly resource was deleted. To actually destroy the live app, a
[fly_destroy_noop] human must run — deliberately, with backups taken first:
[fly_destroy_noop]     flyctl apps destroy ${FLY_APP}
[fly_destroy_noop] (this also destroys attached Postgres meesell-db + all secrets).
MSG
exit 0
