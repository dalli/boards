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

- Accepted: 22건, Rejected: 1건(A-06), Escalated(인간 결정): A-02·E-04(문서 내 명시).
- **다음 행동**: 위 Accepted 항목을 반영해 docs/plan을 v2로 갱신 → 문서 해시 변경으로 본 리뷰 무효화 → **재검증 또는 인간 승인자 판정** 필요. blocking 미해소 상태에서는 구현 착수 불가.
