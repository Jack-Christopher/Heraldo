import { Outlet, Link, NavLink, Navigate } from 'react-router-dom';
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
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/upload">Subir PDF</NavLink>
          <NavLink to="/my-pdfs">Mis PDFs</NavLink>
          <NavLink to="/profile">Perfil</NavLink>
        </nav>
      </header>
      <main>
        <Outlet />
      </main>
    </div>
  );
}
