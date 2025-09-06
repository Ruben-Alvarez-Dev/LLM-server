from __future__ import annotations

from typing import Any, Dict, List, Optional


class MemoryClient:
    def __init__(self, host: str = "localhost", port: int = 8082) -> None:
        self.host = host
        self.port = port

    def search(self, query: str, k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        # Stubbed: returns shaped, deterministic examples
        results = []
        for i in range(k):
            results.append({
                "id": f"doc-{i}",
                "score": 0.9 - i * 0.05,
                "text": f"Snippet {i} for query: {query}",
                "metadata": {"source": "stub", "rank": i},
            })
        return results

