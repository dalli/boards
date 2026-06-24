import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import * as api from "../api/endpoints";
import { useAuth } from "../auth/AuthContext";
import type { BoardResponse } from "../api/types";

export function BoardListPage() {
  const { user } = useAuth();
  const [boards, setBoards] = useState<BoardResponse[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // F-004: clear stale boards on auth change and ignore out-of-order responses so an
    // anonymous view never shows authenticated-only board metadata.
    let active = true;
    setBoards([]);
    setLoading(true);
    api
      .listBoards()
      .then((bs) => {
        if (active) setBoards(bs);
      })
      .catch(() => {
        if (active) setBoards([]);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [user]); // re-fetch when auth changes (anonymous sees PUBLIC only)

  if (loading) return <p>불러오는 중…</p>;

  return (
    <section>
      <div className="page-header">
        <h2>게시판</h2>
        {user?.role === "ADMIN" && <Link to="/admin/boards/new">게시판 만들기</Link>}
      </div>
      {boards.length === 0 ? (
        <p>표시할 게시판이 없습니다.</p>
      ) : (
        <ul className="board-list">
          {boards.map((b) => (
            <li key={b.id}>
              <Link to={`/boards/${b.id}`}>
                <strong>{b.name}</strong> <span className="badge">{b.type}</span>{" "}
                <span className="badge">{b.read_visibility}</span>
              </Link>
              {b.description && <p>{b.description}</p>}
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
