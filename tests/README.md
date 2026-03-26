# tests/

시나리오 생성 품질 검증 스크립트 모음.

---

## 파일 구조

```
tests/
├── test_generate_scenario.py   # 시나리오 생성 테스트 (메인)
├── parse_scenario_results.py   # 결과 JSON → CSV 변환
└── results/                    # 실행 결과 JSON/CSV 저장 위치 (gitignore)
```

---

## 실행 방법

> 반드시 **프로젝트 루트(`korean_learning_simulator/`)** 에서 실행

```bash
# 기본 실행 (한강, 1회)
python tests/test_generate_scenario.py

# 장소·횟수 지정
python tests/test_generate_scenario.py --location 명동 --runs 3

# 수준 지정
python tests/test_generate_scenario.py --location 편의점 --level Intermediate --runs 5
```

실행 후 `tests/results/` 에 JSON 파일이 생성된다.

### 옵션 요약

| 옵션 | 기본값 | 설명 |
|------|--------|------|
| `--location` | 한강 | 장소 (한강 / 지하철 / 편의점 등) |
| `--level` | Beginner | 학습자 수준 (`Beginner` / `Intermediate` / `Advanced`) |
| `--runs` | 1 | 반복 횟수 |

---

## 결과 파싱 (JSON → CSV)

생성한 결과 JSON을 구글 시트용 CSV로 변환:

```bash
# 최신 결과 파일 자동 선택
python tests/parse_scenario_results.py

# 파일 직접 지정
python tests/parse_scenario_results.py --file tests/results/scenario_한강_20260324_183255.json
```

CSV는 JSON과 같은 경로에 저장된다. `utf-8-sig` 인코딩이라 구글 시트/엑셀에서 한글이 깨지지 않는다.
