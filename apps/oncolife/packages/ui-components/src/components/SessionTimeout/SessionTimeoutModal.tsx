import React from 'react';

interface SessionTimeoutModalProps {
  show: boolean;
  onLoginAgain: () => void;
}

const backdropStyle: React.CSSProperties = {
  position: 'fixed',
  top: 0,
  left: 0,
  width: '100vw',
  height: '100vh',
  background: 'rgba(0,0,0,0.5)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  zIndex: 1000,
};

const modalStyle: React.CSSProperties = {
  background: '#fff',
  borderRadius: 8,
  padding: '2rem',
  minWidth: 320,
  maxWidth: '90vw',
  boxShadow: '0 2px 16px rgba(0,0,0,0.2)',
  textAlign: 'center',
};

const buttonStyle: React.CSSProperties = {
  marginTop: '1.5rem',
  padding: '0.5rem 1.5rem',
  background: '#1976d2',
  color: '#fff',
  border: 'none',
  borderRadius: 4,
  fontSize: 16,
  cursor: 'pointer',
};

const SessionTimeoutModal: React.FC<SessionTimeoutModalProps> = ({ show, onLoginAgain }) => {
  if (!show) return null;
  return (
    <div style={backdropStyle}>
      <div style={modalStyle}>
        <h2 style={{ marginBottom: 16 }}>Session Timed Out</h2>
        <div style={{ marginBottom: 24 }}>
          Your session has timed out due to inactivity. Please login again to continue.
        </div>
        <button style={buttonStyle} onClick={onLoginAgain}>
          Login Again
        </button>
      </div>
    </div>
  );
};

export default SessionTimeoutModal; 