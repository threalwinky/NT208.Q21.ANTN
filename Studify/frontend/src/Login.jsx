import { useState } from 'react';
import api from './api';

function Login({ onLoginSuccess, onSwitchRegister }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const submit = async (event) => {
    event.preventDefault();
    try {
      const res = await api.post('/auth/login', { email, password });
      onLoginSuccess(res.data.user);
    } catch (err) {
      setError(err.response?.data?.message || err.message);
    }
  };

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={submit}>
        <h2>Đăng nhập Studify</h2>
        <input
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <input
          type="password"
          placeholder="Mật khẩu"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <button type="submit">Đăng nhập</button>
        <button type="button" className="btn-muted" onClick={onSwitchRegister}>
          Chưa có tài khoản? Đăng ký
        </button>
        {error && <p className="message">{error}</p>}
      </form>
    </div>
  );
}

export default Login;
