"""애플리케이션 설정.

이 파일은 서비스 전역 설정을 한 곳에서 관리합니다.
특히 LLM 모델명과 대화 턴 수/평가 가중치처럼 여러 모듈에서
동일하게 참고해야 하는 값을 상수로 둡니다.
"""

from dataclasses import dataclass
import os
from pathlib import Path


def _load_dotenv() -> None:
    """로컬 .env 파일을 프로세스 환경 변수로 로드한다.

    외부 패키지 의존성을 추가하지 않고, 현재 프로젝트 루트의 .env만 단순 파싱합니다.
    이미 셸 환경에 들어있는 값은 덮어쓰지 않습니다.
    """

    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", maxsplit=1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


_load_dotenv()


@dataclass(frozen=True)
class Settings:
    """환경 변수에서 읽되 안전한 기본값을 사용하는 런타임 설정."""

    app_name: str = os.getenv("APP_NAME", "korean-learning-agent")
    llm_model: str = os.getenv("LLM_MODEL", "solar-pro2")
    upstage_api_key: str = os.getenv("UPSTAGE_API_KEY", "")
    upstage_base_url: str = os.getenv("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1")
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))

    # 대화 난이도별 최대 턴 수 (사용자 발화 수 기준)
    turn_limit_by_level: dict[str, int] = None  # type: ignore[assignment]

    # 평가 항목 가중치 (합계 1.0)
    score_weight_vocab: float = 0.30
    score_weight_context: float = 0.50
    score_weight_spelling: float = 0.20

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "turn_limit_by_level",
            {"Beginner": 3, "Intermediate": 5, "Advanced": 7},
        )


settings = Settings()
