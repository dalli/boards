# 시퀀스: 게시물 작성 + 첨부 (일반/이미지 게시판)

```mermaid
sequenceDiagram
  actor U as 인증 사용자
  participant SPA as React SPA
  participant API as FastAPI api
  participant SVC as post service
  participant IMG as image service
  participant DB as PostgreSQL
  participant S3 as MinIO/S3

  U->>SPA: 제목/본문 + 파일 선택
  SPA->>API: POST /boards/{id}/posts (JWT)
  API->>SVC: create_post(board, author, title, content, files)
  SVC->>SVC: 인가 검사(write_role by Board.type)
  alt IMAGE 게시판인데 이미지 0개
    SVC-->>API: 422 (이미지 1개 이상 필수)
    API-->>SPA: 검증 실패
  else 정상
    SVC->>DB: INSERT post
    loop 각 첨부
      SVC->>SVC: 타입/크기 검증
      SVC->>S3: 원본 업로드(storage_key)
      alt 이미지 파일
        SVC->>IMG: 썸네일 생성(Pillow)
        IMG->>S3: 썸네일 업로드(thumbnail_key)
      end
      SVC->>DB: INSERT attachment(is_image, thumbnail_key?)
    end
    SVC-->>API: 201 + post
    API-->>SPA: 작성 완료
  end
```
