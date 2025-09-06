import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LLAMA_DIR = ROOT / "vendor" / "llama.cpp"
BUILD_DIR = LLAMA_DIR / "build"
LLAMA_BIN = BUILD_DIR / "bin" / "llama-cli"


def ensure_llama_built() -> Path:
    """Ensure llama.cpp is cloned and built with Metal (if on macOS).

    Returns path to llama-cli binary if available after bootstrap.
    """
    if LLAMA_BIN.exists():
        return LLAMA_BIN

    # Clone if missing
    if not LLAMA_DIR.exists():
        _run(["git", "clone", "--depth", "1", "https://github.com/ggerganov/llama.cpp", str(LLAMA_DIR)])

    # Configure with Metal if available
    cmake_args = [
        "cmake",
        "-S",
        str(LLAMA_DIR),
        "-B",
        str(BUILD_DIR),
        "-DGGML_METAL=ON",
        "-DCMAKE_BUILD_TYPE=Release",
    ]
    _run(cmake_args)

    # Build
    _run(["cmake", "--build", str(BUILD_DIR), "--config", "Release", "-j"])

    return LLAMA_BIN


def _run(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True)

