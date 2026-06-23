# DB 스키마 정의서 (Database Schema Definition)

영속 저장소는 PostgreSQL 16. 마이그레이션은 Alembic으로 버전 관리한다.

```mermaid
erDiagram
  USER ||--o{ POST : authors
  USER ||--o{ COMMENT : writes
  BOARD ||--o{ POST : contains
  POST ||--o{ ATTACHMENT : has
  POST ||--o{ COMMENT : has

  USER {
    bigint id PK
    varchar email UK "NOT NULL, unique"
    varchar password_hash "NOT NULL (bcrypt)"
    varchar role "NOT NULL, enum USER|ADMIN, default USER"
    timestamptz created_at "NOT NULL, default now()"
    timestamptz deleted_at "NULL (소프트 삭제, ADR-0006)"
  }
  BOARD {
    bigint id PK
    varchar name "NOT NULL"
    varchar slug UK "NOT NULL, unique"
    varchar type "NOT NULL, enum NOTICE|GENERAL|IMAGE"
    varchar read_visibility "NOT NULL, enum PUBLIC|AUTHENTICATED"
    text description "NULL"
    timestamptz created_at "NOT NULL, default now()"
  }
  POST {
    bigint id PK
    bigint board_id FK "NOT NULL -> BOARD.id"
    bigint author_id FK "NOT NULL -> USER.id"
    varchar title "NOT NULL"
    text content "NOT NULL"
    timestamptz created_at "NOT NULL, default now()"
    timestamptz updated_at "NOT NULL, default now()"
  }
  ATTACHMENT {
    bigint id PK
    bigint post_id FK "NOT NULL -> POST.id"
    varchar storage_key "NOT NULL, unique (S3 원본 키)"
    varchar original_name "NOT NULL"
    varchar content_type "NOT NULL"
    bigint size "NOT NULL"
    boolean is_image "NOT NULL, default false"
    varchar thumbnail_key "NULL (S3 썸네일 키)"
    timestamptz created_at "NOT NULL, default now()"
  }
  COMMENT {
    bigint id PK
    bigint post_id FK "NOT NULL -> POST.id"
    bigint author_id FK "NOT NULL -> USER.id"
    text content "NOT NULL"
    timestamptz created_at "NOT NULL, default now()"
  }
```

## 제약·인덱스

- UNIQUE: `USER.email`, `BOARD.slug`, `ATTACHMENT.storage_key`, **`ATTACHMENT.thumbnail_key`(부분 유니크 — `WHERE thumbnail_key IS NOT NULL`)** (A-05).
- 인덱스: `POST(board_id, created_at DESC)` — 게시판 목록 페이지네이션. `COMMENT(post_id, created_at)`, `ATTACHMENT(post_id)`.
- **FK별 삭제 동작(A-04)** — 일괄 CASCADE 금지:
  - `POST.author_id → USER`: `ON DELETE RESTRICT` (사용자 삭제는 소프트 삭제 정책으로, 콘텐츠 보존 — ADR-0006).
  - `COMMENT.author_id → USER`: `ON DELETE RESTRICT`.
  - `POST.board_id → BOARD`: `ON DELETE RESTRICT` (게시판 삭제는 애플리케이션이 하위 정리 후 수행, E-03).
  - `ATTACHMENT.post_id → POST`, `COMMENT.post_id → POST`: `ON DELETE CASCADE` (게시물 삭제 시 DB 행 정리). **S3 객체 삭제는 애플리케이션 레벨**에서 트랜잭션 후 처리(orphan 정리 잡 보조, E-02).
- enum은 PostgreSQL enum 타입 또는 CHECK 제약으로 강제(ADR-0002 참조).
- `BOARD.read_visibility`(E-04): ADMIN이 게시판 생성 시 지정. `PUBLIC`=비인증 포함 읽기, `AUTHENTICATED`=인증 사용자만 읽기.

## 마이그레이션/버전 전략

- Alembic. 각 phase에서 스키마 변경은 마이그레이션 파일로 추가(되돌릴 수 있게 `upgrade`/`downgrade` 작성). expand/contract 안전 규칙은 deployment.md(P-04) 참조.

## 관리자 라이프사이클 (Y-02)

- **초기 ADMIN**: 시드 스크립트로 생성(비밀번호는 env 주입, 평문 커밋 금지).
- **승격**: 기존 ADMIN이 다른 USER를 ADMIN으로 승격하는 관리 엔드포인트(ADMIN only).
- **비밀번호 재설정/복구**: MVP는 ADMIN이 사용자 비밀번호를 재설정하는 수동 경로(이메일 발송은 범위 밖). 최후의 ADMIN 복구는 시드 스크립트 재실행으로 처리(운영 절차로 문서화).
