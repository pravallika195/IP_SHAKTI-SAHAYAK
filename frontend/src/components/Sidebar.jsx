import React from 'react';
import { NavLink } from 'react-router-dom';
import { 
  Home, 
  Lightbulb, 
  FileText, 
  Bot, 
  Sparkles, 
  ShieldCheck,
  FolderKanban
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Sidebar() {
  const { isAuthenticated } = useAuth();

  const navItems = [
    { to: '/', label: 'Home', icon: Home, end: true },
    ...(isAuthenticated ? [{ to: '/my-innovations', label: 'My Innovations', icon: FolderKanban }] : []),
    { to: '/innovation', label: 'Innovation Submission', icon: Lightbulb },
    { to: '/report', label: 'Analysis Report', icon: FileText },
    { to: '/assistant', label: 'Patent Assistant', icon: Bot },
  ];

  return (
    <aside className="app-sidebar">
      <div className="sidebar-header">
        <NavLink to="/" className="brand-badge">
          <Sparkles className="icon-logo" size={22} />
          <span>IP-SAKTI Sahayak</span>
        </NavLink>
        <p className="brand-tagline">AYUSH Prior-Art & Patent Research</p>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `nav-link-item ${isActive ? 'active' : ''}`
              }
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '6px' }}>
          <ShieldCheck size={14} color="#6366f1" />
          <span style={{ fontWeight: 600 }}>Pre-Patent Analysis</span>
        </div>
        <p>IP-SHAKTI SAHAYAK</p>
      </div>
    </aside>
  );
}
