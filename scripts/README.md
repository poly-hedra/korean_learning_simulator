# scripts/

수동 검증용 실행 스크립트 모음.

## 파일 구조

```text
scripts/
├── generate_scenario.py
├── parse_scenario_results.py
├── vocab_matching_interactive.py
└── results/
```

## 실행 예시

```bash
python scripts/generate_scenario.py --location 한강 --runs 3
python scripts/parse_scenario_results.py
python -m scripts.vocab_matching_interactive
```
