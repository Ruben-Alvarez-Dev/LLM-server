Bootstrap Playbook

Steps
1) Copy a base profile into custom (read-only → editable):
   - Identify a base profile in `configs/base_profiles/` (if present).
   - Save it as `configs/custom_profiles/dev-default.yaml` and update to your needs.

2) Set the default profile pointer:
   - Write `dev-default` into `runtime/current_profile`.

3) Dry-run validation:
   - Run `make validate` to check required files, schema conformity, and RAM headroom.

4) Launch processes (example names and ports):
   - Orchestrator: `orchestrator --port 8080 --profile configs/custom_profiles/dev-default.yaml`
   - LLM-server: `llm-server --port 8081 --models configs/models.yaml`
   - Memory-server: `memory-server --port 8082`

5) Operational sanity checks:
   - Confirm health endpoints on configured ports.
   - Test a prompt flow that exercises Router → Planner → Coder → Verifiers → Finalizer.
