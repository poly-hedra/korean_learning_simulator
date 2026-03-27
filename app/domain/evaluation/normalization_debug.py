"""용언 정규화 디버그 로그 유틸.

사용자 출력에 노출하지 않고, 내부 파일 로그로만 정규화 결과를 남긴다.
환경 변수 `EVAL_NORMALIZATION_DEBUG=1`일 때만 동작한다.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

_DEBUG_SAMPLES = [
    "탈 것 같아요.",
    "듣고 있어요.",
    "걸어가고 있어요.",
    "도와줄게요.",
    "모르면 다시 물어볼게요.",
]

_DEBUG_FILE_PATH = Path(__file__).parent / "debug_logs" / "normalization_samples.jsonl"
_HAS_LOGGED = False


def _is_enabled() -> bool:
    return os.getenv("EVAL_NORMALIZATION_DEBUG", "0").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def maybe_log_irregular_samples(
    kiwi: Any,
    normalizer: Callable[[Any], str],
) -> None:
    """불규칙 활용 샘플 정규화 결과를 JSONL로 기록한다."""

    global _HAS_LOGGED
    if _HAS_LOGGED or not _is_enabled():
        return

    rows: list[dict[str, Any]] = []
    for sample in _DEBUG_SAMPLES:
        token_rows: list[dict[str, str]] = []
        for token in kiwi.tokenize(sample):
            token_rows.append(
                {
                    "form": str(getattr(token, "form", "")),
                    "tag": str(getattr(token, "tag", "")),
                    "lemma": str(getattr(token, "lemma", "")),
                    "normalized": str(normalizer(token)),
                }
            )
        rows.append({"sample": sample, "tokens": token_rows})

    payload = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "samples": rows,
    }

    _DEBUG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _DEBUG_FILE_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")

    _HAS_LOGGED = True
