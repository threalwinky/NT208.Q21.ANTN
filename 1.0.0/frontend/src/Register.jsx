import { useState } from 'react';
import api from './api';

const initialProfile = {
  name: '',
  email: '',
  password: '',
  university: '',
  major: '',
  year: '',
  gpaTarget: '',
  careerGoal: '',
  studyHabits: '',
  freeTimeSlotsRaw: '19:00-21:00'
};

function Register({ onRegisterSuccess, onSwitchLogin }) {
  const [profile, setProfile] = useState(initialProfile);
  const [error, setError] = useState('');

  const register = async (event) => {
    event.preventDefault();
    try {
      const payload = {
        ...profile,
        freeTimeSlots: profile.freeTimeSlotsRaw
          .split(',')
          .map((v) => v.trim())
          .filter(Boolean)
      };
      delete payload.freeTimeSlotsRaw;

      const res = await api.post('/auth/register', payload);
      onRegisterSuccess(res.data.user);
    } catch (err) {
      setError(err.response?.data?.message || err.message);
    }
  };

  return (
    <div className="auth-wrap">
      <form className="auth-card" onSubmit={register}>
        <h2>Tạo hồ sơ sinh viên</h2>
        <div className="grid">
          {Object.entries(profile).map(([key, value]) => (
            <input
              key={key}
              placeholder={key}
              value={value}
              onChange={(e) => setProfile((p) => ({ ...p, [key]: e.target.value }))}
            />
          ))}
        </div>
        <button type="submit">Đăng ký</button>
        <button type="button" className="btn-muted" onClick={onSwitchLogin}>
          Đã có tài khoản? Đăng nhập
        </button>
        {error && <p className="message">{error}</p>}
      </form>
    </div>
  );
}

export default Register;
