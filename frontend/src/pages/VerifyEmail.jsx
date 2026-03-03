import { useState, useEffect } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { verifyEmail } from '../api/client';

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const [status, setStatus] = useState('loading');
  const [message, setMessage] = useState('');

  useEffect(() => {
    if (!token) {
      setStatus('error');
      setMessage('Falta el token de verificación.');
      return;
    }
    verifyEmail(token)
      .then((data) => {
        setStatus('success');
        setMessage(data.message || 'Email verificado correctamente.');
      })
      .catch((err) => {
        setStatus('error');
        setMessage(err.message || 'Error al verificar.');
      });
  }, [token]);

  return (
    <div className="auth-page">
      <h1>Heraldo</h1>
      <p className="subtitle">Verificación de email</p>
      {status === 'loading' && <p>Cargando...</p>}
      {status === 'success' && (
        <div className="success">
          {message}
          <p><Link to="/login">Iniciar sesión</Link></p>
        </div>
      )}
      {status === 'error' && (
        <div className="error-block">
          {message}
          <p><Link to="/login">Volver al inicio de sesión</Link></p>
        </div>
      )}
    </div>
  );
}
