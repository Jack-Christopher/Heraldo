import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { fetchDocuments, downloadAudio } from '../api/client';

const STATUS_LABELS = {
  pending: 'Pendiente',
  processing: 'Procesando...',
  completed: 'Completado',
  failed: 'Error',
};

export default function MyPdfs() {
  const [docs, setDocs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  function load() {
    fetchDocuments()
      .then(setDocs)
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }

  useEffect(() => {
    load();
  }, []);

  useEffect(() => {
    const pending = docs.some((d) => d.status === 'pending' || d.status === 'processing');
    if (!pending) return;
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
  }, [docs]);

  async function handleDownload(id, filename) {
    try {
      const base = filename?.replace(/\.pdf$/i, '') || 'audio';
      await downloadAudio(id, `${base}.wav`);
    } catch (err) {
      alert(err.message || 'Error al descargar');
    }
  }

  if (loading) return <div className="loading">Cargando...</div>;
  if (error) return <div className="error-block">Error: {error}</div>;

  return (
    <div className="my-pdfs">
      <h1>Mis PDFs</h1>
      {docs.length === 0 ? (
        <p>No tienes PDFs. <Link to="/upload">Sube uno</Link> para convertir a audiolibro.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Archivo</th>
              <th>Páginas</th>
              <th>Palabras</th>
              <th>Estado</th>
              <th>Fecha</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {docs.map((d) => (
              <tr key={d.id}>
                <td>{d.original_filename}</td>
                <td>{d.page_count}</td>
                <td>{d.word_count}</td>
                <td>
                  <span className={`status ${d.status}`}>{STATUS_LABELS[d.status] || d.status}</span>
                  {d.error_message && <small className="error-msg">{d.error_message}</small>}
                </td>
                <td>{d.created_at ? new Date(d.created_at).toLocaleDateString() : '-'}</td>
                <td>
                  {d.status === 'completed' && (
                    <button
                      className="btn small"
                      onClick={() => handleDownload(d.id, d.original_filename)}
                    >
                      Descargar
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
