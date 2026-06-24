# Phase 2 codex 리뷰 (§6.2-3)

| 항목 | 값 |
| --- | --- |
| reviewer_id | codex (codex:codex-rescue 포워더) |
| model_id | gpt-5.x-codex (Implementor=Claude와 독립 모델) |
| session_id / thread | codex thread (Phase 2 1차 — agent abd891b20c2ac460b) |
| 검토 대상 | dev staged Phase 2 (board_repository/service/permissions, api/boards, test_boards, openapi) |
| 검토 시각(UTC) | 2026-06-23 |
| 사용 스킬 | code-review (read-only) |
| 결과 | 1건 — **blocking 1** (FINDING-001) |

## 지적

| ID | sev | 파일/라인 | 요약 |
| --- | --- | --- | --- |
| FINDING-001 | **blocking** | backend/app/api/boards.py:26 | 비인증 `GET /boards`가 AUTHENTICATED 게시판 메타데이터(slug/name/description 등)를 노출 → read_visibility 계약(E-04, security.md:23-24) 위반. |

> 근거: `list_boards`가 `list_all()`을 호출해 read_visibility 필터 없이 전체 반환. 권고: `viewer: OptionalUser` 추가 후 익명은 PUBLIC만, 인증 사용자는 전체 반환.

## 1차 판정

UNRESOLVED BLOCKING FINDINGS: **YES** → 수정 필요(아래 resolution).
