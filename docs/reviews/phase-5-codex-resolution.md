# Phase 5 codex 리뷰 처리 (§6.2-4)

원본 리뷰: [phase-5-codex-review.md](phase-5-codex-review.md).

| ID | sev | 처리 | 증거 / 근거 |
| --- | --- | --- | --- |
| R-01 | blocking | **Fixed** | `PostService.create_post`가 IMAGE 게시판에 422(이미지 첨부 라우트 강제). 테스트 `test_image_board_json_create_route_rejected_422`. |
| R-02 | high | **Fixed** | `GET /posts/{id}`가 `PostDetailResponse`(attachments[] + presigned thumbnail_url) 반환. 테스트 `test_image_post_returns_thumbnail_url_array_for_grid`. |
| R-05 | high | **Fixed** | `delete_attachment`가 `PostRepository.get_for_update`(SELECT FOR UPDATE)로 post 행 잠금 → 마지막 이미지 가드와 삭제 직렬화. |
| R-03 | medium | **Accepted(by design)** | post 수정은 title/content만 변경하며 첨부를 건드리지 않음 → IMAGE 글이 update로 이미지 0개가 될 경로 없음. 유일한 이미지 제거 경로(`delete_attachment`)가 E-01 강제. 재리뷰가 "zero 도달 경로 없음" 확인. |
| R-04 | medium | **Accepted(by design)** | 일반 게시판 이미지 썸네일은 data.md 의도(미리보기). IMAGE 게시판 전용 아님. |
| R-06 | medium | **Fixed** | zero-image JSON 라우트 거부 테스트 추가. |
| R-07 | medium | **Fixed** | AC6 그리드 테스트가 `GET /posts/{id}.attachments` 사용. |
| R-08 | low | **Fixed** | DB `Attachment.thumbnail_key is not None` 직접 검증 추가. |

## codex 재검증 (§6.2-4)

재리뷰(thread ab2146b8ea629bed2): "All 8 prior findings are confirmed resolved. No new blocking or high issues found."

> **재리뷰 최종 판정: `UNRESOLVED BLOCKING FINDINGS: NO` · `UNRESOLVED HIGH FINDINGS: NO`** → §6.2-4 게이트 충족.

## 수정 후 검증 증거 (콘솔)

```text
ruff → All checks passed! · mypy → no issues (36 files)
pytest 104 passed · coverage 93.83% (>=80)
```
