# Roles and Limits

Agents
- Router: routes requests to appropriate roles/models.
- Architect: defines high-level approach and interfaces.
- Planner: breaks work into steps and checkpoints.
- Coder: implements changes with safeguards.
- Verifiers: run fast checks, linting, reasoning, and unit verifications.
- Debugger: investigates failures and proposes fixes.
- Finalizer: consolidates results and produces concise handoffs.

Per-role Context and Max In-flight
- Router: context_window ≈ 4096, max_in_flight = 1
- Architect: context_window ≈ 16384, max_in_flight = 1
- Planner: context_window ≈ 16384, max_in_flight = 1
- Analysis: context_window ≈ 65536 (32B), max_in_flight = 1
- Distillation: context_window ≈ 65536 (32B), max_in_flight = 1
- Coder: context_window ≈ 24576 (14B), max_in_flight = 2
- Verifiers: context_window ≈ 16384 (7–8B), max_in_flight = 3
- Debugger: context_window ≈ 8192, max_in_flight = 1
- Finalizer: context_window ≈ 16384, max_in_flight = 1

Note
- Concurrency should align with `configs/limits.yaml` and the active custom profile.
