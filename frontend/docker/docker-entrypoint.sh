#!/bin/sh
# =============================================================================
# MeeSell shell-image entrypoint — renders the per-env CSP into nginx.conf.
# SP07 cutover (D42 / C-CSP-1). Author: meesell-infra-builder.
#
# Selects CSP_POLICY for $APP_ENV from csp-policy.env, exports it, then runs
# `envsubst` over nginx.conf.template to produce the live /etc/nginx/nginx.conf.
# This is the per-env templating the spec §3 / C-CSP-1 requires — the SAME image
# emits the dev / staging / prod CSP by switching APP_ENV at deploy time.
#
# ADD-ONLY guarantee: envsubst only substitutes the ${CSP_POLICY} token. It does
# not touch any other header directive (there are none — see nginx.conf.template).
# =============================================================================
set -eu

# APP_ENV must be one of development|staging|production (matches the Pydantic
# Settings Literal used backend-side; the shell maps it to the CSP env suffix).
APP_ENV="${APP_ENV:-development}"

# shellcheck disable=SC1091
. /etc/nginx/csp-policy.env

case "${APP_ENV}" in
  development|dev)    export CSP_POLICY="${CSP_POLICY_dev}" ;;
  staging)           export CSP_POLICY="${CSP_POLICY_staging}" ;;
  production|prod)   export CSP_POLICY="${CSP_POLICY_prod}" ;;
  *)
    echo "FATAL: unknown APP_ENV='${APP_ENV}' — expected development|staging|production" >&2
    exit 1
    ;;
esac

echo "[shell-entrypoint] APP_ENV=${APP_ENV} — rendering CSP into nginx.conf"
# Only substitute CSP_POLICY (NOT $uri etc. that nginx itself uses at runtime).
envsubst '${CSP_POLICY}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Print the rendered CSP for the deploy log (NOT a secret — it's a public header).
echo "[shell-entrypoint] active CSP: ${CSP_POLICY}"

exec nginx -g 'daemon off;'
