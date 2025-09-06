from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional

from .config_loader import build_effective_config
from .models_catalog import CATALOG
from .bootstrap import ensure_llama_built


@dataclass
class ModelSpec:
    name: str
    path: Path
    context_max: int
    est_ram_gb: float


class ModelRegistry:
    def __init__(self) -> None:
        self.cfg = build_effective_config()
        self.models_root = Path(self.cfg["models_root"]).resolve()
        self.selected = list(self.cfg.get("selected_models", []))
        self.models_cfg = self.cfg.get("models", [])
        self._by_name: Dict[str, ModelSpec] = {}
        self._llama_ok = False

    def refresh(self) -> None:
        # ensure llama.cpp exists
        self._llama_ok = bool(shutil.which(str(ensure_llama_built())))

        # map configs to ModelSpec
        by_name = {}
        for m in self.models_cfg:
            name = m["name"]
            if name not in self.selected:
                continue
            ctx = int(m.get("context_max", 0))
            ram = float(m.get("est_ram_gb", 0))
            file = CATALOG.get(name, {}).get("file")
            if not file:
                continue
            path = (self.models_root / file).resolve()
            by_name[name] = ModelSpec(name=name, path=path, context_max=ctx, est_ram_gb=ram)
        self._by_name = by_name

    def get(self, name: str) -> Optional[ModelSpec]:
        return self._by_name.get(name)

    def list(self) -> List[ModelSpec]:
        return list(self._by_name.values())

    def ready(self) -> bool:
        # ready if llama binary exists and all selected models have files present
        if not self._llama_ok:
            return False
        if not self.selected:
            return False
        for s in self.list():
            if not s.path.exists():
                return False
        return True

    def readiness_report(self) -> Dict[str, object]:
        items = []
        for name in self.selected:
            spec = self.get(name)
            if not spec:
                items.append({"name": name, "present": False, "path": None})
            else:
                items.append({"name": name, "present": spec.path.exists(), "path": str(spec.path)})
        return {
            "llama_ok": self._llama_ok,
            "models_root": str(self.models_root),
            "selected": self.selected,
            "items": items,
            "ready": self.ready(),
        }

