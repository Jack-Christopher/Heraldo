import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { fetchStats, fetchLimits } from '../api/client';

export default function Dashboard() {
  const { user } = useAuth();
  const [stats, setStats] = useState(null);
  const [limits, setLimits] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([fetchStats(), fetchLimits()])
      .then(([s, l]) => {
        setStats(s);
        setLimits(l);
      })
      .catch((err) => setError(err.message));
  }, []);

  if (error) return <div className="error-block">Error: {error}</div>;
  if (!stats || !limits) return <div className="loading">Cargando...</div>;

  const activeCount = (stats.pending || 0) + (stats.processing || 0);
  const remaining = Math.max(0, limits.max_pdfs_per_user - activeCount);

  return (
    <div className="dashboard">
      <h1>Dashboard</h1>
      <p>Hola, {user?.username}</p>

      <section className="limits-info">
        <h2>Límites</h2>
        <ul>
          <li>Máximo <strong>{limits.max_pdfs_per_user} PDFs</strong> por usuario.</li>
          <li>Por PDF: hasta <strong>{limits.max_pages_per_pdf} páginas</strong> y <strong>{limits.max_words_per_pdf.toLocaleString()} palabras</strong> (equivalente a ~5 páginas de texto estándar).</li>
        </ul>
        <p className="quota">Cuota: {remaining} de {limits.max_pdfs_per_user} disponibles.</p>
      </section>

      <section className="stats-cards">
        <div className="card">
          <span className="number">{stats.total_pdfs}</span>
          <span className="label">PDFs totales</span>
        </div>
        <div className="card">
          <span className="number">{stats.completed}</span>
          <span className="label">Completados</span>
        </div>
        <div className="card">
          <span className="number">{stats.pending + stats.processing}</span>
          <span className="label">En proceso</span>
        </div>
      </section>

      {stats.last_pdf && (
        <section>
          <h2>Último PDF</h2>
          <p>{stats.last_pdf.filename} — {stats.last_pdf.status}</p>
        </section>
      )}

      <nav className="quick-links">
        <Link to="/upload" className="btn primary">Subir PDF</Link>
        <Link to="/my-pdfs" className="btn">Mis PDFs</Link>
        <Link to="/profile" className="btn">Perfil</Link>
      </nav>
    </div>
  );
}
