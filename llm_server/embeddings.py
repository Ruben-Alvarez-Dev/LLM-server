from __future__ import annotations

import hashlib
import math
from typing import List


def _hash_to_unit_vec(text: str, dim: int = 256) -> List[float]:
    # Deterministic, cheap embedding: hash n-grams into buckets, L2 normalize.
    buckets = [0.0] * dim
    s = text.strip().lower()
    if not s:
        return buckets
    tokens = s.split()
    for t in tokens:
        h = hashlib.sha256(t.encode("utf-8")).digest()
        # map 4 bytes to an index and sign
        idx = int.from_bytes(h[:2], 'big') % dim
        val = int.from_bytes(h[2:4], 'big') % 1000 / 1000.0
        sign = -1.0 if (h[4] & 1) else 1.0
        buckets[idx] += sign * val
    # normalize
    norm = math.sqrt(sum(x * x for x in buckets)) or 1.0
    return [x / norm for x in buckets]


def embed_texts(texts: List[str], dim: int = 256) -> List[List[float]]:
    return [_hash_to_unit_vec(t, dim=dim) for t in texts]

