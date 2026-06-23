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
  }
  BOARD {
    bigint id PK
    varchar name "NOT NULL"
    varchar slug UK "NOT NULL, unique"
    varchar type "NOT NULL, enum NOTICE|GENERAL|IMAGE"
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

- `USER.email` UNIQUE, `BOARD.slug` UNIQUE, `ATTACHMENT.storage_key` UNIQUE.
- 인덱스: `POST(board_id, created_at DESC)` — 게시판 목록 페이지네이션. `COMMENT(post_id, created_at)`, `ATTACHMENT(post_id)`.
- FK는 `ON DELETE CASCADE`(POST 삭제 시 ATTACHMENT/COMMENT 정리). S3 객체 삭제는 애플리케이션 레벨에서 처리.
- enum은 PostgreSQL enum 타입 또는 CHECK 제약으로 강제(ADR-0002 참조).

## 마이그레이션/버전 전략

- Alembic. 각 phase에서 스키마 변경은 마이그레이션 파일로 추가(되돌릴 수 있게 `upgrade`/`downgrade` 작성).
- 초기 ADMIN 계정은 시드 마이그레이션 또는 별도 시드 스크립트로 생성(비밀번호는 env 주입, 평문 커밋 금지).
