"""대화형 어휘 매칭 테스트 도구.

문장을 입력하면 Kiwi 토크나이징 → 정규화 → vocabulary.json 매칭 결과를 출력하고,
token_logs/conversation_token_logs.jsonl 에 로그를 누적한다.

사용법:
    python -m scripts.vocab_matching_interactive
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from importlib import import_module
from pathlib import Path
from typing import Any

sys.stdin.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]

from kiwipiepy import Kiwi

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

_dialogue_cleansing = import_module("app.domain.evaluation.dialogue_cleansing")
_evaluate_vocab_mod = import_module("app.domain.evaluation.nodes.evaluate_vocab")

canonicalize_word = _dialogue_cleansing.canonicalize_word
expand_vocab_word_forms = _dialogue_cleansing.expand_vocab_word_forms
is_main_pos_tag = _dialogue_cleansing.is_main_pos_tag
normalize_token_for_vocab = _dialogue_cleansing.normalize_token_for_vocab
resolve_entries_by_pos = _dialogue_cleansing.resolve_entries_by_pos

_is_suspicious_pattern = _evaluate_vocab_mod._is_suspicious_pattern
_resolve_entry_by_llm = _evaluate_vocab_mod._resolve_entry_by_llm
_resolve_suspicious_normalization_by_llm = (
    _evaluate_vocab_mod._resolve_suspicious_normalization_by_llm
)

_VOCAB_PATH = _PROJECT_ROOT / "database" / "vocabulary.json"
_HOMONYMS_PATH = _PROJECT_ROOT / "database" / "vocabulary_homonyms.json"
_LOG_PATH = (
    _PROJECT_ROOT / "app" / "domain" / "evaluation" / "token_logs" / "conversation_token_logs.jsonl"
)

_LLM_WSD_CONFIDENCE_THRESHOLD = 0.7
_LLM_SUSPICIOUS_CONFIDENCE_THRESHOLD = 0.85

_HEADER = (
    "form\ttag\tlemma\tnormalized\tmatched\tvocab_index\tvocab_example\tconfidence"
)
_LOW_CONF_HEADER = (
    "form\ttag\tlemma\tnormalized\tmatched\tvocab_index\tconfidence\tutterance"
)
_LOW_CONFIDENCE_THRESHOLD = 0.85


def _load_vocab_entries() -> tuple[dict[str, str], dict[str, list[dict[str, str]]]]:
    with _VOCAB_PATH.open(encoding="utf-8") as handle:
        entries = json.load(handle)

    vocab_map: dict[str, str] = {}
    vocab_entries: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        level = str(entry["index"]).split("_")[0]
        payload = {
            "index": str(entry["index"]),
            "word": str(entry.get("word", "")),
            "kind": str(entry.get("kind", "")),
            "example": str(entry.get("example", "")),
            "level": level,
        }
        for form in expand_vocab_word_forms(entry["word"]):
            vocab_map[form] = level
            vocab_entries.setdefault(form, []).append(payload)
    return vocab_map, vocab_entries


def _load_homonyms() -> dict[str, list[dict[str, str]]]:
    if not _HOMONYMS_PATH.exists():
        return {}
    with _HOMONYMS_PATH.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return {str(key): list(value) for key, value in data.items()}


def _process_utterance(
    utterance: str,
    kiwi: Kiwi,
    vocab_map: dict[str, str],
    vocab_entries: dict[str, list[dict[str, str]]],
    homonyms: dict[str, list[dict[str, str]]],
    use_llm: bool,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """한 문장을 토크나이징 → 정규화 → 매칭한다."""

    tokens = kiwi.tokenize(utterance)
    llm_cache: dict[tuple, tuple] = {}
    suspicious_cache: dict[tuple, tuple] = {}
    compound_consumed: set[int] = set()

    token_rows: list[dict[str, str]] = []
    token_row_indices: dict[int, int] = {}

    for token in tokens:
        if token.tag.startswith("S"):
            continue
        normalized = (
            normalize_token_for_vocab(token)
            if is_main_pos_tag(token.tag)
            else token.form
        )
        token_row_indices[id(token)] = len(token_rows)
        token_rows.append(
            {
                "form": token.form,
                "tag": token.tag,
                "lemma": str(getattr(token, "lemma", "")),
                "normalized": normalized,
                "matched": "X",
                "vocab_index": "",
                "vocab_example": "",
                "confidence": "",
            }
        )

    for token_idx, token in enumerate(tokens):
        normalized_word = (
            normalize_token_for_vocab(token)
            if is_main_pos_tag(token.tag)
            else token.form
        )
        confidence = 0.0
        source = ""

        if token_idx in compound_consumed:
            continue

        compound_key: str | None = None
        compound_tag: str | None = None
        consumed_idx: int | None = None

        if (
            is_main_pos_tag(token.tag)
            and token_idx + 1 < len(tokens)
            and tokens[token_idx + 1].tag == "XSN"
        ):
            compound_key = canonicalize_word(token.form + tokens[token_idx + 1].form)
            compound_tag = token.tag
            consumed_idx = token_idx + 1
        elif (
            token.tag == "XR"
            and token_idx + 1 < len(tokens)
            and tokens[token_idx + 1].tag in {"XSA", "XSV"}
        ):
            compound_key = canonicalize_word(token.form + "하다")
            compound_tag = "VA" if tokens[token_idx + 1].tag == "XSA" else "VV"
            consumed_idx = token_idx + 1

        if compound_key and compound_key in vocab_map and consumed_idx is not None:
            compound_candidates = resolve_entries_by_pos(
                match_key=compound_key,
                token_tag=compound_tag or token.tag,
                vocab_entries=vocab_entries,
                homonyms=homonyms,
            )
            if compound_candidates:
                selected = compound_candidates[0]
                compound_consumed.add(consumed_idx)
                token_row_idx = token_row_indices.get(id(token))
                if token_row_idx is not None:
                    token_rows[token_row_idx]["matched"] = "O"
                    token_rows[token_row_idx]["normalized"] = compound_key
                    token_rows[token_row_idx]["vocab_index"] = str(selected["index"])
                    token_rows[token_row_idx]["vocab_example"] = str(
                        selected.get("example", "")
                    )
                    token_rows[token_row_idx]["confidence"] = "1.00"
                continue

        if _is_suspicious_pattern(tokens, token_idx):
            if use_llm:
                suspicious_key = (utterance, token_idx, token.form, token.tag)
                if suspicious_key not in suspicious_cache:
                    suspicious_cache[suspicious_key] = (
                        _resolve_suspicious_normalization_by_llm(
                            utterance=utterance,
                            token_index=token_idx,
                            tokens=tokens,
                        )
                    )
                llm_normalized, llm_conf = suspicious_cache[suspicious_key]
                confidence = llm_conf
                if (
                    llm_normalized is not None
                    and llm_conf >= _LLM_SUSPICIOUS_CONFIDENCE_THRESHOLD
                ):
                    normalized_word = llm_normalized
                    source = "의심패턴 LLM 확정"
            else:
                token_row_idx = token_row_indices.get(id(token))
                if token_row_idx is not None:
                    token_rows[token_row_idx]["confidence"] = "LLM 미사용"

        if not is_main_pos_tag(token.tag) and not source:
            continue

        match_key = canonicalize_word(normalized_word)
        if match_key not in vocab_map:
            token_row_idx = token_row_indices.get(id(token))
            if token_row_idx is not None and confidence > 0:
                token_rows[token_row_idx]["confidence"] = f"{confidence:.2f}"
            continue

        candidates = resolve_entries_by_pos(
            match_key=match_key,
            token_tag=token.tag,
            vocab_entries=vocab_entries,
            homonyms=homonyms,
        )

        selected_entry = None

        if len(candidates) == 0:
            continue
        if len(candidates) == 1:
            selected_entry = candidates[0]
            if not source:
                source = "단일항목 확정"
            confidence = max(confidence, 1.0)
        elif use_llm:
            candidate_sig = "|".join(
                sorted(str(candidate.get("index", "")) for candidate in candidates)
            )
            cache_key = (match_key, utterance, token.tag, candidate_sig)

            if cache_key not in llm_cache:
                llm_cache[cache_key] = _resolve_entry_by_llm(
                    match_key=match_key,
                    token_tag=token.tag,
                    utterance=utterance,
                    token_index=token_idx,
                    tokens=tokens,
                    candidates=candidates,
                )

            llm_entry, llm_conf = llm_cache[cache_key]
            confidence = llm_conf

            if llm_entry is not None and llm_conf >= _LLM_WSD_CONFIDENCE_THRESHOLD:
                selected_entry = llm_entry
                if not source:
                    source = "LLM 후보재판단 확정"
            else:
                token_row_idx = token_row_indices.get(id(token))
                if token_row_idx is not None and confidence > 0:
                    token_rows[token_row_idx]["confidence"] = f"{confidence:.2f}"
                continue
        else:
            selected_entry = candidates[0]
            confidence = 0.5
            source = "LLM 미사용(첫번째 후보)"

        token_row_idx = token_row_indices.get(id(token))
        if token_row_idx is not None and selected_entry:
            token_rows[token_row_idx]["matched"] = "O"
            token_rows[token_row_idx]["normalized"] = match_key
            token_rows[token_row_idx]["vocab_index"] = str(selected_entry["index"])
            token_rows[token_row_idx]["vocab_example"] = str(
                selected_entry.get("example", "")
            )
            token_rows[token_row_idx]["confidence"] = f"{confidence:.2f}"

    low_conf_rows: list[dict[str, str]] = []
    for row in token_rows:
        raw_conf = row.get("confidence", "").strip()
        if not raw_conf:
            continue
        try:
            conf = float(raw_conf)
        except ValueError:
            continue
        if 0 <= conf < _LOW_CONFIDENCE_THRESHOLD:
            low_conf_rows.append(
                {
                    "form": row["form"],
                    "tag": row["tag"],
                    "lemma": row["lemma"],
                    "normalized": row["normalized"],
                    "matched": row["matched"],
                    "vocab_index": row["vocab_index"],
                    "confidence": raw_conf,
                    "utterance": utterance,
                }
            )

    return token_rows, low_conf_rows


def _print_results(
    utterance: str,
    token_rows: list[dict[str, str]],
    low_conf_rows: list[dict[str, str]],
    utterance_num: int,
) -> None:
    """매칭 결과를 터미널에 출력한다."""

    print(f"\n{'=' * 70}")
    print(f"  문장 {utterance_num}: {utterance}")
    print(f"{'=' * 70}")
    print(_HEADER)
    for row in token_rows:
        print(
            "\t".join(
                [
                    row["form"],
                    row["tag"],
                    row["lemma"],
                    row["normalized"],
                    row["matched"],
                    row["vocab_index"],
                    row["vocab_example"],
                    row["confidence"],
                ]
            )
        )

    matched_count = sum(1 for row in token_rows if row["matched"] == "O")
    matchable_count = sum(
        1 for row in token_rows if is_main_pos_tag(row["tag"]) or row["tag"] == "XR"
    )
    rate = round((matched_count / matchable_count) * 100, 2) if matchable_count else 0.0
    print(f"\n  매칭: {matched_count}/{matchable_count} ({rate}%)")

    if low_conf_rows:
        print(f"\n  ** 저신뢰 토큰 (< {_LOW_CONFIDENCE_THRESHOLD}) **")
        print(f"  {_LOW_CONF_HEADER}")
        for row in low_conf_rows:
            print(
                "  "
                + "\t".join(
                    [
                        row["form"],
                        row["tag"],
                        row["lemma"],
                        row["normalized"],
                        row["matched"],
                        row["vocab_index"],
                        row["confidence"],
                        row["utterance"][:30],
                    ]
                )
            )


def _append_log(
    user_id: str,
    utterance_logs: list[dict[str, Any]],
    all_low_conf: list[dict[str, str]],
) -> None:
    """jsonl 로그 파일에 세션 블록을 추가한다."""

    _LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).isoformat()

    lines: list[str] = [
        f"user_id: {user_id}",
        f"created_at: {created_at}",
    ]

    for idx, entry in enumerate(utterance_logs, start=1):
        utterance = entry["utterance"]
        token_rows = entry["tokens"]
        lines.append(f"original_utterance_{idx}: {utterance}")
        lines.append(_HEADER)
        wrote = False
        for row in token_rows:
            lines.append(
                "\t".join(
                    [
                        row["form"],
                        row["tag"],
                        row["lemma"],
                        row["normalized"],
                        row["matched"],
                        row["vocab_index"],
                        row["vocab_example"],
                        row["confidence"],
                    ]
                )
            )
            wrote = True
        if not wrote:
            lines.append("(필터 후 기록할 토큰 없음)")
        lines.append("")

    lines.append("low_confidence_tokens:")
    lines.append(_LOW_CONF_HEADER)
    if all_low_conf:
        for row in all_low_conf:
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

    block = "\n".join(lines) + "\n"
    with _LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(block)


def main() -> None:
    print("=" * 70)
    print("  어휘 매칭 대화형 테스트 도구")
    print("  - 문장을 입력하면 Kiwi 토크나이징 후 vocabulary.json 매칭 결과를 출력합니다")
    print("  - 'q' 또는 빈 줄 입력 시 세션을 종료하고 로그를 저장합니다")
    print("=" * 70)

    use_llm_input = input("\n  LLM 동음이의어 판별 사용? (y/n, 기본값 y): ").strip().lower()
    use_llm = use_llm_input != "n"
    print("  → LLM 동음이의어 판별 활성화" if use_llm else "  → LLM 미사용 (후보 첫 번째 항목으로 임시 선택)")

    user_id_input = input("  사용자 ID (기본값 test): ").strip()
    user_id = user_id_input if user_id_input else "test"

    print("\n  데이터 로딩 중...")
    kiwi = Kiwi()
    vocab_map, vocab_entries = _load_vocab_entries()
    homonyms = _load_homonyms()
    print(
        f"  → vocabulary: {len(vocab_map)}개 표제어, homonyms: {len(homonyms)}개 동음이의어 로드 완료"
    )

    utterance_logs: list[dict[str, Any]] = []
    all_low_conf: list[dict[str, str]] = []
    utterance_num = 0

    while True:
        try:
            text = input(f"\n  문장 입력 ({utterance_num + 1}번째): ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not text or text.lower() == "q":
            break

        utterance_num += 1
        token_rows, low_conf_rows = _process_utterance(
            utterance=text,
            kiwi=kiwi,
            vocab_map=vocab_map,
            vocab_entries=vocab_entries,
            homonyms=homonyms,
            use_llm=use_llm,
        )

        _print_results(text, token_rows, low_conf_rows, utterance_num)
        utterance_logs.append({"utterance": text, "tokens": token_rows})
        all_low_conf.extend(low_conf_rows)

    if utterance_logs:
        _append_log(user_id, utterance_logs, all_low_conf)
        print(f"\n  {len(utterance_logs)}개 문장 로그 저장 완료 → {_LOG_PATH}")
    else:
        print("\n  입력된 문장이 없어 로그를 저장하지 않습니다.")

    print("  종료.")


if __name__ == "__main__":
    main()
