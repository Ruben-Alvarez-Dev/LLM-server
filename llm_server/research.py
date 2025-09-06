from __future__ import annotations

from typing import Any, Dict, List, Optional


def web_search(query: str, top_k: int = 5, site: Optional[str] = None) -> Dict[str, Any]:
    # Stubbed: deterministic pseudo-results; replace with real web/search backend later
    results: List[Dict[str, Any]] = []
    for i in range(top_k):
        results.append({
            "id": f"res-{i}",
            "title": f"{query} — result {i}",
            "url": f"https://example.org/{i}?q={query}",
            "snippet": f"Snippet {i} about {query}",
        })
    return {"results": results}

