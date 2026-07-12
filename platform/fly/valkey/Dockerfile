# Dockerfile — MeeSell self-hosted Valkey 8.
#
# Minimal image over the OFFICIAL valkey/valkey:8. Adds ONLY:
#   1. valkey.conf         — static config-as-code (persistence, memory, bind)
#   2. docker-entrypoint.sh — injects the requirepass password from the Fly
#                             secret VALKEY_PASSWORD at runtime (never committed)
# No app code, no extra packages — the official image is the base verbatim.
FROM valkey/valkey:8

COPY valkey.conf /usr/local/etc/valkey/valkey.conf
COPY docker-entrypoint.sh /usr/local/bin/meesell-valkey-entrypoint.sh
RUN chmod +x /usr/local/bin/meesell-valkey-entrypoint.sh

EXPOSE 6379
ENTRYPOINT ["/usr/local/bin/meesell-valkey-entrypoint.sh"]
