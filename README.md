# korean_learning_simulator

이상적인 브랜치 개수 상태

## 🔵 평소 상태

main
dev

## 🟢 작업 중

main
dev
feat/a
feat/b
feat/c
feat/d

## 🔴 작업 끝나면

main
dev

### 👉 다시 깔끔하게 돌아옴

---

## ✅ 1️⃣ 클론 한 뒤, 현 상태 파악

git clone (git init 금지!!!)
git status 또는 git branch

## ✅ 2️⃣ 각자 작업 시작

브랜치 생성
git checkout dev
git pull origin dev
git checkout -b feat/login

### 👉 반드시 dev에서 따야 함

## ✅ 3️⃣ 작업 후 (핵심 루틴)

스테이지에 올리기: git add .
커밋 메세지 작성: git commit -m "feat: 로그인 기능"
원격에 push: git push origin feat/login

### 👉 그리고 GitHub에서

### 👉 PR: feat → dev

## ✅ 4️⃣ 5️⃣ merge 후 정리

로컬 삭제: git branch -d feat/login
원격 삭제: git push origin --delete feat/login