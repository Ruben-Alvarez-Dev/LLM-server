import os
import sys
from .app import create_app
from .bootstrap import ensure_llama_built


def main() -> int:
    # Ensure llama.cpp is available (clone+build if needed)
    try:
        llama_bin = ensure_llama_built()
        print(f"llama.cpp ready: {llama_bin}")
    except Exception as e:
        print(f"Warning: llama.cpp bootstrap failed: {e}")

    app = create_app()
    # FastAPI available?
    if hasattr(app, "state"):
        try:
            import uvicorn  # type: ignore

            cfg = app.state.config  # type: ignore[attr-defined]
            port = int(os.getenv("PORT_LLM_SERVER", cfg["ports"]["llm_server"]))
            uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
            return 0
        except Exception as e:  # pragma: no cover - uvicorn optional
            print(f"Failed to start uvicorn: {e}")
            return 1
    else:
        # Stub mode
        print("LLM-server app initialized (stub mode). Install FastAPI+uvicorn to run.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
