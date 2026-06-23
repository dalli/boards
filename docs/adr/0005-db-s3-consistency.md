# ADR-0005: DB-S3 정합성 프로토콜 (PENDING→COMMITTED + 조정 잡)

- 상태: 승인 대기
- 날짜: 2026-06-23
- 관련: codex 교차 검증 A-03, E-02

## 컨텍스트

첨부 메타데이터는 PostgreSQL, 바이너리는 S3에 분리 저장된다. 둘은 분산 트랜잭션이 없어, "DB와 S3가 함께 생성된다"는 선언만으로는 정합성이 보장되지 않는다(부분 실패 시 orphan 발생).

## 결정

2단계 커밋 대신 **상태 전이 + 조정(reconciliation)** 으로 최종 정합성을 보장한다.

1. Attachment/Post를 `PENDING`으로 먼저 INSERT(`storage_key` 확정).
2. 백엔드가 S3에 객체 업로드(A-02, 백엔드 경유).
3. 성공 시 단일 DB 트랜잭션으로 `COMMITTED` 전이.
4. S3 실패 시 행은 `PENDING` 유지(보상 없이).
5. 주기적 조정 잡: COMMITTED 없는 S3 객체 삭제 + threshold 초과 PENDING 행 회수.

`COMMITTED` 행만 사용자에게 노출·서빙한다.

## 대안

- 분산 트랜잭션/2PC: MinIO·PostgreSQL 간 미지원, 복잡.
- DB에 BLOB 저장으로 단일 트랜잭션화: 확장성·성능 불리(ADR-0003에서 기각).

## 결과

- 부분 실패가 사용자에게 노출되지 않음(PENDING 미노출).
- 조정 잡(E-02)은 멱등·재시도·감사 필요. orphan은 결국 정리되나 즉시성은 없음(eventual).
