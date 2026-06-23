# 회고: Phase 5 (이미지 게시판 — 백엔드)

> 인간 결정(2026-06-23): Phase 5는 **이미지 게시판 백엔드(AC5/AC6)**로 종료하고, 썸네일 그리드/라이트박스
> **프론트엔드는 Phase 6에서 일괄 구축**한다.

## 한 일과 결과 (완료된 수락 기준)

- **AC5**: IMAGE 게시판 이미지 0개 생성 시 422 — multipart 라우트(files=[])와 **JSON 라우트(R-01) 양쪽**.
  각 첨부에 서버 Pillow 썸네일 생성(`thumbnail_key` DB 확정). 마지막 이미지 삭제 시 422(E-01 불변식).
- **AC6**: `GET /posts/{id}`가 썸네일 URL 배열(attachments[])을 그리드용으로 반환,
  `GET /attachments/{id}/original-url`이 라이트박스용 원본 presigned GET 반환.

### 검증 증거 (콘솔)

```text
ruff → All checks passed! · mypy → no issues (36 files)
pytest 104 passed · coverage 93.83% (>=80)
codex 재검증: 8건 전건 RESOLVED · UNRESOLVED BLOCKING: NO · UNRESOLVED HIGH: NO
```

## 잘된 점

- Phase 4 첨부 파이프라인을 재사용해 IMAGE 경로(require_image·썸네일·E-01)를 최소 추가로 완성.
- codex가 **JSON 생성 라우트의 E-01 우회(R-01 blocking)**·AC6 응답 형태(R-02)·동시 삭제 비원자성(R-05)을 잡아냄 →
  실제 불변식 누수 차단.

## 어려웠던 점

- E-01을 "with-attachments 라우트"에만 걸었더니 일반 JSON 생성 라우트가 IMAGE 게시판에 빈 글을 허용하는 사각지대 발생.
  → `create_post`에서 board.type 검사로 차단.
- 마지막 이미지 삭제 가드의 동시성: SELECT FOR UPDATE로 post 행을 잠가 직렬화.

## 다음 phase 개선점 (Phase 6 입력)

- 프론트: 게시판 목록/글쓰기/첨부 업로드 + **이미지 썸네일 카드 그리드 + 라이트박스**(원본 presigned GET).
- OpenAPI 타입 생성(`npm run gen:api`)으로 생성 클라이언트 소비(§5.1, 수기 타입 금지).

## codex 리뷰 지적과 그 처리 결과

- 8건(blocking 1/high 2/med 4/low 1). 6건 **Fixed**, 2건(R-03/R-04) **Accepted(by design)**. 재검증 blocking·high 0.
- 상세: [phase-5-codex-review.md](../reviews/phase-5-codex-review.md), [phase-5-codex-resolution.md](../reviews/phase-5-codex-resolution.md).

## Human Check Items

| ID | 분류(Security/Architecture/Scope/Risk/Other) | 확인 필요 사항 | 필요한 인간 판단 | 차단 여부 |
| --- | --- | --- | --- | --- |
| HCI-1 | Scope | 이미지 게시판 **프론트(그리드/라이트박스)**는 인간 결정으로 Phase 6에 일괄 이관. | Phase 6에서 프론트 완성 확인. | 비차단(인간 결정) |
| HCI-2 | Architecture | R-03/R-04를 by-design으로 수용(수정은 첨부 미변경; 일반 이미지 썸네일은 의도). | 이 설계 판단 승인. | 비차단 |
| HCI-3 | Risk | 마지막 이미지 동시 삭제 직렬화는 SELECT FOR UPDATE(Postgres 강제, SQLite 무시). 운영 동시성은 통합 테스트로 검증 예정. | Postgres 통합 테스트 도입 시점 확인(Phase 4 HCI-4와 동일 계열). | 비차단 |
