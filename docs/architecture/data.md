# 데이터 아키텍처 (Data Architecture)

어떤 데이터가 어떤 저장소에 저장되는지의 매핑. 구체적 구조는 [db-schema.md](db-schema.md) 참조.

## 엔티티 ↔ 저장소 매핑

| 엔티티/데이터 | 저장소 | 보존/일관성 |
| --- | --- | --- |
| User, Board, Post, Comment, Attachment(메타데이터) | PostgreSQL 16 | 강한 일관성(ACID), 영구 보존 |
| 첨부 원본 파일(이미지/문서) | MinIO/S3 — 버킷 `attachments` | 객체 영구 보존, DB의 `storage_key`로 참조 |
| 이미지 썸네일 | MinIO/S3 — 버킷 `thumbnails`(또는 prefix) | 파생물, 원본에서 재생성 가능, `thumbnail_key`로 참조 |
| JWT(access token) | 클라이언트 메모리/스토리지 | 무상태, 서버 미보관, 짧은 만료 |
| 비밀번호 | PostgreSQL(`password_hash`만) | bcrypt 해시, 평문 미저장 |
| 시크릿(JWT secret, DB/MinIO 자격증명) | 환경변수/`.env`(미커밋) | §4 보호 대상 |

## 일관성·정합성 규칙

- DB의 Attachment 레코드와 S3 객체는 **업로드 트랜잭션 경계**에서 함께 생성한다. S3 업로드 성공 후 DB 커밋. 실패 시 보상(orphan 객체 정리 잡)으로 정합성 유지.
- 썸네일은 파생물이므로 유실 시 원본에서 재생성 가능(비핵심 데이터).
- Post 삭제 시 연관 Attachment 메타 삭제 + S3 객체 삭제(소프트/하드 삭제 정책은 ADR에서 결정).
