# 게시판 시스템 설계 문서 (Design Spec)

> 작성일: 2026-06-23 · 상태: 인간 승인 대기(Plan Mode) · 본 문서는 AGENTS.md §3.1의 Primary Planner 초안에 해당한다.

## 1. 목표 (Goal)

일반 사용자와 관리자가 분리된 게시판 시스템을 개발한다. 관리자는 여러 게시판을 만들 수 있으며, 게시판은 종류에 따라 권한과 동작이 다르다.

- **공지사항(NOTICE)**: 관리자만 작성, 일반 사용자는 읽기만 가능
- **일반(GENERAL)**: 모든 인증 사용자가 읽기/쓰기 가능, 첨부파일 업로드/다운로드
- **이미지(IMAGE)**: 게시물당 1개 이상 이미지 첨부 필수, 썸네일 카드 그리드 → 라이트박스 원본 보기

## 2. 기술 스택 선언 (Stack Declaration)

AGENTS.md §0/§2는 스택 비종속이므로 본 프로젝트가 아래를 선언한다.

| 영역 | 선택 | 근거 |
| --- | --- | --- |
| 백엔드 | Python 3.12 + FastAPI | 타입 힌트 기반 OpenAPI 자동 생성 → 프론트 계약 소비에 유리 |
| ORM/마이그레이션 | SQLAlchemy 2.x + Alembic | 표준, erDiagram과 1:1 매핑 |
| DB | PostgreSQL 16 | 관계형 메타데이터 |
| 오브젝트 스토리지 | MinIO (S3 호환) | 이미지/첨부 원본 + 썸네일 |
| 이미지 처리 | Pillow | 업로드 시 서버 썸네일 생성 |
| 프론트 | React 18 + Vite + TypeScript | SPA |
| 인증 | 자체 구현: email+password, JWT(access), bcrypt 해시, role(USER/ADMIN) | 요구사항 |

### 빌드/테스트/린트 명령 바인딩 (§2 플레이스홀더)

| 플레이스홀더 | backend | frontend |
| --- | --- | --- |
| `<PROJECT_DECLARED_RUN_CMD>` | `uvicorn app.main:app --reload` | `npm run dev` |
| `<PROJECT_DECLARED_TEST_CMD>` | `pytest` | `npm test` |
| `<PROJECT_DECLARED_LINT_CMD>` | `ruff check . && mypy app` | `npm run lint` |
| `<PROJECT_DECLARED_TEST_COVERAGE_CMD>` | `pytest --cov=app --cov-fail-under=80` | `npm run test:coverage` |

## 3. 아키텍처 개요 (System Architecture)

3-tier. 상세 mermaid는 `docs/architecture/system.md` 참조.

```
React(Vite/TS) ──HTTP/JSON(JWT)──> FastAPI ──> PostgreSQL (메타데이터)
                                       └──────> MinIO/S3 (원본 + 썸네일)
```

- **스코프 경계(§5)**: `backend/`, `frontend/` 두 영역.
- **공유 계약(§5.1)**: OpenAPI 스펙. SoT = backend(`backend/openapi.json` 생성물). frontend는 생성된 TS 클라이언트만 소비, 수동 수정 금지.

## 4. 도메인 모델 (Data Model)

상세 erDiagram은 `docs/architecture/db-schema.md` 참조.

- **User**: id, email(unique), password_hash, role(enum: USER/ADMIN), created_at
- **Board**: id, name, slug(unique), type(enum: NOTICE/GENERAL/IMAGE), description, created_at
- **Post**: id, board_id(FK), author_id(FK→User), title, content, created_at, updated_at
- **Attachment**: id, post_id(FK), storage_key, original_name, content_type, size, is_image(bool), thumbnail_key(nullable), created_at
- **Comment**: id, post_id(FK), author_id(FK→User), content, created_at

### 권한 규칙 (Board.type 기반 분기)

| type | 읽기 | 쓰기 | 첨부 규칙 |
| --- | --- | --- | --- |
| NOTICE | 전체(비로그인 포함 가능) | ADMIN만 | 선택적 |
| GENERAL | 인증 사용자 | 인증 사용자 | 선택적, 다운로드 가능 |
| IMAGE | 인증 사용자 | 인증 사용자 | **1개 이상 이미지 필수**, 썸네일 자동 생성 |

- 게시판 생성/삭제는 ADMIN만.
- 게시물/댓글 수정·삭제는 작성자 본인 또는 ADMIN.

## 5. 핵심 플로우 (Sequences)

각 시퀀스는 `docs/architecture/sequences/*.md`에 mermaid `sequenceDiagram`으로 작성.

1. **인증**: 회원가입 → bcrypt 해시 저장 / 로그인 → JWT 발급 → 보호 엔드포인트 role 검사
2. **게시물 작성 + 첨부**: presigned PUT 또는 멀티파트 업로드 → Attachment 레코드 생성 → IMAGE 게시판이면 Pillow 썸네일 생성·저장
3. **이미지 게시판 조회**: 게시물 선택 → 썸네일 카드 그리드 → 카드 클릭 → 라이트박스(원본 presigned GET)
4. **첨부 다운로드**: 첨부 목록 → presigned GET URL

## 6. 보안 아키텍처 (요약)

상세는 `docs/architecture/security.md`.

- 인증: JWT access token(만료 짧게), bcrypt(cost≥12).
- 인가: FastAPI 의존성으로 role/소유권 검사. NOTICE 쓰기·게시판 생성은 ADMIN 게이트.
- 신뢰 경계: 클라이언트 ↔ API(검증 필수), API ↔ MinIO(presigned, 최소 권한). 업로드 파일 타입/크기 검증, 이미지 MIME 화이트리스트.
- 시크릿: JWT secret, DB/MinIO 자격증명은 `.env`(§4 보호 대상, 커밋 금지).

## 7. 배포 아키텍처 (요약)

상세는 `docs/architecture/deployment.md`.

- 개발: docker-compose(postgres, minio, backend, frontend dev server).
- 환경: dev/staging/prod. 마이그레이션은 Alembic.
- CI: lint + test + coverage 게이트(§3.3).

## 8. Phase 분해 (§6.1) — plan.md에 상세화

- **Phase 0**: 저장소 스캐폴딩, docker-compose, CI 골격, 스코프 경계 확립
- **Phase 1**: 인증/사용자(회원가입·로그인·JWT·role), User 스키마/마이그레이션
- **Phase 2**: 게시판 CRUD(ADMIN 생성) + Board.type 권한 모델
- **Phase 3**: 게시물 CRUD + 댓글
- **Phase 4**: 첨부파일(일반 게시판 업로드/presigned 다운로드)
- **Phase 5**: 이미지 게시판(다중 이미지, Pillow 썸네일, 카드 그리드 + 라이트박스)
- **Phase 6**: 프론트 통합 마감, E2E, 접근성/성능 점검

각 phase는 §6.2 닫힌 게이트(구현→테스트→codex 리뷰→수정→회고→dev commit&push)를 따른다.

## 9. AGENTS.md 조정 사항 (별도 보고)

AGENTS.md는 게시판 프로젝트에 맞게 §0 선언 슬롯을 채우고, 게시판 특화 항목(스코프, 계약 소유권, 명령 바인딩)을 구체화한다. 거버넌스 규칙 본문(§3 DoD, §4 이스케이프, §6 게이트 로직)의 강제 가능성은 보존한다. 변경 상세는 작업 시 인간에게 보고 후 승인받는다.

## 10. 범위 밖 (Out of Scope)

- 실시간 알림, 검색 엔진, 좋아요/추천, 페이지네이션 고도화(기본 페이지네이션은 포함).
- 소셜 로그인, 이메일 인증 메일 발송(향후 phase).
- 실제 prod 인프라 프로비저닝(규칙·diagram만).

## 11. 수락 기준 (Acceptance Criteria)

- [ ] AC1. USER/ADMIN 역할 분리 및 JWT 인증이 동작한다.
- [ ] AC2. ADMIN이 NOTICE/GENERAL/IMAGE 게시판을 생성할 수 있다.
- [ ] AC3. NOTICE는 ADMIN만 작성, USER는 읽기만 가능하다.
- [ ] AC4. GENERAL은 인증 사용자가 글 작성 + 첨부 업로드, 타인은 읽기 + 첨부 다운로드 가능하다.
- [ ] AC5. IMAGE 게시판은 1개 이상 이미지 첨부를 강제하고, 서버가 썸네일을 생성한다.
- [ ] AC6. 이미지 게시물은 썸네일 카드 그리드로 보이고, 카드 선택 시 원본을 크게 본다.
- [ ] AC7. 게시물/댓글의 수정·삭제는 작성자 또는 ADMIN만 가능하다.
- [ ] AC8. §3.4 아키텍처 산출물(system/sequences/data/db-schema/security/deployment + ADR)이 docs/에 작성된다.
