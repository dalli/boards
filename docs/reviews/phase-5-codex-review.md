# Phase 5 codex 리뷰 (§6.2-3)

| 항목 | 값 |
| --- | --- |
| reviewer_id | codex (codex:codex-rescue 포워더) |
| model_id | gpt-5.x-codex (Implementor=Claude와 독립 모델) |
| session_id / thread | 1차 agent a3f6af8e0277bf430 · 재리뷰 ab2146b8ea629bed2 |
| 검토 대상 | dev staged Phase 5 (image board: attachment_service/post_service/image_service, api/posts·attachments, test_image_board, openapi) |
| 검토 시각(UTC) | 2026-06-23 |
| 사용 스킬 | code-review (read-only) |
| 결과(1차) | 8건 — **blocking 1 (R-01)**, high 2 (R-02/R-05), medium 4 (R-03/R-04/R-06/R-07), low 1 (R-08) |

## 1차 지적

| ID | sev | 파일/라인 | 요약 |
| --- | --- | --- | --- |
| R-01 | **blocking** | post_service.py:35 | JSON `POST /boards/{id}/posts`로 IMAGE 게시판에 이미지 0개 글 생성 가능(E-01 위반, AC5). |
| R-02 | high | api/posts.py:57 | AC6 `GET /posts/{id}`가 썸네일 URL 배열을 반환하지 않음(그리드용). |
| R-05 | high | attachment_service.py:175 | 마지막 이미지 삭제 가드가 동시 삭제에 비원자적(count=2에서 둘 다 통과 가능). |
| R-03 | medium | post_service.py:75 | post 수정에 E-01 이미지 수 가드 없음(수정은 첨부 미변경이라 도달 불가). |
| R-04 | medium | attachment_service.py:87 | 썸네일이 IMAGE 게시판뿐 아니라 모든 이미지에 생성됨. |
| R-06 | medium | test_image_board.py:68 | AC5 테스트가 zero-image JSON 생성 라우트를 커버 안 함. |
| R-07 | medium | test_image_board.py:140 | AC6 그리드 테스트가 post GET이 아닌 attachments 목록을 사용. |
| R-08 | low | test_image_board.py:95 | thumbnail_key 검증이 thumbnail_url 간접 확인(DB 컬럼 직접 미검증). |

> 처리·재검증은 [phase-5-codex-resolution.md](phase-5-codex-resolution.md).
