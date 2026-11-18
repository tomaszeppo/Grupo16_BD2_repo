import React, { useEffect, useRef, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './style.css';

async function api(path, options = {}) {
  const response = await fetch('/api/' + path, { ...options, headers: { 'Content-Type': 'application/json', ...options.headers } });
  const data = response.status === 204 ? null : await response.json();
  if (!response.ok) throw new Error(data?.detail || 'No se pudo completar la operación.');
  return data;
}

function App() {
  const [session, setSession] = useState(null), [matches, setMatches] = useState([]), [match, setMatch] = useState(null);
  const [form, setForm] = useState({ usuario_id: 'U001', nombre: '', pais: 'ARG', modo: 'real' });
  const [visible, setVisible] = useState([]), [text, setText] = useState(''), [error, setError] = useState('');
  const queue = useRef([]), known = useRef(new Set()), pending = useRef(null), generation = useRef(0);
  const [detail, setDetail] = useState(null);
  async function loadMatches() { const data = await api('partidos'); setMatches(data.items); }
  useEffect(() => { api('sesion').then(setSession).catch(() => {}); }, []);
  useEffect(() => { if (!session) return; loadMatches().catch(e => setError(e.message)); const timer = setInterval(() => loadMatches().catch(e => setError(e.message)), 15000); return () => clearInterval(timer); }, [session]);
  useEffect(() => {
    if (!match) return;
    const current = ++generation.current; queue.current = []; known.current = new Set(); setVisible([]); setDetail(null); pending.current = null;
    async function poll() {
      try {
        const data = await api(`partidos/${match}/comentarios/recientes`);
        if (generation.current !== current) return;
        const fresh = data.items.slice().reverse().filter(item => !known.current.has(item.comentario_id));
        fresh.forEach(item => known.current.add(item.comentario_id));
        queue.current = [...queue.current, ...fresh].slice(-40);
        // Mantener memoria acotada aun cuando el partido dure horas.
        if (known.current.size > 200) known.current = new Set([...known.current].slice(-100));
        setError('');
      } catch (e) { if (generation.current === current) setError(e.message); }
    }
    async function state() { try { const d = await api(`fixture/partidos/${match}/detalle`); if (generation.current === current) setDetail(d); } catch (e) { if (generation.current === current) setError(e.message); } }
    poll(); state();
    const fetchTimer = setInterval(poll, 8000), stateTimer = setInterval(state, 15000);
    const displayTimer = setInterval(() => { const item = queue.current.shift(); if (item) setVisible(old => [...old.filter(c => c.comentario_id !== item.comentario_id), item].slice(-20)); }, 500);
    return () => { generation.current++; clearInterval(fetchTimer); clearInterval(stateTimer); clearInterval(displayTimer); };
  }, [match]);
  async function login(e) { e.preventDefault(); try { setSession(await api('sesion', { method: 'POST', body: JSON.stringify(form) })); setError(''); } catch(e) { setError(e.message); } }
  async function post(e) {
    e.preventDefault(); const content = text.trim(); if (!content || !match) return;
    if (!pending.current || pending.current.content !== content || pending.current.match !== match) pending.current = { content, match, key: crypto.randomUUID() };
    try { await api(`fixture/partidos/${match}/comentarios`, { method: 'POST', headers: { 'Idempotency-Key': pending.current.key }, body: JSON.stringify({ contenido: content }) }); setText(''); pending.current = null; setError(''); } catch(e) { setError(e.message); }
  }
  return <main><h1>Partidos en vivo</h1>{error && <p role="alert" className="error">{error}</p>}{!session ? <form onSubmit={login}><h2>Ingresar</h2><label>Usuario<input value={form.usuario_id} onChange={e => setForm({...form, usuario_id:e.target.value})}/></label><label>Nombre<input required maxLength="60" value={form.nombre} onChange={e => setForm({...form,nombre:e.target.value})}/></label><label>Región<select value={form.pais} onChange={e => setForm({...form,pais:e.target.value})}>{['ARG','BRA','ESP','FRA','URU'].map(p=><option key={p}>{p}</option>)}</select></label><label>Modo<select value={form.modo} onChange={e => setForm({...form,modo:e.target.value})}><option value="real">Conectado</option><option value="demo">Demostración</option></select></label><button>Entrar</button></form> : <><p>{session.nombre} · {session.pais} · {session.modo}</p><button onClick={async()=>{await api('sesion',{method:'DELETE'}); setSession(null); setMatch(null);}}>Salir</button><section><h2>Partidos actuales</h2>{matches.filter(m=>m.partido && m.estado === 'En juego').map(m=><button key={m.partido.id} onClick={()=>setMatch(m.partido.id)}>{m.partido.equipos.map(e=>e.nombre).join(' vs ')} · {m.partido.id}</button>)}{!matches.some(m=>m.partido && m.estado === 'En juego') && <p>No hay partidos en juego.</p>}</section>{match && <section><h2>{match} · {detail?.estado || 'Consultando estado…'}</h2><p>Minuto y marcador en vivo: pendientes de la simulación del partido.</p><h3>Comentarios · {session.pais}</h3><div className="comments" aria-live="polite">{visible.map(c=><p key={c.comentario_id}><strong>{c.usuario_nombre}:</strong> {c.contenido}</p>)}</div><form onSubmit={post}><label>Tu comentario<textarea value={text} maxLength="280" onChange={e=>setText(e.target.value)} /></label><button disabled={!text.trim() || detail?.estado !== 'En juego'}>Publicar</button></form></section>}</>}</main>;
}
createRoot(document.getElementById('root')).render(<App />);
