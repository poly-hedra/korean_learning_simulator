"""라우터와 그래프에서 사용하는 인메모리 저장소."""

from __future__ import annotations

from collections import defaultdict

from database.models import SessionRecord, UserProfileRecord, WrongWordRecord


class Repository:
    """로컬 개발용 간단한 상태 저장 계층."""

    def __init__(self) -> None:
        self.users: dict[str, UserProfileRecord] = {}
        self.sessions_by_user: dict[str, list[SessionRecord]] = defaultdict(list)
        self.wrong_words_by_user: dict[str, list[WrongWordRecord]] = defaultdict(list)

    def upsert_user_profile(
        self,
        user_id: str,
        country: str,
        korean_level: str,
        has_korean_media_experience: bool,
    ) -> UserProfileRecord:
        existing = self.users.get(user_id)
        if existing:
            return existing

        profile = UserProfileRecord(
            user_id=user_id,
            country=country,
            korean_level=korean_level,
            has_korean_media_experience=has_korean_media_experience,
        )
        self.users[user_id] = profile
        return profile

    def set_selected_role(self, user_id: str, role: str) -> None:
        if user_id in self.users:
            self.users[user_id].selected_role = role

    def save_session(self, record: SessionRecord) -> None:
        self.sessions_by_user[record.user_id].append(record)
        if record.user_id in self.users:
            self.users[record.user_id].latest_tier = record.tier

    def save_wrong_words(
        self, user_id: str, week: int, wrong_words: list[dict]
    ) -> None:
        for row in wrong_words:
            self.wrong_words_by_user[user_id].append(
                WrongWordRecord(
                    user_id=user_id,
                    word=row["word"],
                    meaning=row.get("meaning", ""),
                    source_session_week=week,
                )
            )

    def get_weekly_weak_sessions(
        self, user_id: str, top_k: int = 3
    ) -> list[SessionRecord]:
        sessions = self.sessions_by_user.get(user_id, [])
        return sorted(sessions, key=lambda s: s.total_score_10)[:top_k]

    def get_wrong_word_pool(self, user_id: str) -> list[WrongWordRecord]:
        return self.wrong_words_by_user.get(user_id, [])


repository = Repository()
