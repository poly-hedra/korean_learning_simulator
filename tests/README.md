# tests/

시나리오 생성 품질 검증 및 비교 실험 스크립트 모음.

---

## 파일 구조

```
tests/
├── test_generate_scenario.py   # 시나리오 생성 테스트 (메인)
├── parse_compare_results.py    # compare 결과 JSON → CSV 변환
├── based_prompts/
│   └── education_based.py      # 비교 기준(베이스라인) 프롬프트
└── results/                    # 실행 결과 JSON/CSV 저장 위치 (gitignore)
```

---

## 실행 방법

> 반드시 **프로젝트 루트(`korean_learning_simulator/`)** 에서 실행

```bash
# node 방식 vs education_based 비교 (기본값: 한강, 1회)
python tests/test_generate_scenario.py --mode compare --runs 5

# 장소 지정
python tests/test_generate_scenario.py --mode compare --runs 5 --location 편의점

# node 방식만 (location_context 포함)
python tests/test_generate_scenario.py --location 명동 --runs 3

# education_based만 (하드코딩 베이스라인)
python tests/test_generate_scenario.py --mode education_based --runs 3
```

실행 후 `tests/results/` 에 JSON 파일이 생성된다.

### 옵션 요약

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--location` | 한강 | 장소 (한강 / 지하철 / 편의점 등) |
| `--level` | Beginner | 학습자 수준 |
| `--runs` | 1 | 반복 횟수 |
| `--mode` | node | `node` / `education_based` / `compare` |

---

## 비교 모드 결과 파싱 (compare → CSV)

compare 모드로 생성한 JSON을 구글 시트용 CSV로 변환:

```bash
# 최신 compare 파일 자동 선택
python tests/parse_compare_results.py

# 파일 직접 지정
python tests/parse_compare_results.py --file tests/results/scenario_한강_compare_20260324_183255.json
```

CSV는 JSON과 같은 경로에 저장된다. `utf-8-sig` 인코딩이라 구글 시트/엑셀에서 한글이 깨지지 않는다.

---

## node 방식 vs education_based 차이

| | node 방식 | education_based |
|---|---|---|
| LLM 호출 | 2회 (location_context + 시나리오) | 1회 (시나리오만) |
| 장소 정보 | LLM이 동적 생성 | 장소별 활동 목록 하드코딩 |
| 평균 응답 시간 | ~4.7s | ~2.3s |

education_based의 하드코딩 활동 목록은 **한강 / 지하철 / 편의점** 3곳만 있다. 다른 장소를 입력하면 LLM이 알아서 판단하지만 품질 편차가 생길 수 있다.
