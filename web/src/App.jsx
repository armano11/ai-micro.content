import { useState, useEffect } from 'react';
import { Play, FileJson, Clapperboard, ChevronRight, Download, Activity, Users, Globe, Clock, RotateCw } from 'lucide-react';
import './index.css';

const BACKEND_URL = 'http://127.0.0.1:8000';

const LANGUAGES = [
  "English", "Hindi", "Spanish", "French", "German",
  "Japanese", "Korean", "Arabic", "Portuguese", "Chinese",
  "Italian", "Russian", "Turkish"
];

const STYLES = [
  "Cinematic", "Anime", "Cyberpunk", "Dark Fantasy",
  "Photorealistic", "Noir", "Watercolor"
];

const VOICES = {
  "Auto (match language)": null,
  "Male — Christopher (en-US)": "en-US-ChristopherNeural",
  "Female — Jenny (en-US)": "en-US-JennyNeural",
  "Male — Madhur (hi-IN)": "hi-IN-MadhurNeural"
};

export default function App() {
  const [projects, setProjects] = useState([]);
  const [currentProject, setCurrentProject] = useState(null);
  const [mode, setMode] = useState('generate');
  const [premise, setPremise] = useState('A stray cat discovers it can talk to the moon and asks for a fish.');
  const [genre, setGenre] = useState('Basic');
  const [language, setLanguage] = useState('English');
  const [voice, setVoice] = useState('Auto (match language)');
  const [style, setStyle] = useState('Cinematic');
  const [customJson, setCustomJson] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchProjects();
    const interval = setInterval(fetchProjects, 5000);
    return () => clearInterval(interval);
  }, []);

  const fetchProjects = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/projects`);
      if (res.ok) {
        const data = await res.json();
        setProjects(data.reverse());
      }
    } catch (err) {
      console.error('Failed to fetch projects', err);
    }
  };

  const loadProject = async (pid) => {
    try {
      const res = await fetch(`${BACKEND_URL}/projects/${pid}`);
      if (res.ok) {
        const data = await res.json();
        setCurrentProject(data);
      }
    } catch (err) {
      console.error('Failed to load project details', err);
    }
  };

  const handleGenerate = async () => {
    setLoading(true);
    setError('');
    setCurrentProject(null);
    try {
      let endpoint = '/generate-project';
      let payload = {
        premise, genre, language, image_style: style,
        voice: VOICES[voice]
      };

      if (mode === 'custom') {
        endpoint = '/custom-story';
        payload.story = JSON.parse(customJson);
        payload.premise = "[Custom]";
      }

      const res = await fetch(`${BACKEND_URL}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      
      if (!res.ok) throw new Error('Generation failed');
      const data = await res.json();
      await loadProject(data.project_id);
      fetchProjects();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleContinue = async () => {
    if (!currentProject) return;
    setLoading(true);
    setError('');
    try {
      const payload = {
        parent_project_id: currentProject.project_id,
        language: currentProject.language || language,
        image_style: style,
        voice: VOICES[voice]
      };
      const res = await fetch(`${BACKEND_URL}/continue-episode`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error('Continuation failed');
      const data = await res.json();
      await loadProject(data.project_id);
      fetchProjects();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <div className="sidebar">
        <h2 className="sidebar-title"><Clapperboard size={24} color="#a78bfa" /> Episodes</h2>
        <div style={{ flex: 1, overflowY: 'auto' }}>
          {projects.length === 0 ? (
            <p className="text-muted" style={{ fontSize: '0.9rem' }}>No episodes yet</p>
          ) : (
            projects.map(pid => (
              <div 
                key={pid} 
                className={`project-item ${currentProject?.project_id === pid ? 'active' : ''}`}
                onClick={() => loadProject(pid)}
              >
                <Play size={16} />
                <span style={{ fontSize: '0.9rem', flex: 1 }}>Episode {pid}</span>
              </div>
            ))
          )}
        </div>
        <div style={{ marginTop: 'auto', paddingTop: '20px', borderTop: '1px solid rgba(80,60,140,0.2)' }}>
          <p className="text-muted" style={{ fontSize: '0.75rem', textAlign: 'center' }}>
            AI Micro-Drama Studio v3.0<br/>React Edition
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        <h1 className="hero-title">AI Micro-Drama Studio</h1>
        <p className="hero-sub">One premise → Complete short-form drama episode with AI</p>

        <div className="grid-cols-2">
          {/* Left Panel - Controls */}
          <div>
            <div className="tabs">
              <button 
                className={`tab-btn ${mode === 'generate' ? 'active' : ''}`}
                onClick={() => setMode('generate')}
              >
                <Clapperboard size={16} style={{display:'inline', marginRight:6}}/> New Episode
              </button>
              <button 
                className={`tab-btn ${mode === 'custom' ? 'active' : ''}`}
                onClick={() => setMode('custom')}
              >
                <FileJson size={16} style={{display:'inline', marginRight:6}}/> Custom Story
              </button>
            </div>

            <div className="glass-card">
              {mode === 'generate' ? (
                <div className="form-group">
                  <label>Story Premise</label>
                  <textarea 
                    rows={3} 
                    value={premise} 
                    onChange={e => setPremise(e.target.value)}
                    placeholder="Enter a dramatic premise..."
                  />
                  <div style={{ marginTop: '12px' }}>
                    <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Genre</label>
                    <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '6px' }}>
                      {['Basic', 'Funny', 'Thriller', 'Romance', 'Sci-Fi', 'Horror'].map(g => (
                        <button
                          key={g}
                          onClick={() => setGenre(g)}
                          style={{
                            background: genre === g ? 'var(--gradient-1)' : 'rgba(255,255,255,0.05)',
                            border: `1px solid ${genre === g ? 'transparent' : 'var(--border)'}`,
                            color: '#fff', padding: '6px 14px', borderRadius: '20px',
                            fontSize: '0.85rem', cursor: 'pointer', fontFamily: 'Inter',
                            transition: 'all 0.2s'
                          }}
                        >
                          {g}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
              ) : (
                <div className="form-group">
                  <label>Story JSON</label>
                  <textarea 
                    rows={6} 
                    value={customJson} 
                    onChange={e => setCustomJson(e.target.value)}
                    placeholder='{"title": "...", "hook": "..."}'
                    style={{fontFamily: 'monospace', fontSize: '0.9rem'}}
                  />
                </div>
              )}

              <div className="grid-cols-2" style={{ gap: '16px', marginBottom: '20px' }}>
                <div className="form-group">
                  <label>Language</label>
                  <select value={language} onChange={e => setLanguage(e.target.value)}>
                    {LANGUAGES.map(l => <option key={l}>{l}</option>)}
                  </select>
                </div>
                <div className="form-group">
                  <label>Style</label>
                  <select value={style} onChange={e => setStyle(e.target.value)}>
                    {STYLES.map(s => <option key={s}>{s}</option>)}
                  </select>
                </div>
              </div>

              <div className="form-group">
                <label>Narrator Voice</label>
                <select value={voice} onChange={e => setVoice(e.target.value)}>
                  {Object.keys(VOICES).map(v => <option key={v}>{v}</option>)}
                </select>
              </div>

              <button className="primary" onClick={handleGenerate} disabled={loading}>
                {loading ? <Activity size={20} className="spin" style={{display:'inline', verticalAlign:'middle'}}/> : '🎬 GENERATE EPISODE'}
              </button>

              {error && <p style={{color: '#ef4444', marginTop: '12px', fontSize: '0.9rem'}}>{error}</p>}
            </div>

            {loading && (
              <div className="progress-container">
                <p style={{color: '#a78bfa', fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '8px'}}>
                  <Activity size={16} /> Production Pipeline Active
                </p>
                <div className="progress-bar">
                  <div className="progress-fill" style={{width: '50%'}}></div>
                </div>
                <p className="text-muted" style={{fontSize: '0.8rem', marginTop: '8px'}}>Generating script and parallel assets...</p>
              </div>
            )}
          </div>

          {/* Right Panel - Results */}
          <div>
            {!currentProject ? (
              <div className="glass-card" style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', opacity: 0.5 }}>
                <Clapperboard size={64} color="var(--border)" style={{marginBottom: 16}} />
                <h3>No Episode Selected</h3>
                <p className="text-muted">Generate a new one or pick from the sidebar.</p>
              </div>
            ) : currentProject.status === 'failed' ? (
              <div className="glass-card" style={{borderColor: '#ef4444'}}>
                <h3 style={{color: '#ef4444'}}>Generation Failed</h3>
                <p className="text-muted">{currentProject.error}</p>
              </div>
            ) : (
              <div>
                <div className="badge">{currentProject.language?.toUpperCase()} • {currentProject.duration}s</div>
                {currentProject.parent_project_id && <div className="badge" style={{background: 'var(--gradient-emerald)'}}>SEQUEL</div>}
                
                <h2 style={{marginBottom: '8px', fontSize: '2rem'}}>{currentProject.title}</h2>
                <p className="text-muted mb-2">"{currentProject.premise}"</p>

                <div className="stat-grid mt-4">
                  <div className="stat-card">
                    <div className="stat-val">{currentProject.story?.scenes?.length || 0}</div>
                    <div className="stat-label"><Clapperboard size={12} style={{display:'inline'}}/> Scenes</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-val">{currentProject.duration}s</div>
                    <div className="stat-label"><Clock size={12} style={{display:'inline'}}/> Duration</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-val">{currentProject.story?.characters?.length || 0}</div>
                    <div className="stat-label"><Users size={12} style={{display:'inline'}}/> Cast</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-val">{currentProject.language?.substring(0,3).toUpperCase()}</div>
                    <div className="stat-label"><Globe size={12} style={{display:'inline'}}/> Lang</div>
                  </div>
                </div>

                <button 
                  onClick={handleContinue} 
                  disabled={loading}
                  style={{
                    width: '100%', background: 'var(--gradient-emerald)', color: '#fff',
                    border: 'none', padding: '12px', borderRadius: '10px', 
                    fontWeight: 600, fontFamily: 'Space Grotesk', marginBottom: '24px',
                    cursor: loading ? 'not-allowed' : 'pointer'
                  }}
                >
                  <RotateCw size={16} style={{display:'inline', marginRight: 8, verticalAlign:'middle'}}/>
                  CONTINUE STORY ARC
                </button>

                <div style={{ marginTop: '24px' }}>
                  <div className="tabs">
                    <button 
                      className={`tab-btn ${!currentProject.activeTab || currentProject.activeTab === 'video' ? 'active' : ''}`}
                      onClick={() => setCurrentProject({...currentProject, activeTab: 'video'})}
                    >
                      📺 Output Video
                    </button>
                    <button 
                      className={`tab-btn ${currentProject.activeTab === 'script' ? 'active' : ''}`}
                      onClick={() => setCurrentProject({...currentProject, activeTab: 'script'})}
                    >
                      📝 Storyboard
                    </button>
                    <button 
                      className={`tab-btn ${currentProject.activeTab === 'social' ? 'active' : ''}`}
                      onClick={() => setCurrentProject({...currentProject, activeTab: 'social'})}
                    >
                      📱 Social Text
                    </button>
                  </div>

                  {(!currentProject.activeTab || currentProject.activeTab === 'video') && (
                    <div className="glass-card">
                      <div className="video-container">
                        <video 
                          controls 
                          src={`${BACKEND_URL}/static/projects/${currentProject.project_id}/final_video.mp4`}
                        />
                      </div>
                      <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
                        <a 
                          href={`${BACKEND_URL}/static/projects/${currentProject.project_id}/final_video.mp4`}
                          download
                          style={{
                            flex: 1, textAlign: 'center', background: 'rgba(255,255,255,0.05)',
                            border: '1px solid var(--border)', padding: '10px', borderRadius: '8px',
                            color: 'var(--text-primary)', textDecoration: 'none', fontSize: '0.9rem',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px'
                          }}
                        >
                          <Download size={16} /> Download MP4
                        </a>
                        <a 
                          href={`${BACKEND_URL}/static/projects/${currentProject.project_id}/thumbnail.png`}
                          download
                          style={{
                            flex: 1, textAlign: 'center', background: 'rgba(255,255,255,0.05)',
                            border: '1px solid var(--border)', padding: '10px', borderRadius: '8px',
                            color: 'var(--text-primary)', textDecoration: 'none', fontSize: '0.9rem',
                            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px'
                          }}
                        >
                          <Download size={16} /> Thumbnail
                        </a>
                      </div>
                    </div>
                  )}

                  {currentProject.activeTab === 'script' && (
                    <div className="glass-card">
                      {currentProject.story?.characters?.[0] && (
                        <div style={{display: 'flex', gap: '16px', marginBottom: '24px', paddingBottom: '24px', borderBottom: '1px solid var(--border)'}}>
                          <img 
                            src={`${BACKEND_URL}/static/projects/${currentProject.project_id}/character_base.png`} 
                            style={{width: '100px', height: '100px', borderRadius: '50%', objectFit: 'cover', border: '2px solid var(--accent)'}}
                          />
                          <div>
                            <h4 style={{color: 'var(--accent)', marginBottom: '4px'}}>{currentProject.story.characters[0].name}</h4>
                            <p className="text-muted" style={{fontSize: '0.9rem'}}>{currentProject.story.characters[0].description}</p>
                          </div>
                        </div>
                      )}
                      <div style={{
                        display: 'grid', 
                        gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))', 
                        gap: '20px'
                      }}>
                        {currentProject.story?.scenes?.map(sc => (
                          <div className="scene-card" key={sc.scene_number} style={{
                            flexDirection: 'column', 
                            paddingBottom: 0, 
                            borderBottom: 'none', 
                            background: 'rgba(0,0,0,0.2)',
                            padding: '12px',
                            borderRadius: '12px'
                          }}>
                            <img 
                              src={`${BACKEND_URL}/static/projects/${currentProject.project_id}/scene_${sc.scene_number}.png`} 
                              alt={`Scene ${sc.scene_number}`} 
                              style={{width: '100%', aspectRatio: '9/16', objectFit: 'cover', borderRadius: '8px'}}
                            />
                            <div style={{marginTop: '12px'}}>
                              <h4 style={{marginBottom: 4, color: 'var(--accent)'}}>Scene {sc.scene_number}</h4>
                              <p className="text-muted" style={{fontSize: '0.8rem', lineHeight: 1.4, display: '-webkit-box', WebkitLineClamp: 3, WebkitBoxOrient: 'vertical', overflow: 'hidden'}}>{sc.description}</p>
                              <div className="narration-block" style={{fontSize: '0.8rem', padding: '10px', marginTop: '8px'}}>
                                🎤 {sc.narration}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                      {currentProject.story?.ending_cliffhanger && (
                        <div style={{marginTop: '24px', padding: '16px', background: 'rgba(245, 158, 11, 0.1)', borderLeft: '4px solid #f59e0b', borderRadius: '4px'}}>
                          <h4 style={{color: '#f59e0b', marginBottom: 4}}>Cliffhanger</h4>
                          <p style={{fontSize: '0.9rem'}}>{currentProject.story.ending_cliffhanger}</p>
                        </div>
                      )}
                    </div>
                  )}

                  {currentProject.activeTab === 'social' && (
                    <div className="glass-card">
                      <div style={{marginBottom: '20px'}}>
                        <h4 style={{color: 'var(--accent)', marginBottom: '8px'}}>YouTube Title</h4>
                        <div style={{background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', fontFamily: 'monospace'}}>
                          {currentProject.social?.youtube_title || "..."}
                        </div>
                      </div>
                      <div style={{marginBottom: '20px'}}>
                        <h4 style={{color: 'var(--accent)', marginBottom: '8px'}}>TikTok/Reel Title</h4>
                        <div style={{background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', fontFamily: 'monospace'}}>
                          {currentProject.social?.reel_title || "..."}
                        </div>
                      </div>
                      <div style={{marginBottom: '20px'}}>
                        <h4 style={{color: 'var(--accent)', marginBottom: '8px'}}>Instagram Caption</h4>
                        <div style={{background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', fontFamily: 'monospace', whiteSpace: 'pre-wrap'}}>
                          {currentProject.social?.instagram_caption || "..."}
                        </div>
                      </div>
                      <div>
                        <h4 style={{color: 'var(--accent)', marginBottom: '8px'}}>Hashtags</h4>
                        <div style={{background: 'rgba(0,0,0,0.3)', padding: '12px', borderRadius: '8px', color: '#a78bfa', fontSize: '0.9rem'}}>
                          {currentProject.social?.hashtags?.map(tag => `#${tag}`).join(' ') || "..."}
                        </div>
                      </div>
                    </div>
                  )}
                </div>

              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
