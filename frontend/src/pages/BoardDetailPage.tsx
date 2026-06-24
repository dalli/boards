import { useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import * as api from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import type { BoardResponse, PostResponse } from "../api/types";

export function BoardDetailPage() {
  const { boardId } = useParams();
  const id = Number(boardId);
  const { user } = useAuth();
  const [board, setBoard] = useState<BoardResponse | null>(null);
  const [posts, setPosts] = useState<PostResponse[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // post composer
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [files, setFiles] = useState<File[]>([]);
  const [busy, setBusy] = useState(false);

  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    // F-002: clear stale content on board/auth change so protected content cannot linger
    // after logout or a failed visibility check; guard out-of-order responses.
    let active = true;
    setBoard(null);
    setPosts([]);
    setNextCursor(null);
    setError(null);
    api
      .getBoard(id)
      .then((b) => {
        if (active) setBoard(b);
      })
      .catch((e) => {
        if (!active) return;
        setBoard(null);
        setError(e instanceof ApiError ? e.detail : "게시판을 불러오지 못했습니다.");
      });
    api
      .listPosts(id)
      .then((page) => {
        if (!active) return;
        setPosts(page.items);
        setNextCursor(page.next_cursor ?? null);
      })
      .catch(() => {
        if (active) setPosts([]);
      });
    return () => {
      active = false;
    };
  }, [id, user, reloadKey]);

  const reload = () => setReloadKey((k) => k + 1);

  const loadMore = async () => {
    if (!nextCursor) return;
    const page = await api.listPosts(id, nextCursor);
    setPosts((prev) => [...prev, ...page.items]);
    setNextCursor(page.next_cursor ?? null);
  };

  const canWrite = board && (board.type !== "NOTICE" || user?.role === "ADMIN") && !!user;
  const isImageBoard = board?.type === "IMAGE";

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (isImageBoard || files.length > 0) {
        await api.createPostWithAttachments(id, title, content, files);
      } else {
        await api.createPost(id, title, content);
      }
      setTitle("");
      setContent("");
      setFiles([]);
      reload();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "글을 등록하지 못했습니다.");
    } finally {
      setBusy(false);
    }
  };

  if (error && !board) return <p className="error">{error}</p>;
  if (!board) return <p>불러오는 중…</p>;

  return (
    <section>
      <h2>{board.name}</h2>
      <p>
        <span className="badge">{board.type}</span>{" "}
        <span className="badge">{board.read_visibility}</span>
      </p>

      {canWrite && (
        <form onSubmit={submit} className="post-composer">
          <h3>새 글</h3>
          <input
            placeholder="제목"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />
          <textarea
            placeholder="내용"
            value={content}
            onChange={(e) => setContent(e.target.value)}
            required
          />
          <input
            type="file"
            multiple
            accept={isImageBoard ? "image/*" : undefined}
            onChange={(e) => setFiles(Array.from(e.target.files ?? []))}
          />
          {isImageBoard && <small>이미지 게시판: 1개 이상의 이미지를 첨부하세요.</small>}
          {error && <p className="error" role="alert">{error}</p>}
          <button type="submit" disabled={busy}>등록</button>
        </form>
      )}

      <h3>게시물</h3>
      {posts.length === 0 ? (
        <p>아직 게시물이 없습니다.</p>
      ) : (
        <ul className="post-list">
          {posts.map((p) => (
            <li key={p.id}>
              <Link to={`/posts/${p.id}`}>{p.title}</Link>
            </li>
          ))}
        </ul>
      )}
      {nextCursor && (
        <button onClick={loadMore}>더 보기</button>
      )}
    </section>
  );
}
