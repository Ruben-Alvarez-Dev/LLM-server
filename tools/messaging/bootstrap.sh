#!/usr/bin/env bash
set -euo pipefail

TENANTS="${1:-}"
if [[ "$TENANTS" == "" ]]; then
  echo "Usage: $0 --tenants main,clientA"
  exit 1
fi

if [[ "$TENANTS" =~ ^--tenants ]]; then
  TENANTS="${TENANTS#--tenants }"
fi

IFS=',' read -r -a TENANT_ARR <<< "$TENANTS"

echo "Bootstrap tenants: ${TENANT_ARR[*]}"

# Create topics via rpk inside redpanda container
create_topic() {
  local topic="$1"
  docker exec -t $(docker ps --filter name=redpanda -q | head -n1) rpk topic create "$topic" || true
}

for t in "${TENANT_ARR[@]}"; do
  create_topic "llm.$t.infer.requests.v1"
  create_topic "llm.$t.infer.results.v1"
  create_topic "llm.$t.embeddings.ingest.v1"
  create_topic "llm.$t.mem.events.v1"
  create_topic "llm.$t.retry.infer.v1"
  create_topic "llm.$t.dlq.infer.v1"
done

# Register Avro schemas if Schema Registry is enabled
SCHEMA_URL=${SCHEMA_REGISTRY_URL:-http://localhost:8081}

register_schema() {
  local subject="$1"; shift
  local file="$1"; shift
  echo "Registering schema $subject -> $file"
  curl -sSf -X POST -H 'Content-Type: application/vnd.schemaregistry.v1+json' \
    --data "$(jq -n --arg schema "$(jq -c . "$file")" '{schema: $schema}')" \
    "$SCHEMA_URL/subjects/$subject/versions" >/dev/null || true
}

for t in "${TENANT_ARR[@]}"; do
  register_schema "llm.$t.infer.requests.v1" "configs/messaging/schemas/avro/InferRequestV1.avsc"
  register_schema "llm.$t.infer.results.v1" "configs/messaging/schemas/avro/InferResultV1.avsc"
  register_schema "llm.$t.embeddings.ingest.v1" "configs/messaging/schemas/avro/EmbeddingIngestV1.avsc"
  register_schema "llm.$t.mem.events.v1" "configs/messaging/schemas/avro/MemoryEventV1.avsc"
done

# Generate NATS accounts via nats-box
for t in "${TENANT_ARR[@]}"; do
  docker exec -t $(docker ps --filter name=nats-box -q | head -n1) nats account add "$t" || true
  echo "Created NATS account: $t (subjects: ctrl.$t.*)"
done

echo "Bootstrap complete."
