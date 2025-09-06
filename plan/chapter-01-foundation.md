Chapter 01 — Foundation

Goals
- Solid repo scaffolding and validation so subsequent work is fast and safe.

Checkpoints
1. [x] Context pack normalized (docs/context/*) with manifest
2. [x] Configs populated (models.yaml, limits.yaml, roles)
3. [x] Schemas added (models/limits/profile)
4. [x] Validator + Makefile targets (codex, validate)
5. [x] Custom profile dev-default + runtime pointer
6. [x] Git remote (SSH) configured; push baseline
7. [ ] Add minimal CI (local make validate)

Acceptance Criteria
- `make validate` exits 0 and RAM headroom ≥ 5 GB.
- Remote tracking configured on main and push works.

