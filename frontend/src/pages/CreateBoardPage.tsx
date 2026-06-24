import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import * as api from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import type { BoardType, ReadVisibility } from "../api/types";

export function CreateBoardPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [name, setName] = useState("");
  const [slug, setSlug] = useState("");
  const [type, setType] = useState<BoardType>("GENERAL");
  const [readVisibility, setReadVisibility] = useState<ReadVisibility>("PUBLIC");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);

  if (user?.role !== "ADMIN") return <p className="error">관리자만 접근할 수 있습니다.</p>;

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      const board = await api.createBoard({
        name,
        slug,
        type,
        read_visibility: readVisibility,
        description: description || null,
      });
      navigate(`/boards/${board.id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "게시판을 만들지 못했습니다.");
    }
  };

  return (
    <section>
      <h2>게시판 만들기</h2>
      <form onSubmit={submit} className="board-form">
        <label>
          이름
          <input value={name} onChange={(e) => setName(e.target.value)} required />
        </label>
        <label>
          slug
          <input
            value={slug}
            onChange={(e) => setSlug(e.target.value)}
            pattern="[a-z0-9][a-z0-9-]*"
            required
          />
        </label>
        <label>
          종류
          <select value={type} onChange={(e) => setType(e.target.value as BoardType)}>
            <option value="NOTICE">공지(NOTICE)</option>
            <option value="GENERAL">일반(GENERAL)</option>
            <option value="IMAGE">이미지(IMAGE)</option>
          </select>
        </label>
        <label>
          읽기 권한
          <select
            value={readVisibility}
            onChange={(e) => setReadVisibility(e.target.value as ReadVisibility)}
          >
            <option value="PUBLIC">전체 공개(PUBLIC)</option>
            <option value="AUTHENTICATED">인증 사용자(AUTHENTICATED)</option>
          </select>
        </label>
        <label>
          설명
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit">만들기</button>
      </form>
    </section>
  );
}
