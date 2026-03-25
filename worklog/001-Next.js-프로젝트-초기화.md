# 001 - Next.js 프로젝트 초기화

## 무엇을 했나요?

`platform/` 폴더에 Next.js 15 앱을 새로 만들었습니다.

## 왜 이렇게 했나요?

- CLAUDE.md에 FE 기술 스택이 **Next.js 15+ / TypeScript / Tailwind CSS** 로 명시되어 있음
- `platform/` 폴더가 기존에 없었으므로 `create-next-app` 명령으로 새로 생성
- **App Router** 방식 선택 (Next.js 13+ 권장 방식, 파일 기반 라우팅)

## 생성된 구조

```
platform/
├── app/              ← 페이지 라우팅 폴더 (App Router)
│   ├── layout.tsx    ← 전체 공통 레이아웃
│   ├── page.tsx      ← 홈 페이지 (/)
│   └── globals.css   ← 전역 CSS
├── public/           ← 정적 파일 (이미지 등)
├── package.json      ← 프로젝트 의존성 목록
├── tsconfig.json     ← TypeScript 설정
├── next.config.ts    ← Next.js 설정
└── tailwind.config   ← Tailwind CSS 설정 (v4, postcss 방식)
```

## 설치된 주요 패키지

| 패키지 | 버전 | 역할 |
|--------|------|------|
| next | 15.5.14 | Next.js 프레임워크 |
| react | 19.1.0 | UI 라이브러리 |
| tailwindcss | ^4 | CSS 유틸리티 스타일링 |
| typescript | ^5 | 타입 안전성 |

## 기술 용어 주석

- **App Router**: Next.js 13+에서 도입된 폴더 기반 라우팅 시스템. `app/` 폴더 안에 폴더를 만들면 URL 경로가 됩니다. (예: `app/chat/page.tsx` → `/chat`)
- **TypeScript**: JavaScript에 타입(변수의 종류)을 추가한 언어. 오타나 잘못된 값을 코드 작성 시점에 잡아줍니다.
- **Tailwind CSS**: `className="bg-red-500 p-4"` 처럼 짧은 클래스명으로 스타일을 적용하는 CSS 프레임워크.
- **Turbopack**: Next.js 공식 빌드 도구. Webpack보다 빠름. `dev` 스크립트에 자동 적용됨.
