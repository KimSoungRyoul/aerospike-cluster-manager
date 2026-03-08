---
name: local-project-setup
description: Check and set up local development environment prerequisites
disable-model-invocation: true
---

# Local Project Setup

로컬 개발 환경에 필요한 도구들을 검사하고 설치를 안내합니다.

## Workflow

아래 항목을 순서대로 검사합니다. 각 항목에 대해 설치 여부를 확인하고, 미설치 시 설치 명령을 안내하거나 실행합니다.

### 1. Container Runtime (docker 또는 podman)

```bash
# 둘 중 하나만 있으면 OK
docker --version 2>/dev/null || podman --version 2>/dev/null
docker compose version 2>/dev/null || podman compose --version 2>/dev/null
```

- docker 또는 podman 중 하나 설치되어 있으면 통과
- 둘 다 없으면 안내:
  - macOS: `brew install podman && podman machine init && podman machine start`
  - 또는: Docker Desktop 설치 (https://www.docker.com/products/docker-desktop)
- `compose` 플러그인도 함께 확인

### 2. Node.js & npm

```bash
node --version  # 20+ 권장
npm --version
```

- 미설치 시: `brew install node` 또는 nvm 사용 안내

### 3. Python & uv

```bash
python3 --version  # 3.13+ 필수
uv --version
```

- Python 3.13 미만이면 경고
- uv 미설치 시: `curl -LsSf https://astral.sh/uv/install.sh | sh`

### 4. GitHub CLI (gh)

```bash
gh --version
gh auth status
```

- 미설치 시: `brew install gh`
- 설치되어 있지만 미인증 시: `gh auth login` 안내

### 5. Playwright browsers & CLI skill

```bash
# Playwright 브라우저 설치
cd frontend && npx playwright install

# playwright-cli skill 설치
playwright-cli install --skills
```

### 6. pre-commit

```bash
pre-commit --version
```

- 미설치 시: `brew install pre-commit` 또는 `pip install pre-commit`
- 설치 후 hooks 활성화: `pre-commit install`

### 7. Frontend 의존성 설치

```bash
cd frontend && npm install
```

### 8. Backend 의존성 설치

```bash
cd backend && uv sync
```

## Output

검사 결과를 테이블 형태로 요약합니다:

```
| 항목                | 상태 | 버전/비고           |
|---------------------|------|---------------------|
| Container Runtime   | ✅   | podman 5.x          |
| Node.js             | ✅   | v22.x               |
| Python              | ✅   | 3.13.x              |
| uv                  | ✅   | 0.x.x               |
| GitHub CLI          | ✅   | gh 2.x (인증됨)     |
| Playwright browsers | ✅   | 설치 완료           |
| playwright-cli      | ✅   | skill 설치 완료     |
| pre-commit          | ✅   | hooks 활성화됨      |
| Frontend deps       | ✅   | npm install 완료    |
| Backend deps        | ✅   | uv sync 완료        |
```

미설치 항목이 있으면 설치할지 사용자에게 확인 후 진행합니다.
