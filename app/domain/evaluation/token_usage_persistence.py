"""대화별 토큰/정규화 토큰 누적 저장 유틸."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LOG_PATH = (
    Path(__file__).resolve().parent / "token_logs" / "conversation_token_logs.jsonl"
)
_LOW_CONFIDENCE_THRESHOLD = 0.85
_ROW_HEADER = (
    "form\ttag\tlemma\tnormalized\tmatched\tvocab_index\tvocab_example\tconfidence"
)


def _format_token_row(token: dict[str, Any]) -> str:
    return "\t".join(
        [
            str(token.get("form", "")),
            str(token.get("tag", "")),
            str(token.get("lemma", "")),
            str(token.get("normalized", "")),
            str(token.get("matched", "X")),
            str(token.get("vocab_index", "")),
            str(token.get("vocab_example", "")),
            str(token.get("confidence", "")),
        ]
    )


def reset_token_usage_log() -> None:
    """기존 로그를 모두 지우고 빈 파일로 초기화한다."""

    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LOG_PATH.write_text("", encoding="utf-8")


def _build_session_block(
    state: dict[str, Any],
    utterance_token_logs: list[dict[str, Any]],
) -> str:
    user_profile = state.get("user_profile", {})
    created_at = datetime.now(timezone.utc).isoformat()

    lines: list[str] = [
        f"user_id: {user_profile.get('user_id', '')}",
        f"created_at: {created_at}",
    ]
    low_confidence_rows: list[dict[str, str]] = []

    for utterance_index, utterance_row in enumerate(utterance_token_logs, start=1):
        utterance = str(utterance_row.get("utterance", ""))
        tokens = utterance_row.get("tokens", [])

        lines.append(f"original_utterance_{utterance_index}: {utterance}")
        lines.append(_ROW_HEADER)

        wrote_token = False
        if isinstance(tokens, list):
            for token in tokens:
                if isinstance(token, dict):
                    lines.append(_format_token_row(token))
                    wrote_token = True

                    raw_conf = str(token.get("confidence", "")).strip()
                    if raw_conf:
                        try:
                            conf = float(raw_conf)
                        except Exception:
                            conf = -1.0
                        if 0 <= conf < _LOW_CONFIDENCE_THRESHOLD:
                            low_confidence_rows.append(
                                {
                                    "form": str(token.get("form", "")),
                                    "tag": str(token.get("tag", "")),
                                    "lemma": str(token.get("lemma", "")),
                                    "normalized": str(token.get("normalized", "")),
                                    "matched": str(token.get("matched", "")),
                                    "vocab_index": str(token.get("vocab_index", "")),
                                    "confidence": raw_conf,
                                    "utterance": utterance,
                                }
                            )

        if not wrote_token:
            lines.append("(필터 후 기록할 토큰 없음)")

        lines.append("")  # utterance 사이에 한 칸 개행

    lines.append("low_confidence_tokens:")
    lines.append(
        "form\ttag\tlemma\tnormalized\tmatched\tvocab_index\tconfidence\tutterance"
    )
    if low_confidence_rows:
        for row in low_confidence_rows:
            lines.append(
                "\t".join(
                    [
                        row["form"],
                        row["tag"],
                        row["lemma"],
                        row["normalized"],
                        row["matched"],
                        row["vocab_index"],
                        row["confidence"],
                        row["utterance"],
                    ]
                )
            )
    else:
        lines.append("(low confidence token 없음)")

    lines.append("")

    return "\n".join(lines) + "\n"


def append_token_usage_log(
    state: dict[str, Any],
    utterance_token_logs: list[dict[str, Any]],
    tokenized_original_words: list[str],
    tokenized_normalized_words: list[str],
) -> None:
    """평가 시점의 토큰 정보를 JSONL로 누적 저장한다."""

    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    block = _build_session_block(state=state, utterance_token_logs=utterance_token_logs)

    with _LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(block)
