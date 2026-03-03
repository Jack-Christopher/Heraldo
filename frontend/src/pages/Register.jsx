import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

export default function Register() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const { user, register } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    if (user) navigate('/', { replace: true });
  }, [user, navigate]);

  async function handleSubmit(e) {
    e.preventDefault();
    setError('');
    if (password.length < 6) {
      setError('La contraseña debe tener al menos 6 caracteres');
      return;
    }
    if (!email || !email.includes('@')) {
      setError('El email es obligatorio');
      return;
    }
    setLoading(true);
    try {
      await register(username, password, email);
      setSuccess(true);
    } catch (err) {
      setError(err.message || 'Error al registrarse');
    } finally {
      setLoading(false);
    }
  }

  if (success) {
    return (
      <div className="auth-page">
        <h1>Heraldo</h1>
        <p className="subtitle">Revisa tu email</p>
        <div className="success">
          Te enviamos un correo a <strong>{email}</strong>. Haz clic en el enlace para confirmar tu cuenta.
        </div>
        <p>
          <Link to="/login">Iniciar sesión</Link>
        </p>
      </div>
    );
  }

  return (
    <div className="auth-page">
      <h1>Heraldo</h1>
      <p className="subtitle">Crear cuenta</p>
      <form onSubmit={handleSubmit}>
        {error && <div className="error">{error}</div>}
        <input
          type="text"
          placeholder="Usuario (mín. 2 caracteres)"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          required
          minLength={2}
          autoFocus
        />
        <input
          type="email"
          placeholder="Email (obligatorio)"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Contraseña (mín. 6 caracteres)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
          minLength={6}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Registrando...' : 'Registrarse'}
        </button>
      </form>
      <p>
        ¿Ya tienes cuenta? <Link to="/login">Inicia sesión</Link>
      </p>
    </div>
  );
}
