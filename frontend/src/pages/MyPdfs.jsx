import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { fetchDocuments, downloadAudio, getPlayToken, getStreamUrl, getPdfViewToken, getPdfViewUrl } from '../api/client';

const POS_KEY = (id) => `heraldo_audio_pos_${id}`;

function AudioPlayer({ docId, onClose }) {
  const [streamUrl, setStreamUrl] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const audioRef = useRef(null);

  useEffect(() => {
    getPlayToken(docId)
      .then((token) => setStreamUrl(getStreamUrl(docId, token)))
      .catch((err) => setError(err.message || 'Error'))
      .finally(() => setLoading(false));
  }, [docId]);

  function handleLoadedMetadata() {
    const saved = localStorage.getItem(POS_KEY(docId));
    if (saved != null && audioRef.current) {
      const sec = parseFloat(saved, 10);
      if (Number.isFinite(sec) && sec > 0) audioRef.current.currentTime = sec;
    }
  }

  function handleTimeUpdate() {
    if (audioRef.current) {
      localStorage.setItem(POS_KEY(docId), String(audioRef.current.currentTime));
    }
  }

  function handleEnded() {
    localStorage.removeItem(POS_KEY(docId));
  }

  if (loading) return <div className="audio-player-loading">Cargando reproductor...</div>;
  if (error) return <div className="audio-player-error">{error}</div>;

  return (
    <div className="audio-player">
      <audio
        ref={audioRef}
        src={streamUrl}
        controls
        onLoadedMetadata={handleLoadedMetadata}
        onTimeUpdate={handleTimeUpdate}
        onPause={handleTimeUpdate}
        onEnded={handleEnded}
      />
    </div>
  );
}

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
  const [playingId, setPlayingId] = useState(null);

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

  async function handleViewPdf(id) {
    try {
      const token = await getPdfViewToken(id);
      window.open(getPdfViewUrl(id, token), '_blank', 'noopener,noreferrer');
    } catch (err) {
      alert(err.message || 'Error al abrir PDF');
    }
  }

  async function handleDownload(id, filename) {
    try {
      const defaultName = (filename?.replace(/\.pdf$/i, '') || 'audio') + '.mp3';
      const customName = window.prompt('Nombre del archivo al descargar:', defaultName);
      if (customName == null) return; // usuario canceló
      const name = customName.trim() || defaultName;
      const finalName = name.endsWith('.mp3') ? name : `${name}.mp3`;
      await downloadAudio(id, finalName);
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
                    title="Ver PDF en nueva pestaña"
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
                        <div className="progress-fill" style={{ width: `${d.progress.pct || 0}%` }} />
                      </div>
                      <span className="progress-label">
                        {d.progress.label || ''} — {d.progress.pct}% total
                      </span>
                    </div>
                  )}
                  {d.error_message && <small className="error-msg">{d.error_message}</small>}
                </td>
                <td
                  className={d.created_at ? 'with-tooltip' : ''}
                  title={d.created_at ? (() => {
                    const dt = new Date(d.created_at);
                    const dateStr = dt.toLocaleDateString('es-ES', { day: 'numeric', month: 'long', year: 'numeric' });
                    const timeStr = dt.toLocaleTimeString('es-ES', { hour: 'numeric', minute: '2-digit', hour12: true });
                    return `${dateStr}, ${timeStr}`;
                  })() : ''}
                >
                  {d.created_at ? new Date(d.created_at).toLocaleDateString() : '-'}
                </td>
                <td>
                  {d.status === 'completed' && (
                    <>
                      <button
                        className="btn-icon"
                        onClick={() => setPlayingId(playingId === d.id ? null : d.id)}
                        title="Reproducir en el navegador (streaming, sin descargar)"
                      >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                          {playingId === d.id ? (
                            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
                          ) : (
                            <path d="M8 5v14l11-7z" />
                          )}
                        </svg>
                        <span className="sr-only">{playingId === d.id ? 'Ocultar reproductor' : 'Reproducir'}</span>
                      </button>
                      <button
                        className="btn-icon"
                        onClick={() => handleDownload(d.id, d.original_filename)}
                        title="Descargar archivo MP3 (puedes cambiar el nombre)"
                      >
                        <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                          <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z" />
                        </svg>
                        <span className="sr-only">Descargar</span>
                      </button>
                    </>
                  )}
                </td>
              </tr>
              {playingId === d.id && (
                <tr key={`${d.id}-player`}>
                  <td colSpan={5}>
                    <AudioPlayer docId={d.id} onClose={() => setPlayingId(null)} />
                  </td>
                </tr>
              )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
