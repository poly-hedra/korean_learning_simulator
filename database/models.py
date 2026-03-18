"""Database models.

현재는 단순화를 위해 dataclass 기반 인메모리 모델을 사용합니다.
향후 SQLModel/ORM으로 전환해도 repository 인터페이스는 유지됩니다.
"""

from dataclasses import dataclass, field


@dataclass
class SessionRecord:
    user_id: str
    week: int
    korean_level: str
    location: str
    scenario: str
    conversation_log: list[dict]
    total_score_10: float
    tier: str


@dataclass
class WrongWordRecord:
    user_id: str
    word: str
    meaning: str
    source_session_week: int


@dataclass
class UserProfileRecord:
    user_id: str
    country: str
    korean_level: str
    has_korean_media_experience: bool
    selected_role: str = "A"
    latest_tier: str = ""
    extra: dict = field(default_factory=dict)
