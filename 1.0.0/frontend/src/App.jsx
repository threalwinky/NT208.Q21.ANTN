import { useState } from 'react';
import Login from './Login';
import Register from './Register';
import Dashboard from './Dashboard';

function App() {
  const [screen, setScreen] = useState('login');
  const [user, setUser] = useState(null);

  const handleAuthSuccess = (currentUser) => {
    setUser(currentUser);
    setScreen('dashboard');
  };

  if (screen === 'login') {
    return (
      <Login
        onLoginSuccess={handleAuthSuccess}
        onSwitchRegister={() => setScreen('register')}
      />
    );
  }

  if (screen === 'register') {
    return (
      <Register
        onRegisterSuccess={handleAuthSuccess}
        onSwitchLogin={() => setScreen('login')}
      />
    );
  }

  return (
    <Dashboard
      user={user}
      onLogout={() => {
        setUser(null);
        setScreen('login');
      }}
    />
  );
}

export default App;
