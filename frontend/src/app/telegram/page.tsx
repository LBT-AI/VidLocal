'use client';

import { useEffect, useState, useRef } from 'react';

interface Job {
  id: string;
  platform: string;
  status: string;
  progress: number;
  title: string;
  url?: string | null;
  source_url?: string | null;
  metadata_status: string;
  glossary_status: string | null;
  thumbnail_status: string;
  created_at?: string;
  created_time: string;
  updated_at?: string | null;
  error_message?: string | null;
  error_code?: string | null;
  youtube_url?: string | null;
  current_step: string;
  review_state: string;
  stage_progress: number;
  steps?: Record<string, { status: string; progress: number }>;
  transcript?: string | null;
  glossary?: any[] | null;
  metadata?: any | null;
  files?: any[];
  thumbnail?: any | null;
}

type Tab = 'dashboard' | 'jobs' | 'settings';

export default function TelegramMiniApp() {
  const [tab, setTab] = useState<Tab>('dashboard');
  const [jobs, setJobs] = useState<Job[]>([]);
  const [tg, setTg] = useState<any>(null);
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [newJobUrl, setNewJobUrl] = useState('');
  const [newJobPlatform, setNewJobPlatform] = useState('facebook');
  const [isCreating, setIsCreating] = useState(false);
  const [glossaryItems, setGlossaryItems] = useState<any[]>([]);
  const jobsRef = useRef<Job[]>([]);

  useEffect(() => {
    if (selectedJobId) {
      fetchGlossary(selectedJobId);
    } else {
      setGlossaryItems([]);
    }
  }, [selectedJobId]);

  async function fetchGlossary(jobId: string) {
    try {
      const headers: Record<string, string> = {};
      if ((window as any).Telegram?.WebApp?.initData) {
         headers['Authorization'] = `tma ${(window as any).Telegram.WebApp.initData}`;
      }
      const res = await fetch(`/api/video-jobs/${jobId}/glossary`, { headers });
      if (res.ok) {
        const data = await res.json();
        setGlossaryItems(data);
      }
    } catch (err) {
      console.error("Failed to fetch glossary", err);
    }
  }

  async function saveGlossaryItem(item: any) {
    if (!selectedJobId) return;
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if ((window as any).Telegram?.WebApp?.initData) {
         headers['Authorization'] = `tma ${(window as any).Telegram.WebApp.initData}`;
      }
      const res = await fetch(`/api/video-jobs/${selectedJobId}/glossary/item`, {
        method: 'POST',
        headers,
        body: JSON.stringify(item),
      });
      if (res.ok) {
        fetchGlossary(selectedJobId);
      }
    } catch (err) {
      console.error("Failed to save glossary item", err);
    }
  }

  async function deleteGlossaryItem(itemId: string) {
    if (!selectedJobId) return;
    try {
      const headers: Record<string, string> = {};
      if ((window as any).Telegram?.WebApp?.initData) {
         headers['Authorization'] = `tma ${(window as any).Telegram.WebApp.initData}`;
      }
      const res = await fetch(`/api/video-jobs/${selectedJobId}/glossary/item/${itemId}`, {
        method: 'DELETE',
        headers,
      });
      if (res.ok) {
        fetchGlossary(selectedJobId);
      }
    } catch (err) {
      console.error("Failed to delete glossary item", err);
    }
  }

  async function addGlossaryItem() {
    if (!selectedJobId) return;
    const newItem = {
      category: 'character',
      source_name: 'Tên gốc',
      target_name: 'Dịch Việt',
      pronoun_style: 'ta',
      family_clan: '',
      role: '',
      approved: true
    };
    await saveGlossaryItem(newItem);
  }

  useEffect(() => {
    const webapp = (window as any).Telegram?.WebApp;
    if (webapp && webapp.initData) {
      webapp.ready();
      webapp.expand();
      webapp.enableClosingConfirmation();
      setTg(webapp);
      
      const uid = webapp.initDataUnsafe?.user?.id;
      if (uid && uid.toString() === "1208342332") {
        setIsAdmin(true);
      } else {
        setIsAdmin(false);
      }
    } else {
      if (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') {
        setIsAdmin(true);
      } else {
        setIsAdmin(false);
      }
    }
    fetchJobs();
  }, []);

  useEffect(() => {
    const timer = window.setInterval(fetchJobs, 3000);
    return () => window.clearInterval(timer);
  }, []);

  async function fetchJobs() {
    try {
      const headers: Record<string, string> = {};
      if ((window as any).Telegram?.WebApp?.initData) {
         headers['Authorization'] = `tma ${(window as any).Telegram.WebApp.initData}`;
      }
      const res = await fetch(`/api/video-jobs`, { headers });
      const data = await res.json();
      const newJobs = Array.isArray(data) ? data : data.data || [];
      
      const newJobs = Array.isArray(data) ? data : data.data || [];
      
      // Update ref and state using id+status+progress for stable diff
      const currentHash = jobsRef.current.map(j => `${j.id}-${j.status}-${j.progress}`).join('|');
      const newHash = newJobs.map((j: Job) => `${j.id}-${j.status}-${j.progress}`).join('|');
      
      if (currentHash !== newHash) {
         jobsRef.current = newJobs;
         setJobs(newJobs);
      }
    } catch (e) { 
      console.error(e);
    } finally {
      setIsLoading(false);
    }
  }

  async function createJob() {
    if (!newJobUrl.trim()) {
       if (tg) tg.showAlert('Vui lòng nhập link!');
       else alert('Vui lòng nhập link!');
       return;
    }
    setIsCreating(true);
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (tg?.initData) headers['Authorization'] = `tma ${tg.initData}`;
      
      const res = await fetch(`/api/video-jobs`, {
         method: 'POST',
         headers,
         body: JSON.stringify({ url: newJobUrl, platform: newJobPlatform })
      });
      
      if (res.ok) {
        if (tg) tg.HapticFeedback.notificationOccurred('success');
        setNewJobUrl('');
        await fetchJobs();
      } else {
        const txt = await res.text();
        if (tg) tg.showAlert('Lỗi: ' + txt);
        else alert('Lỗi: ' + txt);
      }
    } catch(e) {
      if (tg) tg.showAlert('Lỗi kết nối');
    } finally {
      setIsCreating(false);
    }
  }

  async function doAction(jobId: string, action: string) {
    setActionLoading(true);
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' };
      if (tg?.initData) headers['Authorization'] = `tma ${tg.initData}`;
      
      const res = await fetch(`/api/video-jobs/${jobId}/${action}`, { 
        method: 'POST',
        headers
      });
      if (res.ok) {
        if (tg) tg.HapticFeedback.notificationOccurred('success');
        await fetchJobs();
      } else {
        const txt = await res.text();
        if (tg) tg.showAlert('Lỗi: ' + txt);
        else alert('Lỗi: ' + txt);
      }
    } catch(e) {
      if (tg) tg.showAlert('Lỗi kết nối');
    } finally {
      setActionLoading(false);
    }
  }

  function jobTitle(job: Job) {
    return job.title || 'Không tiêu đề';
  }

  function isActive(job: Job) {
    return ['pending', 'downloading', 'processing', 'transcribing', 'metadata_generating', 'watermarking', 'uploading_youtube', 'extracting_characters'].includes(job.status);
  }

  function friendlyError(job: Job) {
    if (job.error_code === 'facebook_no_formats') {
      return 'Không tìm thấy video format. Có thể link private hoặc cần cookie.';
    }
    if (job.error_code === 'facebook_video_id_not_found') {
      return 'Không tìm thấy video ID từ link Facebook';
    }
    if (job.error_code?.startsWith('douyin_')) {
      return 'Link Douyin này không tải được. Có thể video bị giới hạn hoặc cần cookie.';
    }
    return job.error_message || null;
  }

  function platformLabel(job: Job) {
    const labels: Record<string, string> = {
      douyin: 'Douyin',
      bilibili: 'Bilibili',
      facebook: 'Facebook',
      tiktok: 'TikTok',
    };
    return labels[job.platform || ''] || job.platform || 'Video';
  }

  function statusText(status: string, job?: Job) {
    if (status === 'pending') return 'Chờ xử lý';
    if (status === 'completed') return 'Hoàn tất';
    if (status === 'failed') return 'Lỗi';
    
    if (status === 'waiting_review') {
      if (job?.review_state === 'waiting_srt') return 'Chờ duyệt phụ đề';
      if (job?.review_state === 'waiting_glossary') return 'Chờ duyệt glossary';
      if (job?.review_state === 'waiting_upload') return 'Chờ duyệt upload';
      return 'Chờ duyệt';
    }
    
    if (status === 'running') {
      if (job?.current_step === 'download') return 'Đang tải video';
      if (job?.current_step === 'transcribe') return 'Đang trích phụ đề';
      if (job?.current_step === 'character_extract') return 'Đang phân tích nhân vật';
      if (job?.current_step === 'seo_metadata') return 'Đang tối ưu SEO';
      if (job?.current_step === 'watermark') return 'Đang thêm watermark';
      if (job?.current_step === 'upload') return 'Đang upload YouTube';
      return 'Đang xử lý';
    }
    
    return 'Đang xử lý';
  }

  function statusIcon(status: string, job?: Job) {
    if (status === 'completed') return '✅';
    if (status === 'failed') return '❌';
    if (status === 'pending') return '🕒';
    if (status === 'waiting_review') return '⏳';
    return '🔄';
  }

  function ProgressBar({ pct }: { pct: number }) {
    return (
      <div className="progress-track">
        <div className="progress-fill" style={{ width: `${pct}%` }} />
      </div>
    );
  }

  function getJobSteps(job: Job) {
    const s = job.steps || {};
    const getPct = (key: string) => s[key]?.progress || 0;
    
    return [
      { label: 'Download', pct: getPct('download') },
      { label: 'Transcript', pct: getPct('transcribe') },
      { label: 'Glossary', pct: getPct('character_extract') },
      { label: 'SEO', pct: getPct('seo_metadata') },
      { label: 'Render', pct: getPct('watermark') },
      { label: 'Upload', pct: getPct('upload') }
    ];
  }

  if (isAdmin === false) {
    return (
      <div className="app-container flex-center">
        <div className="empty-state">
          <h3>Access Denied</h3>
          <p>Chỉ Quản trị viên mới có thể truy cập Mini App này.</p>
        </div>
        <style jsx>{`
          .app-container { background: #000; color: #fff; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
          .empty-state { text-align: center; }
        `}</style>
      </div>
    );
  }

  function TabBar() {
    const tabs: { key: Tab; label: string; icon: string }[] = [
      { key: 'dashboard', label: 'Studio', icon: '📊' },
      { key: 'jobs', label: 'Tệp', icon: '📋' },
      { key: 'settings', label: 'Quản trị', icon: '⚙️' },
    ];
    return (
      <div className="tab-bar">
        {tabs.map(t => (
          <button key={t.key} className={`tab-item ${tab === t.key ? 'active' : ''}`}
            onClick={() => { setTab(t.key); setSelectedJobId(null); }}>
            <span className="tab-icon">{t.icon}</span>
            <span className="tab-label">{t.label}</span>
          </button>
        ))}
      </div>
    );
  }

  function JobDetail() {
    const job = jobs.find(j => j.id === selectedJobId);
    if (!job) {
      return (
        <div className="tab-content">
          <div className="empty-state">
            <p>Job không tồn tại hoặc đã bị xóa.</p>
            <button className="back-btn" onClick={() => setSelectedJobId(null)} style={{marginTop: 10}}>⬅ Trở lại</button>
          </div>
        </div>
      );
    }
    
    const steps = getJobSteps(job);
    return (
      <div className="tab-content">
        <button className="back-btn" onClick={() => setSelectedJobId(null)}>⬅ Trở lại</button>
        <h3 className="section-title detail-title">{jobTitle(job)}</h3>
        <div className="job-meta">
          <span className="job-id">#{job.id.slice(0, 8)}</span>
          <span>{platformLabel(job)}</span>
          <span className="job-status">{statusIcon(job.status, job)} {statusText(job.status, job)}</span>
        </div>
        
        <div className="stepper">
          {steps.map(s => (
            <div key={s.label} className="step-item">
              <div className="step-header">
                <span className="step-label">{s.label}</span>
                <span className="step-pct">{s.pct}%</span>
              </div>
              <ProgressBar pct={s.pct} />
            </div>
          ))}
        </div>

        <div className="job-logs">
           <h4 className="logs-title">Trạng thái</h4>
           <div className="logs-content">
             {friendlyError(job) || `Tiến trình tổng: ${job.progress}%\nTrạng thái hiện tại: ${statusText(job.status)}`}
             {job.youtube_url && (
             </div>
        </div>

        {/* Transcript / SRT Preview */}
        {job.transcript && (
          <div className="job-logs" style={{ marginTop: '16px' }}>
            <h4 className="logs-title">Bản dịch phụ đề gốc (STT)</h4>
            <div className="transcript-box" style={{ 
              maxHeight: '150px', 
              overflowY: 'auto', 
              fontSize: '13px', 
              color: 'var(--text)', 
              background: '#000', 
              padding: '10px', 
              borderRadius: '8px', 
              fontFamily: 'monospace',
              whiteSpace: 'pre-wrap'
            }}>
              {job.transcript}
            </div>
            {job.transcript_srt_path && (
              <div style={{ marginTop: '10px', display: 'flex', gap: '8px' }}>
                <a 
                  href={job.transcript_srt_path.replace('/app/data/', '/data/')} 
                  download="raw.srt" 
                  className="action-sub-btn" 
                  style={{ textDecoration: 'none', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', height: '40px', padding: '0 16px', margin: 0, fontSize: '13px' }}
                  target="_blank"
                  rel="noreferrer"
                >
                  📥 Tải raw.srt
                </a>
              </div>
            )}
          </div>
        )}

        {/* Thumbnail & SEO Preview */}
        {(job.thumbnail?.image_url || job.metadata) && (
          <div className="metadata-container">
            {job.thumbnail?.image_url && (
              <div className="thumbnail-preview">
                <img src={job.thumbnail.image_url} alt="Thumbnail" />
              </div>
            )}
            {job.metadata?.ai_title && (
              <div className="metadata-preview">
                <strong>Title:</strong> {job.metadata.ai_title}
                <br/>
                <strong>Tags:</strong> {job.metadata.tags?.join(', ')}
              </div>
            )}
          </div>
        )}

        {/* Glossary Editor */}
        {job.status === 'waiting_review' && job.review_state === 'waiting_glossary' && (
          <div className="glossary-editor-card" style={{
            background: 'rgba(255,255,255,0.03)',
            borderRadius: '12px',
            padding: '16px',
            marginBottom: '16px',
            border: '1px solid rgba(255,255,255,0.06)'
          }}>
            <h4 style={{ margin: '0 0 12px 0', fontSize: '15px', color: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span>📖 Bảng Thuật Ngữ (Glossary)</span>
              <button 
                onClick={addGlossaryItem}
                style={{
                  background: 'rgba(74, 222, 128, 0.15)',
                  border: 'none',
                  color: '#4ade80',
                  padding: '4px 10px',
                  borderRadius: '6px',
                  fontSize: '12px',
                  cursor: 'pointer'
                }}
              >
                ➕ Thêm
              </button>
            </h4>
            
            {glossaryItems.length === 0 ? (
              <div style={{ color: 'rgba(255,255,255,0.4)', fontSize: '13px', textAlign: 'center', padding: '10px 0' }}>
                Không tìm thấy thuật ngữ nào.
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', maxHeight: '300px', overflowY: 'auto', paddingRight: '4px' }}>
                {glossaryItems.map((item, idx) => (
                  <div key={item.id || idx} style={{
                    background: 'rgba(0,0,0,0.2)',
                    borderRadius: '8px',
                    padding: '10px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                    borderLeft: item.approved ? '3px solid #4ade80' : '3px solid rgba(255,255,255,0.2)'
                  }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '8px' }}>
                      <span style={{ fontWeight: 'bold', fontSize: '13px', color: '#fff' }}>{item.source_name}</span>
                      <button 
                        onClick={() => deleteGlossaryItem(item.id)}
                        style={{ background: 'none', border: 'none', color: '#f87171', fontSize: '14px', cursor: 'pointer', padding: '0 2px' }}
                        title="Xóa"
                      >
                        🗑
                      </button>
                    </div>
                    
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                      <div>
                        <label style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', display: 'block', marginBottom: '2px' }}>Dịch Việt</label>
                        <input 
                          type="text"
                          value={item.target_name}
                          onChange={(e) => {
                            const updated = [...glossaryItems];
                            updated[idx].target_name = e.target.value;
                            setGlossaryItems(updated);
                          }}
                          onBlur={() => saveGlossaryItem(item)}
                          style={{
                            width: '100%',
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: '4px',
                            color: '#fff',
                            padding: '4px 8px',
                            fontSize: '12px'
                          }}
                        />
                      </div>
                      
                      <div>
                        <label style={{ fontSize: '10px', color: 'rgba(255,255,255,0.4)', display: 'block', marginBottom: '2px' }}>Xưng Hô</label>
                        <select
                          value={item.pronoun_style || ''}
                          onChange={(e) => {
                            const updated = [...glossaryItems];
                            updated[idx].pronoun_style = e.target.value;
                            setGlossaryItems(updated);
                            saveGlossaryItem(updated[idx]);
                          }}
                          style={{
                            width: '100%',
                            background: 'rgba(255,255,255,0.05)',
                            border: '1px solid rgba(255,255,255,0.1)',
                            borderRadius: '4px',
                            color: '#fff',
                            padding: '4px 4px',
                            fontSize: '12px',
                            height: '26px'
                          }}
                        >
                          <option value="">(Bản gốc)</option>
                          <option value="ta">ta / ngươi</option>
                          <option value="tôi">tôi / bạn</option>
                          <option value="hắn">hắn</option>
                          <option value="nàng">nàng</option>
                          <option value="tỷ">tỷ / muội</option>
                          <option value="huynh">huynh / đệ</option>
                          <option value="ông">ông / bà</option>
                        </select>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <input 
                        type="checkbox"
                        checked={item.approved}
                        onChange={(e) => {
                          const updated = [...glossaryItems];
                          updated[idx].approved = e.target.checked;
                          setGlossaryItems(updated);
                          saveGlossaryItem(updated[idx]);
                        }}
                        id={`gloss-approve-${item.id}`}
                      />
                      <label htmlFor={`gloss-approve-${item.id}`} style={{ fontSize: '11px', color: 'rgba(255,255,255,0.6)', cursor: 'pointer' }}>
                        Duyệt từ này trong bản dịch
                      </label>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Workflow Actions */}
        <div className="actions-container">
          {job.status === 'waiting_review' && job.review_state === 'waiting_srt' && (
            <div className="action-row">
              <button className="action-main-btn" disabled={actionLoading} onClick={() => doAction(job.id, 'approve-srt')}>✅ Duyệt Phụ Đề</button>
              <button className="action-sub-btn error-btn" disabled={actionLoading} style={{ background: 'var(--red)', border: 'none', color: '#fff' }} onClick={() => doAction(job.id, 'retry-srt')}>♻️ Thử lại STT</button>
            </div>
          )}

          {job.status === 'waiting_review' && job.review_state === 'waiting_glossary' && (
            <div className="action-row">
              <button className="action-main-btn" disabled={actionLoading} onClick={() => doAction(job.id, 'approve-glossary')}>✅ Duyệt Glossary</button>
              <button className="action-sub-btn" disabled={actionLoading} onClick={() => doAction(job.id, 'skip-glossary')}>⏭️ Bỏ qua</button>
            </div>
          )}

          {job.status === 'waiting_review' && job.review_state === 'waiting_upload' && (
            <button className="action-main-btn" disabled={actionLoading} onClick={() => doAction(job.id, 'approve-upload')}>✅ Duyệt Upload</button>
          )}

          {job.status === 'failed' && (
            <div className="action-row" style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
              {job.error_code === 'transcription_failed' && (
                <button className="action-main-btn" disabled={actionLoading} onClick={() => doAction(job.id, 'retry-srt')}>♻️ Thử lại riêng STT</button>
              )}
              <button className="action-sub-btn" style={{ width: '100%', borderColor: 'var(--red)', color: 'var(--red)' }} disabled={actionLoading} onClick={() => doAction(job.id, 'retry')}>🔄 Tải & Chạy lại từ đầu</button>
            </div>
          )}
        </div>
      </div>
    );
  }

  function DashboardTab() {
    if (isLoading) {
      return (
        <div className="tab-content flex-center">
          <div className="spinner"></div>
        </div>
      );
    }
    const active = jobs.filter(j => j.status === 'running');
    const waitingReview = jobs.filter(j => j.status === 'waiting_review');
    const doneToday = jobs.filter(j => j.status === 'completed');
    const failed = jobs.filter(j => j.status === 'failed');

    return (
      <div className="tab-content">
        <div className="create-job-card">
          <h3 className="section-title" style={{ marginTop: 0 }}>Tạo Dự Án Mới</h3>
          <div className="create-form">
            <input 
              type="text" 
              placeholder="Dán link (YouTube, Facebook, Douyin...)"
              value={newJobUrl}
              onChange={e => setNewJobUrl(e.target.value)}
              className="job-input"
            />
            <select value={newJobPlatform} onChange={e => setNewJobPlatform(e.target.value)} className="job-select">
              <option value="facebook">Facebook</option>
              <option value="tiktok">TikTok</option>
              <option value="douyin">Douyin</option>
              <option value="bilibili">Bilibili</option>
            </select>
            <button className="create-btn" disabled={isCreating} onClick={createJob}>
              {isCreating ? 'Đang tạo...' : 'Tải Video'}
            </button>
          </div>
        </div>

        {jobs.length === 0 ? (
          <div className="empty-state">Chưa có dự án nào.</div>
        ) : (
          <>
            <div className="stats-row">
              {active.length > 0 && <div className="stat-card"><span className="stat-num">{active.length}</span><span className="stat-label">Đang xử lý</span></div>}
              {waitingReview.length > 0 && <div className="stat-card"><span className="stat-num waiting">{waitingReview.length}</span><span className="stat-label">Chờ duyệt</span></div>}
              {doneToday.length > 0 && <div className="stat-card"><span className="stat-num success">{doneToday.length}</span><span className="stat-label">Hoàn tất</span></div>}
              {failed.length > 0 && <div className="stat-card"><span className="stat-num error">{failed.length}</span><span className="stat-label">Lỗi</span></div>}
            </div>
            
            <h3 className="section-title">Gần đây</h3>
            {jobs.slice(0, 5).map(j => (
              <div key={j.id} className="job-card" onClick={() => setSelectedJobId(j.id)}>
                <div className="job-card-header">
                  <span className="job-title">{jobTitle(j)}</span>
                  <span className="job-status">{statusIcon(j.status, j)}</span>
                </div>
                <div className="job-meta">
                  <span className="job-id">#{j.id.slice(0, 8)}</span>
                  <span>{platformLabel(j)}</span>
                </div>
                <ProgressBar pct={j.progress} />
              </div>
            ))}
          </>
        )}
      </div>
    );
  }

  function JobsTab() {
    if (isLoading) {
      return (
        <div className="tab-content flex-center">
          <div className="spinner"></div>
        </div>
      );
    }
    return (
      <div className="tab-content">
        <h3 className="section-title">Tất cả tệp</h3>
        {jobs.length === 0 ? (
          <div className="empty-state">Không có tệp nào</div>
        ) : (
          jobs.map(j => (
            <div key={j.id} className="job-card" onClick={() => setSelectedJobId(j.id)}>
              <div className="job-card-header">
                <span className="job-title">{jobTitle(j)}</span>
                <span className="job-status">{statusIcon(j.status, j)} {j.progress}%</span>
              </div>
              <div className="job-meta">
                <span className="job-id">#{j.id.slice(0, 8)}</span>
                <span>Nền tảng nguồn: {platformLabel(j)}</span>
                <span>{statusText(j.status, j)}</span>
              </div>
              <ProgressBar pct={j.progress} />
            </div>
          ))
        )}
      </div>
    );
  }

  function SettingsTab() {
    return (
      <div className="tab-content">
        <h3 className="section-title">Hệ thống</h3>
        <div className="settings-group">
          <h4>Mini App & Bot</h4>
          <button className="action-card" onClick={() => window.open('https://t.me/vidlocal_bot', '_blank')}>
             🔗 Mở VidLocal Bot
          </button>
        </div>
        <div className="settings-group">
          <h4>Kênh Theo Dõi (Watch)</h4>
          <button className="action-card">
             📡 Quản lý nguồn Video (Bilibili/Douyin)
          </button>
        </div>
        <div className="settings-group">
          <h4>Dự Án Cũ (Project)</h4>
          <button className="action-card">
             📂 Quản lý phụ đề thủ công
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="app-container">
      <div className="status-bar">
        <span className="status-title">VidLocal Studio</span>
      </div>
      <div className="main-content">
        {selectedJobId ? (
          <JobDetail />
        ) : (
          <>
            {tab === 'dashboard' && <DashboardTab />}
            {tab === 'jobs' && <JobsTab />}
            {tab === 'settings' && <SettingsTab />}
          </>
        )}
      </div>
      {!selectedJobId && <TabBar />}
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
          padding: 16px 16px 12px;
          display: flex;
          justify-content: center;
          align-items: center;
          border-bottom: 0.5px solid rgba(255,255,255,0.1);
        }
        .status-title {
          font-size: 17px;
          font-weight: 700;
          letter-spacing: -0.4px;
        }
        .main-content {
          padding: 16px;
          padding-bottom: 90px;
        }
        .tab-content {
          animation: fadeIn 0.2s ease;
        }
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .flex-center {
          display: flex;
          justify-content: center;
          align-items: center;
          min-height: 50vh;
        }
        .spinner {
          width: 30px;
          height: 30px;
          border: 3px solid rgba(255,255,255,0.1);
          border-top-color: var(--accent);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        @keyframes spin { 100% { transform: rotate(360deg); } }
        .stats-row {
          display: flex;
          flex-wrap: wrap;
          gap: 10px;
          margin-bottom: 24px;
        }
        .stat-card {
          flex: 1;
          min-width: 40%;
          background: var(--card);
          border-radius: var(--radius);
          padding: 16px 12px;
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;
        }
        .stat-num {
          font-size: 32px;
          font-weight: 700;
          letter-spacing: -0.5px;
        }
        .stat-num.waiting { color: var(--orange); }
        .stat-num.success { color: var(--green); }
        .stat-num.error { color: var(--red); }
        .stat-label {
          font-size: 13px;
          color: var(--text-secondary);
          font-weight: 500;
        }
        .section-title {
          font-size: 14px;
          font-weight: 600;
          margin: 20px 0 12px;
          color: var(--text-secondary);
          text-transform: uppercase;
          letter-spacing: 0.5px;
        }
        .job-card {
          background: var(--card);
          border-radius: var(--radius);
          padding: 16px;
          margin-bottom: 12px;
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
          margin-bottom: 8px;
        }
        .job-title {
          font-size: 16px;
          font-weight: 600;
          flex: 1;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .job-status {
          font-size: 14px;
          margin-left: 12px;
          color: var(--text-secondary);
        }
        .job-meta {
          display: flex;
          gap: 12px;
          font-size: 13px;
          color: var(--text-secondary);
          margin-bottom: 12px;
        }
        .job-id {
          font-family: 'SF Mono', monospace;
          color: var(--accent);
        }
        .progress-track {
          height: 6px;
          background: rgba(255,255,255,0.1);
          border-radius: 3px;
          overflow: hidden;
        }
        .progress-fill {
          height: 100%;
          background: var(--accent);
          border-radius: 3px;
          transition: width 0.5s ease;
        }
        .empty-state {
          text-align: center;
          padding: 60px 0;
          color: var(--text-secondary);
          font-size: 15px;
        }
        .settings-group {
          margin-bottom: 24px;
        }
        .settings-group h4 {
          font-size: 15px;
          color: var(--text);
          margin-bottom: 10px;
          font-weight: 600;
        }
        .action-card {
          background: var(--card);
          border: none;
          border-radius: var(--radius);
          padding: 16px;
          width: 100%;
          text-align: left;
          color: var(--text);
          font-size: 15px;
          margin-bottom: 8px;
          cursor: pointer;
        }
        .action-card:active {
          background: var(--card-hover);
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
          padding: 10px 0 24px;
          z-index: 20;
        }
        .tab-item {
          background: none;
          border: none;
          color: var(--text-secondary);
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 4px;
          cursor: pointer;
          padding: 4px 20px;
        }
        .tab-item.active {
          color: var(--accent);
        }
        .tab-icon {
          font-size: 24px;
        }
        .tab-label {
          font-size: 11px;
          font-weight: 500;
        }
        .back-btn {
          background: none;
          border: none;
          color: var(--accent);
          font-size: 16px;
          padding: 0 0 16px 0;
          cursor: pointer;
          font-weight: 500;
        }
        .detail-title {
          font-size: 20px;
          color: var(--text);
          margin: 0 0 12px 0;
          text-transform: none;
        }
        .stepper {
          background: var(--card);
          border-radius: var(--radius);
          padding: 16px;
          margin-top: 20px;
          display: flex;
          flex-direction: column;
          gap: 16px;
        }
        .step-item {
          display: flex;
          flex-direction: column;
          gap: 8px;
        }
        .step-header {
          display: flex;
          justify-content: space-between;
          font-size: 14px;
          font-weight: 500;
        }
        .step-pct {
          color: var(--text-secondary);
        }
        .job-logs {
          background: var(--card);
          border-radius: var(--radius);
          padding: 16px;
          margin-top: 16px;
        }
        .logs-title {
          font-size: 14px;
          color: var(--text-secondary);
          margin: 0 0 8px 0;
          font-weight: 600;
        }
        .logs-content {
          font-size: 13px;
          line-height: 1.5;
          font-family: 'SF Mono', monospace;
          color: var(--green);
          white-space: pre-wrap;
        }
        .actions-container {
          margin-top: 24px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .action-row {
          display: flex;
          gap: 12px;
        }
        .action-main-btn {
          flex: 2;
          background: var(--accent);
          color: white;
          border: none;
          border-radius: var(--radius);
          padding: 16px;
          font-size: 16px;
          font-weight: 600;
          cursor: pointer;
        }
        .action-main-btn:disabled {
          opacity: 0.6;
        }
        .action-sub-btn {
          flex: 1;
          background: var(--card);
          color: white;
          border: 1px solid rgba(255,255,255,0.1);
          border-radius: var(--radius);
          padding: 16px;
          font-size: 14px;
          font-weight: 600;
          cursor: pointer;
        }
        .action-sub-btn:disabled {
          opacity: 0.6;
        }
        .error-btn {
          background: var(--red);
        }
        .create-job-card {
          background: var(--card);
          border-radius: var(--radius);
          padding: 16px;
          margin-bottom: 20px;
        }
        .create-form {
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .job-input, .job-select {
          background: #000;
          border: 1px solid rgba(255,255,255,0.1);
          color: #fff;
          padding: 12px;
          border-radius: 8px;
          font-size: 14px;
        }
        .create-btn {
          background: var(--green);
          color: #000;
          border: none;
          padding: 12px;
          border-radius: 8px;
          font-weight: 700;
          font-size: 15px;
          cursor: pointer;
        }
        .create-btn:disabled {
          opacity: 0.6;
        }
        .metadata-container {
          margin-top: 16px;
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .thumbnail-preview img {
          width: 100%;
          border-radius: 8px;
          object-fit: cover;
        }
        .metadata-preview {
          background: var(--card);
          border-radius: 8px;
          padding: 12px;
          font-size: 13px;
          color: var(--text-secondary);
          line-height: 1.5;
        }
        .metadata-preview strong {
          color: var(--text);
        }
      `}</style>
    </div>
  );
}
