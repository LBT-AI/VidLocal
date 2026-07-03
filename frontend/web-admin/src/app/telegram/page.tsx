'use client';

import { useEffect, useState } from 'react';

interface Job {
  id: string;
  status: string;
  progress: number;
  ai_title: string | null;
  source_url: string | null;
  metadata_status: string;
  glossary_status: string | null;
  thumbnail_status: string;
  created_at: string;
}

type Tab = 'dashboard' | 'jobs' | 'glossary' | 'settings';

export default function TelegramMiniApp() {
  const [tab, setTab] = useState<Tab>('dashboard');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [tg, setTg] = useState<any>(null);

  useEffect(() => {
    const webapp = (window as any).Telegram?.WebApp;
    if (webapp) {
      webapp.ready();
      webapp.expand();
      webapp.enableClosingConfirmation();
      setTg(webapp);
    }
    fetchJobs();
  }, []);

  async function fetchJobs() {
    try {
      const res = await fetch(`/api/jobs?limit=10`);
      const data = await res.json();
      setJobs(Array.isArray(data) ? data : data.jobs || []);
    } catch { }
  }

  async function sendCommand(cmd: string) {
    if (tg) {
      tg.sendData(cmd);
    }
  }

  function statusIcon(status: string) {
    const icons: Record<string, string> = {
      pending: '⏳', processing: '🔄', completed: '✅',
      approved: '✅', generated: '✅', failed: '❌',
      cancelled: '⛔', skipped: '⏭️', rejected: '⛔',
    };
    return icons[status] || '⏳';
  }

  function ProgressBar({ pct }: { pct: number }) {
    return (
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
    );
  }

  function TabBar() {
    const tabs: { key: Tab; label: string; icon: string }[] = [
      { key: 'dashboard', label: 'Dashboard', icon: '📊' },
      { key: 'jobs', label: 'Jobs', icon: '📋' },
      { key: 'glossary', label: 'Glossary', icon: '📖' },
      { key: 'settings', label: 'Settings', icon: '⚙️' },
    ];
    return (
      <div className="tab-bar">
        {tabs.map(t => (
          <button key={t.key} className={`tab-item ${tab === t.key ? 'active' : ''}`}
            onClick={() => setTab(t.key)}>
            <span className="tab-icon">{t.icon}</span>
            <span className="tab-label">{t.label}</span>
          </button>
        ))}
      </div>
    );
  }

  function DashboardTab() {
    const active = jobs.filter(j => j.status === 'processing' || j.status === 'pending');
    const done = jobs.filter(j => j.status === 'completed' || j.status === 'approved');
    return (
      <div className="tab-content">
        <div className="stats-row">
          <div className="stat-card">
            <span className="stat-num">{active.length}</span>
            <span className="stat-label">Active</span>
          </div>
          <div className="stat-card">
            <span className="stat-num">{done.length}</span>
            <span className="stat-label">Completed</span>
          </div>
          <div className="stat-card">
            <span className="stat-num">{jobs.length}</span>
            <span className="stat-label">Total</span>
          </div>
        </div>
        <h3 className="section-title">Active Jobs</h3>
        {active.length === 0 ? (
          <div className="empty-state">No active jobs</div>
        ) : (
          active.map(j => (
            <div key={j.id} className="job-card" onClick={() => sendCommand(`/status ${j.id}`)}>
              <div className="job-card-header">
                <span className="job-title">{j.ai_title || 'Untitled'}</span>
                <span className="job-status">{statusIcon(j.status)}</span>
              </div>
              <div className="job-meta">
                <span className="job-id">#{j.id.slice(0, 8)}</span>
                <span className="job-source">{j.source_url?.slice(0, 30) || 'N/A'}</span>
              </div>
              <ProgressBar pct={j.progress} />
              <div className="job-progress-text">{j.progress}%</div>
            </div>
          ))
        )}
      </div>
    );
  }

  function JobsTab() {
    return (
      <div className="tab-content">
        <h3 className="section-title">All Jobs</h3>
        {jobs.length === 0 ? (
          <div className="empty-state">No jobs yet</div>
        ) : (
          jobs.map(j => (
            <div key={j.id} className="job-card" onClick={() => sendCommand(`/status ${j.id}`)}>
              <div className="job-card-header">
                <span className="job-title">{j.ai_title || 'Untitled'}</span>
                <span className="job-status">
                  {statusIcon(j.status)} {j.progress}%
                </span>
              </div>
              <div className="job-meta">
                <span className="job-id">#{j.id.slice(0, 8)}</span>
                <span>{j.metadata_status}</span>
                <span>{j.thumbnail_status}</span>
              </div>
              <ProgressBar pct={j.progress} />
            </div>
          ))
        )}
      </div>
    );
  }

  function GlossaryTab() {
    return (
      <div className="tab-content">
        <h3 className="section-title">Glossary Commands</h3>
        <div className="action-grid">
          {[
            { label: 'List Glossary', cmd: '/list_glossary', icon: '📋' },
            { label: 'Add Entry', cmd: '/add_glossary', icon: '➕' },
            { label: 'Delete Entry', cmd: '/delete_glossary', icon: '🗑️' },
            { label: 'Help', cmd: '/glossary', icon: '📖' },
          ].map(a => (
            <button key={a.cmd} className="action-card" onClick={() => sendCommand(a.cmd)}>
              <span className="action-icon">{a.icon}</span>
              <span className="action-label">{a.label}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  function SettingsTab() {
    return (
      <div className="tab-content">
        <h3 className="section-title">Quick Commands</h3>
        <div className="action-grid">
          {[
            { label: 'Projects', cmd: '/projects', icon: '📂' },
            { label: 'Help', cmd: '/help', icon: '❓' },
            { label: 'Subtitle Status', cmd: '/subs', icon: '📝' },
            { label: 'TTS Status', cmd: '/tts', icon: '🔊' },
          ].map(a => (
            <button key={a.cmd} className="action-card" onClick={() => sendCommand(a.cmd)}>
              <span className="action-icon">{a.icon}</span>
              <span className="action-label">{a.label}</span>
            </button>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <div className="status-bar">
        <span className="status-title">VidLocal</span>
        <span className="status-time">{new Date().toLocaleTimeString()}</span>
      </div>
      <div className="main-content">
        {tab === 'dashboard' && <DashboardTab />}
        {tab === 'jobs' && <JobsTab />}
        {tab === 'glossary' && <GlossaryTab />}
        {tab === 'settings' && <SettingsTab />}
      </div>
      <TabBar />
      <style jsx>{`
        .app-container {
          --bg: #000000;
          --card: #1c1c1e;
          --card-hover: #2c2c2e;
          --text: #ffffff;
          --text-secondary: #8e8e93;
          --accent: #0a84ff;
          --green: #30d158;
          --orange: #ff9f0a;
          --red: #ff453a;
          --radius: 12px;
          font-family: -apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Segoe UI', system-ui, sans-serif;
          background: var(--bg);
          color: var(--text);
          min-height: 100vh;
          max-width: 100vw;
          overflow-x: hidden;
          padding: 0;
          margin: 0;
        }
        .status-bar {
          position: sticky;
          top: 0;
          z-index: 10;
          background: var(--bg);
          padding: 12px 16px 8px;
          display: flex;
          justify-content: space-between;
          align-items: center;
          border-bottom: 0.5px solid rgba(255,255,255,0.1);
        }
        .status-title {
          font-size: 17px;
          font-weight: 700;
          letter-spacing: -0.4px;
        }
        .status-time {
          font-size: 13px;
          color: var(--text-secondary);
        }
        .main-content {
          padding: 12px 16px;
          padding-bottom: 80px;
        }
        .tab-content {
          animation: fadeIn 0.2s ease;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .stats-row {
          display: flex;
          gap: 8px;
          margin-bottom: 20px;
        }
        .stat-card {
          flex: 1;
          background: var(--card);
          border-radius: var(--radius);
          padding: 14px 12px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
        }
        .stat-num {
          font-size: 28px;
          font-weight: 700;
          letter-spacing: -0.5px;
        }
        .stat-label {
          font-size: 12px;
          color: var(--text-secondary);
          font-weight: 500;
        }
        .section-title {
          font-size: 15px;
          font-weight: 600;
          margin: 16px 0 8px;
          color: var(--text-secondary);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .job-card {
          background: var(--card);
          border-radius: var(--radius);
          padding: 14px;
          margin-bottom: 8px;
          cursor: pointer;
          transition: background 0.15s;
        }
        .job-card:active {
          background: var(--card-hover);
        }
        .job-card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 6px;
        }
        .job-title {
          font-size: 15px;
          font-weight: 600;
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .job-status {
          font-size: 13px;
          margin-left: 8px;
        }
        .job-meta {
          display: flex;
          gap: 12px;
          font-size: 12px;
          color: var(--text-secondary);
          margin-bottom: 8px;
        }
        .job-id {
          font-family: 'SF Mono', monospace;
          color: var(--accent);
        }
        .progress-track {
          height: 4px;
          background: rgba(255,255,255,0.1);
          border-radius: 2px;
          overflow: hidden;
        }
        .progress-fill {
          height: 100%;
          background: var(--accent);
          border-radius: 2px;
          transition: width 0.5s ease;
        }
        .job-progress-text {
          font-size: 11px;
          color: var(--text-secondary);
          margin-top: 4px;
          text-align: right;
        }
        .empty-state {
          text-align: center;
          padding: 40px 0;
          color: var(--text-secondary);
          font-size: 14px;
        }
        .action-grid {
          display: grid;
          grid-template-columns: 1fr 1fr;
          gap: 8px;
        }
        .action-card {
          background: var(--card);
          border: none;
          border-radius: var(--radius);
          padding: 16px 12px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 8px;
          cursor: pointer;
          color: var(--text);
          font-size: 13px;
          transition: background 0.15s;
        }
        .action-card:active {
          background: var(--card-hover);
        }
        .action-icon {
          font-size: 24px;
        }
        .action-label {
          font-weight: 500;
        }
        .tab-bar {
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          background: rgba(0,0,0,0.95);
          backdrop-filter: blur(20px);
          -webkit-backdrop-filter: blur(20px);
          border-top: 0.5px solid rgba(255,255,255,0.1);
          display: flex;
          justify-content: space-around;
          padding: 6px 0 12px;
          z-index: 20;
        }
        .tab-item {
          background: none;
          border: none;
          color: var(--text-secondary);
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 2px;
          cursor: pointer;
          padding: 4px 12px;
          transition: color 0.15s;
        }
        .tab-item.active {
          color: var(--accent);
        }
        .tab-icon {
          font-size: 22px;
        }
        .tab-label {
          font-size: 10px;
          font-weight: 500;
        }
      `}</style>
    </div>
  );
}
