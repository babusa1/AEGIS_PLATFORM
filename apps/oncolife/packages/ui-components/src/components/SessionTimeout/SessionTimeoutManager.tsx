import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { SESSION_TIMEOUT_MINUTES } from '../config/api';
import SessionTimeoutModal from './SessionTimeoutModal';

export const SESSION_START_KEY = 'sessionStartTime';

const SessionTimeoutManager: React.FC = () => {
  const [sessionTimedOut, setSessionTimedOut] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    let sessionStart = sessionStorage.getItem(SESSION_START_KEY);
    const now = Date.now();
    if (!sessionStart) {
      sessionStorage.setItem(SESSION_START_KEY, now.toString());
      sessionStart = now.toString();
    }
    const sessionStartTime = parseInt(sessionStart, 10);
    const timeoutMs = SESSION_TIMEOUT_MINUTES * 60 * 1000;
    const elapsed = now - sessionStartTime;
    const remaining = timeoutMs - elapsed;

    if (remaining <= 0) {
      setSessionTimedOut(true);
      return;
    }

    const timer = setTimeout(() => {
      setSessionTimedOut(true);
    }, remaining);
    return () => clearTimeout(timer);
  }, []);

  const handleLoginAgain = () => {
    localStorage.removeItem('authToken');
    sessionStorage.removeItem(SESSION_START_KEY);
    setSessionTimedOut(false);
    navigate('/login', { replace: true });
  };

  return (
    <SessionTimeoutModal show={sessionTimedOut} onLoginAgain={handleLoginAgain} />
  );
};

export default SessionTimeoutManager; 