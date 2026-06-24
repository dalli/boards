# 회고: Phase 3 (게시물 & 댓글)

## 한 일과 결과 (완료된 수락 기준)

- **AC3(읽기)**: 게시물/댓글 읽기가 Board.read_visibility 적용(PUBLIC 비인증 200 / AUTHENTICATED 비인증 401).
  COMMITTED 게시물만 노출.
- **AC7**: 게시물·댓글 PUT/DELETE를 작성자 본인 또는 ADMIN만(2xx), 타인 403. 게시물 동시 수정은
  **원자적 낙관적 잠금**(UPDATE ... WHERE version=expected)으로 충돌 시 409.
- **AC9(E-06)**: 키셋 커서 페이지네이션(created_at DESC, id DESC), limit 기본20/상한100,
  불투명 base64 커서, 경계 테스트(빈/정확히 limit/limit+1/연속 페이지 무중복·무누락/상한 클램프/잘못된 커서 422).

### 검증 증거 (콘솔)

```text
ruff → All checks passed! · mypy → no issues (30 files)
pytest 77 passed · coverage 95.11% (>=80)
codex 최종 재검증: UNRESOLVED BLOCKING: NO · UNRESOLVED HIGH: NO
```

## 잘된 점

- Phase 2의 `service/permissions`를 재사용해 읽기/쓰기/소유권 인가를 일관 적용.
- codex가 낙관적 잠금의 비원자성(F-001)·댓글 PUT 누락(F-003)·삭제 게이트 비대칭(NV-002)을 단계적으로 잡아냄 →
  3라운드 리뷰로 blocking/high 0 수렴.

## 어려웠던 점

- 낙관적 잠금을 read-then-write로 처음 구현 → DB 레벨 조건부 UPDATE로 교체해 원자성 확보.
- 비ADMIN이 NOTICE 글을 만들 수 없어 NOTICE 수정/삭제 게이트의 negative 테스트는 서비스 계층에 직접 시드해 검증.

## 다음 phase 개선점 (Phase 4 입력)

- 첨부가 생기면 게시물 생성이 PENDING→COMMITTED 생명주기로 전환(A-03). 현재는 첨부 없으니 즉시 COMMITTED.
- Post 삭제 시 첨부(S3) 선삭제 순서(NV2-002)를 Phase 4에서 구현 — 현재 FK RESTRICT라 첨부 있는 글은 삭제 실패.

## codex 리뷰 지적과 그 처리 결과

- 1차 4건(blocking 2/high 1/med 1) + 재리뷰 신규 2건(high 1/med 1) **전부 Fixed**, 최종 재검증으로 blocking·high 0.
- 상세: [phase-3-codex-review.md](../reviews/phase-3-codex-review.md), [phase-3-codex-resolution.md](../reviews/phase-3-codex-resolution.md).

## Human Check Items

| ID | 분류(Security/Architecture/Scope/Risk/Other) | 확인 필요 사항 | 필요한 인간 판단 | 차단 여부 |
| --- | --- | --- | --- | --- |
| HCI-1 | Architecture | Post 삭제 시 첨부 S3 선삭제 캐스케이드(NV2-002)는 Phase 4에서 구현 예정. 현재 첨부 있는 글 삭제는 FK RESTRICT로 실패. | Phase 4까지 미구현 수용 확인. | 비차단(계획된 후속) |
| HCI-2 | Risk | 낙관적 잠금은 단일 DB 조건부 UPDATE로 원자적. 동시성 부하/경합 실측은 통합·부하 테스트(후속)로 검증 예정. | 부하 테스트 도입 시점 확인. | 비차단 |
| HCI-3 | Architecture | 게시물 생성이 현재 즉시 COMMITTED(첨부 없음). Phase 4에서 첨부 동반 시 PENDING→COMMITTED로 전환. | 전환 설계가 A-03/ADR-0005와 정합함을 Phase 4 리뷰에서 확인. | 비차단 |
