import { useEffect, useState, type FormEvent } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ApiError } from "../api/client";
import * as api from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import { ImageGallery } from "../components/ImageGallery";
import type { CommentResponse, PostDetailResponse } from "../api/types";

export function PostDetailPage() {
  const { postId } = useParams();
  const id = Number(postId);
  const { user } = useAuth();
  const navigate = useNavigate();
  const [post, setPost] = useState<PostDetailResponse | null>(null);
  const [comments, setComments] = useState<CommentResponse[]>([]);
  const [commentText, setCommentText] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    // F-003: clear stale content on post/auth change so protected content cannot linger
    // after logout or a failed visibility check; guard out-of-order responses.
    let active = true;
    setPost(null);
    setComments([]);
    setError(null);
    api
      .getPost(id)
      .then((p) => {
        if (active) setPost(p);
      })
      .catch((e) => {
        if (!active) return;
        setPost(null);
        setError(e instanceof ApiError ? e.detail : "게시물을 불러오지 못했습니다.");
      });
    api
      .listComments(id)
      .then((cs) => {
        if (active) setComments(cs);
      })
      .catch(() => {
        if (active) setComments([]);
      });
    return () => {
      active = false;
    };
  }, [id, user]);

  const refreshComments = async () => {
    // F-005: await + catch so a failed refresh surfaces instead of silently leaving stale UI.
    try {
      setComments(await api.listComments(id));
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "댓글을 불러오지 못했습니다.");
    }
  };

  const canModify = (authorId: number) => user?.role === "ADMIN" || user?.id === authorId;

  const addComment = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api.createComment(id, commentText);
      setCommentText("");
      await refreshComments();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "댓글을 등록하지 못했습니다.");
    }
  };

  const removeComment = async (commentId: number) => {
    try {
      await api.deleteComment(commentId);
      await refreshComments();
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "댓글을 삭제하지 못했습니다.");
    }
  };

  const removePost = async () => {
    if (!post) return;
    try {
      await api.deletePost(post.id);
      navigate(`/boards/${post.board_id}`);
    } catch (err) {
      setError(err instanceof ApiError ? err.detail : "삭제하지 못했습니다.");
    }
  };

  if (error && !post) return <p className="error">{error}</p>;
  if (!post) return <p>불러오는 중…</p>;

  return (
    <article>
      <h2>{post.title}</h2>
      {canModify(post.author_id) && (
        <button onClick={removePost} className="danger">삭제</button>
      )}
      {/* React escapes text by default (S-04) — no dangerouslySetInnerHTML. */}
      <p className="post-content">{post.content}</p>

      <ImageGallery attachments={post.attachments ?? []} />

      <section className="comments">
        <h3>댓글</h3>
        {user && (
          <form onSubmit={addComment}>
            <input
              value={commentText}
              onChange={(e) => setCommentText(e.target.value)}
              placeholder="댓글을 입력하세요"
              required
            />
            <button type="submit">등록</button>
          </form>
        )}
        {error && <p className="error" role="alert">{error}</p>}
        <ul>
          {comments.map((c) => (
            <li key={c.id}>
              {c.content}
              {canModify(c.author_id) && (
                <button onClick={() => removeComment(c.id)} className="link-button">삭제</button>
              )}
            </li>
          ))}
        </ul>
      </section>
    </article>
  );
}
