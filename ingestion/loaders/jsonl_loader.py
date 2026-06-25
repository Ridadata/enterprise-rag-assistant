import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any


def load_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError as exc:
                msg = f"Invalid JSON on line {line_number} in {path}"
                raise ValueError(msg) from exc

