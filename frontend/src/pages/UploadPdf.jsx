import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { uploadPdf, fetchStats, fetchLimits } from '../api/client';

export default function UploadPdf() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [limits, setLimits] = useState(null);
  const [quota, setQuota] = useState(null);

  useEffect(() => {
    Promise.all([fetchLimits(), fetchStats()])
      .then(([l, s]) => {
        setLimits(l);
        const active = (s.pending || 0) + (s.processing || 0);
        setQuota({ used: active, max: l.max_pdfs_per_user, remaining: Math.max(0, l.max_pdfs_per_user - active) });
      })
      .catch(() => {});
  }, []);

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer?.files?.[0];
    if (f && f.type === 'application/pdf') setFile(f);
    else if (f) setError('Solo se permiten archivos PDF');
  }

  function handleFileChange(e) {
    const f = e.target?.files?.[0];
    setFile(f || null);
    setError('');
  }

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;
    setError('');
    setLoading(true);
    try {
      await uploadPdf(file);
      navigate('/my-pdfs');
    } catch (err) {
      setError(err.message || 'Error al subir');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="upload-page">
      <h1>Subir PDF</h1>

      <section className="limits-info">
        <h2>Límites</h2>
        <ul>
          <li>Máximo <strong>{limits?.max_pdfs_per_user ?? 2} PDFs</strong> por usuario.</li>
          <li>Por PDF: hasta <strong>{limits?.max_pages_per_pdf ?? 5} páginas</strong> y <strong>{(limits?.max_words_per_pdf ?? 1500).toLocaleString()} palabras</strong> (equivalente a ~5 páginas de texto estándar).</li>
        </ul>
        {quota && (
          <p className="quota">Cuota: {quota.remaining} de {quota.max} disponibles ({quota.used} en proceso).</p>
        )}
      </section>

      {quota && quota.remaining <= 0 && (
        <div className="error-block">Has alcanzado el límite de PDFs. Espera a que terminen los actuales.</div>
      )}

      <form onSubmit={handleSubmit}>
        {error && <div className="error">{error}</div>}
        <label
          htmlFor="pdf-file-input"
          className={`drop-zone ${dragOver ? 'drag-over' : ''} ${quota?.remaining <= 0 ? 'disabled' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <input
            id="pdf-file-input"
            type="file"
            accept=".pdf"
            onChange={handleFileChange}
            disabled={quota?.remaining <= 0}
          />
          {file ? (
            <p><strong>{file.name}</strong></p>
          ) : (
            <p>Arrastra un PDF aquí o haz clic para seleccionar</p>
          )}
        </label>
        <button type="submit" disabled={!file || loading || (quota?.remaining <= 0)} className="btn primary">
          {loading ? 'Subiendo...' : 'Convertir a audiolibro'}
        </button>
      </form>
    </div>
  );
}
