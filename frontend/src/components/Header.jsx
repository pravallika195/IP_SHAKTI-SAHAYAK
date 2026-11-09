import React, { useEffect, useState } from 'react';
import { useLocation, Link, useNavigate } from 'react-router-dom';
import { Activity, AlertCircle, User, LogOut, LogIn, UserPlus } from 'lucide-react';
import { getHealth } from '../api/client';
import { useAuth } from '../context/AuthContext';

export default function Header() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuth();
  const [healthStatus, setHealthStatus] = useState({ loading: true, online: false, error: null });

  useEffect(() => {
    let isMounted = true;
    getHealth()
      .then((data) => {
        if (isMounted) {
          setHealthStatus({ loading: false, online: data.status === 'ok', error: null });
        }
      })
      .catch((err) => {
        if (isMounted) {
          setHealthStatus({ loading: false, online: false, error: err.message });
        }
      });
    return () => { isMounted = false; };
  }, []);

  // Determine current page title
  const getPageTitle = () => {
    switch (location.pathname) {
      case '/':
        return 'National AYUSH Prior-Art & Patent Research';
      case '/my-innovations':
        return 'My Innovation Workspaces';
      case '/innovation':
        return 'Innovation Submission & Evaluation';
      case '/report':
        return 'Prior-Art Analysis Report';
      case '/assistant':
        return 'Conversational Patent Assistant';
      case '/login':
        return 'Researcher Sign In';
      case '/register':
        return 'Researcher Registration';
      default:
        return 'IP-SAKTI Sahayak';
    }
  };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <header className="app-header">
      <div className="header-title-section">
        <h2 style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)' }}>
          {getPageTitle()}
        </h2>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
        {/* User Auth Section */}
        {isAuthenticated && user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div
                style={{
                  width: '32px',
                  height: '32px',
                  borderRadius: '50%',
                  backgroundColor: 'var(--accent-glow)',
                  border: '1px solid rgba(99, 102, 241, 0.3)',
                  color: 'var(--accent-secondary)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontWeight: 600,
                  fontSize: '0.85rem',
                }}
              >
                {user.full_name ? user.full_name.charAt(0).toUpperCase() : 'U'}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1.2 }}>
                  {user.full_name}
                </span>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  {user.role}
                </span>
              </div>
            </div>

            <button
              onClick={handleLogout}
              className="btn btn-secondary"
              title="Sign Out"
              style={{ fontSize: '0.78rem', padding: '6px 10px', marginLeft: '6px' }}
            >
              <LogOut size={14} />
              <span>Sign Out</span>
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Link to="/login" className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '6px 12px' }}>
              <LogIn size={14} />
              <span>Sign In</span>
            </Link>
            <Link to="/register" className="btn btn-primary" style={{ fontSize: '0.8rem', padding: '6px 12px' }}>
              <UserPlus size={14} />
              <span>Register</span>
            </Link>
          </div>
        )}
      </div>
    </header>
  );
}
