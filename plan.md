# 작업 계획: 게시판 시스템 (plan.md)

> 본 계획은 AGENTS.md §3.1 Primary Planner 초안이다. 설계 상세는 [docs/superpowers/specs/2026-06-23-board-system-design.md](docs/superpowers/specs/2026-06-23-board-system-design.md) 참조. 인간 승인 전까지 구현 단계로 넘어가지 않는다(§3.1-4).

## 목표 (Goal)

일반 사용자/관리자가 분리된 게시판 시스템. 관리자는 공지(NOTICE)/일반(GENERAL)/이미지(IMAGE) 게시판을 생성·관리하고, 게시판 종류에 따라 권한과 동작이 분기된다.

## 스택 선언 (§0.1 참조)

Python 3.12 + FastAPI + SQLAlchemy/Alembic + PostgreSQL 16 + MinIO(S3) + Pillow / React 18 + Vite + TS. 인증 자체 구현(JWT, role).

## 수락 기준 (Acceptance Criteria)

- [ ] AC1. USER/ADMIN 역할 분리 + JWT 인증 동작.
- [ ] AC2. ADMIN이 NOTICE/GENERAL/IMAGE 게시판 생성 가능.
- [ ] AC3. NOTICE: ADMIN만 작성, USER 읽기 전용.
- [ ] AC4. GENERAL: 인증 사용자 작성+첨부 업로드, 타인 읽기+다운로드.
- [ ] AC5. IMAGE: 1개 이상 이미지 첨부 강제, 서버 썸네일 생성.
- [ ] AC6. 이미지 게시물 썸네일 카드 그리드 → 카드 선택 시 원본 라이트박스.
- [ ] AC7. 게시물/댓글 수정·삭제는 작성자 또는 ADMIN만.
- [ ] AC8. §3.4 아키텍처 산출물 + ADR이 docs/에 존재.

## 아키텍처 방향 (Architecture Direction)

- backend 3계층(api→service→repository/model), 인가는 service 계층 의존성으로 강제.
- 공유 계약 = OpenAPI, SoT=backend(`backend/openapi.json`), frontend는 생성 클라이언트 소비(§5.1).
- 파일은 MinIO에 저장, 메타데이터는 DB. 썸네일은 업로드 시 Pillow로 생성.

## Phase 분해 (§6.1)

각 phase는 §6.2 닫힌 게이트(구현→테스트→codex 리뷰→수정→회고→dev commit&push)를 따른다.

### Phase 0 — 스캐폴딩 & 인프라 골격
- 목표: backend/frontend 스켈레톤, docker-compose(postgres+minio), CI 골격, 스코프 경계 확립.
- 산출물: 디렉토리 구조, `.env.example`, lint/test/coverage 명령 동작.
- 수락 기준: `<PROJECT_DECLARED_LINT_CMD>`/`<PROJECT_DECLARED_TEST_CMD>`가 빈 통과, docker-compose up 성공.
- 의존성: 없음. (선행: git 저장소·dev 브랜치 — 인간 승인 필요)

### Phase 1 — 인증 & 사용자
- 목표: 회원가입/로그인/JWT/role 미들웨어, User 모델·마이그레이션.
- 수락 기준: AC1. 보호 엔드포인트 role 검사 테스트.
- 의존성: Phase 0.

### Phase 2 — 게시판 CRUD & 권한 모델
- 목표: Board(type) CRUD(생성은 ADMIN), type별 읽기/쓰기 인가 규칙.
- 수락 기준: AC2, AC3(쓰기 측면).
- 의존성: Phase 1.

### Phase 3 — 게시물 & 댓글
- 목표: Post CRUD + Comment CRUD, 소유권 기반 수정·삭제.
- 수락 기준: AC3(읽기), AC7.
- 의존성: Phase 2.

### Phase 4 — 첨부파일 (일반 게시판)
- 목표: 업로드(MinIO presigned/멀티파트), Attachment 메타, presigned 다운로드, 타입·크기 검증.
- 수락 기준: AC4.
- 의존성: Phase 3.

### Phase 5 — 이미지 게시판
- 목표: 다중 이미지 첨부 강제, Pillow 썸네일 생성, 썸네일 카드 그리드 + 라이트박스(프론트).
- 수락 기준: AC5, AC6.
- 의존성: Phase 4.

### Phase 6 — 통합 마감
- 목표: 프론트 전체 통합, E2E, 접근성/성능 점검, 문서 정리.
- 수락 기준: 전체 AC 회귀 통과.
- 의존성: Phase 5.

## 범위 밖 (Out of Scope)

실시간 알림, 검색 엔진, 좋아요/추천, 소셜 로그인, 이메일 발송, prod 인프라 프로비저닝.

## 검증 절차 (Verification)

1. AGENTS.md §3.4 산출물 존재 점검(스크립트).
2. AC1~AC8 자체 점검 추적표(§3.2-1).
3. codex 플러그인 교차 검증(§3.1-2) — 독립 세션.
4. 인간 개발자 최종 승인(§3.1-4).
