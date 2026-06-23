# Phase 3 codex 리뷰 처리 (§6.2-4)

원본 리뷰: [phase-3-codex-review.md](phase-3-codex-review.md).

| ID | sev | 처리 | 증거 / 근거 |
| --- | --- | --- | --- |
| F-001 | blocking | **Fixed** | `PostRepository.update_if_version`로 `UPDATE ... WHERE id=? AND version=?` 원자적 갱신, rowcount==0→409. `post_service.update_post`가 사용. 테스트 `test_stale_version_conflicts_409`. |
| F-002 | high | **Fixed** | `update_post`가 `ensure_can_write_board` 재적용(NOTICE=ADMIN). 테스트 `test_non_admin_author_cannot_update_notice_post`. |
| F-003 | blocking | **Fixed** | 댓글 수정 구현: `PUT /comments/{id}`(owner-or-admin), `comment_service.update_comment`, `comment_repository.update_content`, `CommentUpdateRequest`. 테스트 author/other(403)/admin. |
| F-004 | medium | **Fixed** | `decode_cursor`가 `binascii.Error`/`UnicodeError` 포착→422. 테스트 `test_malformed_base64_cursor_422`, `test_decode_cursor_raises_validation_on_bad_padding`. |
| NV-002 | high | **Fixed** | `delete_post`도 `ensure_can_write_board` 재적용(수정과 대칭). 테스트 `test_non_admin_author_cannot_delete_notice_post`. |
| NV-001 | medium | **Fixed** | NOTICE 게이트 negative 테스트 추가(비ADMIN 원작성자 update/delete→PermissionDeniedError). |

## codex 재검증 (§6.2-4)

- 2차(재리뷰): F-001~F-004 전부 RESOLVED, `UNRESOLVED BLOCKING FINDINGS: NO`. 신규 NV-001/NV-002 발견.
- 3차(최종): NV-001/NV-002 RESOLVED. **`UNRESOLVED BLOCKING FINDINGS: NO` · `UNRESOLVED HIGH FINDINGS: NO`** → §6.2-4 게이트 충족.

## 수정 후 검증 증거 (콘솔)

```text
ruff → All checks passed! · mypy → no issues (30 files)
pytest 77 passed · coverage 95.11% (>=80)
```
