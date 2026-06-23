# Phase 3 codex 리뷰 (§6.2-3)

| 항목 | 값 |
| --- | --- |
| reviewer_id | codex (codex:codex-rescue 포워더) |
| model_id | gpt-5.x-codex (Implementor=Claude와 독립 모델) |
| session_id / thread | 1차 agent a866043e0490999b8 · 재리뷰 ae6927e4f72f89541 · 최종 a6aa7a957bee0b592 |
| 검토 대상 | dev staged Phase 3 (post/comment repository·service·pagination, api/posts, tests, openapi) |
| 검토 시각(UTC) | 2026-06-23 |
| 사용 스킬 | code-review (read-only) |
| 결과(1차) | 4건 — **blocking 2 (F-001/F-003)**, high 1 (F-002), medium 1 (F-004) |

## 1차 지적

| ID | sev | 파일/라인 | 요약 |
| --- | --- | --- | --- |
| F-001 | **blocking** | post_service.py:83 | 낙관적 잠금이 Python read-then-write라 동시 수정 시 둘 다 통과해 갱신 유실 가능(원자성 부재). |
| F-002 | high | post_service.py:81 | post 수정이 owner-or-admin만 검사하고 Board.type 쓰기 게이트(NOTICE=ADMIN) 재적용 안 함. |
| F-003 | **blocking** | api/posts.py:104 | 댓글 수정(PUT) 미구현 → AC7 "댓글 PUT 작성자/ADMIN" 누락. |
| F-004 | medium | pagination.py:33 | `decode_cursor`가 base64 패딩 오류(binascii.Error) 미포착 → 일부 잘못된 커서가 500으로 누출. |

## 재리뷰 신규 지적 (1차 수정 후)

| ID | sev | 파일/라인 | 요약 |
| --- | --- | --- | --- |
| NV-002 | high | post_service.py:103 | `delete_post`가 NOTICE 쓰기 게이트 미재적용 → 비ADMIN 원작성자가 NOTICE 글 삭제 가능(수정과 비대칭). |
| NV-001 | medium | test_posts.py:281 | F-002 NOTICE 게이트 테스트가 positive-only(비ADMIN 거부 미검증). |

> 처리·재검증은 [phase-3-codex-resolution.md](phase-3-codex-resolution.md).
