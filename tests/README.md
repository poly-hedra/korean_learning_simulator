# tests/

`pytest` 기반 자동 테스트 코드 위치.

## 원칙

- `tests/`에는 자동 검증용 테스트 코드만 둔다.
- 수동 실행 스크립트는 `scripts/`로 분리한다.
- 테스트는 현재 구현된 비즈니스 로직 동작을 고정하는 데 집중한다.

## 실행 방법

> 반드시 **프로젝트 루트(`korean_learning_simulator/`)** 에서 실행
>
> `python tests/test_xxx.py` 방식으로 실행하면 상위 패키지를 못 찾으므로 반드시 `-m` 플래그를 사용한다.

```bash
# 기본 실행 (한강, 1회)
python -m tests.test_generate_scenario

# 장소·횟수 지정
python -m tests.test_generate_scenario --location 명동 --runs 3

# 수준 지정
python -m tests.test_generate_scenario --location 편의점 --level Intermediate --runs 5
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
python -m tests.parse_scenario_results

# 파일 직접 지정
python -m tests.parse_scenario_results --file tests/results/scenario_한강_20260326_202632.json
```

CSV는 JSON과 같은 경로에 저장된다. `utf-8-sig` 인코딩이라 구글 시트/엑셀에서 한글이 깨지지 않는다.
