import { Outlet, Link, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Layout() {
  const { user, loading } = useAuth();

  if (loading) return <div className="loading">Cargando...</div>;
  if (!user) return <Navigate to="/login" replace />;

  return (
    <div className="layout">
      <header>
        <Link to="/" className="logo">Heraldo</Link>
        <nav>
          <Link to="/">Dashboard</Link>
          <Link to="/upload">Subir PDF</Link>
          <Link to="/my-pdfs">Mis PDFs</Link>
          <Link to="/profile">Perfil</Link>
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
