# korean_learning_simulator

이상적인 브랜치 개수 상태

## 🔵 평소 상태

- main
- dev

## 🟢 작업 중

- main
- dev
- feat/a
- feat/b
- feat/c
- feat/d

## 🔴 작업 끝나면

- main
- dev

### 👉 다시 깔끔하게 돌아옴

---

## ✅ 1️⃣ 클론 한 뒤, 현 상태 파악

```bash
git clone <repository-url>
git status
git branch
```

git init은 사용하지 않습니다.

## ✅ 2️⃣ 각자 작업 시작

브랜치 생성 순서:

```bash
git checkout dev
git pull origin dev
git checkout -b feat/login
```

### 👉 반드시 dev에서 따야 함

## ✅ 3️⃣ 작업 후 (핵심 루틴)

```bash
git add .
git commit -m "feat: 로그인 기능"
git push origin feat/login
```

### 👉 그리고 GitHub에서

feat 브랜치에서 dev 브랜치로 PR을 생성합니다.

## ✅ 4️⃣ merge 후 정리

```bash
git branch -d feat/login
git push origin --delete feat/login
```