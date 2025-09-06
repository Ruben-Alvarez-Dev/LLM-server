Memory-server Design

Summaries (N1–N5)
- N1: High-level project intent and constraints (1–2 paragraphs).
- N2: Component/module overviews with interfaces and contracts.
- N3: File-level summaries including key functions, entry points, and side effects.
- N4: Region-level notes (per class/function) capturing invariants and tricky logic.
- N5: Chunk-level embeddings with bidirectional links to N3/N4.

Directed Retrieval
- Start from task type → identify relevant components (N2) → narrow to files (N3) → fetch N4/N5 chunks.
- Prioritize recent edits and hot paths; bias towards code touched by the current branch.

Storage & Performance
- NVMe-backed vector store with mmap-friendly shard layout.
- Batch queries; cache hot chunks and summary layers near the model.
- Deduplicate near-duplicate chunks and collapse noisy embeddings.

Interfaces
- `search(query, k, filters)` returns chunk ids + scores.
- `fetch(ids)` returns chunk text + metadata + lineage (N-level origins).
- `summarize(layer, targets)` builds/refreshes summaries across N1–N5.
