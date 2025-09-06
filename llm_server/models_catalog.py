from typing import Dict

# Central catalog for model artifacts and sources.
# Keep in sync with configs/models.yaml names.

CATALOG: Dict[str, Dict[str, str]] = {
    "deepseek-r1-qwen-32b-q4_k_m": {
        "repo": "lmstudio-community/DeepSeek-R1-Distill-Qwen-32B-GGUF",
        "file": "DeepSeek-R1-Distill-Qwen-32B-Q4_K_M.gguf",
        "provider": "HuggingFace",
    },
    "qwen2.5-14b-instruct-q4_k_m": {
        "repo": "Qwen/Qwen2.5-14B-Instruct-GGUF",
        "file": "Qwen2.5-14B-Instruct-Q4_K_M.gguf",
        "provider": "HuggingFace",
    },
    "phi-4-mini-instruct": {
        "repo": "microsoft/Phi-4-mini-instruct-GGUF",
        "file": "Phi-4-mini-instruct-Q4_K_M.gguf",
        "provider": "HuggingFace",
    },
}

