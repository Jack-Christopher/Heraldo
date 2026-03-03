import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { uploadPdf, fetchStats, fetchLimits, countPdfWords } from '../api/client';

export default function UploadPdf() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading] = useState(false);
  const [countLoading, setCountLoading] = useState(false);
  const [wordCount, setWordCount] = useState(null);
  const [withinLimit, setWithinLimit] = useState(null);
  const [error, setError] = useState('');
  const [limits, setLimits] = useState(null);
  const [quota, setQuota] = useState(null);

  useEffect(() => {
    function load() {
      Promise.all([fetchLimits(), fetchStats()])
        .then(([l, s]) => {
          setLimits(l);
          const total = s.total_pdfs || 0;
          const active = (s.pending || 0) + (s.processing || 0);
          const max = l.max_pdfs_per_user ?? 2;
          setQuota({
            total,
            active,
            max,
            atLimit: total >= max,
            remaining: Math.max(0, max - total),
          });
        })
        .catch(() => {});
    }
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);

  async function countWordsForFile(f) {
    if (!f || f.type !== 'application/pdf') return;
    setCountLoading(true);
    setWordCount(null);
    setWithinLimit(null);
    try {
      const data = await countPdfWords(f);
      setWordCount(data.word_count);
      setWithinLimit(data.within_limit);
    } catch {
      setWordCount(null);
      setWithinLimit(null);
    } finally {
      setCountLoading(false);
    }
  }

  function handleDrop(e) {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer?.files?.[0];
    if (f && f.type === 'application/pdf') {
      setFile(f);
      setError('');
      countWordsForFile(f);
    } else if (f) setError('Solo se permiten archivos PDF');
  }

  function handleFileChange(e) {
    const f = e.target?.files?.[0];
    if (f && f.type !== 'application/pdf') {
      setError('Solo se permiten archivos PDF');
      setFile(null);
      setWordCount(null);
      setWithinLimit(null);
      e.target.value = '';
      return;
    }
    setFile(f || null);
    setError('');
    if (f) countWordsForFile(f);
    else { setWordCount(null); setWithinLimit(null); }
  }

  const [uploadWordCount, setUploadWordCount] = useState(null);

  async function handleSubmit(e) {
    e.preventDefault();
    if (!file) return;
    setError('');
    setUploadWordCount(null);
    setWordCount(null);
    setLoading(true);
    try {
      const data = await uploadPdf(file);
      navigate('/my-pdfs');
    } catch (err) {
      setError(err.message || 'Error al subir');
      if (err.wordCount != null) setUploadWordCount(err.wordCount);
    } finally {
      setLoading(false);
    }
  }

  const atLimit = quota?.atLimit ?? false;

  return (
    <div className="upload-page">
      <h1>Subir PDF</h1>

      <section className="limits-info">
        <h2>Límites</h2>
        <ul>
          <li>Máximo <strong>{limits?.max_pdfs_per_user ?? 2} PDFs</strong> en tu cuenta.</li>
          <li>Por PDF: hasta <strong>{(limits?.max_words_per_pdf ?? 1500).toLocaleString()} palabras</strong>.</li>
        </ul>
        {quota && (
          <p className="quota">
            {atLimit
              ? `Límite alcanzado: ${quota.total} de ${quota.max} PDFs`
              : `PDFs en tu cuenta: ${quota.total} de ${quota.max}${quota.active > 0 ? ` (${quota.active} en proceso)` : ''}`}
          </p>
        )}
      </section>

      {atLimit ? (
        <div className="limit-reached">
          <div className="limit-reached-icon" aria-hidden>⚠</div>
          <h3>Has alcanzado el límite de PDFs</h3>
          <p>
            Ya tienes <strong>{quota.total} de {quota.max}</strong> PDFs convertidos. No puedes subir más archivos.
          </p>
          <p className="limit-reached-hint">
            Ve a <Link to="/my-pdfs">Mis PDFs</Link> para ver tus audiolibros.
          </p>
        </div>
      ) : (
      <form onSubmit={handleSubmit}>
        {error && <div className="error">{error}</div>}
        {uploadWordCount != null && error && (
          <p className="word-count-display">Palabras del archivo: <strong>{uploadWordCount.toLocaleString()}</strong></p>
        )}
        <label
          htmlFor="pdf-file-input"
          className={`drop-zone ${dragOver ? 'drag-over' : ''} ${(quota?.active ?? 0) >= (quota?.max ?? 2) ? 'disabled' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
        >
          <input
            id="pdf-file-input"
            type="file"
            accept="application/pdf,.pdf"
            onChange={handleFileChange}
            disabled={atLimit}
          />
          {file ? (
            <>
              <p><strong>{file.name}</strong></p>
              <div className={`word-count-badge ${withinLimit === true ? 'within' : withinLimit === false ? 'over' : ''}`}>
                {countLoading ? (
                  <span>Contando palabras...</span>
                ) : wordCount != null ? (
                  <>
                    <span className="word-count-number">{wordCount.toLocaleString()}</span>
                    <span> palabras</span>
                    {withinLimit === true && <span className="limit-ok"> • Dentro del límite</span>}
                    {withinLimit === false && <span className="limit-over"> • Excede el límite ({(limits?.max_words_per_pdf ?? 1500).toLocaleString()} máx.)</span>}
                  </>
                ) : null}
              </div>
            </>
          ) : (
            <p>Arrastra un PDF aquí o haz clic para seleccionar</p>
          )}
        </label>
        <button type="submit" disabled={!file || loading || countLoading || atLimit || withinLimit === false} className="btn primary">
          {loading ? 'Subiendo...' : 'Convertir a audiolibro'}
        </button>
      </form>
      )}
    </div>
  );
}
