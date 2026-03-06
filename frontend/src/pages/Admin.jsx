import React, { useState, useEffect, useRef } from 'react';
import { Link, useParams, useNavigate, Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  adminListUsers,
  adminGetUser,
  adminUpdateUserLimits,
  adminListUserDocuments,
  adminGetPlayToken,
  adminGetPdfViewToken,
  getStreamUrl,
  getPdfViewUrl,
} from '../api/client';

const STATUS_LABELS = {
  pending: 'Pendiente',
  processing: 'Procesando...',
  completed: 'Completado',
  failed: 'Error',
};

function AdminAudioPlayer({ userId, docId, onClose }) {
  const [streamUrl, setStreamUrl] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const audioRef = useRef(null);

  useEffect(() => {
    adminGetPlayToken(userId, docId)
      .then((token) => setStreamUrl(getStreamUrl(docId, token)))
      .catch((err) => setError(err.message || 'Error'))
      .finally(() => setLoading(false));
  }, [userId, docId]);

  if (loading) return <div className="audio-player-loading">Cargando reproductor...</div>;
  if (error) return <div className="audio-player-error">{error}</div>;

  return (
    <div className="audio-player">
      <audio ref={audioRef} src={streamUrl} controls />
    </div>
  );
}

function UserDetail({ userId, onBack }) {
  const [user, setUser] = useState(null);
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [limitsForm, setLimitsForm] = useState({ max_pdfs: '', max_words: '' });
  const [saving, setSaving] = useState(false);
  const [playingId, setPlayingId] = useState(null);

  function load() {
    Promise.all([adminGetUser(userId), adminListUserDocuments(userId)])
      .then(([u, d]) => {
        setUser(u);
        setDocs(d);
        const eff = u.effective_limits || {};
        setLimitsForm({
          max_pdfs: (u.limits?.max_pdfs_per_user ?? eff.max_pdfs_per_user ?? '').toString(),
          max_words: (u.limits?.max_words_per_pdf ?? eff.max_words_per_pdf ?? '').toString(),
        });
      })
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, [userId]);

  useEffect(() => {
    const pending = docs.some((d) => d.status === 'pending' || d.status === 'processing');
    if (!pending) return;
    const id = setInterval(() => adminListUserDocuments(userId).then(setDocs), 3000);
    return () => clearInterval(id);
  }, [docs, userId]);

  function handleSaveLimits(e) {
    e.preventDefault();
    setSaving(true);
    const max_pdfs = limitsForm.max_pdfs.trim() ? parseInt(limitsForm.max_pdfs, 10) : null;
    const max_words = limitsForm.max_words.trim() ? parseInt(limitsForm.max_words, 10) : null;
    adminUpdateUserLimits(userId, {
      max_pdfs_per_user: max_pdfs,
      max_words_per_pdf: max_words,
    })
      .then((u) => {
        setUser(u);
        setLimitsForm({
          max_pdfs: (u.limits?.max_pdfs_per_user ?? '').toString(),
          max_words: (u.limits?.max_words_per_pdf ?? '').toString(),
        });
      })
      .catch((err) => alert(err.message))
      .finally(() => setSaving(false));
  }

  async function handleViewPdf(docId) {
    try {
      const token = await adminGetPdfViewToken(userId, docId);
      window.open(getPdfViewUrl(docId, token), '_blank', 'noopener,noreferrer');
    } catch (err) {
      alert(err.message || 'Error al abrir PDF');
    }
  }

  if (loading) return <div className="loading">Cargando...</div>;
  if (error) return <div className="error-block">Error: {error}</div>;
  if (!user) return null;

  return (
    <div className="admin-user-detail">
      <button type="button" className="btn back" onClick={onBack}>
        ← Volver a usuarios
      </button>
      <h1>{user.full_name || user.email || user.id}</h1>
      <p className="admin-user-email">{user.email}</p>
      <p className="admin-user-role">
        Rol: <strong>{user.role || 'user'}</strong>
      </p>
      <p className="admin-user-stats">
        PDFs: {user.stats?.total_pdfs ?? 0} total · {user.stats?.completed ?? 0} completados ·{' '}
        {user.stats?.active_pdfs ?? 0} en proceso
      </p>

      <section className="admin-limits">
        <h2>Límites</h2>
        <p className="admin-limits-current">
          Efectivos: {user.effective_limits?.max_pdfs_per_user ?? '-'} PDFs ·{' '}
          {(user.effective_limits?.max_words_per_pdf ?? 0).toLocaleString()} palabras/PDF
        </p>
        <form onSubmit={handleSaveLimits} className="admin-limits-form">
          <label>
            Máx. PDFs por usuario (vacío = usar global)
            <input
              type="number"
              min="0"
              placeholder="Global"
              value={limitsForm.max_pdfs}
              onChange={(e) => setLimitsForm((f) => ({ ...f, max_pdfs: e.target.value }))}
            />
          </label>
          <label>
            Máx. palabras por PDF (vacío = usar global)
            <input
              type="number"
              min="0"
              placeholder="Global"
              value={limitsForm.max_words}
              onChange={(e) => setLimitsForm((f) => ({ ...f, max_words: e.target.value }))}
            />
          </label>
          <button type="submit" className="btn primary" disabled={saving}>
            {saving ? 'Guardando...' : 'Guardar límites'}
          </button>
        </form>
      </section>

      <section className="admin-documents">
        <h2>Documentos (PDFs y audios)</h2>
        {docs.length === 0 ? (
          <p>No hay documentos.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Archivo</th>
                <th>Palabras</th>
                <th>Estado</th>
                <th>Fecha</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {docs.map((d) => (
                <React.Fragment key={d.id}>
                  <tr>
                    <td>
                      <button
                        type="button"
                        className="link-filename"
                        onClick={() => handleViewPdf(d.id)}
                        title="Ver PDF"
                      >
                        {d.original_filename}
                      </button>
                    </td>
                    <td>{d.word_count != null ? d.word_count.toLocaleString() : '-'}</td>
                    <td>
                      <span className={`status ${d.status}`}>{STATUS_LABELS[d.status] || d.status}</span>
                      {d.status === 'processing' && d.progress && (
                        <div className="progress-detail">
                          <div className="progress-bar">
                            <div
                              className="progress-fill"
                              style={{ width: `${d.progress.pct || 0}%` }}
                            />
                          </div>
                          <span className="progress-label">
                            {d.progress.label || ''} — {d.progress.pct}% total
                          </span>
                        </div>
                      )}
                      {d.error_message && <small className="error-msg">{d.error_message}</small>}
                    </td>
                    <td>{d.created_at ? new Date(d.created_at).toLocaleDateString() : '-'}</td>
                    <td>
                      {d.status === 'completed' && (
                        <button
                          type="button"
                          className="btn-icon"
                          onClick={() =>
                            setPlayingId(playingId === d.id ? null : d.id)
                          }
                          title="Reproducir audio"
                        >
                          <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                            {playingId === d.id ? (
                              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
                            ) : (
                              <path d="M8 5v14l11-7z" />
                            )}
                          </svg>
                        </button>
                      )}
                    </td>
                  </tr>
                  {playingId === d.id && (
                    <tr key={`${d.id}-player`}>
                      <td colSpan={5}>
                        <AdminAudioPlayer
                          userId={userId}
                          docId={d.id}
                          onClose={() => setPlayingId(null)}
                        />
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}

export default function Admin() {
  const { user } = useAuth();
  const { userId } = useParams();
  const navigate = useNavigate();

  if (user && user.role !== 'admin') {
    return <Navigate to="/" replace />;
  }
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!userId) {
      adminListUsers()
        .then(setUsers)
        .catch((err) => setError(err.message))
        .finally(() => setLoading(false));
    }
  }, [userId]);

  if (userId) {
    return (
      <UserDetail
        userId={userId}
        onBack={() => navigate('/admin')}
      />
    );
  }

  if (loading) return <div className="loading">Cargando usuarios...</div>;
  if (error) return <div className="error-block">Error: {error}</div>;

  return (
    <div className="admin-page">
      <h1>Administración</h1>
      <p className="admin-intro">
        Gestiona usuarios, límites y consulta sus documentos (PDFs y audios).
      </p>
      {users.length === 0 ? (
        <p>No hay usuarios.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Nombre</th>
              <th>Email</th>
              <th>Rol</th>
              <th>Último login</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name || '-'}</td>
                <td>{u.email || '-'}</td>
                <td>
                  <span className={`role-badge ${u.role || 'user'}`}>
                    {u.role || 'user'}
                  </span>
                </td>
                <td>
                  {u.last_login ? new Date(u.last_login).toLocaleString() : '-'}
                </td>
                <td>
                  <Link to={`/admin/users/${u.id}`} className="btn btn-sm">
                    Ver detalle
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
