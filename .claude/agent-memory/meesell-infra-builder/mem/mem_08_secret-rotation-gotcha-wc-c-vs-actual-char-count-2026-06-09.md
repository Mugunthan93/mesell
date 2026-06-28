## Secret rotation gotcha — `wc -c` vs actual char count (2026-06-09)

When verifying a no-trailing-newline secret, do NOT eyeball-count the source string for the expected length. `wc -c` counts BYTES; for `printf '%s'` (no newline) the byte count == char count exactly. I briefly mis-flagged `razorpay-key-id` as "23 bytes vs expected 22" — but the string `rzp_test_SzNwynjr6l05dy` is genuinely 23 chars (I miscounted). The authoritative integrity check is `... | tail -c N | xxd` to confirm the LAST byte is NOT `0a` (newline). That hexdump tail check is the trustworthy "no trailing newline" proof — use it, not arithmetic on a hand-counted expected length.

Idempotent SM rotation pattern (re-confirmed working):
```
gcloud secrets describe <id> --project=... --format="value(name)"   # EXIT 0 = exists, skip create
printf '%s' '<value>' | gcloud secrets versions add <id> --project=... --data-file=-   # adds new version, old stays ENABLED
gcloud secrets versions list <id> --project=... --filter="state=ENABLED" --format="value(name,state)"
```
Adding a version does NOT disable prior versions — `latest` alias auto-points to the newest. Apps reading `latest` pick up the rotation on next fetch (or pod restart if cached at startup). Old versions remain ENABLED unless explicitly disabled/destroyed.
