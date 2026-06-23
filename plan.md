# 작업 계획: 게시판 시스템 (plan.md)

> 본 계획은 AGENTS.md §3.1 Primary Planner 초안이다. 설계 상세는 [docs/superpowers/specs/2026-06-23-board-system-design.md](docs/superpowers/specs/2026-06-23-board-system-design.md) 참조. 인간 승인 전까지 구현 단계로 넘어가지 않는다(§3.1-4).

## 목표 (Goal)

일반 사용자/관리자가 분리된 게시판 시스템. 관리자는 공지(NOTICE)/일반(GENERAL)/이미지(IMAGE) 게시판을 생성·관리하고, 게시판 종류에 따라 권한과 동작이 분기된다.

## 스택 선언 (§0.1 참조)

Python 3.12 + FastAPI + SQLAlchemy/Alembic + PostgreSQL 16 + MinIO(S3) + Pillow / React 18 + Vite + TS. 인증 자체 구현(JWT, role).

## 수락 기준 (Acceptance Criteria) — 측정 가능 형태 (P-02)

각 AC는 검증 가능한 관찰 결과(상태 코드/응답/테스트)로 기술한다.

- [ ] AC1. 인증: `POST /auth/signup`→201, `POST /auth/login`(정상)→200+JWT, (오답)→401. role=USER가 ADMIN 전용 엔드포인트 호출 시 403. (대응 테스트 존재)
- [ ] AC2. `POST /admin/boards`로 ADMIN이 type∈{NOTICE,GENERAL,IMAGE} + read_visibility∈{PUBLIC,AUTHENTICATED} 게시판 생성→201. 비ADMIN→403.
- [ ] AC3. NOTICE 게시판: 비ADMIN `POST /boards/{id}/posts`→403, ADMIN→201. read_visibility=PUBLIC이면 비인증 GET→200.
- [ ] AC4. GENERAL: 인증 사용자 글작성+첨부 업로드→201. 다운로드는 read_visibility 검사 후 presigned GET URL(200) 반환, 비인가 읽기→401/403.
- [ ] AC5. IMAGE: 이미지 0개로 생성 시 422. 정상 생성 시 각 첨부에 `thumbnail_key`가 채워짐(서버 Pillow 생성). 마지막 이미지 삭제 시 422(E-01 불변식).
- [ ] AC6. 이미지 게시물 GET 응답이 썸네일 URL 배열을 포함(그리드용), `GET /attachments/{id}/original-url`이 원본 presigned GET 반환(라이트박스용).
- [ ] AC7. 게시물/댓글 PUT·DELETE: 작성자 본인/ADMIN→2xx, 타인→403. 동시 수정은 낙관적 잠금으로 충돌 시 409(E-05).
- [ ] AC8. §3.4 아키텍처 산출물 + ADR(0001~0006)이 docs/에 존재(점검 스크립트 통과).
- [ ] AC9. 목록 API는 페이지네이션 계약(커서 기반, limit 상한, created_at DESC 안정 정렬)을 따른다(E-06).

## 아키텍처 방향 (Architecture Direction)

- backend 3계층(api→service→repository/model), 인가는 service 계층 의존성으로 강제.
- **읽기/쓰기 권한 분리(E-04)**: 쓰기=`Board.type`, 읽기=`Board.read_visibility`(PUBLIC/AUTHENTICATED). ADMIN이 게시판 생성 시 지정.
- **업로드 백엔드 경유(A-02)**: 파일 업로드는 service 경유(검증·썸네일·정합성). 다운로드만 presigned GET(TTL 5분, S-06).
- **DB-S3 정합성(A-03, ADR-0005)**: PENDING→COMMITTED + 조정/orphan 정리 잡(E-02).
- **삭제 시맨틱(ADR-0006)**: User 소프트삭제, Post/Comment/Board 하드삭제(애플리케이션 캐스케이드 + S3 정리). FK는 RESTRICT 기본(A-04).
- 파일은 MinIO, 메타데이터는 DB. 썸네일은 업로드 시 Pillow 생성.

### 공유 계약 소유권 (§5.1, A-01)

| 항목 | 값 |
| --- | --- |
| contract_id | `boards-api-openapi` |
| source_of_truth_path | `backend/openapi.json` (FastAPI 생성) |
| owner_role | `backend` |
| owner_human_approver | (인간 승인자 지정 필요 — 승인 시 기입) |
| producer_paths | `backend/app/api/**`, `backend/openapi.json` |
| consumer_paths | `frontend/src/api/generated/**` |
| regen_command | backend: `python -m app.export_openapi > openapi.json`; frontend: `npm run gen:api` |
| drift_check_command | `git diff --exit-code backend/openapi.json` + 프론트 생성물 재생성 후 diff 0 |

> 생성물(`frontend/src/api/generated/**`)은 수동 수정 금지(§5.1 드리프트 제어).

## Phase 분해 (§6.1)

각 phase는 §6.2 닫힌 게이트(구현→테스트→codex 리뷰→수정→회고→dev commit&push)를 따른다.

### Phase 0 — 스캐폴딩 & 인프라 골격
- 목표: backend/frontend 스켈레톤, docker-compose(postgres+minio), CI 골격, 스코프 경계 확립.
- 산출물: 디렉토리 구조, `.env.example`, lint/test/coverage 명령 동작.
- 수락 기준: `<PROJECT_DECLARED_LINT_CMD>`/`<PROJECT_DECLARED_TEST_CMD>`가 빈 통과, docker-compose up 성공.
- 의존성: 없음. (선행: git 저장소·dev 브랜치 — 인간 승인 필요)
- ⚠️ **CI/CD 설정은 AGENTS.md §4 보호 대상(P-03)** — Phase 0의 CI 골격 작성·변경은 인간 승인을 거친다.

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

1. AGENTS.md §3.4 산출물 존재 점검(스크립트). ✅ 통과
2. AC1~AC8 자체 점검 추적표(§3.2-1).
3. codex 플러그인 교차 검증(§3.1-2) — 독립 세션. ✅ 완료(아래 §교차 검증 기록)
4. 인간 개발자 최종 승인(§3.1-4). ⏳ 대기

## 교차 검증 기록 (Cross-Review Record, §3.1-2)

| 항목 | 값 |
| --- | --- |
| reviewer_id | codex (codex:codex-rescue 포워더 경유) |
| model_id | gpt-5.x-codex (Primary Planner=Claude와 독립 모델) |
| session_id | codex thread 019ef35f-23d2-7d00-92a3-21d8bc406c2e |
| 검토 대상 커밋 | dd9674f88c5a30fb7a0de0adf39ab71643f548a1 |
| draft 해시(plan.md, SHA-256) | 35dcff8f97b76eb7bc81fb4930b2b295740e9572e66f02e9e540bcd45727f872 |
| 검토 시각(UTC) | 2026-06-23T07:30Z |
| 결과 요약 | 총 23건 (blocking 5, high 10, medium 8) |

> 신선도 바인딩(§3.1-2): plan.md 또는 검토 대상 문서가 변경되면 위 해시가 달라지며 본 리뷰는 무효화된다. 아래 조정으로 문서가 갱신되면 **재검증이 필요**하다.

## 피드백 통합 / 이의 처리 (Synthesis & Adjudication, §3.1-3)

각 지적을 Accepted / Rejected / Escalated로 분류한다. blocking·security 지적은 인간 승인자 판정 전까지 구현으로 넘어갈 수 없다(§3.1-3, §4).

### Blocking (5)

| ID | 분류 | 판정 | 조치 |
| --- | --- | --- | --- |
| P-01 | Scope | **Accepted** | 본 절차(교차검증→조정→인간승인)로 해소 중. 인간 승인 시 종료. |
| A-01 | Architecture | **Accepted** | 구현 전 §5.1 계약 소유권 표(contract_id, owner_human_approver, producer/consumer_paths, regen_command, drift_check_command)를 plan.md/docs에 추가. |
| A-02 | Architecture | **Accepted** | 업로드 흐름 단일화 필요. **인간 결정 항목**: 백엔드 경유 업로드 vs 클라이언트 presigned PUT. (썸네일 서버 생성·파일 검증을 고려하면 백엔드 경유 권장) 결정 후 system/sequence/security/phase 일괄 정합. |
| A-03 | Architecture | **Accepted** | DB-S3 일관성 프로토콜 구체화: pending 상태→S3 스테이징→커밋→실패 보상 잡. data.md + ADR-0005 신설. |
| E-01 | EdgeCase | **Accepted** | IMAGE 불변식을 생성뿐 아니라 수정·첨부삭제·게시판타입변경에도 강제. 규칙을 security/data + AC5에 반영. |

### High (10) — 전부 Accepted

S-01(JWT 저장 전략 단일화), S-02(토큰 TTL·로그아웃·폐기 정의), S-03(매직바이트·이미지 디코딩·압축폭탄 방어), S-04(XSS 출력 인코딩·CSP), S-06(presigned TTL·메서드·키 바인딩), A-04(FK별 삭제 동작 — 사용자/게시판 RESTRICT 또는 소프트삭제), E-02(orphan 정리 잡 설계), E-03(게시판 삭제 시 S3 정리), E-04(GENERAL/IMAGE 읽기 권한 문서 간 충돌 해소 — **인간 결정 항목**: 비인증 읽기 허용 여부), Y-02(관리자 프로비저닝/복구 최소 정책), P-02(AC를 측정 가능한 API/UI/테스트 결과로 재작성), P-03(Phase 0 CI 설정은 §4 보호 대상 — 인간 승인 게이트 명시).

### Medium (8) — 판정

| ID | 판정 | 비고 |
| --- | --- | --- |
| A-05 | **Accepted** | thumbnail_key 부분 유니크 제약 추가(또는 비유니크 근거 문서화). |
| E-05 | **Accepted** | 동시 편집: 낙관적 잠금(updated_at/ETag) 결정 + AC. |
| E-06 | **Accepted** | 페이지네이션 계약(커서/오프셋, limit 상한, 정렬 안정성) + 경계 테스트. |
| P-04 | **Accepted** | phase별 expand/contract 마이그레이션 안전 규칙. |
| Y-01 | **Accepted** | multipart는 defer(YAGNI). 대용량 요건 생기면 ADR로 재도입. |
| Y-03 | **Accepted** | 삭제 시맨틱(소프트/하드) 결정 ADR-0006 신설. |
| A-06 | **Rejected** | 근거: 실제 문서는 AGENTS.md §3.4가 요구하는 `docs/architecture/` 경로에 정확히 위치함. codex 리뷰 *프롬프트*가 잘못된 경로(`docs/system.md`)를 나열한 것이며 산출물 결함이 아님. 경로 정합성은 유지됨. |

### 조정 결과 요약

- Accepted: 22건, Rejected: 1건(A-06), Escalated(인간 결정): A-02·E-04.

### 인간 결정 반영 (v2)

- **A-02 → 백엔드 경유 업로드**로 결정. system/sequence/security/ADR-0003/plan 정합 완료.
- **E-04 → Board.read_visibility(PUBLIC/AUTHENTICATED)** 신설. ADMIN이 게시판 생성 시 지정. db-schema/security/ADR-0002/AC 반영 완료.
- **배포 → docker-compose**(dev/staging/prod 동일 compose + env 오버라이드). deployment.md 반영 완료.

### v2 반영 현황 (Accepted 22건)

- Blocking: A-01(계약 소유권 표 추가)·A-02(업로드 흐름 단일화)·A-03(ADR-0005 정합성)·E-01(IMAGE 불변식 전구간) **모두 반영**. P-01은 인간 승인으로 종료.
- High/Medium: S-01~S-06·A-04·A-05·E-02·E-03·E-05·E-06·Y-01(multipart defer)·Y-02·Y-03·P-02·P-03·P-04 **모두 반영**(security.md/db-schema.md/data.md/deployment.md/ADR-0005,0006/plan AC).
- **신선도(§3.1-2)**: 문서가 v2로 갱신되어 기존 codex 리뷰는 무효화됨 → **재검증 권장 후 인간 최종 승인**. blocking 해소를 인간 승인자가 확인하기 전까지 구현 착수 불가.
