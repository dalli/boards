// Typed API endpoint wrappers. App code calls these; they consume the generated contract.
import { apiForm, apiJson, setAccessToken } from "./client";
import type {
  AttachmentResponse,
  BoardCreateRequest,
  BoardResponse,
  CommentResponse,
  PostDetailResponse,
  PostListResponse,
  PostResponse,
  TokenResponse,
  UserResponse,
} from "./types";

// ---- Auth ----

export async function signup(email: string, password: string): Promise<UserResponse> {
  return apiJson("/auth/signup", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function login(email: string, password: string): Promise<UserResponse> {
  // NF-001: drop any pre-existing token up front so a failed re-login never leaves a
  // stale session token in memory, and the /auth/login call itself is unauthenticated.
  setAccessToken(null);
  const token = await apiJson<TokenResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setAccessToken(token.access_token);
  try {
    return await apiJson<UserResponse>("/auth/me");
  } catch (err) {
    // F-001: if the profile fetch fails, don't leave an authenticated token behind.
    setAccessToken(null);
    throw err;
  }
}

export function logout(): void {
  setAccessToken(null);
}

export async function me(): Promise<UserResponse> {
  return apiJson("/auth/me");
}

// ---- Boards ----

export async function listBoards(): Promise<BoardResponse[]> {
  return apiJson("/boards");
}

export async function getBoard(boardId: number): Promise<BoardResponse> {
  return apiJson(`/boards/${boardId}`);
}

export async function createBoard(payload: BoardCreateRequest): Promise<BoardResponse> {
  return apiJson("/admin/boards", { method: "POST", body: JSON.stringify(payload) });
}

// ---- Posts ----

export async function listPosts(
  boardId: number,
  cursor?: string | null,
  limit = 20,
): Promise<PostListResponse> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (cursor) params.set("cursor", cursor);
  return apiJson(`/boards/${boardId}/posts?${params.toString()}`);
}

export async function getPost(postId: number): Promise<PostDetailResponse> {
  return apiJson(`/posts/${postId}`);
}

export async function createPost(
  boardId: number,
  title: string,
  content: string,
): Promise<PostResponse> {
  return apiJson(`/boards/${boardId}/posts`, {
    method: "POST",
    body: JSON.stringify({ title, content }),
  });
}

export async function createPostWithAttachments(
  boardId: number,
  title: string,
  content: string,
  files: File[],
): Promise<PostResponse> {
  const form = new FormData();
  form.set("title", title);
  form.set("content", content);
  for (const f of files) form.append("files", f);
  return apiForm(`/boards/${boardId}/posts/with-attachments`, form);
}

export async function updatePost(
  postId: number,
  title: string,
  content: string,
  version: number,
): Promise<PostResponse> {
  return apiJson(`/posts/${postId}`, {
    method: "PUT",
    body: JSON.stringify({ title, content, version }),
  });
}

export async function deletePost(postId: number): Promise<void> {
  return apiJson(`/posts/${postId}`, { method: "DELETE" });
}

// ---- Attachments ----

export async function listAttachments(postId: number): Promise<AttachmentResponse[]> {
  return apiJson(`/posts/${postId}/attachments`);
}

export async function getOriginalUrl(attachmentId: number): Promise<string> {
  const resp = await apiJson<{ url: string }>(`/attachments/${attachmentId}/original-url`);
  return resp.url;
}

export async function deleteAttachment(postId: number, attachmentId: number): Promise<void> {
  return apiJson(`/posts/${postId}/attachments/${attachmentId}`, { method: "DELETE" });
}

// ---- Comments ----

export async function listComments(postId: number): Promise<CommentResponse[]> {
  return apiJson(`/posts/${postId}/comments`);
}

export async function createComment(postId: number, content: string): Promise<CommentResponse> {
  return apiJson(`/posts/${postId}/comments`, {
    method: "POST",
    body: JSON.stringify({ content }),
  });
}

export async function deleteComment(commentId: number): Promise<void> {
  return apiJson(`/comments/${commentId}`, { method: "DELETE" });
}
