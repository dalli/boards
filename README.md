# Boards — 게시판 시스템

분리된 일반/관리자 게시판 시스템. 설계·거버넌스는 [AGENTS.md](AGENTS.md), [plan.md](plan.md),
[docs/](docs/) 참조.

## 스택

- **backend**: Python 3.12 · FastAPI · SQLAlchemy 2.x · Alembic · PostgreSQL 16 · MinIO(S3) · Pillow
- **frontend**: React 18 · Vite · TypeScript
- 인증: 자체 구현(email+password, bcrypt, JWT/HS256, role USER/ADMIN)

## 구조 (스코프 경계 §5)

```
backend/    FastAPI 3계층 (api → service → repository/model)
frontend/   React SPA (생성된 OpenAPI 클라이언트만 소비)
docs/       아키텍처 산출물 + ADR + 시퀀스 + 리뷰/회고
```

## 로컬 개발

### docker-compose (전체 스택)

```bash
cp .env.example .env.dev        # 비시크릿 설정만; 실제 시크릿 커밋 금지(§4)
docker compose --env-file .env.dev up --build
```

postgres(5432), minio(9000/9001), backend(8000), frontend(5173) 기동.

### backend 단독

```bash
cd backend
python3.12 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/alembic upgrade head                       # 마이그레이션
.venv/bin/uvicorn app.main:app --reload              # 실행
```

### 명령 바인딩 (§2)

| 목적 | backend | frontend |
| --- | --- | --- |
| 실행 | `uvicorn app.main:app --reload` | `npm run dev` |
| 테스트 | `pytest` | `npm test` |
| 린트 | `ruff check . && mypy app` | `npm run lint` |
| 커버리지 게이트 | `pytest --cov=app --cov-fail-under=80` | `npm run test:coverage` |

## API 계약 (§5.1)

OpenAPI가 단일 진실 공급원(SoT). backend가 생성:

```bash
cd backend && python -m app.export_openapi > openapi.json   # 생성
cd frontend && npm run gen:api                               # TS 클라이언트 재생성(수동 수정 금지)
```

## CI

CI/CD 파이프라인 설정은 AGENTS.md §4 보호 대상이라 인간 승인 후 추가됩니다(P-03). 현재 미포함.
