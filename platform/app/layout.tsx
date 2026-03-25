import type { Metadata } from "next";
import "./globals.css";

/* ──────────────────────────────────────────
   전체 레이아웃 (Root Layout)
   - 모든 페이지에 공통으로 적용되는 최상위 레이아웃
   - 모바일 웹 고정: max-width 480px, 가운데 정렬
   ────────────────────────────────────────── */

export const metadata: Metadata = {
  title: "코대헌 — Korean Dialogue Hunters",
  description: "AI와 함께하는 한국어 대화 학습 시뮬레이터",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body>
        {/* 모바일 고정 래퍼: 최대 480px, 화면 중앙 배치 */}
        <div className="mx-auto w-full max-w-[480px] min-h-screen relative">
          {children}
        </div>
      </body>
    </html>
  );
}
