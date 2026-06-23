# 회고: Phase 2 (게시판 CRUD + 권한 모델)

## 한 일과 결과 (완료된 수락 기준)

- **AC2**: ADMIN이 type∈{NOTICE,GENERAL,IMAGE} + read_visibility∈{PUBLIC,AUTHENTICATED} 게시판 생성→201,
  비ADMIN→403, 비인증→401, 잘못된 enum→422, 중복 slug→409.
- **AC3(쓰기 측면 + read_visibility)**: NOTICE 쓰기 게이트(ADMIN only)/GENERAL·IMAGE(인증 사용자)를
  `permissions.ensure_can_write_board`로 중앙화(Phase 3에서 재사용). 단일 게시판 읽기는 read_visibility 적용
  (PUBLIC 비인증 200 / AUTHENTICATED 비인증 401 / 토큰 200).
- 게시판 삭제 ADMIN-only(204). 목록은 가시성 필터(익명=PUBLIC만).

### 검증 증거 (콘솔)

```text
ruff → All checks passed! · mypy → no issues (25 files)
pytest 43 passed · coverage 93.90% (>=80)
codex 재리뷰: FINDING-001 RESOLVED · UNRESOLVED BLOCKING FINDINGS: NO
```

## 잘된 점

- 인가 규칙을 `service/permissions.py`에 단일 소스로 모아 Phase 3/4가 재사용하도록 설계.
- codex가 **blocking**(익명 목록의 AUTHENTICATED 메타 노출)을 잡아 즉시 수정 → 가시성 누출 차단.

## 어려웠던 점

- "목록은 메타만이라 공개"라는 초기 가정이 read_visibility 계약과 충돌. 계약을 코드보다 우선해 수정.

## 다음 phase 개선점 (Phase 3 입력)

- Post/Comment는 `ensure_can_read_board`(읽기)·`ensure_can_write_board`(쓰기)·`ensure_owner_or_admin`(수정/삭제)를 재사용.
- E-03 게시판 캐스케이드 삭제: FK가 RESTRICT라 하위 Post/Comment 존재 시 게시판 삭제가 실패함 →
  Phase 3(하위 정리) / Phase 4(S3 정리)에서 애플리케이션 캐스케이드 구현 필요.

## codex 리뷰 지적과 그 처리 결과

- 1건 blocking(FINDING-001) **Fixed** + low(FINDING-008) **Fixed**, 재리뷰로 미해결 blocking 0 확인.
- 상세: [phase-2-codex-review.md](../reviews/phase-2-codex-review.md), [phase-2-codex-resolution.md](../reviews/phase-2-codex-resolution.md).

## Human Check Items

| ID | 분류(Security/Architecture/Scope/Risk/Other) | 확인 필요 사항 | 필요한 인간 판단 | 차단 여부 |
| --- | --- | --- | --- | --- |
| HCI-1 | Architecture | E-03 게시판 캐스케이드 삭제 미구현 — 현재 하위 콘텐츠가 있으면 게시판 삭제가 RESTRICT로 실패. Phase 3/4에서 애플리케이션 캐스케이드(+S3 정리) 예정. | 캐스케이드 삭제를 Phase 4 완료 시까지 미구현으로 두는 것 승인. | 비차단(계획된 후속) |
| HCI-2 | Security | 게시판 type 변경은 MVP 범위 밖(불변)으로 둠(security.md E-01). 생성 후 type/read_visibility 수정 엔드포인트 미제공. | 게시판 속성 수정 기능의 필요 여부/시점 확인. | 비차단 |
