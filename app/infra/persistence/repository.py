"""In-memory persistence repository used by the application layer."""

from __future__ import annotations

from collections import defaultdict

from app.infra.persistence.models import (
    SessionRecord,
    UserProfileRecord,
    WrongWordRecord,
)


class Repository:
    """로컬 개발용 인메모리 저장소."""

    def __init__(self) -> None:
        self.users: dict[str, UserProfileRecord] = {}
        self.sessions_by_user: dict[str, list[SessionRecord]] = defaultdict(list)
        self.sessions_by_id: dict[str, SessionRecord] = {}
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
            existing.country = country
            existing.korean_level = korean_level
            existing.has_korean_media_experience = has_korean_media_experience
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
        self.sessions_by_id[record.session_id] = record
        existing = [
            session
            for session in self.sessions_by_user[record.user_id]
            if session.session_id != record.session_id
        ]
        existing.append(record)
        self.sessions_by_user[record.user_id] = existing
        if record.user_id in self.users:
            self.users[record.user_id].latest_tier = record.tier

    def get_session(self, session_id: str) -> SessionRecord | None:
        return self.sessions_by_id.get(session_id)

    def next_week_for_user(self, user_id: str) -> int:
        return len(self.sessions_by_user.get(user_id, [])) + 1

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
        return sorted(sessions, key=lambda session: session.total_score_10)[:top_k]

    def get_wrong_word_pool(self, user_id: str) -> list[WrongWordRecord]:
        return self.wrong_words_by_user.get(user_id, [])


repository = Repository()
