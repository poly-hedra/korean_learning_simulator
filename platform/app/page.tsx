/* ──────────────────────────────────────────
   홈 페이지 (/)
   - TODO 05~11에서 본격 구현 예정
   - 현재는 레이아웃 확인용 임시 화면
   ────────────────────────────────────────── */

export default function Home() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen px-4">
      {/* 앱 타이틀 */}
      <h1 className="text-3xl font-bold text-gold">코대헌</h1>
      <p className="mt-2 text-sm text-tab-inactive">
        Korean Dialogue Hunters
      </p>

      {/* 레이아웃 확인용 임시 안내 */}
      <div className="mt-8 w-full rounded-xl border border-gold/30 p-6 text-center">
        <p className="text-foreground">홈 화면 준비 중</p>
        <p className="mt-1 text-xs text-tab-inactive">
          max-width 480px 모바일 고정 레이아웃
        </p>
      </div>
    </div>
  );
}
