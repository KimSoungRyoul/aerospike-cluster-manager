---
name: e2e-test
description: Run full-stack E2E tests with podman compose + Playwright
disable-model-invocation: true
arguments:
  - name: action
    description: "start | test | explore | stop | all (default: all)"
    required: false
  - name: spec
    description: "Specific spec file or test name filter (optional, for test/explore action)"
    required: false
---

# E2E Test — Full-Stack End-to-End Testing (Container Mode)

전체 스택을 컨테이너로 띄워서 E2E 테스트하는 워크플로우. `compose.yaml`로 Aerospike + Backend + Frontend를 모두 컨테이너로 기동하고, Playwright로 `localhost:3100`에 접근하여 테스트합니다.

> **로컬 개발 환경에서의 E2E 테스트는 `/e2e-dev`를 사용하세요.** e2e-dev는 Aerospike만 컨테이너로 띄우고 Backend/Frontend는 로컬에서 실행하여 hot-reload가 가능합니다.

## Architecture

```
compose.yaml (전체 컨테이너 — Aerospike 포트 비공개, 내부 네트워크만 사용)
  ├── aerospike-node-1,2,3  (내부 전용, host 포트 없음)
  ├── aerospike-tools        (aql, asadm 등)
  ├── aerospike-exporter-1,2,3 (Prometheus 9145-9147)
  ├── backend               (port 8000, FastAPI)
  └── frontend              (port 3100, Next.js) ← Playwright targets here
```

**Aerospike Tools 사용**:
```bash
podman exec -it aerospike-tools aql -h aerospike-node-1
podman exec -it aerospike-tools asadm -h aerospike-node-1
```

## Actions

### `all` (default) — 전체 워크플로우 실행

start → test → stop을 순서대로 실행합니다.

### `start` — 인프라 기동

1. 기존 컨테이너 정리 및 전체 스택 빌드/기동:
```bash
podman compose -f compose.yaml down && podman compose -f compose.yaml up -d --build
```

2. 서비스 준비 상태 확인 (health check):
```bash
# Backend health check (최대 120초 대기)
until curl -sf http://localhost:8000/api/health > /dev/null 2>&1; do sleep 3; done

# Frontend 접근 가능 확인
until curl -sf http://localhost:3100 > /dev/null 2>&1; do sleep 3; done
```

3. 전체 컨테이너 상태 확인:
```bash
podman compose -f compose.yaml ps
```

**중요**: Backend는 Aerospike 3노드 모두 healthy 상태가 된 후에야 기동됩니다. Frontend는 Backend가 healthy 상태가 된 후에 기동됩니다. 전체 기동에 1~2분 소요될 수 있습니다.

### `test` — Playwright spec 실행

인프라가 이미 기동 중이어야 합니다.

```bash
# 전체 spec 실행
cd frontend && npx playwright test

# 특정 spec 실행
cd frontend && npx playwright test e2e/specs/{spec}

# 이름으로 필터
cd frontend && npx playwright test -g "{test name}"
```

**Playwright 프로젝트 구조**:
- `setup` 프로젝트: `01-connection.spec.ts` 실행 (테스트 데이터 생성)
- `features` 프로젝트: 나머지 spec 실행 (`setup`에 의존)

**사용 가능한 spec 파일**:
| Spec | 설명 |
|------|------|
| `01-connection.spec.ts` | 연결 관리 (setup 프로젝트) |
| `02-cluster.spec.ts` | 클러스터 정보 |
| `03-browser.spec.ts` | 네임스페이스/셋 브라우저 |
| `04-records.spec.ts` | 레코드 CRUD |
| `05-query.spec.ts` | 쿼리 빌더 |
| `06-indexes.spec.ts` | 보조 인덱스 |
| `08-udfs.spec.ts` | UDF 관리 |
| `09-terminal.spec.ts` | AQL 터미널 |
| `10-settings.spec.ts` | 설정 |
| `11-navigation.spec.ts` | 네비게이션 |

**테스트 결과 확인**:
```bash
# HTML 리포트 열기
cd frontend && npx playwright show-report

# 실패 시 trace 확인
cd frontend && npx playwright show-trace e2e/test-results/{trace-path}/trace.zip
```

### `explore` — playwright-cli로 수동 브라우저 탐색

인프라가 이미 기동 중이어야 합니다. `playwright-cli` skill을 사용하여 브라우저를 열고 수동으로 앱을 탐색합니다.

```bash
# 브라우저 열기
playwright-cli open http://localhost:3100

# 스냅샷으로 현재 상태 확인
playwright-cli snapshot

# 요소 클릭, 입력 등 상호작용
playwright-cli click e3
playwright-cli fill e5 "test-value"

# 스크린샷 찍기
playwright-cli screenshot

# 브라우저 닫기
playwright-cli close
```

이 모드는 다음 상황에 유용합니다:
- 새로운 기능 구현 후 시각적 확인
- 버그 재현 및 디버깅
- E2E spec 작성 전 셀렉터 탐색

### `stop` — 인프라 정지

```bash
podman compose -f compose.yaml down
```

볼륨 데이터도 삭제하려면:
```bash
podman compose -f compose.yaml down -v
```

## Global Setup/Teardown

Playwright는 자체 global setup/teardown을 가지고 있습니다:
- **global-setup** (`e2e/global-setup.ts`): Frontend(`localhost:3100`)와 Backend API(`localhost:3100/api/health`) 접근 가능 여부를 최대 120초 대기
- **global-teardown** (`e2e/global-teardown.ts`): `E2E` 접두사를 가진 테스트 커넥션을 자동 정리

## Configuration

| 항목 | 값 |
|------|-----|
| Base URL | `http://localhost:3100` |
| Test timeout | 60초 |
| Expect timeout | 15초 |
| Action timeout | 10초 |
| Navigation timeout | 30초 |
| Workers | 1 (순차 실행) |
| Screenshots | 항상 캡처 |
| Traces | 실패 시 보존 |
| Output | `frontend/e2e/test-results/` |
| Screenshots | `frontend/e2e/screenshots/` |

## Troubleshooting

- **컨테이너가 기동되지 않는 경우**: `podman compose -f compose.yaml logs -f` 로 로그 확인
- **Backend health check 실패**: Aerospike 노드가 모두 healthy인지 확인 — `podman compose -f compose.yaml ps`
- **Frontend 접근 불가**: Backend가 먼저 healthy 상태여야 함 — `curl http://localhost:8000/api/health`
- **테스트 실패 후 디버깅**: `cd frontend && npx playwright test --debug e2e/specs/{spec}` 로 Playwright Inspector 사용
- **포트 충돌**: `.env.example` 참고하여 `BACKEND_PORT`, `FRONTEND_PORT` 변경
