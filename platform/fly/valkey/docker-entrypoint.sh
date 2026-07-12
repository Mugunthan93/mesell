#!/bin/sh
# docker-entrypoint.sh — MeeSell self-hosted Valkey entrypoint.
#
# Injects the requirepass password from the Fly secret VALKEY_PASSWORD at RUNTIME
# so the secret is NEVER baked into the image or committed to git. All other config
# is static in /usr/local/etc/valkey/valkey.conf.
set -eu

if [ -z "${VALKEY_PASSWORD:-}" ]; then
  echo "FATAL: VALKEY_PASSWORD not set (expected to arrive from the Fly secret)" >&2
  exit 1
fi

# exec so valkey-server is PID 1 (receives SIGTERM cleanly on Fly machine stop,
# flushing the AOF buffer). Password passed as an arg overrides any conf value.
exec valkey-server /usr/local/etc/valkey/valkey.conf --requirepass "$VALKEY_PASSWORD"
