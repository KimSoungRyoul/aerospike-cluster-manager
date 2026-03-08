---
name: e2e-dev
description: Local dev E2E environment — Aerospike in container, Backend + Frontend running locally
disable-model-invocation: true
arguments:
  - name: action
    description: "start | test | explore | stop | all (default: all)"
    required: false
  - name: spec
    description: "Specific spec file or test name filter (optional, for test action)"
    required: false
---

# E2E Dev — Local Development E2E Testing

로컬 개발 E2E 환경. Aerospike만 컨테이너로 띄우고, Backend/Frontend는 로컬에서 직접 실행합니다. 코드 변경 시 hot-reload가 적용되어 빠른 피드백이 가능합니다.

## Architecture

```
compose.dev.yaml (컨테이너)
  ├── aerospike-node-1,2,3  (host port 14790, 14791, 14792)
  ├── aerospike-exporter-1,2,3 (Prometheus 9145-9147)
  └── aerospike-tools

로컬 프로세스
  ├── backend   (port 8000, uv run uvicorn --reload)
  └── frontend  (port 3000, npm run dev) ← Playwright targets here
```

### e2e-test vs e2e-dev 차이

| | e2e-test | e2e-dev |
|---|---|---|
| Compose 파일 | `compose.yaml` | `compose.dev.yaml` |
| Aerospike 포트 | 비공개 (내부 네트워크) | 14790, 14791, 14792 |
| Backend | 컨테이너 | 로컬 (`uv run uvicorn --reload`) |
| Frontend | 컨테이너 (port 3100) | 로컬 (`npm run dev`, port 3000) |
| E2E 대상 URL | `localhost:3100` | `localhost:3000` |
| Hot-reload | 없음 | 있음 (Backend + Frontend) |
| 용도 | CI/배포 전 검증 | 로컬 개발 + 빠른 피드백 |

## Actions

### `all` (default) — 전체 워크플로우 실행

start → test → stop을 순서대로 실행합니다.

### `start` — 환경 기동

**Step 1: Aerospike 클러스터 기동**

```bash
podman compose -f compose.dev.yaml down 2>/dev/null
podman compose -f compose.dev.yaml up -d
```

Aerospike health check 대기:
```bash
until podman compose -f compose.dev.yaml ps --format json | grep -q '"Health":"healthy"'; do sleep 3; done
```

**Step 2: Backend 기동 (별도 터미널/백그라운드)**

```bash
cd backend && AEROSPIKE_HOST=localhost AEROSPIKE_PORT=14790 uv run uvicorn aerospike_cluster_manager_api.main:app --reload --host 0.0.0.0 --port 8000
```

Backend health check 대기:
```bash
until curl -sf http://localhost:8000/api/health > /dev/null 2>&1; do sleep 2; done
```

**Step 3: Frontend 기동 (별도 터미널/백그라운드)**

```bash
cd frontend && npm run dev
```

Frontend 접근 가능 확인:
```bash
until curl -sf http://localhost:3000 > /dev/null 2>&1; do sleep 2; done
```

**환경변수 참고**:
- Backend: `AEROSPIKE_HOST=localhost`, `AEROSPIKE_PORT=14790` (compose.dev.yaml의 host 매핑 포트)
- Frontend의 `BACKEND_URL` 기본값은 `http://localhost:8000` (next.config.ts rewrites)

**Aerospike Tools 사용**:
```bash
# aql 접속
podman exec -it aerospike-tools aql -h aerospike-node-1

# asadm 접속
podman exec -it aerospike-tools asadm -h aerospike-node-1
```

### `test` — Playwright spec 실행

환경이 이미 기동 중이어야 합니다. **주의**: 로컬 dev 서버는 port 3000을 사용하므로 `baseURL` override가 필요합니다.

```bash
# 전체 spec 실행 (baseURL을 localhost:3000으로 override)
cd frontend && BASE_URL=http://localhost:3000 npx playwright test

# 특정 spec 실행
cd frontend && BASE_URL=http://localhost:3000 npx playwright test e2e/specs/{spec}

# 이름으로 필터
cd frontend && BASE_URL=http://localhost:3000 npx playwright test -g "{test name}"
```

**참고**: `playwright.config.ts`의 `baseURL`이 `http://localhost:3100`으로 설정되어 있습니다. 로컬 dev 환경에서는 Frontend가 port 3000에서 실행되므로 `BASE_URL` 환경변수로 override합니다.

### `explore` — playwright-cli로 수동 브라우저 탐색

환경이 이미 기동 중이어야 합니다. `playwright-cli` skill로 브라우저를 열고 수동으로 앱을 탐색합니다.

```bash
playwright-cli open http://localhost:3000
playwright-cli snapshot
playwright-cli click e3
playwright-cli screenshot
playwright-cli close
```

이 모드는 다음 상황에 유용합니다:
- 코드 변경 후 즉시 시각적 확인 (hot-reload 반영)
- 버그 재현 및 디버깅
- E2E spec 작성 전 셀렉터 탐색

### `stop` — 환경 정지

```bash
# Aerospike 컨테이너 정지
podman compose -f compose.dev.yaml down
```

Backend/Frontend는 로컬 프로세스이므로 Ctrl+C 또는 해당 프로세스를 종료합니다.

볼륨 데이터도 삭제하려면:
```bash
podman compose -f compose.dev.yaml down -v
```

## Troubleshooting

- **Aerospike 기동 실패**: `podman compose -f compose.dev.yaml logs -f` 로 로그 확인
- **Backend 연결 실패**: `AEROSPIKE_HOST=localhost AEROSPIKE_PORT=14790`으로 설정했는지 확인
- **Frontend API 프록시 실패**: Backend가 port 8000에서 실행 중인지 확인 — `curl http://localhost:8000/api/health`
- **Port 충돌**: Aerospike(14790-14792), Backend(8000), Frontend(3000) 포트가 이미 사용 중인지 확인
- **Frontend port 3000 vs 3100**: 로컬 dev는 3000 (`npm run dev`), 컨테이너 모드는 3100 (`compose.yaml`)
