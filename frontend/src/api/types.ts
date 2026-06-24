// Re-export the relevant generated types so app code imports from one place.
// The generated schema (src/api/generated/schema.ts) is the SoT (§5.1) — never hand-edit it.
import type { components } from "./generated/schema";

export type UserResponse = components["schemas"]["UserResponse"];
export type TokenResponse = components["schemas"]["TokenResponse"];
export type BoardResponse = components["schemas"]["BoardResponse"];
export type BoardCreateRequest = components["schemas"]["BoardCreateRequest"];
export type PostResponse = components["schemas"]["PostResponse"];
export type PostDetailResponse = components["schemas"]["PostDetailResponse"];
export type PostListResponse = components["schemas"]["PostListResponse"];
export type AttachmentResponse = components["schemas"]["AttachmentResponse"];
export type CommentResponse = components["schemas"]["CommentResponse"];

export type BoardType = BoardResponse["type"];
export type ReadVisibility = BoardResponse["read_visibility"];
