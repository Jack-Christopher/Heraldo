import { useAuth } from '../context/AuthContext';
import { fetchMe, changePassword } from '../api/client';
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

export default function Profile() {
  const { user, logout } = useAuth();
  const [profile, setProfile] = useState(null);
  const [pwCurrent, setPwCurrent] = useState('');
  const [pwNew, setPwNew] = useState('');
  const [pwError, setPwError] = useState('');
  const [pwSuccess, setPwSuccess] = useState(false);
  const [pwLoading, setPwLoading] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchMe()
      .then(setProfile)
      .catch(() => {});
  }, []);

  function handleLogout() {
    logout();
    navigate('/login');
  }

  async function handleChangePassword(e) {
    e.preventDefault();
    setPwError('');
    setPwSuccess(false);
    if (!pwCurrent || !pwNew || pwNew.length < 6) {
      setPwError('La contraseña nueva debe tener al menos 6 caracteres');
      return;
    }
    setPwLoading(true);
    try {
      await changePassword(pwCurrent, pwNew);
      setPwSuccess(true);
      setPwCurrent('');
      setPwNew('');
    } catch (err) {
      setPwError(err.message || 'Error al cambiar contraseña');
    } finally {
      setPwLoading(false);
    }
  }

  return (
    <div className="profile-page">
      <h1>Perfil</h1>
      {profile && (
        <div className="profile-info">
          <p><strong>Usuario:</strong> {profile.username}</p>
          {profile.email && <p><strong>Email:</strong> {profile.email}</p>}
          {profile.last_ip && <p><strong>Última IP:</strong> {profile.last_ip}</p>}
          {profile.last_login && (
            <p><strong>Último acceso:</strong> {new Date(profile.last_login).toLocaleString()}</p>
          )}
        </div>
      )}

      <section className="change-password">
        <h2>Cambiar contraseña</h2>
        <form onSubmit={handleChangePassword}>
          {pwError && <div className="error">{pwError}</div>}
          {pwSuccess && <div className="success">Contraseña actualizada correctamente</div>}
          <input
            type="password"
            placeholder="Contraseña actual"
            value={pwCurrent}
            onChange={(e) => setPwCurrent(e.target.value)}
            required
          />
          <input
            type="password"
            placeholder="Nueva contraseña (mín. 6 caracteres)"
            value={pwNew}
            onChange={(e) => setPwNew(e.target.value)}
            required
            minLength={6}
          />
          <button type="submit" disabled={pwLoading} className="btn primary">
            {pwLoading ? 'Guardando...' : 'Cambiar contraseña'}
          </button>
        </form>
      </section>

      <button onClick={handleLogout} className="btn secondary">Cerrar sesión</button>
    </div>
  );
}
