# ADR-0006: 삭제 시맨틱 (소프트 vs 하드 삭제)

- 상태: 승인 대기
- 날짜: 2026-06-23
- 관련: codex 교차 검증 Y-03, A-04, E-03

## 컨텍스트

User/Board/Post/Comment/Attachment의 삭제 동작이 미결정 상태였다(data.md가 "ADR에서 결정"으로 유예). FK 동작(A-04)과 게시판 삭제(E-03)도 이에 종속된다.

## 결정

- **User**: **소프트 삭제**(`deleted_at` 마킹). 작성한 Post/Comment는 보존(FK `RESTRICT`). 표시는 "탈퇴한 사용자".
  - **이메일 즉시 비식별화**: 소프트 삭제 시 서비스가 `USER.email`을 비식별 값(예: `deleted+{id}@invalid.local`)으로 즉시 재작성한다. 이는 **소프트 삭제 시점에 동일 트랜잭션 내에서** 수행한다.
  - 효과: 부분 유니크 인덱스(`WHERE deleted_at IS NULL`)에서 원래 이메일 주소가 해제되어 **재가입에 재사용 가능**해진다.
  - 로그인 흐름은 `deleted_at IS NOT NULL` 사용자를 항상 제외한다.
- **Post / Comment**: **하드 삭제**. Comment는 DB CASCADE. Attachment는 `RESTRICT`이므로 삭제 순서를 애플리케이션이 강제(NV2-002): **① S3 객체 삭제 → ② Attachment 행 삭제 → ③ Post 행 삭제**(단일 트랜잭션 경계, 실패분은 조정 잡 회수).
- **Board**: **하드 삭제**, 단 FK가 `RESTRICT`이므로 애플리케이션이 하위(Post→Attachment/Comment + S3 객체)를 먼저 정리 후 Board 삭제(E-03).
- **Attachment**: 하드 삭제. IMAGE 게시판은 마지막 이미지 삭제 거부(E-01 불변식).

## 대안

- 전면 하드 삭제: 사용자 삭제 시 작성 글이 사라져 토론 맥락 훼손.
- 전면 소프트 삭제: 스토리지·쿼리 복잡도 증가, MVP 과설계.

## 결과

- 사용자 데이터는 보존되면서 개인정보(이메일 등)는 소프트 삭제로 비식별 가능.
- 게시판/게시물 삭제는 애플리케이션 레벨 캐스케이드 + S3 정리 책임 명확화(ADR-0005 조정 잡 보조).
