# Phase 2 codex 리뷰 처리 (§6.2-4)

원본 리뷰: [phase-2-codex-review.md](phase-2-codex-review.md).

| ID | sev | 처리 | 증거 / 근거 |
| --- | --- | --- | --- |
| FINDING-001 | blocking | **Fixed** | `BoardRepository.list_public()` 추가(read_visibility==PUBLIC 필터). `BoardService.list_boards(viewer)`가 익명→PUBLIC만, 인증→전체 반환. `GET /boards`에 `viewer: OptionalUser` 추가. 테스트: `test_list_boards_anonymous_sees_only_public`, `test_list_boards_authenticated_sees_all`, `test_list_boards_invalid_token_treated_as_anonymous`(FINDING-008). |
| FINDING-008 | low | **Fixed** | 잘못된 토큰이 익명으로 다운그레이드되어 가시성이 넓어지지 않음을 보장하는 회귀 테스트 추가. |

## codex 재리뷰 (§6.2-4 미해결 blocking 부재 확인)

Fixed 적용 후 staged 코드에 대해 codex 재리뷰 수행(독립 모델, 새 thread af32971740ad88287).

| ID | 상태 |
| --- | --- |
| FINDING-001 | **RESOLVED** — 익명 요청은 public-only 쿼리 사용, 대체 익명 경로 없음 확인(board_service.py:52, board_repository.py:24). |
| 인가 모델(FINDING-002~005) | 확인 — read=read_visibility, write=Board.type(NOTICE=ADMIN), create/delete ADMIN-only + service 재검사. |
| 테스트(FINDING-006/007) | 확인 — 혼합 가시성 익명/인증 케이스 커버. |
| 신규 blocking/high | **없음(None)**. |

> **재리뷰 최종 판정: `UNRESOLVED BLOCKING FINDINGS: NO`.** → §6.2-4 게이트 충족.

## 수정 후 검증 증거 (콘솔)

```text
ruff → All checks passed! · mypy → no issues (25 files)
pytest 43 passed · coverage 93.90% (>=80)
```
