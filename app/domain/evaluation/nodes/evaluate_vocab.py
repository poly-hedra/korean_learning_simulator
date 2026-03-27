"""평가 노드: 어휘 다양성 (30%) + 어휘 목록 일치 (SCK_correspondence)."""

import json
import re
from pathlib import Path
from typing import Any

from kiwipiepy import Kiwi
from app.infra.ai.rag_service import rag_service
from app.infra.ai.service import llm_service
from ..dialogue_cleansing import (
    build_normalized_tokens,
    build_original_tokens,
    canonicalize_word,
    expand_vocab_word_forms,
    is_main_pos_tag,
    normalize_token_for_vocab,
    resolve_entries_by_pos,
)
from ..normalization_debug import maybe_log_irregular_samples
from ..token_usage_persistence import append_token_usage_log
from ..state import EvaluationState

_VOCAB_PATH = Path(__file__).parents[3] / "infra" / "persistence" / "data" / "vocabulary.json"
_HOMONYMS_PATH = (
    Path(__file__).parents[3] / "infra" / "persistence" / "data" / "vocabulary_homonyms.json"
)
_LLM_WSD_CONFIDENCE_THRESHOLD = 0.7
_LLM_SUSPICIOUS_CONFIDENCE_THRESHOLD = 0.85


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
            "example": str(entry.get("example", "")),
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


# 동음이의어 의미선택 단계(WSD, word sense disambiguation) LLM 호출
def _resolve_entry_by_llm(
    match_key: str,
    token_tag: str,
    utterance: str,
    token_index: int,
    tokens,
    candidates: list[dict[str, Any]],
) -> tuple[dict[str, Any] | None, float]:
    """품사 필터 후보 리스트에서 LLM으로 최종 엔트리를 선택한다.

    각 후보의 example 필드를 프롬프트에 포함해 문맥 기반 판별 정확도를 높인다.
    """

    if len(candidates) <= 1:
        return (candidates[0], 1.0) if candidates else (None, 0.0)

    left = max(0, token_index - 4)
    right = min(len(tokens), token_index + 5)
    local_context = " ".join(tok.form for tok in tokens[left:right])
    candidate_lines = [
        (
            f"- index={c.get('index')} | word={c.get('word')} | kind={c.get('kind')}"
            f" | example={c.get('example', '없음')}"
        )
        for c in candidates
    ]

    system_prompt = (
        "너는 한국어 동음이의어 의미 판별기다. "
        "문장과 로컬 문맥, 그리고 각 후보의 example(용례)을 근거로 가장 적절한 후보를 선택하라. "
        "불확실하면 null을 반환한다. 반드시 JSON 객체만 반환한다."
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

    for entry in candidates:
        if str(entry.get("index")) == str(selected_index):
            return entry, confidence

    return None, confidence


def _is_suspicious_pattern(tokens: list[Any], token_index: int) -> bool:
    """Kiwi 오분석 가능성이 높은 패턴인지 판별한다."""

    token = tokens[token_index]

    # 드세요 -> 드세/VA + 어미(E*) 오분석 가능
    if (
        token.tag == "VA"
        and token.form == "드세"
        and token_index + 1 < len(tokens)
        and tokens[token_index + 1].tag.startswith("E")
    ):
        return True

    # 바로 다음이 존칭 EP(시/으시)이고 그 다음이 어미면, 현재 토큰의 품사/표제어 오분석 가능성이 높다.
    if (
        token_index + 2 < len(tokens)
        and tokens[token_index + 1].tag == "EP"
        and tokens[token_index + 1].form in {"시", "으시"}
        and tokens[token_index + 2].tag.startswith("E")
    ):
        if token.tag in {"IC", "NNP", "NNG", "MAG", "VV", "VA"}:
            return True

    # token 자체가 드시/드시다처럼 존칭형으로 복원된 경우 + 뒤에 어미가 바로 붙는 패턴
    if (
        token.tag in {"VV", "VA"}
        and str(getattr(token, "lemma", "")).endswith("시다")
        and token_index + 1 < len(tokens)
        and tokens[token_index + 1].tag.startswith("E")
    ):
        return True

    return False


# 동사/형용사 정규화 보정 LLM 호출
def _resolve_suspicious_normalization_by_llm(
    utterance: str,
    token_index: int,
    tokens: list[Any],
) -> tuple[str | None, float]:
    """의심 패턴에서만 LLM으로 정규화 후보를 판별한다."""

    token = tokens[token_index]
    if not _is_suspicious_pattern(tokens, token_index):
        return None, 0.0

    left = max(0, token_index - 4)
    right = min(len(tokens), token_index + 5)
    local_context = " ".join(tok.form for tok in tokens[left:right])

    candidates = [
        "들다 (동사, '(음식을) 드시다' 계열)",
        "드세다 (형용사, '고집이 드세다')",
        "알다 / 살다 / 멀다 / 울다 / 불다 / 놀다 / 떠들다 (존칭 오분석 빈출)",
    ]

    system_prompt = (
        "너는 한국어 형태소 오분석 보정기다. 문맥을 보고 정규화 표제어를 하나 선택한다. "
        "확신이 낮으면 null을 반환한다. 반드시 JSON 객체만 반환한다."
    )
    user_prompt = (
        f"문장: {utterance}\n"
        f"대상 토큰: form={token.form}, tag={token.tag}, lemma={getattr(token, 'lemma', '')}\n"
        f"로컬 문맥: {local_context}\n"
        "후보:\n- " + "\n- ".join(candidates) + "\n\n"
        "다음 JSON 형식으로만 답해줘:\n"
        '{"normalized": "사전형_또는_null", "confidence": 0.0, "reason": "짧은 근거"}'
    )

    raw = llm_service.generate_text(
        system_prompt=system_prompt, user_prompt=user_prompt
    )
    parsed = _extract_json_object(raw)
    if not parsed:
        return None, 0.0

    normalized = str(parsed.get("normalized", "")).strip()
    try:
        confidence = float(parsed.get("confidence", 0.0))
    except Exception:
        confidence = 0.0

    normalized = canonicalize_word(normalized)
    if normalized.lower() == "null" or normalized not in _vocab_map:
        return None, confidence

    return normalized, confidence


def evaluate_vocab(state: EvaluationState) -> EvaluationState:
    """사용자 발화만 기준으로 어휘 다양성 점수와 어휘 목록 일치 항목을 계산한다."""

    # 내부 디버그 모드일 때만 불규칙 활용 샘플 정규화 결과를 파일로 남긴다.
    maybe_log_irregular_samples(_kiwi, normalize_token_for_vocab)

    user_utterances = [
        turn["utterance"]
        for turn in state.get("conversation_log", [])
        if turn.get("speaker") == "user"
    ]

    original_tokens: list[str] = []
    normalized_tokens: list[str] = []
    utterance_token_logs: list[dict[str, Any]] = []
    matched_occurrences = 0
    level_counts: dict[str, int] = {}
    level_word_counts: dict[str, dict[str, int]] = {}
    matched: dict[str, dict[str, str | int]] = {}
    unresolved_homonyms: dict[str, int] = {}
    llm_cache: dict[tuple[str, str, str, str], tuple[dict[str, Any] | None, float]] = {}
    suspicious_cache: dict[tuple[str, int, str, str], tuple[str | None, float]] = {}
    suspicious_token_reviews: list[dict[str, str]] = []

    for utterance in user_utterances:
        tokens = _kiwi.tokenize(utterance)
        original_tokens.extend(build_original_tokens(tokens))
        normalized_tokens.extend(build_normalized_tokens(tokens))

        token_rows: list[dict[str, str]] = []
        token_row_indices: dict[int, int] = {}
        for token_idx, token in enumerate(tokens):
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
        utterance_token_logs.append({"utterance": utterance, "tokens": token_rows})

        compound_consumed: set[int] = set()

        for token_idx, token in enumerate(tokens):
            if token_idx in compound_consumed:
                continue

            original_word = token.form
            normalized_word = (
                normalize_token_for_vocab(token)
                if is_main_pos_tag(token.tag)
                else token.form
            )
            source = ""
            confidence = 0.0

            # --- 복합 매칭 블록 ---
            # XSN(접미사) 복합 매칭: 선생+님=선생님
            # XR+XSA/XSV(어근+하다) 복합 매칭: 조용+하다=조용하다
            compound_key: str | None = None
            compound_tag: str | None = None
            consumed_idx: int | None = None

            if (
                is_main_pos_tag(token.tag)
                and token_idx + 1 < len(tokens)
                and tokens[token_idx + 1].tag == "XSN"
            ):
                compound_key = canonicalize_word(
                    token.form + tokens[token_idx + 1].form
                )
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

            if compound_key and compound_key in _vocab_map and consumed_idx is not None:
                compound_candidates = resolve_entries_by_pos(
                    match_key=compound_key,
                    token_tag=compound_tag or token.tag,
                    vocab_entries=_vocab_entries,
                    homonyms=_homonyms,
                )
                if compound_candidates:
                    compound_entry = compound_candidates[0]
                    source = "복합매칭"
                    confidence = 1.0
                    compound_consumed.add(consumed_idx)

                    level = str(compound_entry["level"])
                    matched_occurrences += 1
                    level_counts[level] = level_counts.get(level, 0) + 1
                    if level not in level_word_counts:
                        level_word_counts[level] = {}
                    level_word_counts[level][compound_key] = (
                        level_word_counts[level].get(compound_key, 0) + 1
                    )

                    if compound_key not in matched:
                        matched[compound_key] = {
                            "original_word": token.form + tokens[consumed_idx].form,
                            "normalized_word": compound_key,
                            "index": str(compound_entry["index"]),
                            "kind": str(compound_entry["kind"]),
                            "level": level,
                            "source": source,
                            "confidence": 1.0,
                            "count": 1,
                        }
                    else:
                        matched[compound_key]["count"] = (
                            int(matched[compound_key]["count"]) + 1
                        )

                    token_row_index = token_row_indices.get(id(token))
                    if token_row_index is not None:
                        token_rows[token_row_index]["matched"] = "O"
                        token_rows[token_row_index]["normalized"] = compound_key
                        token_rows[token_row_index]["vocab_index"] = str(
                            compound_entry["index"]
                        )
                        token_rows[token_row_index]["vocab_example"] = str(
                            compound_entry.get("example", "")
                        )
                        token_rows[token_row_index]["confidence"] = "1.00"
                    continue

            if _is_suspicious_pattern(tokens, token_idx):
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

                suspicious_token_reviews.append(
                    {
                        "utterance": utterance,
                        "form": token.form,
                        "tag": token.tag,
                        "lemma": str(getattr(token, "lemma", "")),
                        "normalized": canonicalize_word(normalized_word),
                        "confidence": f"{llm_conf:.2f}",
                        "applied": "Y"
                        if (
                            llm_normalized is not None
                            and llm_conf >= _LLM_SUSPICIOUS_CONFIDENCE_THRESHOLD
                        )
                        else "N",
                    }
                )

            if not is_main_pos_tag(token.tag) and not source:
                continue

            match_key = canonicalize_word(normalized_word)
            if match_key not in _vocab_map:
                token_row_index = token_row_indices.get(id(token))
                if token_row_index is not None and confidence > 0:
                    token_rows[token_row_index]["confidence"] = f"{confidence:.2f}"
                continue

            candidates = resolve_entries_by_pos(
                match_key=match_key,
                token_tag=token.tag,
                vocab_entries=_vocab_entries,
                homonyms=_homonyms,
            )

            selected_entry = None

            if len(candidates) == 0:
                token_row_index = token_row_indices.get(id(token))
                if token_row_index is not None and confidence > 0:
                    token_rows[token_row_index]["confidence"] = f"{confidence:.2f}"
                continue

            elif len(candidates) == 1:
                selected_entry = candidates[0]
                if not source:
                    source = "단일항목 확정"
                confidence = max(confidence, 1.0)

            else:
                # 후보가 2개 이상이면 LLM이 example 기반으로 최종 판별
                candidate_sig = "|".join(
                    sorted(str(c.get("index", "")) for c in candidates)
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
                    unresolved_homonyms[match_key] = (
                        unresolved_homonyms.get(match_key, 0) + 1
                    )
                    token_row_index = token_row_indices.get(id(token))
                    if token_row_index is not None and confidence > 0:
                        token_rows[token_row_index]["confidence"] = f"{confidence:.2f}"
                    continue

            level = str(selected_entry["level"])
            matched_occurrences += 1
            level_counts[level] = level_counts.get(level, 0) + 1
            if level not in level_word_counts:
                level_word_counts[level] = {}
            level_word_counts[level][match_key] = (
                level_word_counts[level].get(match_key, 0) + 1
            )

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

            token_row_index = token_row_indices.get(id(token))
            if token_row_index is not None:
                token_rows[token_row_index]["matched"] = "O"
                token_rows[token_row_index]["normalized"] = match_key
                token_rows[token_row_index]["vocab_index"] = str(
                    selected_entry["index"]
                )
                token_rows[token_row_index]["vocab_example"] = str(
                    selected_entry.get("example", "")
                )
                token_rows[token_row_index]["confidence"] = f"{confidence:.2f}"

    sck_correspondence = list(matched.values())
    token_count = len(normalized_tokens)
    match_rate = (
        round((matched_occurrences / token_count) * 100, 2) if token_count else 0.0
    )

    try:
        append_token_usage_log(
            state=state,
            utterance_token_logs=utterance_token_logs,
            tokenized_original_words=original_tokens,
            tokenized_normalized_words=normalized_tokens,
        )
    except Exception:
        # 로깅 실패가 평가 플로우를 중단시키지 않도록 방어한다.
        pass

    return {
        "vocab_score": rag_service.vocab_diversity_score(user_utterances),
        "tokenized_original_words": original_tokens,
        "tokenized_normalized_words": normalized_tokens,
        "SCK_correspondence": sck_correspondence,
        "SCK_match_count": matched_occurrences,
        "SCK_total_tokens": token_count,
        "SCK_match_rate": match_rate,
        "SCK_level_counts": level_counts,
        "SCK_level_word_counts": level_word_counts,
        "SCK_unresolved_homonyms": unresolved_homonyms,
        "SCK_suspicious_tokens": suspicious_token_reviews,
    }
