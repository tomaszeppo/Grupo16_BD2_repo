/* Vista del hincha: HTML/CSS/JS y el contrato de la API del Hito 10. */
(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const FLAGS = {ARG:'🇦🇷',BRA:'🇧🇷',ESP:'🇪🇸',FRA:'🇫🇷',GER:'🇩🇪',ENG:'🏴',ITA:'🇮🇹',POR:'🇵🇹',NED:'🇳🇱',BEL:'🇧🇪',CRO:'🇭🇷',URU:'🇺🇾',MEX:'🇲🇽',USA:'🇺🇸',CAN:'🇨🇦',JPN:'🇯🇵'};
  const COUNTRIES = {ARG:'Argentina',BRA:'Brasil',ESP:'España',FRA:'Francia',URU:'Uruguay'};
  const LAB_WINDOW = '2030-06-15T18:30:00Z';
  let user = null, matches = [], selected = null, generation = 0, loading = false;
  let commentCursor = null, commentItems = [], pendingComment = null, submitting = false;
  let statsStart = LAB_WINDOW, serviceStates = {}, toastTimer, teamGeneration = 0;
  let liveSource = null, selectedState = null, page = 'inicio', lastCommentMarkup = '', lastHeartbeat = 0;
  function stopLive() { if (liveSource) liveSource.close(); liveSource = null; }
  function connection(text, state = '') { $('live-status').textContent = text; $('live-status').className = 'connection-status '+state; }
  const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const flag = code => FLAGS[code] || '⚽';
  const fmtDate = value => {
    const d = new Date(value.length === 10 ? value+'T12:00:00' : value);
    return Number.isNaN(d.getTime()) ? 'Fecha por confirmar' : d.toLocaleDateString('es-AR',{day:'numeric',month:'short'});
  };
  function localInput(iso) {
    const d = new Date(iso), pad = n => String(n).padStart(2,'0');
    return `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
  }
  $('stats-start').value = localInput(LAB_WINDOW);
  function errorBox(id, message) { $(id).textContent = message || ''; $(id).hidden = !message; }
  function toast(message) {
    clearTimeout(toastTimer); $('toast').textContent = message; $('toast').hidden = false;
    toastTimer = setTimeout(() => { $('toast').hidden = true; }, 4500);
  }
  async function api(path, options = {}) {
    let r;
    try { r = await fetch('/api/'+path, {cache:'no-store', ...options, headers:{'Content-Type':'application/json', ...options.headers}}); }
    catch { throw new Error('No pudimos conectar con la vista del Fixture. Intentá nuevamente.'); }
    const data = r.status === 204 ? null : await r.json();
    if (!r.ok) {
      if (r.status === 401 && user) showLogin('Tu sesión venció o fue cerrada. Volvé a ingresar.');
      throw new Error(typeof data?.detail === 'string' ? data.detail : 'Revisá los datos e intentá nuevamente.');
    }
    return data;
  }
  function fixture(path, params = {}) { return api('fixture/'+path+'?'+new URLSearchParams(params)); }
  function showLogin(message = '') {
    stopLive(); user = null; generation++; teamGeneration++; selected = null; matches = []; pendingComment = null;
    $('application').hidden = true; $('login').hidden = false; errorBox('login-error', message);
    document.title = 'Fixture 2030 · Tu tribuna';
  }
  async function login(mode) {
    if (mode === 'real' && !$('login-form').reportValidity()) return;
    $('login-submit').disabled = $('demo-login').disabled = true;
    errorBox('login-error','');
    try {
      const session = await api('sesion',{method:'POST',body:JSON.stringify({
        nombre:$('name').value.trim() || 'Hincha', pais:$('country').value,
        usuario_id:$('user-id').value || 'U001', modo:mode,
      })});
      await enter(session);
    } catch (e) { errorBox('login-error',e.message); }
    finally { $('login-submit').disabled = $('demo-login').disabled = false; }
  }
  async function enter(session) {
    user = session; $('login').hidden = true; $('application').hidden = false;
    window.scrollTo({top:0,behavior:'instant'});
    $('account-name').textContent = user.nombre;
    $('account-country').textContent = `${flag(user.pais)} ${COUNTRIES[user.pais]}`;
    $('avatar').textContent = user.nombre.slice(0,2).toUpperCase();
    $('chat-flag').textContent = flag(user.pais);
    $('welcome-text').textContent = `${user.nombre}, la tribuna de ${COUNTRIES[user.pais]} te estaba esperando.`;
    $('mode-banner').classList.toggle('real',user.modo === 'real');
    $('mode-banner').textContent = user.modo === 'demo'
      ? 'DEMOSTRACIÓN · Datos sintéticos, sin conexión a las bases. La tribuna se comparte con otros visitantes de la demo.'
      : 'LABORATORIO CONECTADO · Sesión existente del Fixture. Fechas, equipos y resultados son datos de prueba.';
    $('comment').value = ''; $('char-count').textContent = '0 / 280';
    $('comment-period').value = 'now';
    if (!location.hash.startsWith('#/')) history.replaceState(null,'','#/inicio');
    await loadMatches();
  }
  async function loadMatches(navigate = true) {
    const session = user;
    if (!session) return;
    $('refresh').disabled = true; errorBox('page-error','');
    try {
      const data = await api('partidos');
      if (user !== session) return;
      matches = data.items;
      $('catalog-status').textContent = `✓ Fixture consultado a las ${new Date().toLocaleTimeString('es-AR')} · actualización cada 15 s`;
      renderMatches();
      if (navigate) await route();
      if (!matches.some(m=>m.partido)) errorBox('page-error','No pudimos consultar los partidos. Podés actualizar para volver a intentar.');
    } catch(e) { if (user === session) errorBox('page-error',e.message); }
    finally { $('refresh').disabled = false; }
  }
  function matchCard(row) {
    const p = row.partido;
    if (!p) return '';
    const state = row.estado, live = state === 'En juego';
    return `<a class="fixture-card ${live ? 'is-live' : ''}" href="#/partido/${esc(p.id)}"><div class="fixture-card-top"><span class="fixture-status ${live ? 'live' : ''}">${esc(state || 'Estado sin verificar')}</span><span>${esc(fmtDate(p.fecha))}</span></div><div class="fixture-card-teams">${p.equipos.map(e=>`<div><span>${flag(e.codigo)}</span><strong>${esc(e.nombre)}</strong><small>${esc(e.codigo)}</small></div>`).join('<span class="fixture-vs">vs</span>')}</div><div class="fixture-card-bottom"><span>${esc(p.estadio?.nombre || 'Sede por confirmar')}</span><strong>${live ? 'Entrar a la tribuna ↗' : state === 'Finalizado' ? 'Ver encuentro ↗' : 'Ver la previa ↗'}</strong></div></a>`;
  }
  function renderMatches() {
    const live = matches.filter(m=>m.partido && m.estado === 'En juego');
    const upcoming = matches.filter(m=>m.partido && m.estado === 'Programado');
    const finished = matches.filter(m=>m.partido && m.estado === 'Finalizado');
    const unknown = matches.filter(m=>!m.partido || !m.estado);
    $('live-count').textContent = live.length;
    $('match-list').innerHTML = live.length ? live.map(matchCard).join('') : '<div class="empty card">No hay partidos en curso confirmados en este momento.<br>Podés recorrer el historial o mirar las próximas fechas.</div>';
    $('upcoming-list').innerHTML = upcoming.length ? upcoming.map(matchCard).join('') : '<p class="subtle">No hay próximos partidos confirmados.</p>';
    $('history-list').innerHTML = finished.length ? finished.map(matchCard).join('') : '<div class="empty card">Todavía no hay partidos finalizados confirmados.</div>';
    $('unknown-list').innerHTML = unknown.length ? `<div class="error-box">No pudimos verificar ${unknown.length} encuentro(s). No los clasificamos como en curso o finalizados. Actualizá para reintentar.</div>` : '';
  }
  async function route() {
    if (!user) return;
    stopLive(); generation++; teamGeneration++;
    const parts = location.hash.replace('#/','').split('/'); page = parts[0] || 'inicio';
    const detail = page === 'partido', historyPage = page === 'historial';
    $('home-view').hidden = detail || historyPage;
    $('history-view').hidden = !historyPage;
    $('detail-view').hidden = !detail;
    document.querySelectorAll('[data-nav]').forEach(a=>a.classList.toggle('active',a.dataset.nav === (historyPage ? 'historial' : 'inicio')));
    errorBox('page-error','');
    if (detail) {
      const row = matches.find(m=>m.partido?.id === parts[1]);
      if (!row) { errorBox('page-error','No encontramos ese partido. Volvé al inicio para elegir uno disponible.'); $('detail-view').hidden = true; return; }
      selectedState = row.estado;
      $('comment-period').value = row.estado === 'En juego' ? 'now' : 'lab';
      $('back-to-list').href = row.estado === 'Finalizado' ? '#/historial' : '#/inicio';
      $('back-to-list').textContent = row.estado === 'Finalizado' ? '← Volver al historial' : '← Volver al inicio';
      $('detail-context').textContent = row.estado === 'Finalizado' ? 'UN PARTIDO PARA VOLVER A VIVIR' : 'TU TRIBUNA DEL PARTIDO';
      setTab('summary');
      await selectMatch(row.partido);
      startLive();
    } else { selected = null; document.title = historyPage ? 'Historial · Fixture 2030' : 'Mi tribuna · Fixture 2030'; }
    window.scrollTo({top:0,behavior:'instant'});
  }
  function startLive() {
    stopLive();
    if (!user || !selected || page !== 'partido' || $('comment-period').value !== 'now' || selectedState !== 'En juego') {
      connection(selectedState === 'En juego' ? 'Viendo comentarios de la muestra' : 'Encuentro sin tribuna en directo');
      return;
    }
    lastHeartbeat = Date.now();
    connection('Conectando con la tribuna…');
    const id = selected.id;
    liveSource = new EventSource(`/api/directo/${id}/comentarios`);
    const source = liveSource;
    liveSource.addEventListener('comentarios', event=>{
      if (liveSource !== source || !selected || selected.id !== id || page !== 'partido') return;
      const data = JSON.parse(event.data);
      lastHeartbeat = Date.now();
      commentItems = data.items; commentCursor = null;
      renderComments(); serviceStates.comentarios = true; renderServices();
      connection('En directo · sincronizado','connected');
      $('live-checked').textContent = `${data.items.length} comentario(s) recientes · verificado ${new Date(data.consultado_en).toLocaleTimeString('es-AR')}`;
    });
    liveSource.addEventListener('estado', event=>{
      if (liveSource !== source) return;
      const data = JSON.parse(event.data);
      if (data.codigo === 401) { showLogin(data.mensaje); return; }
      serviceStates.comentarios = false; renderServices();
      connection('Sin sincronizar · reintentando','disconnected');
      $('live-checked').textContent = data.mensaje;
    });
    liveSource.onerror = ()=>{
      if (liveSource !== source) return;
      connection('Conexión interrumpida · reconectando','disconnected');
      serviceStates.comentarios = false; renderServices();
    };
  }
  function commentWindow() {
    if ($('comment-period').value === 'lab') return LAB_WINDOW;
    const d = new Date(); d.setUTCMinutes(Math.floor(d.getUTCMinutes()/30)*30,0,0);
    return d.toISOString().replace('.000Z','Z');
  }
  function renderWindow() {
    if ($('comment-period').value === 'now') { $('comment-window').textContent = 'Comentarios recientes · ventana actual y media hora anterior'; return; }
    const d = new Date(commentWindow());
    $('comment-window').textContent = `${d.toLocaleDateString('es-AR')} · ${d.toLocaleTimeString('es-AR',{hour:'2-digit',minute:'2-digit'})} a ${new Date(d.getTime()+1800000).toLocaleTimeString('es-AR',{hour:'2-digit',minute:'2-digit'})} (tu hora local)`;
  }
  function scoreFor(p) {
    const r = p.resultado;
    if (!r) return '— : —';
    return p.equipos.map(e => e.codigo === r.ganador ? r.goles_ganador : r.goles_perdedor).join(' : ');
  }
  async function selectMatch(p) {
    stopLive(); lastCommentMarkup = '';
    const changed = selected?.id !== p.id;
    selected = p; generation++; teamGeneration++;
    if (changed) { pendingComment = null; $('comment').value = ''; $('char-count').textContent = '0 / 280'; $('comment-feedback').textContent = ''; }
    const [home,away] = p.equipos;
    for (const [prefix,team] of [['home',home],['away',away]]) {
      $(prefix+'-name').textContent = team?.nombre || 'Por confirmar';
      $(prefix+'-code').textContent = team?.codigo || '';
      $(prefix+'-flag').textContent = flag(team?.codigo);
    }
    $('score').textContent = scoreFor(p);
    $('score-note').textContent = p.resultado ? 'Marcador simulado de laboratorio' : 'Sin marcador disponible';
    $('match-phase').textContent = p.fase.toUpperCase(); $('match-date').textContent = fmtDate(p.fecha);
    $('stadium').textContent = p.estadio ? `${p.estadio.nombre} · ${p.estadio.ciudad}` : 'Sede por confirmar';
    $('match-state').textContent = 'Consultando estado…'; $('match-state').classList.remove('playing');
    $('team-picker').innerHTML = p.equipos.map(e=>`<option value="${esc(e.codigo)}">${flag(e.codigo)} ${esc(e.nombre)}</option>`).join('');
    $('event-list').innerHTML = '<div class="empty">Buscando las jugadas…</div>';
    $('stats-content').innerHTML = '<div class="empty">Consultando las estadísticas…</div>';
    $('comments-list').innerHTML = '<div class="empty">Buscando a la hinchada…</div>';
    $('players-list').innerHTML = '<div class="empty">Buscando el plantel…</div>';
    commentCursor = null; $('more-comments').hidden = true;
    serviceStates = {}; renderServices();
    $('comment-form').hidden = selectedState !== 'En juego';
    $('fan-note-title').textContent = selectedState === 'En juego' ? 'Tu mirada también juega.' : 'Cada encuentro tiene su historia.';
    $('fan-note-copy').textContent = selectedState === 'En juego' ? 'Compartí lo que ves con la hinchada de tu país. Un comentario, mil formas de sentirlo.' : 'Recorré las jugadas, los números y los comentarios de este encuentro.';
    $('chat-foot').textContent = selectedState === 'Finalizado' ? 'Este partido terminó. La tribuna está en modo lectura.' : selectedState === 'Programado' ? 'La tribuna en directo abre cuando el partido está en juego.' : 'Alentamos con pasión. Nos tratamos con respeto.';
    $('live-checked').textContent = '';
    document.title = `${home?.codigo} – ${away?.codigo} · Fixture 2030`;
    await Promise.all([refreshMatch(), loadPlayers()]);
  }
  async function refreshMatch() {
    if (!selected || !user) return;
    const ticket = generation, id = selected.id;
    const start = statsStart, end = new Date(new Date(start).getTime()+600000).toISOString();
    const window = commentWindow(); renderWindow(); loading = true;
    const results = await Promise.allSettled([
      fixture(`partidos/${id}/detalle`), fixture(`partidos/${id}/eventos`),
      fixture(`partidos/${id}/estadisticas`,{desde:start,hasta:end,agregacion:'1m'}),
      fixture(`partidos/${id}/comentarios`,{ventana:window,limit:20}),
    ]);
    if (ticket !== generation || !user) { loading = false; return; }
    const [detail,events,stats,comments] = results;
    if (detail.status === 'fulfilled') {
      const state = detail.value.estado; $('match-state').textContent = state;
      const changedState = selectedState !== state; selectedState = state;
      const row = matches.find(m=>m.partido?.id === id); if (row) row.estado = state;
      $('comment-form').hidden = state !== 'En juego';
      if (changedState) startLive();
      $('match-state').classList.toggle('playing',state === 'En juego');
    } else { $('match-state').textContent = 'Estado no disponible'; }
    renderEvents(events, detail);
    if (stats.status === 'fulfilled') renderStats(stats.value);
    else $('stats-content').innerHTML = `<div class="empty">${esc(stats.reason.message)}</div>`;
    if (comments.status === 'fulfilled' && !liveSource) {
      commentItems = comments.value.items; commentCursor = comments.value.next_cursor; renderComments();
    } else if (comments.status !== 'fulfilled' && !liveSource) { $('comments-list').innerHTML = `<div class="empty">${esc(comments.reason.message)}</div>`; $('more-comments').hidden = true; }
    for (const [key,result] of [['partidos',events],['estado',detail],['estadisticas',stats],['comentarios',comments]]) serviceStates[key] = result.status === 'fulfilled';
    renderServices();
    $('last-update').textContent = `Actualizado ${new Date().toLocaleTimeString('es-AR',{hour:'2-digit',minute:'2-digit'})}`;
    loading = false;
  }
  function renderEvents(events, detail) {
    // IRIS aporta contexto; el recorrido de eventos de Neo4j conserva su propia fuente.
    if (events.status !== 'fulfilled') { $('event-list').innerHTML = `<div class="empty">${esc(events.reason.message)}</div>`; return; }
    const items = [...events.value.items].sort((a,b)=>b.minuto-a.minuto);
    if (!items.length) { $('event-list').innerHTML = '<div class="empty">Todavía no hay jugadas registradas para este encuentro.</div>'; return; }
    $('event-list').innerHTML = items.map(e=>{
      const extra = detail.status === 'fulfilled' ? detail.value.eventos.find(d=>d.minuto === e.minuto && d.tipo === e.tipo)?.descripcion : null;
      return `<div class="event"><span class="event-minute">${esc(e.minuto)}′</span><span class="event-icon" aria-hidden="true">${e.tipo === 'Gol' ? '⚽' : e.tipo === 'Final' ? '⚑' : '↗'}</span><div><strong>${esc(e.tipo)}</strong><p>${esc(extra || 'Evento registrado del partido')}</p></div></div>`;
    }).join('');
    if (detail.status === 'fulfilled' && detail.value.estado === 'En juego' && items.some(e=>e.tipo === 'Final')) {
      $('event-list').insertAdjacentHTML('beforeend','<p class="subtle" style="padding:12px 18px;margin:0">La muestra contiene un evento de final en el grafo; el estado del partido en IRIS sigue “En juego”.</p>');
    }
  }
  function renderStats(data) {
    if (!data.puntos.length) { $('stats-content').innerHTML = '<div class="empty">No hay estadísticas para este intervalo.<br>Probá con P-01 o P-02 y la ventana de muestra.</div>'; return; }
    const teams = selected.equipos;
    const totals = teams.map(e=>{
      const rows = data.puntos.filter(p=>p.equipo_id === e.codigo);
      const sum = field => rows.reduce((n,r)=>n+(Number(r[field])||0),0);
      return {posesion:rows.length ? sum('posesion_pct_prom')/rows.length : null,
        pases:sum('pases_completados'),tiros:sum('tiros'),recuperaciones:sum('recuperaciones')};
    });
    $('stats-content').innerHTML = `<div class="stat-legend">${teams.map(e=>`<span>${flag(e.codigo)} ${esc(e.nombre)}</span>`).join('')}</div>` +
      [['posesion','Posesión promedio','%'],['pases','Pases completados',''],['tiros','Tiros',''],['recuperaciones','Recuperaciones','']].map(([key,label,unit])=>{
        const a = totals[0][key], b = totals[1][key], total = (a||0)+(b||0);
        const show = v => v === null ? '—' : `${Number(v.toFixed(1))}${unit}`;
        return `<div class="stat-row"><div class="stat-labels"><strong>${show(a)}</strong><span>${label}</span><strong>${show(b)}</strong></div><div class="stat-bars"><i style="width:${total ? a/total*100 : 50}%"></i><i style="width:${total ? b/total*100 : 50}%"></i></div></div>`;
      }).join('')+`<p class="subtle">${esc(new Date(data.desde).toLocaleTimeString('es-AR',{hour:'2-digit',minute:'2-digit'}))}–${esc(new Date(data.hasta).toLocaleTimeString('es-AR',{hour:'2-digit',minute:'2-digit'}))} (tu hora local). Promedio de posesión y suma de operaciones en la ventana; no son totales del partido.${data.truncado ? ' Muestra truncada: reducí el intervalo.' : ''}</p>`;
  }
  function renderServices() {
    $('fan-services').innerHTML = [['partidos','Las jugadas'],['estado','El encuentro'],['estadisticas','Los números'],['comentarios','La tribuna']].map(([key,label])=>{
      const state = serviceStates[key];
      return `<div class="service ${state === undefined ? 'unknown' : state ? '' : 'unavailable'}">${label}<span>${state === undefined ? 'Consultando' : state ? 'Disponible' : 'No disponible'}</span></div>`;
    }).join('');
  }
  async function loadPlayers() {
    const ticket = ++teamGeneration, id = generation, code = $('team-picker').value;
    if (!code || !user) return;
    $('players-list').innerHTML = '<div class="empty">Buscando el plantel…</div>';
    try {
      const data = await fixture(`equipos/${code}/jugadores`,{limit:20});
      if (ticket !== teamGeneration || id !== generation) return;
      $('players-list').innerHTML = data.items.length ? data.items.map(p=>`<div class="player"><span class="shirt">${esc(p.dorsal)}</span><div><strong>${esc(p.nombre)} ${esc(p.apellido)}</strong><span>${esc(p.posicion)}</span></div></div>`).join('') : '<div class="empty">No hay jugadores cargados para esta selección.</div>';
    } catch(e) { if (ticket === teamGeneration && id === generation) $('players-list').innerHTML = `<div class="empty">${esc(e.message)}</div>`; }
  }
  function renderComments() {
    const markup = commentItems.length ? commentItems.map(c=>`<article class="comment"><div class="comment-author"><span class="avatar">${esc(c.usuario_nombre.slice(0,2).toUpperCase())}</span><strong>${esc(c.usuario_nombre)}</strong><time datetime="${esc(c.creado_en)}">${esc(new Date(c.creado_en).toLocaleTimeString('es-AR',{hour:'2-digit',minute:'2-digit'}))}</time></div><p>${esc(c.contenido)}</p><span class="comment-likes" aria-label="${esc(c.likes)} me gusta">${esc(c.likes)}</span></article>`).join('') : `<div class="empty">${selectedState === 'En juego' ? 'La tribuna está esperando tu voz.<br>' : ''}Todavía no hay comentarios en esta ventana.</div>`;
    if (markup !== lastCommentMarkup) {
      const scroll = $('comments-list').scrollTop;
      $('comments-list').innerHTML = markup; $('comments-list').scrollTop = scroll; lastCommentMarkup = markup;
    }
    $('more-comments').hidden = !commentCursor;
  }
  async function sendComment(e) {
    e.preventDefault(); if (submitting || !selected || selectedState !== 'En juego') return;
    const content = $('comment').value.trim();
    if (!content) return;
    const match = selected.id, ticket = generation;
    if (!pendingComment || pendingComment.content !== content || pendingComment.match !== match) pendingComment = {content,match,key:crypto.randomUUID()};
    submitting = true; $('send-comment').disabled = true; $('comment-feedback').textContent = 'Enviando tu comentario…';
    try {
      const saved = await api(`fixture/partidos/${match}/comentarios`,{method:'POST',headers:{'Idempotency-Key':pendingComment.key},body:JSON.stringify({contenido:content})});
      if (ticket !== generation || !user) return;
      pendingComment = null; $('comment').value = ''; $('char-count').textContent = '0 / 280';
      $('comment-period').value = 'now'; renderWindow();
      $('comment-feedback').textContent = `✓ Publicado a las ${new Date(saved.creado_en).toLocaleTimeString('es-AR')} · confirmado por el servidor.`;
      commentItems = [saved,...commentItems.filter(c=>c.comentario_id !== saved.comentario_id)]; renderComments();
      startLive();
    } catch(e) { if (ticket === generation) $('comment-feedback').textContent = e.message+' Podés reintentar sin duplicarlo.'; }
    finally { submitting = false; $('send-comment').disabled = false; }
  }
  function setTab(name, focus = false) {
    document.querySelectorAll('[data-tab]').forEach(button=>{
      const active = button.dataset.tab === name;
      button.setAttribute('aria-selected',String(active)); button.tabIndex = active ? 0 : -1;
      $('panel-'+button.dataset.tab).hidden = !active;
      if (active && focus) button.focus();
    });
  }
  $('login-form').addEventListener('submit',e=>{e.preventDefault();login('real');});
  $('demo-login').addEventListener('click',()=>login('demo'));
  $('logout').addEventListener('click',async()=>{
    $('logout').disabled = true;
    try { await api('sesion',{method:'DELETE'}); showLogin(); }
    catch(e) { toast(e.message+' La sesión no se cerró; podés volver a intentar.'); }
    finally { $('logout').disabled = false; }
  });
  $('refresh').addEventListener('click',loadMatches);
  $('refresh-history').addEventListener('click',loadMatches);
  $('open-history').addEventListener('click',()=>{location.hash = '/historial';});
  window.addEventListener('hashchange',()=>{if (location.hash.startsWith('#/')) route();});
  document.querySelectorAll('[data-tab]').forEach(button=>{
    button.addEventListener('click',()=>setTab(button.dataset.tab));
    button.addEventListener('keydown',e=>{
      const tabs = ['summary','stats','teams'], index = tabs.indexOf(button.dataset.tab);
      if (['ArrowLeft','ArrowRight','Home','End'].includes(e.key)) {
        e.preventDefault(); setTab(e.key === 'Home' ? tabs[0] : e.key === 'End' ? tabs[2] : tabs[(index+(e.key === 'ArrowRight' ? 1 : 2))%3],true);
      }
    });
  });
  $('team-picker').addEventListener('change',loadPlayers);
  $('comment-form').addEventListener('submit',sendComment);
  $('comment').addEventListener('input',()=>{ $('char-count').textContent = `${$('comment').value.length} / 280`; });
  $('comment-period').addEventListener('change',async()=>{stopLive(); generation++; lastCommentMarkup = ''; await refreshMatch(); startLive();});
  $('apply-stats').addEventListener('click',()=>{
    const date = new Date($('stats-start').value);
    if (Number.isNaN(date.getTime())) { toast('Elegí una fecha y una hora válidas.'); return; }
    statsStart = date.toISOString(); generation++; refreshMatch();
  });
  $('more-comments').addEventListener('click',async()=>{
    if (!commentCursor || !selected) return;
    const ticket = generation, cursor = commentCursor; $('more-comments').disabled = true;
    try {
      const data = await fixture(`partidos/${selected.id}/comentarios`,{ventana:commentWindow(),limit:20,cursor});
      if (ticket !== generation) return;
      const ids = new Set(commentItems.map(c=>c.comentario_id));
      commentItems.push(...data.items.filter(c=>!ids.has(c.comentario_id))); commentCursor = data.next_cursor; renderComments();
    } catch(e) { toast(e.message); }
    finally { $('more-comments').disabled = false; }
  });
  setInterval(()=>{if (user && !document.hidden && !submitting && !loading) { if (page === 'partido' && selected) refreshMatch(); else loadMatches(false); }},15000);
  setInterval(()=>{if (liveSource && Date.now()-lastHeartbeat > 10000) connection('Esperando sincronización · datos sin confirmar','disconnected');},1000);
  window.addEventListener('pagehide',stopLive);
  window.addEventListener('pageshow',event=>{if (event.persisted && user) startLive();});
  api('sesion').then(enter).catch(()=>showLogin());
})();
