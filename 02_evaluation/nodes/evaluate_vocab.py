"""평가 노드: 어휘 다양성 (30%) + 어휘 목록 일치 (SCK_correspondence)."""

import json
import re
from pathlib import Path
from typing import Any

from kiwipiepy import Kiwi
from services.llm_service import llm_service
from services.rag_service import rag_service
from ..dialogue_cleansing import (
    MAIN_POS_TAGS,
    build_normalized_tokens,
    build_original_tokens,
    canonicalize_word,
    expand_vocab_word_forms,
    normalize_token_for_vocab,
    resolve_entry_by_pos,
)
from ..state import EvaluationState

_VOCAB_PATH = Path(__file__).parents[2] / "database" / "vocabulary.json"
_HOMONYMS_PATH = Path(__file__).parents[2] / "database" / "vocabulary_homonyms.json"
_LLM_WSD_CONFIDENCE_THRESHOLD = 0.7


def _load_vocab_map() -> dict[str, str]:
    """vocabulary.json 에서 {기본형: 급수} 맵을 반환한다."""
    with _VOCAB_PATH.open(encoding="utf-8") as f:
        entries = json.load(f)

    vocab_map: dict[str, str] = {}
    for entry in entries:
        level = str(entry["index"]).split("_")[0]
        for form in expand_vocab_word_forms(entry["word"]):
            vocab_map[form] = level
    return vocab_map


def _load_vocab_entries() -> dict[str, list[dict[str, str]]]:
    """vocabulary.json 에서 표제어별 상세 엔트리 목록을 로드한다."""

    with _VOCAB_PATH.open(encoding="utf-8") as f:
        entries = json.load(f)

    vocab_entries: dict[str, list[dict[str, str]]] = {}
    for entry in entries:
        level = str(entry["index"]).split("_")[0]
        payload = {
            "index": str(entry["index"]),
            "word": str(entry.get("word", "")),
            "kind": str(entry.get("kind", "")),
            "level": level,
        }
        for form in expand_vocab_word_forms(entry["word"]):
            vocab_entries.setdefault(form, []).append(payload)
    return vocab_entries


def _load_homonyms() -> dict[str, list[dict[str, str]]]:
    """동음이의어 사전 레이어를 로드한다."""

    if not _HOMONYMS_PATH.exists():
        return {}

    with _HOMONYMS_PATH.open(encoding="utf-8") as f:
        data = json.load(f)
    return {str(k): list(v) for k, v in data.items()}


_kiwi = Kiwi()
_vocab_map: dict[str, str] = _load_vocab_map()
_vocab_entries: dict[str, list[dict[str, str]]] = _load_vocab_entries()
_homonyms: dict[str, list[dict[str, str]]] = _load_homonyms()


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """LLM 응답에서 JSON 객체를 파싱한다."""

    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        pass

    match = re.search(r"\{[\s\S]*\}", text)
    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
        return parsed if isinstance(parsed, dict) else None
    except Exception:
        return None


def _resolve_entry_by_llm(
    match_key: str,
    token_tag: str,
    utterance: str,
    token_index: int,
    tokens,
) -> tuple[dict[str, Any] | None, float]:
    """미해결 동음이의어를 LLM으로 판별한다."""

    candidates = _homonyms.get(match_key, [])
    if len(candidates) <= 1:
        return None, 0.0

    left = max(0, token_index - 4)
    right = min(len(tokens), token_index + 5)
    local_context = " ".join(tok.form for tok in tokens[left:right])
    candidate_lines = [
        f"- index={c.get('index')} | word={c.get('word')} | kind={c.get('kind')}"
        for c in candidates
    ]

    system_prompt = (
        "너는 한국어 동음이의어 의미 판별기다. 후보 중 하나를 선택하거나 불확실하면 null을 반환한다. "
        "반드시 JSON 객체만 반환한다."
    )
    user_prompt = (
        f"표제어: {match_key}\n"
        f"Kiwi 품사: {token_tag}\n"
        f"문장: {utterance}\n"
        f"로컬 문맥: {local_context}\n"
        "후보:\n" + "\n".join(candidate_lines) + "\n\n"
        "다음 JSON 형식으로만 답해줘:\n"
        '{"index": "선택한_index_또는_null", "confidence": 0.0, "reason": "짧은 근거"}'
    )

    raw = llm_service.generate_text(
        system_prompt=system_prompt, user_prompt=user_prompt
    )
    parsed = _extract_json_object(raw)
    if not parsed:
        return None, 0.0

    selected_index = parsed.get("index")
    try:
        confidence = float(parsed.get("confidence", 0.0))
    except Exception:
        confidence = 0.0

    if not selected_index or str(selected_index).lower() == "null":
        return None, confidence

    for entry in _vocab_entries.get(match_key, []):
        if entry["index"] == str(selected_index):
            return entry, confidence

    return None, confidence


def evaluate_vocab(state: EvaluationState) -> EvaluationState:
    """사용자 발화만 기준으로 어휘 다양성 점수와 어휘 목록 일치 항목을 계산한다."""

    user_utterances = [
        turn["utterance"]
        for turn in state.get("conversation_log", [])
        if turn.get("speaker") == "user"
    ]

    original_tokens: list[str] = []
    normalized_tokens: list[str] = []
    matched_occurrences = 0
    level_counts: dict[str, int] = {}
    matched: dict[str, dict[str, str | int]] = {}
    unresolved_homonyms: dict[str, int] = {}
    llm_cache: dict[tuple[str, str, str], tuple[dict[str, Any] | None, float]] = {}

    for utterance in user_utterances:
        tokens = _kiwi.tokenize(utterance)
        original_tokens.extend(build_original_tokens(tokens))
        normalized_tokens.extend(build_normalized_tokens(tokens))

        for token_idx, token in enumerate(tokens):
            if token.tag not in MAIN_POS_TAGS:
                continue

            original_word = token.form
            normalized_word = normalize_token_for_vocab(token)
            match_key = canonicalize_word(normalized_word)
            if match_key not in _vocab_map:
                continue

            selected_entry = resolve_entry_by_pos(
                match_key=match_key,
                token_tag=token.tag,
                vocab_entries=_vocab_entries,
                homonyms=_homonyms,
            )
            if selected_entry is None:
                source = ""
                confidence = 0.0

                if match_key in _homonyms:
                    cache_key = (match_key, utterance, token.tag)
                    if cache_key not in llm_cache:
                        llm_cache[cache_key] = _resolve_entry_by_llm(
                            match_key=match_key,
                            token_tag=token.tag,
                            utterance=utterance,
                            token_index=token_idx,
                            tokens=tokens,
                        )
                    llm_entry, llm_conf = llm_cache[cache_key]
                    confidence = llm_conf
                    if (
                        llm_entry is not None
                        and confidence >= _LLM_WSD_CONFIDENCE_THRESHOLD
                    ):
                        selected_entry = llm_entry
                        source = "LLM 확정"
                    else:
                        unresolved_homonyms[match_key] = (
                            unresolved_homonyms.get(match_key, 0) + 1
                        )
                        continue
                else:
                    continue
            else:
                if match_key in _homonyms:
                    source = "품사필터 확정"
                else:
                    source = "단일항목 확정"
                confidence = 1.0

            level = str(selected_entry["level"])
            matched_occurrences += 1
            level_counts[level] = level_counts.get(level, 0) + 1

            if match_key not in matched:
                matched[match_key] = {
                    "original_word": original_word,
                    "normalized_word": match_key,
                    "index": str(selected_entry["index"]),
                    "kind": str(selected_entry["kind"]),
                    "level": level,
                    "source": source,
                    "confidence": round(confidence, 2),
                    "count": 1,
                }
            else:
                matched[match_key]["count"] = int(matched[match_key]["count"]) + 1

    sck_correspondence = list(matched.values())
    token_count = len(normalized_tokens)
    match_rate = (
        round((matched_occurrences / token_count) * 100, 2) if token_count else 0.0
    )

    return {
        "vocab_score": rag_service.vocab_diversity_score(user_utterances),
        "tokenized_original_words": original_tokens,
        "tokenized_normalized_words": normalized_tokens,
        "SCK_correspondence": sck_correspondence,
        "SCK_match_count": matched_occurrences,
        "SCK_total_tokens": token_count,
        "SCK_match_rate": match_rate,
        "SCK_level_counts": level_counts,
        "SCK_unresolved_homonyms": unresolved_homonyms,
    }
