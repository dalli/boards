import { BrowserRouter, Link, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { BoardDetailPage } from "./pages/BoardDetailPage";
import { BoardListPage } from "./pages/BoardListPage";
import { CreateBoardPage } from "./pages/CreateBoardPage";
import { LoginPage } from "./pages/LoginPage";
import { PostDetailPage } from "./pages/PostDetailPage";
import "./app.css";

function NavBar() {
  const { user, logout } = useAuth();
  return (
    <header className="navbar">
      <Link to="/" className="brand">Boards</Link>
      <nav>
        {user ? (
          <>
            <span className="me">{user.email}</span>
            <button onClick={logout} className="link-button">로그아웃</button>
          </>
        ) : (
          <Link to="/login">로그인</Link>
        )}
      </nav>
    </header>
  );
}

export function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <NavBar />
        <main className="container">
          <Routes>
            <Route path="/" element={<BoardListPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/boards/:boardId" element={<BoardDetailPage />} />
            <Route path="/posts/:postId" element={<PostDetailPage />} />
            <Route path="/admin/boards/new" element={<CreateBoardPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </BrowserRouter>
    </AuthProvider>
  );
}
