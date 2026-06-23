# 데이터 아키텍처 (Data Architecture)

어떤 데이터가 어떤 저장소에 저장되는지의 매핑. 구체적 구조는 [db-schema.md](db-schema.md) 참조.

## 엔티티 ↔ 저장소 매핑

| 엔티티/데이터 | 저장소 | 보존/일관성 |
| --- | --- | --- |
| User, Board, Post, Comment, Attachment(메타데이터) | PostgreSQL 16 | 강한 일관성(ACID), 영구 보존 |
| 첨부 원본 파일(이미지/문서) | MinIO/S3 — 버킷 `attachments` | 객체 영구 보존, DB의 `storage_key`로 참조 |
| 이미지 썸네일 | MinIO/S3 — 버킷 `thumbnails`(또는 prefix) | 파생물, 원본에서 재생성 가능, `thumbnail_key`로 참조 |
| JWT(access token) | 클라이언트 **메모리 전용**(localStorage 금지, S-01) | 무상태, 서버 미보관, TTL 30분 |
| 비밀번호 | PostgreSQL(`password_hash`만) | bcrypt 해시, 평문 미저장 |
| 시크릿(JWT secret, DB/MinIO 자격증명) | 환경변수/`.env`(미커밋) | §4 보호 대상 |

## 일관성·정합성 규칙

> 모든 업로드는 **백엔드 경유(backend-mediated)** 방식이다. 클라이언트가 S3에 직접 업로드하지 않으며(client-direct 아님), 백엔드가 객체 저장과 DB 레코드 전이를 모두 중재한다. (A-02)

### DB↔S3 일관성 프로토콜 (A-03, ADR-0005 참조)

DB와 S3는 분산 트랜잭션을 지원하지 않으므로, 2단계 커밋 대신 **PENDING → COMMITTED 상태 전이 + 조정(reconciliation) 잡** 패턴으로 최종 정합성을 보장한다.

1. **PENDING 생성**: 백엔드가 Attachment 레코드를 `PENDING` 상태로 먼저 INSERT한다(`storage_key` 확정).
2. **S3 업로드**: 백엔드가 해당 `storage_key`로 S3 객체를 업로드한다.
3. **COMMITTED 커밋**: 업로드 성공 시 단일 DB 트랜잭션으로 레코드를 `COMMITTED`로 전이한다.
4. **실패 처리**: S3 업로드가 실패하면 레코드는 `PENDING`으로 남는다(롤백/보상 없이 그대로 유지).
5. **조정/고아 정리**: 주기적 reconciliation·orphan-cleanup 잡이 (a) `COMMITTED` 레코드가 없는 S3 객체를 삭제하고, (b) 임계 시간(threshold)을 초과한 `PENDING` 레코드를 회수(삭제)한다.

`COMMITTED` 상태의 레코드만 사용자에게 노출·서빙된다.

### 고아 정리 잡 설계 (E-02)

- **소유 주체**: 백엔드의 스케줄드 잡(예: 주기적 태스크). 별도 외부 시스템이 아니라 백엔드가 책임진다.
- **멱등성(idempotent)**: 동일 입력에 대해 반복 실행해도 결과가 동일하며, 이미 정리된 객체/레코드를 재처리해도 부작용이 없다.
- **재시도**: 일시적 오류(S3/DB 일시 장애)는 백오프(backoff)를 적용해 재시도한다.
- **감사/로깅**: 삭제 대상·삭제 결과를 로그/감사(audit) 기록으로 남겨 추적 가능하게 한다.
- **임계값(threshold)**: `PENDING` 레코드 회수 기준 시간(예: 업로드 미완료가 비정상으로 간주되는 경과 시간)을 설정해, 진행 중 업로드를 오삭제하지 않으면서 고아만 정리한다.

### 삭제 정합성

- 썸네일은 파생물이므로 유실 시 원본에서 재생성 가능(비핵심 데이터).
- **Post 삭제**: 연관 Attachment 메타 삭제 + S3 객체 삭제.
- **Board 삭제 (E-03)**: ADMIN이 Board를 삭제하면, FK가 `RESTRICT`이므로 DB가 자동 캐스케이드하지 않는다. 따라서 애플리케이션이 명시적으로 캐스케이드한다 — 먼저 모든 하위 Post·Comment·Attachment(DB 레코드 + S3 객체)를 삭제한 뒤, 마지막으로 Board 레코드를 삭제한다.
- 소프트/하드 삭제 시맨틱은 ADR-0006에서 결정한다.
