LOCATION_CONTEXT_PROMPT = """
{location}에서 외국인 대학생이 접할 수 있는 구체적인 소재들을 3~5문장으로 나열해라.

- 이 장소에서 먹을 수 있는 음식과 음료
- 이 장소에서 볼 수 있는 명소나 랜드마크
- 이 장소에서 할 수 있는 활동 (다양하게)
- 이 장소의 분위기나 느낌 (예: 조용한지 시끄러운지, 낭만적인지 활기찬지)
- 이 장소와 관련된 시간 맥락 (예: 운영 시간, 붐비는 시간대, 계절·날씨 영향)
- 이 장소를 배경으로 다음 약속이나 계획을 이야기할 수 있는 소재

주의:
- 확실하지 않은 브랜드명·장소명은 일반 표현으로 대체할 것
  (예: 없는 브랜드 → "편의점", "푸드트럭", "한강 카페")
- 실제 사실에 기반한 정보만 포함하고 가상의 정보는 피할 것
- 설명·번호·제목·주석·자기 수정 없이 자연스러운 문장으로만 출력한다
{location_specific_note}
"""

_LOCATION_NOTES = {
    "한강": "- 자전거 타기는 최소화하고 다른 활동 위주로 작성할 것",
    "지하철": "- 환승 노선·출구 정보는 실제 사실만 포함할 것",
}

def build_location_context_prompt(location: str) -> str:
    note = _LOCATION_NOTES.get(location, "")
    note_str = f"\n{note}" if note else ""
    return LOCATION_CONTEXT_PROMPT.format(
        location=location,
        location_specific_note=note_str
    )