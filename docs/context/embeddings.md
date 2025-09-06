Embeddings Services (Multi-Instance)

Overview
- Configure multiple embeddings services per profile (e.g., `default`, `code`, `docs`).
- Each service defines a default `dimensions` and a `purpose` string.

Profile Config
- Location: `configs/custom_profiles/<profile>.yaml`
- Example:
  "embeddings": [
    { "name": "default", "dimensions": 256, "purpose": "general" },
    { "name": "code",    "dimensions": 384, "purpose": "code" }
  ]

HTTP API
- `GET /v1/embeddings/list` — lists configured services.
- `POST /v1/embeddings/{name}` — generate embeddings with named service; omitting `dimensions` uses the service default.
- `GET /v1/embeddings/{name}/ready` — readiness (stub=ok in this release).
- Back-compat: `POST /v1/embeddings` without name uses the first configured service.

MCP Tool
- `embeddings.generate` — optional `name` selects the service; default `dimensions` come from the profile when not specified.

Ports (Hubs)
- Hubs are listed in `GET /v1/ports` under `hubs` as `embeddings-<name>`.
- Rule: base `B000` → models block `B200`; embeddings hubs start at `B200+30` and increment by `+10` per service.

