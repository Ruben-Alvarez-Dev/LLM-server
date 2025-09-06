#!/usr/bin/env bash
set -euo pipefail
TENANT="$1"; shift || { echo "Usage: $0 <tenant> [writer_user reader_user]"; exit 1; }
WRITER_USER="${1:-${TENANT}_writer}"
READER_USER="${2:-${TENANT}_reader}"
OUTDIR="runtime/messaging/acls"
mkdir -p "$OUTDIR"
OUT="$OUTDIR/$TENANT.json"
cat >"$OUT" <<JSON
{
  "tenant": "$TENANT",
  "acls": [
    {"resource": "topic", "name": "llm.$TENANT.*", "operation": "write", "username": "$WRITER_USER"},
    {"resource": "topic", "name": "llm.$TENANT.*", "operation": "read",  "username": "$READER_USER"}
  ]
}
JSON
echo "Wrote $OUT"
