# 회고: Phase 0(스캐폴딩·인프라) + Phase 1(인증·사용자)

> 두 phase를 한 게이트로 묶어 진행(연속 진행, 인간 승인). 산출물은 dev 브랜치에 통합.

## 한 일과 결과 (완료된 수락 기준)

- **Phase 0**: backend(FastAPI 3계층 api→service→repository/model) + frontend(React/Vite/TS) 스켈레톤,
  docker-compose(postgres+minio+backend+frontend), `.env.example`(비시크릿), Alembic 초기 마이그레이션(0001),
  OpenAPI 내보내기(`python -m app.export_openapi`), lint/test/coverage 명령 동작.
- **Phase 1 (AC1)**: 회원가입(201)·로그인(200+JWT)·오답(401)·role 게이트(USER→ADMIN 엔드포인트 403),
  bcrypt(cost≥12 강제) 해시, JWT HS256(exp/iat/sub 필수), 소프트삭제 사용자 로그인 배제,
  초기 ADMIN 시드(Y-02, 멱등), ADMIN 승격 엔드포인트.
- **AC8(부분)**: §3.4 아키텍처 산출물·ADR은 계획 단계에서 이미 존재. 점검 스크립트 통과.

### 검증 증거 (콘솔)

```text
backend:  ruff → All checks passed! · mypy → no issues (22 files) · pytest 25 passed, coverage 93.32% (≥80)
          alembic upgrade head / downgrade base → OK (P-04 downgrade 검증)
frontend: vitest 3 passed · eslint clean
codex 재리뷰: high 5건 전건 RESOLVED · BLOCKING FINDINGS REMAINING: NO
```

## 잘된 점

- TDD-가까운 흐름으로 AC1을 측정 가능한 상태코드 테스트로 1:1 매핑.
- codex 교차검증에서 실제 보안 결함(JWT exp 미강제, 타이밍 사이드채널, compose 시크릿 폴백)을 잡아 즉시 수정.
- SQLite(단위 테스트)/Postgres(운영) 양립을 `BigInteger.with_variant`·부분 유니크 인덱스로 해결.

## 어려웠던 점

- `passlib`가 `bcrypt` 5.x와 비호환 → `bcrypt` 직접 사용으로 전환(72바이트 한계는 SHA-256 프리해시로 처리).
- bcrypt cost≥12 강제와 테스트 속도 상충 → 테스트에서 실제 코드경로를 유지하며 salt만 저비용으로 패치.

## 다음 phase 개선점

- Phase 2부터 read 엔드포인트가 생기므로 `get_optional_user`(현재 부분 커버)에 read_visibility 테스트 추가.
- 프론트는 Phase 2+에서 `npm run gen:api`로 OpenAPI 타입 생성 후 소비(수기 타입 금지, §5.1).

## codex 리뷰 지적과 처리 결과

- 총 12건(blocking 0/high 3/medium 8/low 1). high 전건 + 다수 medium **Fixed**, 재리뷰로 미해결 blocking 0 확인.
- 상세: [phase-0-codex-review.md](../reviews/phase-0-codex-review.md), [phase-0-codex-resolution.md](../reviews/phase-0-codex-resolution.md).

## Human Check Items

| ID | 분류(Security/Architecture/Scope/Risk/Other) | 확인 필요 사항 | 필요한 인간 판단 | 차단 여부 |
| --- | --- | --- | --- | --- |
| HCI-1 | Scope | Phase 0 CI/CD 워크플로(.github/workflows) 작성을 인간 결정에 따라 **생략**함(§4/P-03 보호 대상). | CI 골격을 언제·누가 추가할지, 커버리지 게이트를 CI에 강제할지 결정. | 비차단(합의된 생략) |
| HCI-2 | Security | SEC-003: signup 중복 이메일 409가 계정 존재를 노출. 완전 비열거화는 이메일 인증(범위 밖) 전제로 **MVP 보류**. | 가입 경로 열거 방어를 MVP에 포함할지, 후속 phase로 둘지 승인. | 비차단(deferred) |
| HCI-3 | Security | SEC-005: 로그인 rate-limit·인증 감사 로그 미구현(security.md S-05 설계만 존재). | 횡단 미들웨어를 어느 phase에서 구현할지, MVP 필수 여부 결정. | 비차단(deferred) |
| HCI-4 | Architecture | OTH-002: 프론트 `apiFetch`는 전송 래퍼로 유지하고 계약 타입은 생성물(`generated/`)로 분리하기로 정함. | 이 분리 방침 승인(생성 타입과 전송 래퍼 공존). | 비차단 |
| HCI-5 | Risk | dev/단위테스트는 SQLite, 운영은 Postgres. 부분 유니크 인덱스·enum 등 Postgres 전용 제약은 통합 테스트(후속)로 검증 예정. | Postgres 통합 테스트 도입 시점 확인. | 비차단 |
