/* Prode Mundial 2030 — interfaz de demostración. Sin dependencias: habla con la API del mismo origen.
   Todo texto que viene de la API se inserta con esc() para que un nombre de usuario no pueda meter HTML. */
"use strict";

// Fondo de la portada: una de las cinco fotos del Bernabéu, al azar en cada carga (créditos en img/CREDITOS.md).
document.documentElement.style.setProperty("--foto-estadio", `url("/demo/img/estadio-${1 + Math.floor(Math.random() * 5)}.jpg")`);

const contenido = document.getElementById("contenido");
const sesion = {
  get usuario() {
    try {
      const guardado = localStorage.getItem("usuario") || sessionStorage.getItem("usuario");
      if (guardado && !localStorage.getItem("usuario")) localStorage.setItem("usuario", guardado);
      sessionStorage.removeItem("usuario");
      return JSON.parse(guardado);
    } catch { return null; }
  },
  set usuario(u) {
    u ? localStorage.setItem("usuario", JSON.stringify(u)) : localStorage.removeItem("usuario");
    sessionStorage.removeItem("usuario");
  },
};
let claveAdmin = localStorage.getItem("admin_clave") || "";
let comentariosTimers = [];
let sondeo = null;        // consulta periódica del avance de la puntuación
let preparacionAdmin = null;
let administradorPreparado = false;
let navegacionActual = 0;

// ---------- utilidades ----------
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const base = (fuente) => {
  const clase = ["mongodb", "neo4j", "redis", "cassandra", "influxdb"].includes(fuente) ? fuente : "otra";
  const nombre = { mongodb: "MongoDB", neo4j: "Neo4j", redis: "Redis", cassandra: "Cassandra", influxdb: "InfluxDB" }[fuente] || fuente;
  return `<span class="badge rounded-pill base ${clase}" title="Base que respondió este bloque">${esc(nombre)}</span>`;
};
const fecha = (iso) => new Date(iso).toLocaleString("es-AR", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const hora = (iso) => new Date(iso).toLocaleTimeString("es-AR", { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
const diaLargo = (iso) => { const t = new Date(iso).toLocaleDateString("es-AR", { weekday: "long", day: "numeric", month: "long" }); return t.charAt(0).toUpperCase() + t.slice(1); };
const claveDia = (iso) => { const d = new Date(iso); return `${d.getFullYear()}-${d.getMonth()}-${d.getDate()}`; };
const claseEstado = (e) => e === "En juego" ? "en-juego" : e === "Finalizado" ? "finalizado" : "programado";
const nombreEquipo = (e) => e ? esc(e.nombre) : "Por definir";

// Banderas: un SVG por selección en vendor/banderas (paquete flag-icons, licencia MIT), que se ve igual en todos
// los sistemas. Los emoji quedan solo para la lista de países del ingreso, donde no entra una imagen.
const ISO = {
  ARG: "AR", BRA: "BR", URU: "UY", COL: "CO", ECU: "EC", PAR: "PY", CHI: "CL", PER: "PE", BOL: "BO", VEN: "VE",
  ESP: "ES", POR: "PT", FRA: "FR", GER: "DE", ITA: "IT", NED: "NL", BEL: "BE", CRO: "HR", SUI: "CH", DEN: "DK",
  POL: "PL", SRB: "RS", AUT: "AT", SWE: "SE", NOR: "NO", IRL: "IE", UKR: "UA", CZE: "CZ", TUR: "TR", GRE: "GR",
  HUN: "HU", ROU: "RO", SVK: "SK", MAR: "MA", SEN: "SN", NGA: "NG", EGY: "EG", GHA: "GH", CMR: "CM", CIV: "CI",
  TUN: "TN", ALG: "DZ", RSA: "ZA", MLI: "ML", MEX: "MX", USA: "US", CAN: "CA", CRC: "CR", PAN: "PA", JAM: "JM",
  HON: "HN", JPN: "JP", KOR: "KR", AUS: "AU", IRN: "IR", KSA: "SA", QAT: "QA", UZB: "UZ", NZL: "NZ", IRQ: "IQ",
  CHN: "CN",
};
const SUBDIVISION = { ENG: "gbeng", SCO: "gbsct", WAL: "gbwls" };
const banderasEmoji = typeof navigator === "undefined" || !/Windows/i.test(navigator.userAgent || "");
function banderaEmoji(codigo) {
  if (!banderasEmoji) return "";
  if (SUBDIVISION[codigo]) return String.fromCodePoint(0x1F3F4, ...[...SUBDIVISION[codigo]].map(c => 0xE0000 + c.charCodeAt(0)), 0xE007F);
  const iso = ISO[codigo];
  return iso ? String.fromCodePoint(...[...iso].map(c => 0x1F1E6 + c.charCodeAt(0) - 65)) : "";
}
const tieneBandera = (codigo) => Boolean(ISO[codigo] || SUBDIVISION[codigo]);
const escudo = (e) => e?.codigo
  ? `<span class="escudo" aria-hidden="true">${tieneBandera(e.codigo) ? `<img class="escudo-bandera" src="/demo/vendor/banderas/${esc(e.codigo)}.svg" alt="" width="24" height="18" loading="lazy" decoding="async">` : ""}<span class="escudo-codigo">${esc(e.codigo)}</span></span>`
  : `<span class="escudo escudo-vacio" aria-hidden="true"><span class="escudo-codigo">?</span></span>`;

// Catálogo de selecciones (MongoDB): no cambia durante el torneo, así que se pide una sola vez.
let catalogo = null;
function catalogoEquipos() {
  if (!catalogo) catalogo = api("/equipos").then(d => new Map(d.equipos.map(e => [e.codigo, e]))).catch(e => { catalogo = null; throw e; });
  return catalogo;
}
const grupoDe = (partido, equipos) => partido.fase === "Fase de grupos" ? equipos?.get(partido.local?.codigo)?.grupo : null;

const ANFITRIONES = [["ARG", "Argentina"], ["PAR", "Paraguay"], ["URU", "Uruguay"], ["ESP", "España"], ["POR", "Portugal"], ["MAR", "Marruecos"]];
const marcador = (p) => p.goles_local == null ? "–" : `${p.goles_local} - ${p.goles_visitante}`;
// Anticipación acumulada (tercer criterio del ranking), en unidades enteras: "2 d 19 h 12 min", "4 h 5 min", "12 min 30 s".
const duracion = (segundos) => {
  const seg = Math.max(0, Math.round(segundos || 0));
  const d = Math.floor(seg / 86400), h = Math.floor(seg % 86400 / 3600), m = Math.floor(seg % 3600 / 60), s = seg % 60;
  if (d) return `${d} d ${h} h ${m} min`;
  if (h) return `${h} h ${m} min`;
  if (m) return `${m} min ${s} s`;
  return `${s} s`;
};

class ErrorDeApi extends Error {
  constructor(estado, codigo, mensaje) { super(mensaje); this.estado = estado; this.codigo = codigo; }
}

async function api(ruta, { metodo = "GET", cuerpo, admin = false } = {}) {
  const encabezados = {};
  if (cuerpo !== undefined) encabezados["Content-Type"] = "application/json";
  // La sesión viaja sola en la cookie HttpOnly que dejó POST /sesiones: el código de la página no la ve.
  if (admin) encabezados["X-Admin-Clave"] = claveAdmin;
  let respuesta;
  try {
    respuesta = await fetch(ruta, { method: metodo, headers: encabezados, body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo) });
  } catch {
    throw new ErrorDeApi(0, "SIN_CONEXION", "No se pudo conectar con la API. Revisá que esté levantada.");
  }
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    if (admin && respuesta.status === 401) { claveAdmin = ""; localStorage.removeItem("admin_clave"); dibujarQuien(); }
    else if (respuesta.status === 401 && sesion.usuario) { sesion.usuario = null; dibujarQuien(); location.hash = "#/ingreso"; }
    const e = datos.error || {};
    const detalle = (e.detalle || []).map((d) => `${d.campo}: ${d.motivo}`).join("; ");
    throw new ErrorDeApi(respuesta.status, e.codigo || "ERROR", [e.mensaje || `La API respondió ${respuesta.status}.`, detalle].filter(Boolean).join(" "));
  }
  datos._estado = respuesta.status;
  return datos;
}

async function iniciarAdministrador() {
  await api("/administracion/acceso", {admin: true});
  const datos = await api("/administracion/usuario-prueba", {metodo: "POST", admin: true});
  if (!claveAdmin) throw new Error("La sesión administrativa se cerró.");
  // El usuario de prueba del administrador también entra con sesión (cookie), como cualquier usuario.
  await api("/sesiones", { metodo: "POST", cuerpo: { usuario_id: datos.usuario.id } });
  sesion.usuario = { id: datos.usuario.id, nombre: datos.usuario.nombre, pais: datos.usuario.pais };
  administradorPreparado = true;
  localStorage.setItem("admin_clave", claveAdmin);
  dibujarQuien();
  return datos;
}

function avisar(texto, mal = false) {
  const caja = document.getElementById("aviso");
  caja.textContent = texto;
  caja.className = mal ? "aviso mal" : "aviso";
  caja.hidden = false;
  clearTimeout(avisar.reloj);
  avisar.reloj = setTimeout(() => { caja.hidden = true; }, mal ? 7000 : 3500);
}

// Un error de la API se muestra como error, con su mensaje: nunca como una lista vacía.
const cajaDeError = (e) => `<p class="alert alert-danger error" role="alert">${esc(e.message)}${e.estado === 503 || e.estado === 504 ? " La base que atiende este bloque no está respondiendo." : ""}</p>`;

function bloque(titulo, fuente, cuerpo, extra = "") {
  return `<section class="card bloque"><header><h2>${esc(titulo)}</h2>${extra}${fuente ? base(fuente) : ""}</header>${cuerpo}</section>`;
}

async function cargarBloque(titulo, fuenteEsperada, promesa, dibujar) {
  try {
    const datos = await promesa;
    return bloque(titulo, datos.fuente || fuenteEsperada, dibujar(datos));
  } catch (e) {
    return bloque(titulo, fuenteEsperada, cajaDeError(e));
  }
}

// ---------- cabecera y pie ----------
function dibujarQuien() {
  const u = sesion.usuario;
  document.getElementById("menu").hidden = !u && !claveAdmin;
  document.getElementById("menu-admin").hidden = !claveAdmin;
  document.getElementById("quien").innerHTML = u
    ? `<span class="quien-usuario">${escudo({ codigo: u.pais })}<span><strong>${esc(u.nombre)}</strong><small>${esc(u.id)}</small></span></span><button class="btn btn-sm quien-salir" id="salir">Cambiar<span class="visually-hidden"> de usuario</span></button>`
    : claveAdmin ? `<span>Administración</span><button class="btn btn-sm quien-salir" id="salir">Salir</button>` : `<a class="quien-entrar" href="#/ingreso">Entrar</a>`;
  document.getElementById("salir")?.addEventListener("click", () => { if (sesion.usuario) api("/sesiones/actual", { metodo: "DELETE" }).catch(() => {}); sesion.usuario = null; claveAdmin = ""; administradorPreparado = false; localStorage.removeItem("admin_clave"); location.hash = "#/ingreso"; dibujarQuien(); });
}

async function dibujarSalud() {
  const caja = document.getElementById("salud");
  try {
    const s = await api("/health/dependencias");
    const una = (nombre, d) => `<b class="${d.estado === "ok" ? "ok" : "caida"}">${nombre}: ${d.estado === "ok" ? "responde" : "no responde"}</b>`;
    const cal = s.calendario;
    const copia = !cal.cargado ? "sin copia del calendario todavía"
      : `copia del calendario de hace ${Math.round(cal.antiguedad_segundos)} s${cal.desactualizado ? " (no se pudo renovar)" : ""}`;
    const otras = [["Redis", s.redis], ["Cassandra América", s.cassandra_america], ["Cassandra Europa", s.cassandra_europa], ["InfluxDB", s.influxdb]]
      .filter(([, d]) => d).map(([n, d]) => una(n, d)).join("");
    caja.innerHTML = `${una("MongoDB", s.mongodb)}${una("Neo4j", s.neo4j)}${otras}<span class="salud-copia">${esc(copia)}</span>`;
  } catch (e) {
    caja.innerHTML = `<b class="caida">API: no responde</b>`;
  }
}

// ---------- ingreso ----------
async function vistaIngreso() {
  contenido.innerHTML = `
    ${portadaTorneo("Entrá al Prode", "Pronosticá los 128 partidos, armá tu grupo con amigos y seguí cada partido con la tribuna de tu país.")}
    <div class="row g-3 g-lg-4">
      <div class="col-12 col-md-6 col-xl-4"><section class="card bloque h-100"><header><h2>Usuario nuevo</h2>${base("mongodb")}</header>
        <form id="alta"><div><label class="form-label" for="nombre">Nombre</label><input class="form-control" id="nombre" required maxlength="60" autocomplete="off"></div>
        <div><label class="form-label" for="pais">País</label><select class="form-select" id="pais"><option>Cargando…</option></select></div>
        <button class="btn btn-primary">Crear usuario y entrar</button><div id="alta-error"></div></form></section></div>
      <div class="col-12 col-md-6 col-xl-4"><section class="card bloque h-100"><header><h2>Usuario existente</h2>${base("mongodb")}</header>
        <form id="entrar"><div><label class="form-label" for="uid">Identificador</label><input class="form-control" id="uid" placeholder="U0000001" pattern="[Uu][0-9]{7}" required autocomplete="off"></div>
        <button class="btn btn-outline-primary">Entrar</button><div id="entrar-error" role="alert"></div></form></section></div>
      <div class="col-12 col-md-6 col-xl-4"><section class="card bloque h-100"><header><h2>Administración</h2></header><form id="entrar-admin"><div><label class="form-label" for="clave-ingreso">Clave de administración</label><input class="form-control" id="clave-ingreso" type="password" required autocomplete="off"></div><button class="btn btn-outline-primary">Entrar a administración</button><div id="ingreso-admin-error" role="alert"></div></form></section></div>
    </div>`;
  const pais = document.getElementById("pais");
  const altaError = document.getElementById("alta-error");
  catalogoEquipos().then((equipos) => {
    const lista = [...equipos.values()].sort((a, b) => a.nombre.localeCompare(b.nombre, "es"));
    pais.innerHTML = lista.map((e) => `<option value="${esc(e.codigo)}">${banderaEmoji(e.codigo) ? banderaEmoji(e.codigo) + " " : ""}${esc(e.nombre)}</option>`).join("");
    pais.value = equipos.has("ARG") ? "ARG" : lista[0]?.codigo;
  }).catch((e) => { altaError.innerHTML = cajaDeError(e); });

  // Abre la sesión en Redis; la API deja la cookie. Se guarda aparte solo lo que se muestra (nombre, país).
  const entrarCon = async (usuarioId) => {
    const d = await api("/sesiones", { metodo: "POST", cuerpo: { usuario_id: usuarioId } });
    claveAdmin = ""; administradorPreparado = false; localStorage.removeItem("admin_clave");
    sesion.usuario = { id: d.usuario.id, nombre: d.usuario.nombre, pais: d.usuario.pais };
    dibujarQuien(); location.hash = "#/en-vivo";
  };
  document.getElementById("alta").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    try {
      const d = await api("/usuarios", { metodo: "POST", cuerpo: { nombre: document.getElementById("nombre").value, pais: document.getElementById("pais").value } });
      avisar(`Usuario ${d.usuario.id} creado.`);
      await entrarCon(d.usuario.id);
    } catch (e) { document.getElementById("alta-error").innerHTML = cajaDeError(e); }
  });
  document.getElementById("entrar").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    try {
      await entrarCon(document.getElementById("uid").value.trim().toUpperCase());
    } catch (e) { claveAdmin = ""; document.getElementById("entrar-error").innerHTML = cajaDeError(e); }
  });
  document.getElementById("entrar-admin").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    claveAdmin = document.getElementById("clave-ingreso").value;
    try { await iniciarAdministrador(); location.hash = "#/en-vivo"; }
    catch (e) { claveAdmin = ""; document.getElementById("ingreso-admin-error").innerHTML = cajaDeError(e); }
  });
}

// ---------- portada del torneo ----------
// Seis anfitriones en tres continentes: la franja se repite en el ingreso y en la portada.
function portadaTorneo(titulo, bajada, extra = "") {
  return `<section class="portada" aria-labelledby="portada-titulo">
    <div class="portada-cancha" aria-hidden="true"></div>
    <div class="portada-cuerpo">
      <p class="portada-volanta">Mundial 2030 · 64 selecciones · 128 partidos</p>
      <h1 id="portada-titulo">${esc(titulo)}</h1>
      <p class="portada-bajada">${esc(bajada)}</p>
      <ul class="anfitriones" aria-label="Países anfitriones">
        ${ANFITRIONES.map(([codigo, nombre]) => `<li>${escudo({ codigo })}<span>${esc(nombre)}</span></li>`).join("")}
      </ul>
      <p class="portada-continentes">Sudamérica · Europa · África</p>
      ${extra}
    </div>
  </section>`;
}

// ---------- fixture ----------
const FASES = ["Fase de grupos", "Dieciseisavos", "Octavos", "Cuartos", "Semifinal", "Tercer puesto", "Final"];
const GRUPOS = "ABCDEFGHIJKLMNOP".split("");
let faseElegida = "Fase de grupos";
let grupoElegido = "";

// Una tarjeta para el fixture, la portada y el historial: los equipos siempre ocupan una fila cada uno.
function tarjetaPartido(p, {
  estado = p.estado, marcador = [p.goles_local, p.goles_visitante], minuto, detalle, accion, grupo, conFecha = true,
} = {}) {
  const equipo = (e, goles) => `<div class="partido-equipo">
    ${escudo(e)}<span class="partido-nombre">${nombreEquipo(e)}</span><strong class="partido-goles">${esc(goles ?? "–")}</strong>
  </div>`;
  const cuando = conFecha ? fecha(p.fecha_hora) : hora(p.fecha_hora);
  return `<div class="col"><a class="card partido h-100 ${claseEstado(estado)}" href="#/partido/${esc(p.id)}">
    <div class="card-body">
      <div class="partido-cabecera"><span>${grupo ? `<b class="partido-grupo">Grupo ${esc(grupo)}</b> · ` : ""}${esc(p.id)} · ${esc(cuando)}</span>
        <span class="estado ${claseEstado(estado)}">${estado === "En juego" ? '<span class="punto-vivo" aria-hidden="true"></span>' : ""}${esc(estado)}${minuto == null ? "" : ` · ${esc(minuto)}′`}</span>
      </div>
      <div class="partido-equipos">${equipo(p.local, marcador[0])}${equipo(p.visitante, marcador[1])}</div>
    </div>
    ${detalle || accion ? `<div class="partido-pie">
      ${detalle ? `<span>${esc(detalle)}</span>` : ""}${accion ? `<strong>${esc(accion)}</strong>` : ""}
    </div>` : ""}
  </a></div>`;
}

// Agrupa por día y por horario de inicio. Dos o más partidos con el mismo horario se juegan en simultáneo.
function partidosPorHorario(partidos, equipos, hastaInicioReal) {
  const dias = new Map();
  for (const p of partidos) {
    const dia = claveDia(p.fecha_hora);
    if (!dias.has(dia)) dias.set(dia, { fecha: p.fecha_hora, horarios: new Map() });
    const horarios = dias.get(dia).horarios;
    if (!horarios.has(p.fecha_hora)) horarios.set(p.fecha_hora, []);
    horarios.get(p.fecha_hora).push(p);
  }
  return [...dias.values()].map(({ fecha: f, horarios }) => `<section class="jornada" aria-label="${esc(diaLargo(f))}">
    <h2 class="jornada-dia">${esc(diaLargo(f))}</h2>
    ${[...horarios.entries()].map(([inicio, lista]) => `<div class="horario">
      <div class="horario-cabecera"><span class="horario-hora">${esc(hora(inicio))}</span>${lista.length > 1 ? `<span class="simultaneo">En simultáneo · ${lista.length} partidos</span>` : ""}</div>
      <div class="row row-cols-1 row-cols-md-2 g-3">${lista.map(p => tarjetaPartido(p, {
        conFecha: false, grupo: grupoDe(p, equipos),
        detalle: [p.estadio?.nombre, p.estadio?.ciudad].filter(Boolean).join(", "),
        accion: pronosticoAbierto(p, hastaInicioReal) ? "Hacer pronóstico" : null,
      })).join("")}</div>
    </div>`).join("")}
  </section>`).join("");
}

async function vistaFixture() {
  contenido.innerHTML = `
    <div class="titulo"><div><h1>Fixture</h1><p>Los 128 partidos, día por día. En la fase de grupos, los dos partidos de cada grupo se juegan a la misma hora.</p></div>${base("neo4j")}</div>
    <div class="fixture-fases">
      <label class="form-label" for="fases-movil" id="fases-titulo">Fase del torneo</label>
      <select id="fases-movil" class="form-select d-md-none">${FASES.map(f => `<option value="${esc(f)}">${esc(f)}</option>`).join("")}</select>
      <div class="filtros d-none d-md-flex" role="group" aria-labelledby="fases-titulo">${FASES.map(f => `<button type="button" class="btn btn-sm" aria-pressed="${f === faseElegida}" data-fase="${esc(f)}">${esc(f)}</button>`).join("")}</div>
      <div id="filtro-grupo" class="filtro-grupo">
        <label class="form-label" for="grupo-elegido">Grupo</label>
        <select id="grupo-elegido" class="form-select"><option value="">Todos los grupos</option>${GRUPOS.map(g => `<option value="${g}">Grupo ${g}</option>`).join("")}</select>
      </div>
    </div>
    <div id="fixture-estado" class="fixture-estado" role="status"></div>
    <div id="lista" class="partidos"></div>`;
  const lista = document.getElementById("lista"), estado = document.getElementById("fixture-estado");
  const fases = [...contenido.querySelectorAll("[data-fase]")];
  const selectorFase = document.getElementById("fases-movil");
  const selectorGrupo = document.getElementById("grupo-elegido"), filtroGrupo = document.getElementById("filtro-grupo");
  selectorGrupo.value = grupoElegido;
  let consulta = 0;
  async function cargarFase(fase) {
    const actual = ++consulta;
    faseElegida = fase;
    selectorFase.value = fase;
    fases.forEach(b => b.setAttribute("aria-pressed", String(b.dataset.fase === fase)));
    filtroGrupo.hidden = fase !== "Fase de grupos";
    estado.textContent = "Cargando partidos…";
    lista.setAttribute("aria-busy", "true");
    lista.replaceChildren();
    try {
      const [d, equipos] = await Promise.all([api(`/partidos?fase=${encodeURIComponent(fase)}`), catalogoEquipos().catch(() => null)]);
      if (actual !== consulta || !lista.isConnected) return;
      const elegidos = fase === "Fase de grupos" && grupoElegido && equipos
        ? d.partidos.filter(p => grupoDe(p, equipos) === grupoElegido) : d.partidos;
      const simultaneos = new Set(elegidos.map(p => p.fecha_hora)).size;
      estado.textContent = elegidos.length
        ? `${elegidos.length} ${elegidos.length === 1 ? "partido" : "partidos"} en ${simultaneos} ${simultaneos === 1 ? "horario" : "horarios"}`
        : "No hay partidos en esta fase.";
      lista.innerHTML = partidosPorHorario(elegidos, equipos, d.pronosticos_hasta_inicio_real);
    } catch (e) {
      if (actual !== consulta || !lista.isConnected) return;
      estado.innerHTML = cajaDeError(e);
    } finally {
      if (actual === consulta) lista.removeAttribute("aria-busy");
    }
  }
  fases.forEach(b => b.addEventListener("click", () => cargarFase(b.dataset.fase)));
  selectorFase.addEventListener("change", () => cargarFase(selectorFase.value));
  selectorGrupo.addEventListener("change", () => { grupoElegido = selectorGrupo.value; cargarFase(faseElegida); });
  await cargarFase(faseElegida);
}

// ---------- grupos ----------
// Las tablas de posiciones no se guardan en ninguna base: se calculan acá con los partidos finalizados.
function tablaDeGrupo(equiposDelGrupo, partidos) {
  const filas = new Map(equiposDelGrupo.map(e => [e.codigo, { equipo: e, pj: 0, g: 0, e: 0, p: 0, gf: 0, gc: 0 }]));
  for (const p of partidos) {
    if (p.estado !== "Finalizado" || p.goles_local == null) continue;
    const local = filas.get(p.local?.codigo), visitante = filas.get(p.visitante?.codigo);
    if (!local || !visitante) continue;
    for (const [fila, propios, ajenos] of [[local, p.goles_local, p.goles_visitante], [visitante, p.goles_visitante, p.goles_local]]) {
      fila.pj++; fila.gf += propios; fila.gc += ajenos;
      if (propios > ajenos) fila.g++; else if (propios === ajenos) fila.e++; else fila.p++;
    }
  }
  return [...filas.values()].map(f => ({ ...f, dg: f.gf - f.gc, pts: 3 * f.g + f.e }))
    .sort((a, b) => b.pts - a.pts || b.dg - a.dg || b.gf - a.gf || a.equipo.nombre.localeCompare(b.equipo.nombre, "es"));
}

async function vistaGrupos() {
  contenido.innerHTML = `
    <div class="titulo"><div><h1>Fase de grupos</h1><p>16 grupos de 4. Pasan los dos primeros de cada grupo a los dieciseisavos de final.</p></div><div class="titulo-bases">${base("mongodb")}${base("neo4j")}</div></div>
    <p class="nota grupos-aclaracion">Las tablas se calculan en tu navegador con los partidos finalizados del fixture (Neo4j) y el catálogo de selecciones (MongoDB). Orden: puntos, diferencia de gol y goles a favor.</p>
    <div id="grupos" class="grupos" aria-busy="true"><p class="vacio">Cargando grupos…</p></div>`;
  const caja = document.getElementById("grupos");
  try {
    const [equipos, d] = await Promise.all([catalogoEquipos(), api("/partidos?fase=" + encodeURIComponent("Fase de grupos"))]);
    if (!caja.isConnected) return;
    const porGrupo = new Map(GRUPOS.map(g => [g, []]));
    for (const e of equipos.values()) (porGrupo.get(e.grupo) || porGrupo.set(e.grupo, []).get(e.grupo)).push(e);
    const partidosDe = (g) => d.partidos.filter(p => grupoDe(p, equipos) === g);
    const jugados = d.partidos.filter(p => p.estado === "Finalizado").length;
    caja.innerHTML = `<p class="grupos-avance">${jugados} de ${d.partidos.length} partidos de grupos jugados</p>
      <div class="row row-cols-1 row-cols-md-2 row-cols-xl-3 g-3">${[...porGrupo.entries()].filter(([, lista]) => lista.length).map(([g, lista]) => {
        const partidos = partidosDe(g);
        const proximo = partidos.filter(p => p.estado !== "Finalizado").sort((a, b) => new Date(a.fecha_hora) - new Date(b.fecha_hora))[0];
        const filas = tablaDeGrupo(lista, partidos);
        return `<div class="col"><section class="card grupo" aria-labelledby="grupo-${g}">
          <header class="grupo-cabecera"><h2 id="grupo-${g}"><span class="grupo-letra">${g}</span>Grupo ${g}</h2>${proximo ? `<a href="#/partido/${esc(proximo.id)}" class="grupo-proximo">${proximo.estado === "En juego" ? "En juego" : "Próximo"}: ${esc(fecha(proximo.fecha_hora))}</a>` : '<span class="grupo-proximo">Completo</span>'}</header>
          <div class="tabla-caja" tabindex="0" role="region" aria-label="Posiciones del grupo ${g}"><table class="tabla-grupo">
            <thead><tr><th scope="col" class="pos"><span class="visually-hidden">Posición</span>#</th><th scope="col">Selección</th><th scope="col" class="n" title="Partidos jugados">PJ</th><th scope="col" class="n" title="Ganados">G</th><th scope="col" class="n" title="Empatados">E</th><th scope="col" class="n" title="Perdidos">P</th><th scope="col" class="n opcional" title="Goles a favor">GF</th><th scope="col" class="n opcional" title="Goles en contra">GC</th><th scope="col" class="n" title="Diferencia de gol">DG</th><th scope="col" class="n" title="Puntos">Pts</th></tr></thead>
            <tbody>${filas.map((f, i) => `<tr class="${i < 2 ? "clasifica" : ""}"><td class="pos">${i + 1}</td><td><span class="grupo-equipo">${escudo(f.equipo)}<span>${esc(f.equipo.nombre)}</span></span></td><td class="n">${f.pj}</td><td class="n">${f.g}</td><td class="n">${f.e}</td><td class="n">${f.p}</td><td class="n opcional">${f.gf}</td><td class="n opcional">${f.gc}</td><td class="n">${f.dg > 0 ? "+" : ""}${f.dg}</td><td class="n pts">${f.pts}</td></tr>`).join("")}</tbody>
          </table></div>
          <p class="grupo-nota"><span class="marca-clasifica" aria-hidden="true"></span>Los dos primeros pasan a dieciseisavos.</p>
        </section></div>`;
      }).join("")}</div>`;
  } catch (e) { if (caja.isConnected) caja.innerHTML = cajaDeError(e); }
  finally { caja.removeAttribute("aria-busy"); }
}

// ---------- partido en vivo: conexión, tribuna y audiencia ----------
// Una conexión abierta por pestaña (eventos del servidor). Trae los comentarios de la tribuna elegida, el estado
// del partido y la audiencia; mientras está abierta, este usuario cuenta como espectador de su país.
let conexionVivo = null;
function cerrarVivo() { if (conexionVivo) { conexionVivo.close(); conexionVivo = null; } }

function abrirVivo(id, alcance, manejadores, alEstadoConexion) {
  cerrarVivo();
  const fuente = new EventSource(`/partidos/${encodeURIComponent(id)}/vivo?alcance=${alcance}`);
  conexionVivo = fuente;
  const leer = (tipo) => fuente.addEventListener(tipo, (ev) => { try { manejadores[tipo]?.(JSON.parse(ev.data)); } catch { /* mensaje dañado: se ignora */ } });
  ["comentario", "estado", "audiencia"].forEach(leer);
  fuente.addEventListener("error", (ev) => {
    if (ev.data) { try { alEstadoConexion(JSON.parse(ev.data).mensaje); } catch { alEstadoConexion("Sin conexión"); } }
    else alEstadoConexion(fuente.readyState === EventSource.CLOSED ? "Sin conexión" : "Reconectando…");
  });
  fuente.addEventListener("open", () => alEstadoConexion("En vivo"));
  return fuente;
}

const movimientoReducido = window.matchMedia?.("(prefers-reduced-motion: reduce)") ?? { matches: true };

function animarVivo(elemento, inicio, fin, duracion, ease = "power2.out") {
  if (movimientoReducido.matches || document.hidden) return;
  window.gsap?.fromTo(elemento, inicio, {
    ...fin, duration: duracion, ease, overwrite: "auto",
    clearProps: Object.keys(fin).join(","),
  });
}

const entradasVivo = typeof IntersectionObserver === "function" ? new IntersectionObserver(entradas => {
  for (const { target: fila, isIntersecting } of entradas) {
    if (!isIntersecting) continue;
    entradasVivo.unobserve(fila);
    fila.classList.remove("entrada-vivo-pendiente");
    animarVivo(fila, { opacity: 0 }, { opacity: 1 }, .52, "sine.out");
  }
}, { rootMargin: "0px 0px -2px 0px" }) : null;

function fundirEntradaVivo(fila) {
  if (movimientoReducido.matches || document.hidden || !window.gsap) return;
  if (!entradasVivo) {
    animarVivo(fila, { opacity: 0 }, { opacity: 1 }, .52, "sine.out");
    return;
  }
  // La fila ocupa su lugar antes de verse. El fade empieza al entrar en el área visible.
  fila.classList.add("entrada-vivo-pendiente");
  entradasVivo.observe(fila);
}

function seguirListaEnVivo(lista) {
  let desplazamiento = null, leyendo = false;
  const final = () => Math.max(0, lista.scrollHeight - lista.clientHeight);
  function detener() {
    desplazamiento?.kill();
    desplazamiento = null;
  }
  function pausaManual() {
    detener();
    leyendo = final() > 0;
  }
  lista.addEventListener("wheel", ev => {
    if (ev.deltaY < 0 || (ev.deltaY > 0 && desplazamiento)) pausaManual();
  }, { passive: true });
  lista.addEventListener("touchmove", pausaManual, { passive: true });
  lista.addEventListener("pointerdown", ev => {
    if (ev.target === lista && ev.clientX >= lista.getBoundingClientRect().left + lista.clientWidth) pausaManual();
  });
  lista.addEventListener("keydown", ev => {
    const sube = ["ArrowUp", "PageUp", "Home"].includes(ev.key) || (ev.key === " " && ev.shiftKey);
    const baja = ["ArrowDown", "PageDown", "End", " "].includes(ev.key);
    if (sube || (baja && desplazamiento)) pausaManual();
  });
  lista.addEventListener("scroll", () => {
    if (final() - lista.scrollTop <= 2) leyendo = false;
  }, { passive: true });

  return {
    detener,
    siguiendo: () => !leyendo && (desplazamiento !== null || final() - lista.scrollTop < 48),
    irAlFinal(inmediato = false) {
      leyendo = false;
      const destino = final();
      if (inmediato || movimientoReducido.matches || document.hidden || !window.gsap) {
        detener();
        lista.scrollTop = destino;
      } else if (desplazamiento) {
        desplazamiento.resetTo("scrollTop", destino, lista.scrollTop);
      } else if (Math.abs(destino - lista.scrollTop) > 1) {
        desplazamiento = window.gsap.to(lista, {
          scrollTop: destino, duration: .46, ease: "power2.out",
          onComplete: () => { desplazamiento = null; },
        });
      }
    },
  };
}

function iniciarComentarios(id, partido, vivo) {
  const caja = document.getElementById("comentarios");
  const usuario = sesion.usuario, pais = usuario?.pais || "ARG";
  const formulario = usuario ? `<form id="comentario-form" style="margin-top:16px"><label class="form-label" for="comentario-texto">Tu comentario en la tribuna de ${esc(pais)}</label><textarea class="form-control" id="comentario-texto" maxlength="280" rows="2" required placeholder="Sumate a la conversación" aria-describedby="comentario-mensaje"></textarea><button class="btn btn-primary" id="comentario-enviar" ${partido.estado === "En juego" ? "" : "disabled"}>Enviar comentario</button><p id="comentario-mensaje" role="status"></p></form>` : `<p><a href="#/ingreso">Ingresá</a> para comentar.</p>`;
  caja.innerHTML = `<section class="card bloque tribuna"><header><div><h2>Comentarios</h2><div class="nav nav-pills tribuna-pestanas" role="tablist"><button class="btn btn-outline-primary" type="button" role="tab" data-alcance="pais" aria-selected="true">Mi país (${esc(pais)})</button><button class="btn btn-outline-primary" type="button" role="tab" data-alcance="todos" aria-selected="false">Todos los países</button></div></div><div class="tribuna-lado"><span class="tribuna-estado" id="comentarios-estado" role="status">Conectando…</span>${base("cassandra")}</div></header><div id="comentarios-lista" class="comentarios-lista" tabindex="0" role="log" aria-label="Comentarios"><p class="vacio">Todavía no hay comentarios.</p></div>${formulario}</section>`;
  let alcance = "pais", siguiente = null, version = 0;
  const lista = caja.querySelector("#comentarios-lista");
  const seguimiento = seguirListaEnVivo(lista);
  const indicador = caja.querySelector("#comentarios-estado");
  const vacio = lista.firstElementChild;
  const conocidos = new Set();
  // La API devuelve el nombre público, que no es único. Reconocemos los IDs enviados por este usuario en este navegador.
  const clavePropios = usuario ? `prode:comentarios-propios:${usuario.id}` : null;
  const propios = new Set();
  if (clavePropios) {
    try {
      const guardados = JSON.parse(localStorage.getItem(clavePropios) || "[]");
      if (Array.isArray(guardados)) guardados.slice(-200).forEach(id => propios.add(id));
    } catch { /* El resaltado sigue funcionando en esta vista. */ }
  }
  const anteriores = document.createElement("button");
  anteriores.type = "button"; anteriores.className = "btn btn-outline-primary btn-sm align-self-start"; anteriores.textContent = "Ver comentarios anteriores"; anteriores.hidden = true;
  lista.before(anteriores);
  const estado = texto => { indicador.textContent = texto; };
  const consultaTribuna = () => alcance === "todos" ? "alcance=todos" : `pais=${encodeURIComponent(pais)}`;

  function filaComentario(c) {
    conocidos.add(c.comentario_id);
    const propio = propios.has(c.comentario_id);
    const fila = document.createElement("article");
    fila.className = propio ? "comentario comentario-propio" : "comentario";
    fila.innerHTML = `<span class="comentario-avatar" aria-hidden="true">${esc((c.usuario_nombre || "H").slice(0, 1).toUpperCase())}</span><div><div class="comentario-cabecera"><strong>${esc(c.usuario_nombre)}</strong>${propio ? '<span class="comentario-tu">Tu comentario</span>' : ""}${alcance === "todos" ? `<span class="comentario-pais">${esc(c.pais)}</span>` : ""}</div><p>${esc(c.contenido)}</p></div>`;
    vacio.remove();
    return fila;
  }

  function sumar(c) {
    if (!caja.isConnected || conocidos.has(c.comentario_id)) return;
    if (alcance === "pais" && c.pais !== pais) return;
    const seguir = seguimiento.siguiendo() || propios.has(c.comentario_id);
    const fila = filaComentario(c);
    lista.append(fila);
    fundirEntradaVivo(fila);
    if (seguir) {
      if (lista.childElementCount > 40) {
        const alto = lista.scrollHeight, posicion = lista.scrollTop;
        while (lista.childElementCount > 40) {
          const primera = lista.firstElementChild;
          entradasVivo?.unobserve(primera);
          primera.remove();
        }
        lista.scrollTop = posicion - (alto - lista.scrollHeight);
      }
      seguimiento.irAlFinal();
    }
  }

  async function cambiar(nuevo) {
    const peticion = ++version;
    alcance = nuevo; siguiente = null; anteriores.hidden = true;
    seguimiento.detener();
    lista.querySelectorAll(".entrada-vivo-pendiente").forEach(fila => entradasVivo?.unobserve(fila));
    conocidos.clear(); lista.replaceChildren(vacio);
    caja.querySelectorAll("[data-alcance]").forEach(b => b.setAttribute("aria-selected", String(b.dataset.alcance === alcance)));
    try {
      const datos = await api(`/partidos/${encodeURIComponent(id)}/comentarios?${consultaTribuna()}&limit=20`);
      if (!caja.isConnected || peticion !== version) return;
      const filas = datos.items.slice().reverse().filter(c => !conocidos.has(c.comentario_id)).map(filaComentario);
      lista.prepend(...filas);
      seguimiento.irAlFinal(true);
      siguiente = datos.siguiente; anteriores.hidden = !siguiente;
    } catch (e) { if (peticion === version) estado(e.message); }
    if (!caja.isConnected || peticion !== version) return;
    if (usuario && partido.estado !== "Finalizado") abrirVivo(id, alcance, {
      ...vivo, comentario: c => { if (peticion === version) sumar(c); },
    }, estado);
    else estado(partido.estado === "Finalizado" ? "Partido terminado" : "Ingresá para seguirlo en vivo");
  }
  caja.querySelectorAll("[data-alcance]").forEach(b => b.addEventListener("click", () => { if (b.dataset.alcance !== alcance) cambiar(b.dataset.alcance); }));
  anteriores.addEventListener("click", async () => {
    if (!siguiente) return;
    const peticion = version;
    anteriores.disabled = true;
    try {
      const datos = await api(`/partidos/${encodeURIComponent(id)}/comentarios?${consultaTribuna()}&limit=20&antes_de=${encodeURIComponent(siguiente)}`);
      if (!caja.isConnected || peticion !== version) return;
      seguimiento.detener();
      const alto = lista.scrollHeight, posicion = lista.scrollTop;
      const filas = datos.items.slice().reverse().filter(c => !conocidos.has(c.comentario_id)).map(filaComentario);
      lista.prepend(...filas);
      lista.scrollTop = posicion + lista.scrollHeight - alto;
      siguiente = datos.siguiente; anteriores.hidden = !siguiente;
    } catch (e) { if (peticion === version) estado(e.message); }
    finally { anteriores.disabled = false; }
  });
  document.getElementById("comentario-form")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const form = ev.currentTarget, texto = document.getElementById("comentario-texto"), boton = document.getElementById("comentario-enviar"), mensaje = document.getElementById("comentario-mensaje");
    const contenido = texto.value.trim(); if (!contenido) { mensaje.textContent = "Escribí un comentario."; return; }
    // El mismo identificador en cada reintento del mismo texto: si el primero llegó, la API no lo duplica.
    if (form.dataset.texto !== contenido) { form.dataset.texto = contenido; form.dataset.id = crypto.randomUUID(); }
    // Registrar antes del POST: la copia por SSE puede llegar antes que la respuesta.
    propios.add(form.dataset.id);
    if (propios.size > 200) propios.delete(propios.values().next().value);
    try { localStorage.setItem(clavePropios, JSON.stringify([...propios])); } catch { /* El resaltado sigue funcionando en esta vista. */ }
    boton.disabled = true; boton.dataset.enviando = "si"; mensaje.textContent = "Enviando…";
    try {
      const comentario = await api(`/partidos/${encodeURIComponent(id)}/comentarios`, { metodo: "POST", cuerpo: { comentario_id: form.dataset.id, contenido } });
      if (!caja.isConnected) return;
      sumar(comentario);
      texto.value = ""; delete form.dataset.texto; mensaje.textContent = "Comentario enviado.";
    } catch (e) { if (caja.isConnected) mensaje.textContent = e.estado === 429 ? "Modo lento: esperá unos segundos y volvé a enviar." : e.message; }
    finally { if (boton.isConnected) { boton.dataset.enviando = "no"; boton.disabled = boton.dataset.cerrado === "si"; } }
  });
  cambiar("pais");
}

// Curva de espectadores simultáneos minuto a minuto, con los goles marcados.
function curvaAudiencia(puntos, goles = []) {
  if (!puntos.length) return `<p class="vacio">Todavía no hay audiencia medida.</p>`;
  const ancho = 600, alto = 140, maximo = Math.max(1, ...puntos.map(p => p.total));
  const x = (m) => (m / 90) * ancho, y = (v) => alto - 6 - (v / maximo) * (alto - 16);
  const linea = puntos.map(p => `${x(p.minuto).toFixed(1)},${y(p.total).toFixed(1)}`).join(" ");
  const area = `0,${alto} ${linea} ${x(puntos[puntos.length - 1].minuto).toFixed(1)},${alto}`;
  const marcas = goles.map(g => `<line class="curva-gol" x1="${x(g.minuto)}" x2="${x(g.minuto)}" y1="0" y2="${alto}"><title>Gol ${esc(g.equipo_id)} ${g.minuto}′</title></line>`).join("");
  // Las etiquetas van fuera del SVG: el gráfico se estira a lo ancho y deformaría el texto.
  const etiquetas = goles.map(g => `<span class="curva-gol-texto" style="left:${(g.minuto / 90 * 100).toFixed(1)}%">Gol ${esc(g.equipo_id)} ${g.minuto}′</span>`).join("");
  return `<div class="curva-caja"><div class="curva-goles">${etiquetas}</div><svg class="curva-audiencia" viewBox="0 0 ${ancho} ${alto}" preserveAspectRatio="none" role="img" aria-label="Espectadores por minuto, máximo ${maximo}"><polygon class="curva-area" points="${area}"/><polyline class="curva-linea" points="${linea}"/>${marcas}</svg></div><div class="curva-eje"><span>0′</span><span>45′</span><span>90′</span></div>`;
}

function iniciarAudiencia(id, estadoPartido) {
  const caja = document.getElementById("audiencia");
  const pais = sesion.usuario?.pais;
  const puntos = [];
  caja.innerHTML = bloque("Audiencia", "redis", `<div class="audiencia-ahora" id="aud-ahora" ${estadoPartido === "Finalizado" ? "hidden" : ""}><div><span>Mirando ahora</span><strong id="aud-total">—</strong></div>${pais ? `<div><span>Desde ${esc(pais)}</span><strong id="aud-pais">—</strong></div>` : ""}</div><div id="aud-curva">${curvaAudiencia([])}</div><div id="aud-resumen"></div>`);
  const fijar = (sel, v) => { const e = document.getElementById(sel); if (e) e.textContent = v; };
  async function analisis() {
    try {
      const d = await api(`/partidos/${encodeURIComponent(id)}/audiencia`);
      if (!caja.isConnected) return;
      document.getElementById("aud-curva").innerHTML = curvaAudiencia(d.curva, d.goles);
      const tarjeta = (titulo, valor) => `<div><span>${esc(titulo)}</span><strong>${esc(valor)}</strong></div>`;
      document.getElementById("aud-resumen").innerHTML = `<div class="audiencia-resumen">${tarjeta("Pico", d.pico ? `${d.pico.espectadores} en el ${d.pico.minuto}′` : "—")}${tarjeta("Promedio", d.promedio ?? "—")}${tarjeta("Minutos vistos", d.minutos_vistos)}${tarjeta("Espectadores únicos", d.unicos.total)}${tarjeta("Tiempo medio", d.tiempo_medio_min == null ? "—" : `${d.tiempo_medio_min} min`)}</div><p class="nota">Análisis guardado en InfluxDB${d.incompleta ? "; faltan algunos minutos por una falla" : ""}. ${base("influxdb")}</p>`;
    } catch (e) { if (e.estado !== 404 && caja.isConnected) document.getElementById("aud-resumen").innerHTML = cajaDeError(e); }
  }
  if (estadoPartido === "Finalizado") analisis();
  return {
    audiencia(a) { fijar("aud-total", a.total); fijar("aud-pais", a.mi_pais); },
    minuto(m, total) {
      if (puntos.length && puntos[puntos.length - 1].minuto >= m) return;
      puntos.push({ minuto: m, total }); const c = document.getElementById("aud-curva"); if (c) c.innerHTML = curvaAudiencia(puntos);
    },
    terminado() { const ahora = document.getElementById("aud-ahora"); if (ahora) ahora.hidden = true; analisis(); },
  };
}

function iniciarRelato(id, partido) {
  const caja = document.getElementById("relato-lista");
  const seguimiento = seguirListaEnVivo(caja);
  const estado = document.getElementById("relato-estado");
  const seccion = caja.closest("section");
  seccion.hidden = true;
  const cola = [], vistos = new Set(), nombres = new Map();
  const equipos = [partido.local, partido.visitante].filter(Boolean);
  const textoJugada = (j) => {
    if (j.texto) return j.texto;
    const nombre = nombres.get(j.jugador_id) || "Un jugador";
    const equipo = equipos.find(e => e.codigo === j.equipo_id)?.nombre || j.equipo_id;
    const verbos = {pase: "completa un pase", tiro: "remata al arco", gol: "convierte un gol", falta: "comete una falta", amarilla: "recibe una tarjeta amarilla", roja: "recibe una tarjeta roja", cambio: "participa en un cambio"};
    // Un tiro registrado no especifica si fue al arco.
    if (j.categoria === "tiro") return `${nombre} remata para ${equipo}.`;
    if (j.categoria === "pase" && j.resultado !== "exitoso") return `${nombre} intenta un pase para ${equipo}.`;
    return `${nombre} ${verbos[j.categoria] || "participa en una jugada"} para ${equipo}.`;
  };
  const nombresListos = Promise.allSettled(equipos.map(e => api(`/equipos/${encodeURIComponent(e.codigo)}/jugadores?limit=50`))).then(resultados => {
    resultados.forEach(r => { if (r.status === "fulfilled") (r.value.jugadores || []).forEach(j => nombres.set(j.id, [j.nombre, j.apellido].filter(Boolean).join(" "))); });
  });
  let consultando = false, cargaInicial = true;
  async function actualizar() {
    if (consultando || !caja.isConnected) return;
    consultando = true;
    try {
      const datos = await api(`/partidos/${encodeURIComponent(id)}/jugadas/temporales`);
      if (!caja.isConnected) return;
      seccion.hidden = datos.jugadas.length === 0 && vistos.size === 0;
      datos.jugadas.forEach(j => { if (!vistos.has(j.evento_id)) { vistos.add(j.evento_id); cola.push(j); } });
      if (cola.length && (cargaInicial || partido.estado === "Finalizado")) {
        const seguir = cargaInicial || seguimiento.siguiendo();
        while (cola.length) mostrar(false);
        if (seguir) seguimiento.irAlFinal(true);
      }
      cargaInicial = false;
      estado.textContent = datos.incompletas ? "Actualización incompleta" : "Actualizado";
    } catch (e) {
      if (caja.isConnected && e.estado !== 404) { seccion.hidden = false; estado.textContent = "No se pudo actualizar"; }
    } finally { consultando = false; }
  }
  function mostrar(animar = true) {
    if (!caja.isConnected || !cola.length) return;
    const jugada = cola.shift();
    const vacio = caja.querySelector(".vacio"); if (vacio) vacio.remove();
    const seguir = animar && seguimiento.siguiendo();
    const fila = document.createElement("article"); fila.className = jugada.categoria === "gol" ? "relato-accion relato-gol" : "relato-accion";
    fila.innerHTML = `<span class="relato-minuto">${esc(jugada.minuto)}′</span><div><strong>${esc(textoJugada(jugada))}</strong><span>${esc(jugada.equipo_id)}</span></div>`;
    caja.appendChild(fila);
    if (animar && partido.estado === "En juego") fundirEntradaVivo(fila);
    if (seguir) seguimiento.irAlFinal();
  }
  nombresListos.then(() => {
    if (!caja.isConnected) return;
    actualizar();
    if (partido.estado !== "Finalizado") {
      comentariosTimers.push(setInterval(actualizar, 1000));
      comentariosTimers.push(setInterval(mostrar, 1000));
    }
  });
}

function marcadorPortada({ partido, minuto, marcador }, equipos) {
  const grupo = grupoDe(partido, equipos);
  return `<article class="vivo-partido">
    <div class="vivo-partido-info">
      <span class="vivo-indicador"><span class="punto-vivo" aria-hidden="true"></span>En juego</span><span class="vivo-minuto">${esc(minuto ?? 0)}′</span>
      <span class="vivo-meta">${grupo ? `Grupo ${esc(grupo)}` : esc(partido.fase)}${partido.estadio?.ciudad ? ` · ${esc(partido.estadio.ciudad)}` : ""}</span>
    </div>
    <div class="vivo-marcador">
      <span class="vivo-equipo">${escudo(partido.local)}<strong>${nombreEquipo(partido.local)}</strong></span>
      <span class="vivo-goles" aria-label="${esc(marcador?.local ?? 0)} a ${esc(marcador?.visitante ?? 0)}"><span>${esc(marcador?.local ?? 0)}</span><span class="vivo-guion" aria-hidden="true">–</span><span>${esc(marcador?.visitante ?? 0)}</span></span>
      <span class="vivo-equipo vivo-equipo-visitante"><strong>${nombreEquipo(partido.visitante)}</strong>${escudo(partido.visitante)}</span>
    </div>
    <a class="btn vivo-accion" href="#/partido/${esc(partido.id)}">Seguir partido<span class="visually-hidden">: ${nombreEquipo(partido.local)} vs ${nombreEquipo(partido.visitante)}</span></a>
  </article>`;
}

async function vistaEnVivo() {
  contenido.innerHTML = `
    <section class="inicio-vivo" aria-labelledby="portada-vivo-titulo">
      <header class="inicio-vivo-cabecera">
        <div><p class="portada-volanta">Mundial 2030</p><h1 id="portada-vivo-titulo">Partidos en vivo</h1><p class="vivo-meta">Seguí el marcador, las jugadas y la tribuna de tu país.</p></div>
        <span id="cantidad-vivo" class="vivo-cantidad" hidden></span>
      </header>
      <div id="lista-vivo" class="lista-vivo">
        <p class="vivo-meta" role="status">Buscando partidos…</p>
      </div>
    </section>
    <section class="proximos" aria-labelledby="proximos-titulo"><div class="recientes-titulo"><div><h2 id="proximos-titulo">Próximo horario</h2><p id="proximos-nota">Los partidos que arrancan juntos.</p></div><a href="#/fixture">Ver fixture →</a></div><div id="proximos-lista" class="row row-cols-1 row-cols-md-2 g-3"><p class="vacio">Cargando partidos…</p></div></section>
    <section class="recientes" aria-labelledby="recientes-titulo"><div class="recientes-titulo"><div><h2 id="recientes-titulo">Últimos resultados</h2><p>Resultados y recorrido de jugadas.</p></div><a href="#/grupos">Ver grupos →</a></div><div id="recientes-lista" class="row row-cols-1 row-cols-sm-2 row-cols-lg-3 g-3"><p class="vacio">Cargando partidos…</p></div><button id="recientes-mas" class="btn btn-outline-primary" type="button" hidden>Ver más partidos</button></section>
    ${portadaTorneo("Seis anfitriones, tres continentes", "Un solo torneo para seguir desde cualquier lugar: la tribuna de cada país comenta en su región y el ranking es uno solo para todos.")}`;
  const lista = document.getElementById("lista-vivo");
  const contador = document.getElementById("cantidad-vivo");
  const equipos = await catalogoEquipos().catch(() => null);
  if (!lista.isConnected) return;
  let ultimoContenido;
  async function actualizar() {
    try {
      const d = await api("/en-vivo/partidos");
      if (!lista.isConnected) return;
      const cantidad = d.partidos.length;
      contador.hidden = cantidad < 2;
      contador.textContent = `${cantidad} partidos en simultáneo`;
      const tarjetas = d.partidos.map(p => marcadorPortada(p, equipos)).join("") || `<div class="vivo-vacio">
        <h2>No hay partidos en juego</h2>
        <p class="vivo-meta">Mirá abajo cuándo arranca el próximo horario.</p>
        <div class="vivo-vacio-acciones"><a class="btn vivo-accion" href="#/fixture">Ver fixture</a>${claveAdmin ? '<a class="btn btn-outline-light" href="#/admin">Ir a administración</a>' : ""}</div>
      </div>`;
      if (tarjetas !== ultimoContenido) {
        const enlaceActivo = lista.contains(document.activeElement) ? document.activeElement.getAttribute("href") : null;
        lista.innerHTML = tarjetas;
        lista.classList.toggle("varios", cantidad > 1);
        if (enlaceActivo) [...lista.querySelectorAll("a")].find(a => a.getAttribute("href") === enlaceActivo)?.focus({ preventScroll: true });
        ultimoContenido = tarjetas;
      }
    } catch (e) {
      if (lista.isConnected) { contador.hidden = true; lista.innerHTML = `<div class="vivo-vacio">${cajaDeError(e)}</div>`; ultimoContenido = null; }
    }
  }
  actualizar(); comentariosTimers.push(setInterval(actualizar, 3000));

  // El próximo horario con partidos programados: en la fase de grupos, dos partidos a la vez.
  const proximos = document.getElementById("proximos-lista"), notaProximos = document.getElementById("proximos-nota");
  api("/partidos?estado=Programado").then(d => {
    if (!proximos.isConnected) return;
    const conEquipos = d.partidos.filter(p => p.local && p.visitante).sort((a, b) => new Date(a.fecha_hora) - new Date(b.fecha_hora));
    if (!conEquipos.length) { proximos.innerHTML = '<p class="vacio">No quedan partidos programados con equipos definidos.</p>'; return; }
    const inicio = conEquipos[0].fecha_hora;
    const juntos = conEquipos.filter(p => p.fecha_hora === inicio);
    notaProximos.textContent = `${diaLargo(inicio)}, ${hora(inicio)}${juntos.length > 1 ? ` · ${juntos.length} partidos en simultáneo` : ""}`;
    proximos.innerHTML = juntos.map(p => tarjetaPartido(p, {
      conFecha: false, grupo: grupoDe(p, equipos), detalle: [p.estadio?.nombre, p.estadio?.ciudad].filter(Boolean).join(", "),
      accion: pronosticoAbierto(p, d.pronosticos_hasta_inicio_real) ? "Hacer pronóstico" : "Ver partido",
    })).join("");
  }).catch(e => { if (proximos.isConnected) proximos.innerHTML = cajaDeError(e); });

  const recientes = document.getElementById("recientes-lista");
  const mas = document.getElementById("recientes-mas");
  try {
    const datos = await api("/partidos?estado=Finalizado");
    if (!recientes.isConnected) return;
    const partidos = datos.partidos.slice().sort((a, b) => new Date(b.fecha_hora) - new Date(a.fecha_hora));
    let cantidad = 6;
    const dibujar = () => {
      recientes.innerHTML = partidos.slice(0, cantidad).map(p => tarjetaPartido(p, {
        grupo: grupoDe(p, equipos), detalle: grupoDe(p, equipos) ? null : p.fase, accion: "Ver partido",
      })).join("") || '<p class="vacio w-100">Todavía no hay partidos finalizados.</p>';
      mas.hidden = cantidad >= partidos.length;
    };
    mas.onclick = () => { cantidad += 6; dibujar(); }; dibujar();
  } catch (e) { if (recientes.isConnected) recientes.innerHTML = cajaDeError(e); }
}

// ---------- partido ----------
function prepararCelebracionGol(tablero, marcadorVivo) {
  const aviso = tablero.querySelector(".gol-aviso");
  const luz = tablero.querySelector(".gol-luz");
  const anuncio = tablero.querySelector(".gol-anuncio");
  let secuencia, reloj, celebracion;

  return (equipo, lado) => {
    clearTimeout(reloj);
    secuencia?.revert();
    celebracion?.remove();
    celebracion = document.createElement("div");
    celebracion.className = "gol-pantalla";
    celebracion.setAttribute("aria-hidden", "true");
    celebracion.innerHTML = '<div class="gol-pantalla-banda"><strong>¡GOOOOOOOL!</strong><span></span></div>';
    celebracion.querySelector("span").textContent = equipo;
    document.body.append(celebracion);
    const limites = marcadorVivo.getBoundingClientRect();
    const marcadorVisible = limites.top >= 0 && limites.bottom <= window.innerHeight;
    aviso.classList.toggle("gol-aviso-flotante", !marcadorVisible);
    aviso.querySelector("span").textContent = equipo;
    anuncio.textContent = `Gol de ${equipo}`;
    aviso.hidden = false;
    if (!movimientoReducido.matches && !document.hidden && window.gsap) {
      luz.hidden = false;
      secuencia = window.gsap.timeline({
        onComplete: () => {
          luz.hidden = true;
          aviso.hidden = true;
          anuncio.textContent = "";
          celebracion?.remove();
          celebracion = null;
        },
      });
      secuencia
        .fromTo(celebracion.querySelector('.gol-pantalla-banda'), { xPercent: 110 },
          { xPercent: 0, duration: .55, ease: 'power3.out' }, 0)
        .to(celebracion.querySelector('.gol-pantalla-banda'),
          { xPercent: -110, duration: .5, ease: 'power2.in' }, 2.4)
        .fromTo(luz, { scaleX: 0, opacity: .18 }, {
          scaleX: 1, opacity: 0, transformOrigin: lado === "local" ? "left center" : "right center",
          duration: .8, ease: "power2.out", clearProps: "transform,transformOrigin,opacity",
        }, 0)
        .fromTo(marcadorVivo, { scale: .92 }, { scale: 1.14, duration: .24, ease: "power3.out" }, 0)
        .to(marcadorVivo, { scale: 1, duration: .42, ease: "power2.out", clearProps: "transform" }, .24)
        .fromTo(aviso, { opacity: 0, y: 6 }, { opacity: 1, y: 0, duration: .32, ease: "power3.out" }, 0)
        .to(aviso, { opacity: 0, y: -4, duration: .26, ease: "sine.in", clearProps: "opacity,transform" }, 3);
    } else {
      luz.hidden = true;
      reloj = setTimeout(() => {
        aviso.hidden = true;
        anuncio.textContent = "";
        celebracion?.remove();
        celebracion = null;
      }, 3260);
    }
  };
}

async function vistaPartido(id) {
  const version = navegacionActual;
  contenido.innerHTML = `<p class="vacio">Cargando el partido…</p>`;
  let partido;
  try {
    const datos = await api(`/partidos/${encodeURIComponent(id)}`);
    partido = { ...datos.partido, pronosticos_hasta_inicio_real: datos.pronosticos_hasta_inicio_real };
  }
  catch (e) { if (version !== navegacionActual) return; contenido.innerHTML = `<div class="titulo"><h1>Partido ${esc(id)}</h1>${base("neo4j")}</div>${cajaDeError(e)}<p><a href="#/fixture">Volver al fixture</a></p>`; return; }

  const equiposCatalogo = await catalogoEquipos().catch(() => null);
  if (version !== navegacionActual) return;
  const grupoPartido = grupoDe(partido, equiposCatalogo);
  contenido.innerHTML = `
    <nav aria-label="Ubicación"><ol class="breadcrumb mb-3"><li class="breadcrumb-item"><a href="#/en-vivo">Inicio</a></li><li class="breadcrumb-item"><a href="#/fixture">Fixture</a></li><li class="breadcrumb-item active" aria-current="page">Partido ${esc(partido.id)}</li></ol></nav>
    <section class="tablero marcador-partido" aria-labelledby="partido-titulo">
      <div class="gol-luz" hidden aria-hidden="true"></div>
      <div class="gol-aviso" hidden aria-hidden="true"><strong>¡Gol!</strong><span></span></div>
      <div class="gol-anuncio visually-hidden" role="status"></div>
      <h1 id="partido-titulo" class="visually-hidden">${nombreEquipo(partido.local)} vs ${nombreEquipo(partido.visitante)}</h1>
      <div class="meta"><span>${esc(partido.id)} · ${grupoPartido ? `Grupo ${esc(grupoPartido)}` : esc(partido.fase)} · ${esc(fecha(partido.fecha_hora))}</span><span>${esc(partido.estadio.nombre)}, ${esc(partido.estadio.ciudad)} ${base("neo4j")}</span></div>
      <div class="equipos">
        <div class="equipo">${escudo(partido.local)}<span>${nombreEquipo(partido.local)}</span><small>local</small></div>
        <div class="goles" id="marcador-vivo" aria-live="polite" aria-atomic="true">${esc(marcador(partido))}</div>
        <div class="equipo">${escudo(partido.visitante)}<span>${nombreEquipo(partido.visitante)}</span><small>visitante</small></div>
      </div>
      <div class="meta"><span class="estado marcador-estado" id="estado-vivo">${esc(partido.estado)}</span><span>${partido.inicio_real ? "Empezó " + esc(fecha(partido.inicio_real)) : ""}</span></div>
      <div class="ranking-accion" id="ranking-accion" ${partido.estado === "Finalizado" ? "" : "hidden"}><button class="btn btn-outline-light" id="abrir-ranking">Ver rankings</button></div>
    </section>
    <dialog id="ranking-modal" class="ranking-modal rounded-3" aria-labelledby="ranking-modal-titulo"><div class="ranking-modal-cabecera"><div><h2 id="ranking-modal-titulo">Rankings</h2><p>Elegí un grupo para comparar los pronósticos y los puntos de este partido. El puesto se ordena por el puntaje acumulado.</p></div><button class="btn btn-outline-primary btn-sm" id="cerrar-ranking" aria-label="Cerrar rankings">Cerrar</button></div><label class="form-label" for="ranking-selector">Elegí un ranking</label><select class="form-select" id="ranking-selector"><option value="general">General</option></select><div id="ranking-aviso-grupos" class="nota mb-2" aria-live="polite"></div><div id="ranking-contenido" role="status"><p>Consultando ranking…</p></div></dialog>
    <div class="vstack gap-3 partido-en-vivo">
      <div class="partido-principal">
        <div id="estadisticas"></div>
        <div id="pronostico"></div>
        <section class="card bloque relato" aria-labelledby="relato-titulo"><header><div><h2 id="relato-titulo">Minuto a minuto</h2><p class="relato-subtitulo">Las últimas acciones del partido</p></div><span id="relato-estado" class="relato-estado" role="status">Conectando…</span></header><div id="relato-lista" class="relato-lista" tabindex="0" aria-label="Historial de jugadas" aria-live="polite"><p class="vacio">Esperando la primera jugada.</p></div></section>
        <div id="audiencia"></div>
        <details class="partido-detalles"><summary>Recorrido de jugadas</summary><div id="jugadas"></div></details>
      </div>
      <div class="partido-lateral"><div id="comentarios"></div></div>
    </div>`;

  const modal = document.getElementById("ranking-modal");
  const selector = document.getElementById("ranking-selector");
  const rankingContenido = document.getElementById("ranking-contenido");
  let consultaRanking = 0, aperturaRanking = 0, ultimoGrupoRanking = "";
  async function cargarRankingModal() {
    const consulta = ++consultaRanking;
    const vigente = () => consulta === consultaRanking && modal.open && rankingContenido.isConnected;
    const grupo = selector.value;
    const general = grupo === "general";
    if (!general) ultimoGrupoRanking = grupo;
    rankingContenido.innerHTML = '<p class="nota">Consultando ranking…</p>';
    try {
      const datos = await api(general ? "/ranking?limit=20" :
        `/prodes/${encodeURIComponent(grupo)}/tabla/${encodeURIComponent(id)}`);
      if (!vigente()) return;
      const nota = general ? "Primeros 20 puestos" :
        `${esc(datos.prode.nombre)} · Pronósticos de ${nombreEquipo(partido.local)} vs ${nombreEquipo(partido.visitante)}`;
      rankingContenido.innerHTML = `${general && sesion.usuario ? '<div id="ranking-pronostico-propio" class="mb-2"></div>' : ""}<p class="nota mb-2">${nota}</p>${tablaRanking(general ? datos.ranking : datos.tabla, sesion.usuario?.id, !general)}`;
      const propio = rankingContenido.querySelector("#ranking-pronostico-propio");
      if (propio) {
        try {
          const { pronostico } = await api(`/partidos/${encodeURIComponent(id)}/pronostico`);
          if (vigente()) propio.innerHTML = pronostico
            ? `<p><strong>Tu pronóstico</strong> <span class="pronostico-ranking">${esc(pronostico.goles_local)} – ${esc(pronostico.goles_visitante)}</span>${pronostico.anulado ? ' <span class="nota">Anulado</span>' : ""}</p>`
            : '<p class="nota">No guardaste un pronóstico para este partido.</p>';
        } catch { if (vigente()) propio.innerHTML = '<p class="nota">No se pudo consultar tu pronóstico.</p>'; }
      }
    } catch (e) { if (vigente()) rankingContenido.innerHTML = cajaDeError(e); }
  }
  document.getElementById("abrir-ranking").addEventListener("click", async () => {
    const apertura = ++aperturaRanking;
    ++consultaRanking;
    const vigente = () => apertura === aperturaRanking && modal.open && selector.isConnected;
    const usuario = sesion.usuario;
    const avisoGrupos = modal.querySelector("#ranking-aviso-grupos");
    selector.replaceChildren(new Option("General", "general"));
    selector.value = "general";
    avisoGrupos.replaceChildren();
    modal.showModal();
    // Primero el ranking público; los grupos privados se listan después y se piden solo si se eligen.
    await cargarRankingModal();
    if (!vigente()) return;
    try {
      if (usuario) {
        const { prodes } = await api(`/usuarios/${encodeURIComponent(usuario.id)}/prodes`);
        if (!vigente()) return;
        for (const grupo of prodes) selector.add(new Option(grupo.nombre, grupo.id));
        avisoGrupos.innerHTML = prodes.length
          ? `Elegí ${prodes.some(p => p.id === ultimoGrupoRanking) ? "otra vez tu grupo" : "uno de tus grupos"} para ver sus pronósticos de este partido.`
          : 'Todavía no pertenecés a un grupo. Podés crear uno o unirte desde <a href="#/prodes">Mis prodes</a>.';
      } else {
        avisoGrupos.innerHTML = '<a href="#/ingreso">Ingresá</a> para ver los pronósticos de tus grupos.';
      }
    } catch (e) {
      if (vigente()) avisoGrupos.innerHTML = cajaDeError(e);
    }
  });
  document.getElementById("cerrar-ranking").addEventListener("click", () => modal.close());
  selector.addEventListener("change", cargarRankingModal);
  const audiencia = iniciarAudiencia(id, partido.estado);
  let ultimoMinuto = 0;
  iniciarComentarios(id, partido, {
    estado(e) {
      ultimoMinuto = e.minuto ?? ultimoMinuto;
      versionEstadoEnVivo++;
      ultimoEstadoSSE = Date.now();
      pintarEstado(e);
      if (e.estado === "Finalizado") {
        cerrarVivo(); const t = document.getElementById("comentarios-estado"); if (t) t.textContent = "Partido terminado";
        audiencia.terminado(); setTimeout(actualizarVivo, 4000);
      }
    },
    audiencia(a) { audiencia.audiencia(a); audiencia.minuto(ultimoMinuto, a.total); },
  });
  const estadisticas = document.getElementById("estadisticas");
  const sinEstadisticas = bloque("Estadísticas", null, '<p class="nota">Todavía no hay estadísticas para este partido.</p>');
  estadisticas.innerHTML = bloque("Estadísticas", null, '<p class="nota" role="status">Consultando estadísticas…</p>');
  async function actualizarEstadisticas() {
    try {
      const d = await api(`/partidos/${encodeURIComponent(id)}/estadisticas`);
      if (!estadisticas.isConnected) return;
      const porCodigo = Object.fromEntries(d.equipos.map(e => [e.equipo_id, e]));
      const local = porCodigo[partido.local?.codigo], visitante = porCodigo[partido.visitante?.codigo];
      if (!local || !visitante) { estadisticas.innerHTML = sinEstadisticas; return; }
      const detalleCompleto = (e) => e.muestras != null && e.muestras_detalladas === e.muestras;
      const tienenDetalle = detalleCompleto(local) && detalleCompleto(visitante);
      const entero = (v) => v == null ? "—" : String(v);
      const porcentaje = (v) => v == null ? "—" : `${Number(v).toFixed(1)} %`;
      const fila = (nombre, a, b, textoA = entero(a), textoB = entero(b)) => {
        const total = Number(a) + Number(b), disponible = a != null && b != null;
        const proporción = disponible && total > 0 ? Math.max(0, Math.min(100, 100 * Number(a) / total)) : 50;
        if (a == null && b == null) return "";
        return `<div class="estadistica-fila"><div class="estadistica-valores"><strong>${esc(textoA)}</strong><span>${esc(nombre)}</span><strong>${esc(textoB)}</strong></div>${disponible ? `<div class="progress estadistica-barra" aria-hidden="true"><span class="progress-bar" style="width:${proporción}%"></span></div>` : ""}</div>`;
      };
      const precision = (e) => e.pases_intentados > 0 ? 100 * e.pases_completados / e.pases_intentados : null;
      const pl = tienenDetalle ? precision(local) : null, pv = tienenDetalle ? precision(visitante) : null;
      const detalle = (e, clave) => tienenDetalle ? e[clave] : null;
      const contenido = `<div class="estadistica-equipos"><strong>${nombreEquipo(partido.local)}</strong><span>Comparación</span><strong>${nombreEquipo(partido.visitante)}</strong></div>` +
        fila("Posesión", local.posesion_pct, visitante.posesion_pct, porcentaje(local.posesion_pct), porcentaje(visitante.posesion_pct)) +
        fila("Tiros", local.tiros, visitante.tiros) +
        fila("Tiros al arco", detalle(local, "tiros_arco"), detalle(visitante, "tiros_arco")) +
        fila("Pases acertados", local.pases_completados, visitante.pases_completados) +
        fila("Precisión de pases", pl, pv, porcentaje(pl), porcentaje(pv)) +
        fila("Faltas", detalle(local, "faltas"), detalle(visitante, "faltas")) +
        `<p class="nota estadistica-nota">${d.incompletas ? "Faltan algunas muestras por una falla de InfluxDB. " : ""}${!tienenDetalle ? "Algunas métricas no están disponibles para esta simulación anterior. " : ""}Datos simulados por jugador. Posesión calculada sobre segundos de ambos equipos; acciones acumuladas.</p>`;
      estadisticas.innerHTML = bloque("Estadísticas", d.fuente, contenido);
    } catch (e) { if (estadisticas.isConnected) estadisticas.innerHTML = e.estado === 404 ? sinEstadisticas : bloque("Estadísticas", "influxdb", cajaDeError(e)); }
  }
  actualizarEstadisticas(); comentariosTimers.push(setInterval(actualizarEstadisticas, 5000));
  iniciarRelato(id, partido);
  const marcadorVivo = document.getElementById("marcador-vivo");
  const celebrarGol = prepararCelebracionGol(marcadorVivo.closest(".marcador-partido"), marcadorVivo);
  let jugadasArchivadas = false, versionEstadoEnVivo = 0, ultimoEstadoSSE = 0;
  let minutoDibujado = -1, consultandoEstado = false;
  let ultimoMarcadorEnVivo = partido.estado === "Programado" ? { local: 0, visitante: 0 } : null;
  function pintarEstado(d) {
    if (!marcadorVivo.isConnected) return;
    if (d.estado !== "Finalizado" && (partido.estado === "Finalizado" || d.minuto < minutoDibujado)) return;
    minutoDibujado = d.minuto ?? minutoDibujado;
    const tanteador = d.marcador;
    if (Number.isInteger(tanteador?.local) && Number.isInteger(tanteador?.visitante)) {
      const nuevoMarcador = `${tanteador.local} - ${tanteador.visitante}`;
      if (marcadorVivo.textContent !== nuevoMarcador) marcadorVivo.textContent = nuevoMarcador;
      if (ultimoMarcadorEnVivo &&
          (d.estado === "En juego" || (d.estado === "Finalizado" && partido.estado === "En juego"))) {
        const subeLocal = tanteador.local > ultimoMarcadorEnVivo.local;
        const subeVisitante = tanteador.visitante > ultimoMarcadorEnVivo.visitante;
        if (subeLocal !== subeVisitante &&
            tanteador.local >= ultimoMarcadorEnVivo.local && tanteador.visitante >= ultimoMarcadorEnVivo.visitante) {
          const lado = subeLocal ? "local" : "visitante";
          celebrarGol(partido[lado]?.nombre || (subeLocal ? "el local" : "el visitante"), lado);
        }
      }
      if (d.estado === "En juego" || d.estado === "Finalizado") ultimoMarcadorEnVivo = tanteador;
    }
    const estado = document.getElementById("estado-vivo"); if (estado) estado.textContent = `${d.estado} · ${d.minuto ?? 0}′`;
    const boton = document.getElementById("comentario-enviar"); if (boton) { boton.dataset.cerrado = d.estado === "En juego" ? "no" : "si"; boton.disabled = boton.dataset.cerrado === "si" || boton.dataset.enviando === "si"; }
    if (d.estado && d.estado !== partido.estado) { partido.estado = d.estado; dibujarPronostico(partido); }
    if (d.estado === "Finalizado") document.getElementById("ranking-accion").hidden = false;
  }
  async function actualizarVivo() {
    if (consultandoEstado || !marcadorVivo.isConnected) return;
    consultandoEstado = true;
    const version = versionEstadoEnVivo;
    try { const d = await api(`/en-vivo/partidos/${encodeURIComponent(id)}`); if (!marcadorVivo.isConnected) return;
      if (version === versionEstadoEnVivo) pintarEstado(d);
      if (d.archivo_estado === "completo" && !jugadasArchivadas) { jugadasArchivadas = true; dibujarJugadas(partido); }
      else if (d.estado === "Finalizado" && !jugadasArchivadas) setTimeout(actualizarVivo, 4000);
    } catch (e) { if (e.estado !== 404 && version === versionEstadoEnVivo && marcadorVivo.isConnected) avisar(e.message, true); }
    finally { consultandoEstado = false; }
  }
  // Mientras llegan estados por SSE no se hacen consultas extra.
  actualizarVivo();
  if (partido.estado !== "Finalizado") {
    const respaldoEstado = setInterval(() => {
      if (partido.estado === "Finalizado") { clearInterval(respaldoEstado); return; }
      if (Date.now() - ultimoEstadoSSE > 2500) actualizarVivo();
    }, 3000);
    comentariosTimers.push(respaldoEstado);
  }
  dibujarPronostico(partido);
  let revisionesPronostico = 0;
  const relojPronostico = setInterval(() => {
    if (partido.estado !== "Finalizado" || !sesion.usuario) return;
    dibujarPronostico(partido);
    if (++revisionesPronostico >= 12) clearInterval(relojPronostico);
  }, 5000);
  comentariosTimers.push(relojPronostico);
  dibujarJugadas(partido);
}

function pronosticoAbierto(partido, hastaInicioReal = partido.pronosticos_hasta_inicio_real) {
  return partido.estado === "Programado" && partido.local && partido.visitante &&
    (hastaInicioReal || new Date(partido.fecha_hora) > new Date());
}

const consultasPronostico = new WeakMap();

async function dibujarPronostico(partido) {
  const caja = document.getElementById("pronostico");
  if (!caja) return;
  const consulta = Symbol();
  consultasPronostico.set(caja, consulta);
  const vigente = () => caja.isConnected && consultasPronostico.get(caja) === consulta;
  const u = sesion.usuario;
  if (!u) { caja.innerHTML = bloque("Tu pronóstico", "mongodb", `<p><a href="#/ingreso">Elegí un usuario</a> para ver o guardar tu pronóstico.</p>`); return; }
  if (!caja.hasChildNodes?.()) caja.innerHTML = bloque("Tu pronóstico", "mongodb", '<p class="nota" role="status">Consultando tu pronóstico…</p>');
  const identidad = `<p class="nota mb-2">Usuario: <strong>${esc(u.nombre || u.id)}</strong> · ${esc(u.id)}</p>`;
  let mio;
  try {
    const d = await api(`/partidos/${encodeURIComponent(partido.id)}/pronostico`);
    mio = d.pronostico;
  } catch (e) {
    if (vigente()) caja.innerHTML = bloque("Tu pronóstico", "mongodb", identidad + cajaDeError(e));
    return;
  }
  if (!vigente()) return;
  const abierto = pronosticoAbierto(partido);
  if (!abierto) {
    const motivo = !partido.local || !partido.visitante ? "Todavía no están definidos los equipos." :
      partido.estado === "Programado" ? "Ya pasó el horario previsto y se cerraron los pronósticos." : "Los pronósticos se cerraron al empezar el partido.";
    const resultado = !mio ? "<p>No hay un pronóstico guardado para este partido con este usuario.</p>"
      : `<p class="mb-1">Pronóstico guardado: <strong>${esc(mio.goles_local)} - ${esc(mio.goles_visitante)}</strong>.</p>` +
        (mio.puntos === undefined ? "" : mio.anulado ? `<p class="alert alert-danger error">No cuenta: se cargó cuando el partido ya había empezado.</p>`
          : `<p>Sumaste <strong>${mio.puntos} ${mio.puntos === 1 ? "punto" : "puntos"}</strong>${mio.exacto ? " (resultado exacto)" : ""} y ${esc(duracion(mio.tiempo_seg))} de anticipación para el desempate.</p>`);
    caja.innerHTML = bloque("Tu pronóstico", "mongodb", identidad + resultado + `<p class="nota mt-1">${esc(motivo)}</p>`);
    return;
  }
  const g = { local: mio ? mio.goles_local : 0, visitante: mio ? mio.goles_visitante : 0 };
  const paso = (lado, nombre) => `<div class="paso-grupo"><div class="nombre">${nombre}</div><div class="paso">
      <button type="button" class="btn btn-outline-primary" data-lado="${lado}" data-d="-1" aria-label="Un gol menos para ${nombre}">−</button>
      <output id="g-${lado}" aria-live="polite">${g[lado]}</output>
      <button type="button" class="btn btn-outline-primary" data-lado="${lado}" data-d="1" aria-label="Un gol más para ${nombre}">+</button></div></div>`;
  caja.innerHTML = bloque("Tu pronóstico", "mongodb", `
    ${identidad}<div class="pasos">${paso("local", nombreEquipo(partido.local))}${paso("visitante", nombreEquipo(partido.visitante))}</div>
    <div class="fila d-flex flex-column flex-sm-row flex-wrap gap-2 align-items-stretch align-items-sm-end"><button class="btn btn-primary" id="guardar">${mio ? "Corregir pronóstico" : "Guardar pronóstico"}</button>
    <p class="nota">${mio ? "Guardado " + esc(fecha(mio.cargado_en)) + ". " : ""}Vale para el prode general y para todos tus prodes. Se puede corregir hasta que empiece el partido.</p></div><div id="pron-error"></div>`);
  caja.querySelectorAll("[data-lado]").forEach((b) => b.addEventListener("click", () => {
    const lado = b.dataset.lado;
    g[lado] = Math.min(20, Math.max(0, g[lado] + Number(b.dataset.d)));
    document.getElementById(`g-${lado}`).textContent = g[lado];
  }));
  const guardar = caja.querySelector("#guardar");
  const error = caja.querySelector("#pron-error");
  guardar.addEventListener("click", async () => {
    const controles = caja.querySelectorAll("button");
    controles.forEach(b => { b.disabled = true; });
    const etiqueta = guardar.textContent;
    guardar.textContent = "Guardando…";
    error.replaceChildren();
    try {
      const d = await api(`/partidos/${encodeURIComponent(partido.id)}/pronostico`, {
        metodo: "PUT", cuerpo: { goles_local: g.local, goles_visitante: g.visitante },
      });
      if (!vigente()) return;
      avisar(d._estado === 201 ? "Pronóstico guardado." : "Pronóstico corregido.");
      await dibujarPronostico(partido);
    } catch (e) {
      if (vigente()) error.innerHTML = cajaDeError(e);
    } finally {
      if (guardar.isConnected) {
        controles.forEach(b => { b.disabled = false; });
        guardar.textContent = etiqueta;
      }
    }
  });
}

async function dibujarJugadas(partido) {
  const caja = document.getElementById("jugadas");
  try {
    const d = await api(`/partidos/${encodeURIComponent(partido.id)}/eventos`);
    if (!caja.isConnected) return;
    if (!d.eventos.length) { caja.innerHTML = ""; return; }
    const eventos = d.eventos, porId = new Map(eventos.map(e => [e.id, e]));
    const etiqueta = e => `${e.minuto}′ · ${e.tipo}${e.jugador ? " · " + [e.jugador.nombre, e.jugador.apellido].filter(Boolean).join(" ") : ""}`;
    caja.innerHTML = bloque("Recorrido de jugadas", "neo4j", `<p class="nota">Explorá cómo se conectan las acciones del partido.</p><details class="buscador-hilo"><summary>Buscar otra jugada</summary><label class="busqueda-jugadas" for="buscar-jugadas">Jugador, equipo, minuto o acción</label><input class="form-control" id="buscar-jugadas" type="search" placeholder="Ej.: gol, 23 o Suárez"><div class="jugadas-resultados" role="group" aria-label="Jugadas encontradas"></div></details><div id="cadena" class="recorrido" aria-live="polite"></div>`);
    const resultados = caja.querySelector('.jugadas-resultados'), destino = caja.querySelector('#cadena');
    let seleccionado = eventos[0].id;
    function seleccionar(id) {
      const e = porId.get(id); if (!e) return;
      seleccionado = id;
      const conectados = new Set([id]), pendientes = [id];
      while (pendientes.length) {
        const actual = pendientes.shift(), accion = porId.get(actual);
        const vecinos = [...(accion?.influido_por || []), ...eventos.filter(x => (x.influido_por || []).includes(actual)).map(x => x.id)];
        vecinos.forEach(v => { if (porId.has(v) && !conectados.has(v)) { conectados.add(v); pendientes.push(v); } });
      }
      const hilo = eventos.filter(x => conectados.has(x.id));
      destino.innerHTML = `<div class="hilo-encabezado"><h3>Secuencia de acciones</h3><span>${hilo.length} ${hilo.length === 1 ? 'jugada' : 'jugadas'}</span></div><p class="nota">Tocá una acción para destacarla. Las relaciones indicadas son las registradas en el grafo.</p><ol class="hilo-secuencia">${hilo.map(x => {
        const anteriores = (x.influido_por || []).map(v => porId.get(v)).filter(Boolean);
        const nombre = x.jugador ? [x.jugador.nombre, x.jugador.apellido].filter(Boolean).join(' ') : 'Jugador no registrado';
        return `<li><button type="button" class="btn btn-outline-primary hilo-paso ${x.id === id ? 'actual' : ''}" data-ir="${esc(x.id)}" aria-pressed="${x.id === id}"><span class="hilo-tiempo">${esc(x.minuto)}′</span><span class="hilo-cuerpo"><strong>${esc(x.tipo)}</strong><span>${esc(nombre)}${x.jugador?.equipo ? ' · ' + esc(x.jugador.equipo) : ''}</span>${anteriores.length ? `<small>Viene de ${anteriores.map(v => esc(v.tipo) + ' ' + esc(v.minuto) + '′').join(' y ')}</small>` : '<small>Inicio de esta secuencia</small>'}</span></button></li>`;
      }).join('')}</ol>${hilo.length === 1 ? '<p class="nota">Esta acción no tiene conexiones registradas.</p>' : ''}`;
      destino.querySelectorAll('[data-ir]').forEach(btn => btn.addEventListener('click', () => seleccionar(btn.dataset.ir)));
      resultados.querySelectorAll('[data-elegir]').forEach(btn => btn.setAttribute('aria-pressed', String(btn.dataset.elegir === id)));
    }
    function filtrar() {
      const texto = caja.querySelector('#buscar-jugadas').value.trim().toLocaleLowerCase('es');
      const encontrados = eventos.filter(e => `${etiqueta(e)} ${e.jugador?.equipo || ''}`.toLocaleLowerCase('es').includes(texto));
      resultados.innerHTML = encontrados.map(e => `<button class="btn btn-outline-primary" type="button" data-elegir="${esc(e.id)}" aria-pressed="${e.id === seleccionado}">${esc(etiqueta(e))}</button>`).join('') || '<p class="nota">No encontramos jugadas con esa búsqueda.</p>';
      resultados.querySelectorAll('[data-elegir]').forEach(btn => btn.addEventListener('click', () => (seleccionar(btn.dataset.elegir), caja.querySelector('.buscador-hilo').open = false)));
    }
    caja.querySelector('#buscar-jugadas').addEventListener('input', filtrar); filtrar(); seleccionar(seleccionado);
  } catch (e) { if (caja.isConnected) caja.innerHTML = bloque("Jugadas", "neo4j", cajaDeError(e)); }
}

// ---------- ranking ----------
function celdaPronostico(pronostico) {
  if (!pronostico) return '<td><span class="nota">Sin pronóstico</span></td>';
  return `<td><span class="pronostico-ranking">${esc(pronostico.goles_local)} – ${esc(pronostico.goles_visitante)}</span>${pronostico.anulado ? '<span class="nota d-block">Anulado</span>' : ""}</td>`;
}

function celdaPuntosPartido(pronostico) {
  if (!pronostico) return '<td class="n">—</td>';
  if (!Number.isInteger(pronostico.puntos)) return '<td class="n nota">Pendiente</td>';
  return `<td class="n">${pronostico.puntos}</td>`;
}

const filaRanking = (f, yo, verPronosticos) => `<tr class="${f.usuario_id === yo ? "yo" : ""}"><td class="puesto">${f.puesto}</td><td>${esc(f.nombre || f.usuario_id)}</td>
  ${verPronosticos ? celdaPronostico(f.pronostico) + celdaPuntosPartido(f.pronostico) : ""}<td class="n">${f.puntos}</td><td class="n">${f.exactos}</td><td class="n" title="${esc(f.tiempo_seg)} segundos">${esc(duracion(f.tiempo_seg))}</td></tr>`;
const tablaRanking = (filas, yo, verPronosticos = false) => filas.length
  ? `<div class="table-responsive ranking-tabla" tabindex="0" role="region" aria-label="Tabla de posiciones"><table class="table table-hover align-middle mb-0"><thead><tr><th scope="col">Puesto</th><th scope="col">Usuario</th>${verPronosticos ? '<th scope="col">Pronóstico</th><th scope="col" class="n">Puntos del partido</th>' : ""}<th scope="col" class="n">${verPronosticos ? "Puntos acumulados" : "Puntos"}</th><th scope="col" class="n">Exactos</th><th scope="col" class="n" title="Tercer criterio: cuánto antes del partido cargaste cada pronóstico acertado, sumado">Anticipación <span class="desempate">(desempate)</span></th></tr></thead><tbody>${filas.map(f => filaRanking(f, yo, verPronosticos)).join("")}</tbody></table></div>`
  : `<p class="vacio">Todavía no se cerró ningún partido con pronósticos: el ranking está vacío.</p>`;


async function vistaRanking() {
  const yo = sesion.usuario?.id;
  contenido.innerHTML = `<div class="titulo"><div><h1>Ranking general</h1><p>Uno solo para todo el mundo. Orden: puntos, resultados exactos y anticipación acumulada. 3 puntos por resultado exacto, 1 por acertar ganador o empate.</p></div></div>
    <div class="row g-3 g-lg-4 align-items-start"><div class="col-12 col-lg-8" id="top"><p class="vacio" role="status">Cargando el ranking…</p></div><div class="col-12 col-lg-4 pila"><div id="mio"></div></div></div>`;
  const top = document.getElementById("top");
  const mio = document.getElementById("mio");
  // El ranking público se pide y se dibuja antes que cualquier dato propio del usuario.
  const podio = (filas) => filas.length >= 3 ? `<ol class="podio" aria-label="Podio">${filas.slice(0, 3).map(f => `<li class="podio-${f.puesto} ${f.usuario_id === yo ? "yo" : ""}"><span class="podio-puesto">${f.puesto}°</span><strong>${esc(f.nombre || f.usuario_id)}</strong><span>${f.puntos} ${f.puntos === 1 ? "punto" : "puntos"}</span></li>`).join("")}</ol>` : "";
  top.innerHTML = await cargarBloque("Primeros 20", "redis", api("/ranking?limit=20"), (d) => podio(d.ranking) + tablaRanking(d.ranking, yo));
  if (!top.isConnected) return;
  if (!yo) { mio.innerHTML = bloque("Tu puesto", "mongodb", `<p><a href="#/ingreso">Elegí un usuario</a> para ver tu puesto.</p>`); return; }
  try {
    const d = await api(`/ranking/usuarios/${yo}`);
    mio.innerHTML = bloque("Tu puesto", d.fuente, `<div class="mi-puesto"><span><b>${d.puesto}°</b> de ${d.total_usuarios}</span><span>${d.puntos} ${d.puntos === 1 ? "punto" : "puntos"} · ${d.exactos} ${d.exactos === 1 ? "exacto" : "exactos"}</span></div>
      <p class="nota" style="margin-top:10px">Tu puntaje acumula los partidos que pronosticaste y ya fueron puntuados.</p>`);
  } catch (e) {
    mio.innerHTML = bloque("Tu puesto", "redis", e.estado === 404 ? `<p>Todavía no tenés puntaje: se calcula cuando termina un partido que hayas pronosticado.</p>` : cajaDeError(e));
  }
}

// ---------- prodes ----------
async function vistaProdes() {
  const u = sesion.usuario;
  if (!u) { contenido.innerHTML = `<div class="titulo"><h1>Mis prodes</h1></div><p><a href="#/ingreso">Elegí un usuario</a> para ver tus prodes.</p>`; return; }
  contenido.innerHTML = `<div class="prodes-pagina">
    <header class="prodes-encabezado"><div><h1>Mis prodes</h1><p>Compartí el mundial con tu gente. Un mismo pronóstico suma en todos tus grupos.</p></div><button type="button" id="prodes-ir-acciones" class="btn btn-outline-primary prodes-saltar">Crear o unirme a un grupo</button></header>
    <div class="row g-3 g-lg-4 align-items-start">
      <div class="col-12 col-lg-4"><section class="card prodes-panel prodes-grupos" aria-labelledby="mis-grupos-titulo"><header class="prodes-panel-cabecera"><div><h2 id="mis-grupos-titulo">Tus grupos</h2><p>Elegí uno para ver sus posiciones.</p></div></header><div id="mios" aria-live="polite"><p class="prodes-estado">Cargando tus grupos…</p></div></section></div>
      <div class="col-12 col-lg-8"><section class="card prodes-panel prodes-ranking" aria-labelledby="titulo-tabla"><header class="prodes-panel-cabecera"><div><h2 id="titulo-tabla">Tabla de posiciones</h2><p>Los puntos se acumulan en cada partido.</p></div></header><div id="tabla" aria-live="polite"><p class="prodes-estado">Elegí un grupo para ver la tabla.</p></div></section></div>
    </div>
    <section id="prodes-acciones" class="prodes-acciones" aria-labelledby="prodes-acciones-titulo"><div class="prodes-acciones-intro"><h2 id="prodes-acciones-titulo">Sumá a tu gente</h2><p>Creá un grupo nuevo o usá el código que te compartieron. Cada grupo admite hasta 100 personas.</p></div><div class="row row-cols-1 row-cols-md-2 g-3 g-lg-4 mt-2">
      <div class="col"><form id="crear" class="card prodes-form h-100"><div><h3>Crear un grupo</h3><p>Elegí un nombre y compartí el código.</p></div><label class="form-label" for="pnombre">Nombre del grupo</label><input class="form-control" id="pnombre" required maxlength="60" autocomplete="off" placeholder="Ej. La mesa del domingo"><button class="btn btn-primary" type="submit">Crear grupo</button><div id="crear-error" role="alert"></div></form></div>
      <div class="col"><form id="unir" class="card prodes-form h-100"><div><h3>Unirme a un grupo</h3><p>Ingresá el código de invitación.</p></div><label class="form-label" for="codigo">Código de invitación</label><input class="form-control" id="codigo" required maxlength="8" autocomplete="off" placeholder="Ej. ABCD1234" style="text-transform:uppercase"><button class="btn btn-outline-primary" type="submit">Unirme al grupo</button><div id="unir-error" role="alert"></div></form></div>
    </div></section>
  </div>`;
  let seleccionado = null;
  const lista = document.getElementById("mios"), tabla = document.getElementById("tabla");
  document.getElementById("prodes-ir-acciones").addEventListener("click", () => document.getElementById("prodes-acciones").scrollIntoView());
  async function mostrarTabla(id) {
    seleccionado = id;
    lista.querySelectorAll("[data-tabla]").forEach(b => b.setAttribute("aria-pressed", String(b.dataset.tabla === id)));
    tabla.innerHTML = `<p class="prodes-estado">Cargando posiciones…</p>`;
    try {
      const d = await api(`/prodes/${encodeURIComponent(id)}/tabla`);
      if (!tabla.isConnected || seleccionado !== id) return;
      tabla.innerHTML = `<div class="prodes-ranking-titulo"><div><h3>${esc(d.prode.nombre)}</h3><p>${d.tabla.length} ${d.tabla.length === 1 ? "integrante" : "integrantes"}</p></div><span class="prodes-ranking-nota">Ranking acumulado</span></div>${tablaRanking(d.tabla, u.id)}`;
    } catch (e) { if (tabla.isConnected && seleccionado === id) tabla.innerHTML = cajaDeError(e); }
  }
  const listar = async (preferido = seleccionado) => {
    try {
      const d = await api(`/usuarios/${encodeURIComponent(u.id)}/prodes`);
      if (!lista.isConnected) return;
      if (!d.prodes.length) {
        seleccionado = null;
        lista.innerHTML = `<div class="prodes-vacio"><strong>Todavía no tenés grupos</strong><p>Creá uno o unite con un código para empezar a jugar.</p></div>`;
        tabla.innerHTML = `<p class="prodes-estado">Cuando formes parte de un grupo, sus posiciones aparecerán acá.</p>`;
        return;
      }
      const elegido = d.prodes.some(p => p.id === preferido) ? preferido : d.prodes[0].id;
      lista.innerHTML = `<div class="list-group prodes-lista">${d.prodes.map(p => `<button type="button" class="list-group-item list-group-item-action prodes-grupo" data-tabla="${esc(p.id)}" aria-pressed="${p.id === elegido}"><span class="prodes-grupo-info"><strong>${esc(p.nombre)}</strong><span>${p.integrantes.length} / 100 integrantes</span></span><span class="prodes-grupo-codigo"><small>Código</small><b>${esc(p.codigo)}</b></span></button>`).join("")}</div>`;
      lista.querySelectorAll("[data-tabla]").forEach(b => b.addEventListener("click", () => mostrarTabla(b.dataset.tabla)));
      await mostrarTabla(elegido);
    } catch (e) { if (lista.isConnected) lista.innerHTML = cajaDeError(e); }
  };
  listar();
  document.getElementById("crear").addEventListener("submit", async (ev) => {
    ev.preventDefault(); const boton = ev.currentTarget.querySelector("button"); boton.disabled = true;
    try { const d = await api("/prodes", { metodo: "POST", cuerpo: { nombre: document.getElementById("pnombre").value } }); avisar(`Grupo creado. Código: ${d.prode.codigo}`); ev.target.reset(); await listar(d.prode.id); }
    catch (e) { document.getElementById("crear-error").innerHTML = cajaDeError(e); }
    finally { boton.disabled = false; }
  });
  document.getElementById("unir").addEventListener("submit", async (ev) => {
    ev.preventDefault(); const boton = ev.currentTarget.querySelector("button"); boton.disabled = true;
    try { const d = await api("/prodes/unirse", { metodo: "POST", cuerpo: { codigo: document.getElementById("codigo").value.trim().toUpperCase() } }); avisar(d.resultado === "unido" ? `Te uniste a ${d.prode.nombre}.` : `Ya estabas en ${d.prode.nombre}.`); ev.target.reset(); await listar(d.prode.id); }
    catch (e) { document.getElementById("unir-error").innerHTML = cajaDeError(e); }
    finally { boton.disabled = false; }
  });
}

// ---------- administración ----------
const TIPOS = ["Pase", "Tiro", "Gol", "Falta", "Tarjeta amarilla", "Tarjeta roja", "Cambio", "Inicio", "Final"];

async function vistaAdmin() {
  if (claveAdmin && !sesion.usuario) {
    try { await iniciarAdministrador(); }
    catch (e) { avisar(`No se pudo preparar el usuario administrador: ${e.message}`, true); }
  }
  if (!claveAdmin) {
    contenido.innerHTML = `<div class="titulo"><div><h1>Administración</h1><p>Para operar un partido hace falta la clave de administración (ADMIN_CLAVE del archivo .env). Se guarda en este navegador hasta que salgas.</p></div></div>
      <section class="card bloque" style="max-width:520px"><form id="clave-form"><div><label class="form-label" for="clave">Clave de administración</label><input class="form-control" id="clave" type="password" required autocomplete="off"></div><button class="btn btn-primary">Entrar a administración</button><div id="clave-error" role="alert"></div></form></section>`;
    document.getElementById("clave-form").addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const form = ev.currentTarget, error = document.getElementById("clave-error");
      const boton = form.querySelector("button"); boton.disabled = true;
      claveAdmin = document.getElementById("clave").value;
      try { await iniciarAdministrador(); vistaAdmin(); }
      catch (e) { claveAdmin = ""; if (form.isConnected) { error.innerHTML = cajaDeError(e); boton.disabled = false; } }
    });
    return;
  }
  contenido.innerHTML = `<div class="titulo"><div><h1>Administración</h1><p>Operá un partido: ponerlo en juego cierra los pronósticos, las jugadas van al grafo y el cierre dispara la puntuación.</p></div></div>
    <section class="card bloque mb-3"><header><h2>Seleccionar partido</h2></header><div class="fila d-flex flex-column flex-sm-row flex-wrap gap-2 align-items-stretch align-items-sm-end"><div><label class="form-label" for="buscar-partido">Buscar por equipo o código</label><input class="form-control" id="buscar-partido" type="search" placeholder="Nigeria o P-14"></div><div><label class="form-label" for="apartido">Partido</label><select class="form-select" id="apartido"><option>Cargando…</option></select></div><button class="btn btn-outline-primary" id="ver">Abrir vista del partido</button></div><div id="admin-error"></div></section>
    <section class="card bloque mb-3 simulacion-panel"><header><h2>Simulación completa</h2></header><p>En 90 segundos genera jugadas, estadísticas y comentarios, cierra el partido y puntúa los pronósticos.</p><button class="btn btn-primary" id="simular" disabled>Iniciar simulación completa</button><p id="simulacion-estado" role="status"></p><button class="btn btn-outline-primary" id="archivar-simulacion" type="button" hidden>Reintentar archivo histórico</button></section>
    <div id="operacion"></div>`;
  const selector = document.getElementById("apartido");
  const errorAdmin = document.getElementById("admin-error");
  let partidos = [];
  try { partidos = (await api("/partidos")).partidos; }
  catch (e) { errorAdmin.innerHTML = cajaDeError(e); return; }
  if (!selector.isConnected) return;
  const buscar = document.getElementById("buscar-partido");
  const ver = document.getElementById("ver");
  const pendientes = partidos.filter((p) => p.estado !== "Finalizado");
  const normalizar = (texto) => texto.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase();
  function filtrarPartidos(preferido) {
    const palabras = normalizar(buscar.value.trim()).split(/\s+/);
    const encontrados = pendientes.filter(p => {
      const texto = normalizar(`${p.id} ${p.local?.nombre ?? ""} ${p.visitante?.nombre ?? ""} ${p.fase ?? ""}`);
      return palabras.every(palabra => texto.includes(palabra));
    });
    selector.innerHTML = encontrados.map((p) => `<option value="${esc(p.id)}">${esc(p.id)} — ${nombreEquipo(p.local)} vs ${nombreEquipo(p.visitante)} (${esc(p.estado)})</option>`).join("") ||
      '<option value="">No hay partidos que coincidan</option>';
    if (encontrados.some(p => p.id === preferido)) selector.value = preferido;
    ver.disabled = !selector.value;
    if (selector.value) operar(selector.value);
    else {
      document.getElementById("operacion").innerHTML = "";
      document.getElementById("simular").disabled = true;
    }
  }
  buscar.addEventListener("input", () => filtrarPartidos(selector.value));
  selector.addEventListener("change", () => { sessionStorage.setItem("admin-partido", selector.value); operar(selector.value); });
  document.getElementById("simular").addEventListener("click", async () => {
    const estado = document.getElementById("simulacion-estado");
    const id = selector.value;
    let operacionActualizada = false;
    const boton = document.getElementById("simular"); const archivar = document.getElementById("archivar-simulacion"); archivar.hidden = true; boton.disabled = true; selector.disabled = buscar.disabled = true;
    try {
      await api(`/administracion/simulaciones/${id}`, {metodo:"POST", admin:true});
      estado.textContent = "Iniciando simulación…";
      const consultar = async () => {
        try {
          const d = await api(`/administracion/simulaciones/${id}`, {admin:true});
          if (!estado.isConnected) { clearInterval(reloj); return; }
          if (!operacionActualizada && d.estado_simulacion === "en_curso" && selector.value === id) { operacionActualizada = true; operar(id); }
          estado.textContent = d.estado_simulacion === "fallida" ? "La simulación falló. Revisá los registros de la API." :
            d.estado_simulacion === "completa" ? (d.archivo_estado === "completo" ? "Simulación finalizada e histórico guardado en Neo4j." : "Partido finalizado; archivo histórico pendiente.") : `Simulación en curso · minuto ${d.minuto ?? 0}`;
          if (d.estado_simulacion === "completa" && d.archivo_estado !== "completo") {
            archivar.hidden = false;
            archivar.onclick = async () => {
              archivar.disabled = true;
              try { await api(`/administracion/simulaciones/${id}/archivar`, {metodo:"POST", admin:true}); estado.textContent = "Histórico guardado en Neo4j."; archivar.hidden = true; }
              catch (e) { estado.textContent = e.message; }
              finally { archivar.disabled = false; }
            };
          }
          if (["fallida", "completa"].includes(d.estado_simulacion)) { clearInterval(reloj); selector.disabled = buscar.disabled = false; operar(id); }
        } catch (e) { clearInterval(reloj); if (estado.isConnected) { estado.textContent = e.message; selector.disabled = buscar.disabled = false; operar(id); } }
      };
      const reloj = setInterval(consultar, 2000); consultar();
    } catch (e) { if (e.estado === 401) { claveAdmin = ""; vistaAdmin(); avisar("La clave de administración no es correcta.", true); } else { estado.textContent = e.message; selector.disabled = buscar.disabled = false; operar(id); } }
  });
  document.getElementById("ver").addEventListener("click", () => { location.hash = `#/partido/${selector.value}`; });
  filtrarPartidos(sessionStorage.getItem("admin-partido"));
}

async function operar(id) {
  clearInterval(sondeo);
  const caja = document.getElementById("operacion");
  const selector = document.getElementById("apartido"), simular = document.getElementById("simular");
  simular.disabled = true;
  caja.innerHTML = '<p class="nota">Cargando partido…</p>';
  let p;
  try {
    const datos = await api(`/partidos/${id}`);
    p = { ...datos.partido, pronosticos_hasta_inicio_real: datos.pronosticos_hasta_inicio_real };
  } catch (e) { if (caja.isConnected && selector.value === id) caja.innerHTML = cajaDeError(e); return; }
  if (!caja.isConnected || selector.value !== id) return;
  const intentar = async (accion, mensaje) => {
    try { await accion(); if (mensaje) avisar(mensaje); operar(id); }
    catch (e) { if (e.estado === 401) { claveAdmin = ""; avisar("La clave de administración no es correcta.", true); vistaAdmin(); } else avisar(e.message, true); }
  };

  if (p.estado === "Programado") {
    const sinEquipos = !p.local || !p.visitante;
    simular.disabled = sinEquipos || selector.disabled;
    caja.innerHTML = sinEquipos
      ? `<section class="card bloque"><header><h2>Definir los equipos</h2>${base("neo4j")}</header><form id="equipos"><div class="fila d-flex flex-column flex-sm-row flex-wrap gap-2 align-items-stretch align-items-sm-end"><div><label class="form-label" for="elocal">Local</label><select class="form-select" id="elocal"></select></div><div><label class="form-label" for="evisit">Visitante</label><select class="form-select" id="evisit"></select></div><button class="btn btn-primary">Guardar equipos</button></div></form></section>`
      : `<div id="pronostico" style="margin-bottom:22px"></div><section class="card bloque"><header><h2>${nombreEquipo(p.local)} vs ${nombreEquipo(p.visitante)}</h2>${base("neo4j")}</header><p>Programado para ${esc(fecha(p.fecha_hora))}. Al comenzar se cierran los pronósticos.</p><details style="margin-top:14px"><summary>Operación manual</summary><p class="nota">Este control solo inicia el partido; para generar datos y cerrarlo automáticamente, usá «Iniciar simulación completa».</p><button class="btn btn-outline-primary" id="iniciar" type="button">Poner en juego manualmente</button></details></section>`;
    if (sinEquipos) {
      const equipos = (await api("/equipos")).equipos;
      if (!caja.isConnected || selector.value !== id) return;
      const opciones = equipos.map((e) => `<option value="${esc(e.codigo)}">${esc(e.nombre)}</option>`).join("");
      document.getElementById("elocal").innerHTML = opciones;
      document.getElementById("evisit").innerHTML = opciones;
      document.getElementById("evisit").selectedIndex = 1;
      document.getElementById("equipos").addEventListener("submit", (ev) => { ev.preventDefault(); intentar(() => api(`/partidos/${id}/equipos`, { metodo: "POST", admin: true, cuerpo: { local: document.getElementById("elocal").value, visitante: document.getElementById("evisit").value } }), "Equipos definidos."); });
    } else {
      dibujarPronostico(p);
      document.getElementById("iniciar").addEventListener("click", () => intentar(() => api(`/partidos/${id}/estado`, { metodo: "POST", admin: true, cuerpo: { estado: "En juego" } }), "Partido en juego: pronósticos cerrados."));
    }
    return;
  }

  if (p.estado === "En juego") {
    const [eventos, local, visitante] = await Promise.all([
      api(`/partidos/${id}/eventos`).then((d) => d.eventos).catch(() => []),
      api(`/equipos/${p.local.codigo}/jugadores?limit=50`).then((d) => d.jugadores).catch(() => []),
      api(`/equipos/${p.visitante.codigo}/jugadores?limit=50`).then((d) => d.jugadores).catch(() => []),
    ]);
    const goles = (codigo) => eventos.filter((e) => e.tipo === "Gol" && e.jugador && e.jugador.equipo === codigo).length;
    const jugadores = (lista, equipo) => `<optgroup label="${nombreEquipo(equipo)}">${lista.map((j) => `<option value="${esc(j.id)}">${j.dorsal} · ${esc(j.nombre + " " + j.apellido)}</option>`).join("")}</optgroup>`;
    const proximo = `EV-${id}-${String(eventos.length + 1).padStart(4, "0")}`;
    caja.innerHTML = `<div class="row g-3 g-lg-4 align-items-start">
      <div class="col-12 col-lg-6"><section class="card bloque"><header><h2>Cargar una jugada</h2>${base("neo4j")}</header>
        <form id="jugada"><div class="fila d-flex flex-column flex-sm-row flex-wrap gap-2 align-items-stretch align-items-sm-end"><div><label class="form-label" for="jtipo">Tipo</label><select class="form-select" id="jtipo">${TIPOS.map((t) => `<option>${t}</option>`).join("")}</select></div>
          <div><label class="form-label" for="jmin">Minuto</label><input class="form-control" id="jmin" type="number" min="0" max="130" value="${eventos.length ? eventos[eventos.length - 1].minuto + 1 : 1}" required></div></div>
          <div><label class="form-label" for="jjug">Jugador</label><select class="form-select" id="jjug"><option value="">(sin jugador)</option>${jugadores(local, p.local)}${jugadores(visitante, p.visitante)}</select></div>
          <div><label class="form-label" for="jprev">Vino de la jugada</label><select class="form-select" id="jprev"><option value="">(ninguna)</option>${eventos.slice().reverse().map((e) => `<option value="${esc(e.id)}">${e.minuto}' ${esc(e.tipo)}${e.jugador ? " de " + esc(e.jugador.apellido) : ""}</option>`).join("")}</select></div>
          <button class="btn btn-primary">Cargar jugada</button><p class="nota">Se guarda como ${esc(proximo)}.</p></form></section></div>
      <div class="col-12 col-lg-6"><section class="card bloque"><header><h2>Cerrar el partido</h2>${base("mongodb")}</header>
        <p>Goles cargados como jugadas: <strong>${goles(p.local.codigo)} - ${goles(p.visitante.codigo)}</strong>. El marcador tiene que coincidir.</p>
        <form id="cierre" style="margin-top:12px"><div class="fila d-flex flex-column flex-sm-row flex-wrap gap-2 align-items-stretch align-items-sm-end"><div><label class="form-label" for="cl">${nombreEquipo(p.local)}</label><input class="form-control" id="cl" type="number" min="0" max="30" value="${goles(p.local.codigo)}" required></div>
          <div><label class="form-label" for="cv">${nombreEquipo(p.visitante)}</label><input class="form-control" id="cv" type="number" min="0" max="30" value="${goles(p.visitante.codigo)}" required></div></div>
          ${p.fase === "Fase de grupos" ? "" : `<div><label class="form-label" for="cc">Si empatan, clasifica</label><select class="form-select" id="cc"><option value="">(define el marcador)</option><option value="${esc(p.local.codigo)}">${nombreEquipo(p.local)}</option><option value="${esc(p.visitante.codigo)}">${nombreEquipo(p.visitante)}</option></select></div>`}
          <button class="btn btn-primary">Cerrar partido y puntuar</button></form></section></div></div>`;
    document.getElementById("jugada").addEventListener("submit", (ev) => {
      ev.preventDefault();
      const previa = document.getElementById("jprev").value;
      const cuerpo = { id: proximo, tipo: document.getElementById("jtipo").value, minuto: Number(document.getElementById("jmin").value), orden: eventos.length + 1, influido_por: previa ? [previa] : [] };
      if (document.getElementById("jjug").value) cuerpo.jugador = document.getElementById("jjug").value;
      intentar(() => api(`/partidos/${id}/eventos`, { metodo: "POST", admin: true, cuerpo }), "Jugada cargada.");
    });
    document.getElementById("cierre").addEventListener("submit", (ev) => {
      ev.preventDefault();
      const cuerpo = { goles_local: Number(document.getElementById("cl").value), goles_visitante: Number(document.getElementById("cv").value) };
      const clasifica = document.getElementById("cc")?.value;
      if (clasifica) cuerpo.clasificado = clasifica;
      intentar(() => api(`/partidos/${id}/resultado`, { metodo: "POST", admin: true, cuerpo }), "Partido cerrado. Puntuando…");
    });
    return;
  }

  // Finalizado: avance de la puntuación
  const dibujarAvance = async () => {
    try {
      const d = await api(`/partidos/${id}/puntuacion`, { admin: true });
      const pu = d.puntuacion;
      const paso = (clave, nombre, detalle) => `<div class="${pu.pasos[clave] !== undefined ? "hecho" : ""}"><b>${nombre}</b><span>${pu.pasos[clave] !== undefined ? pu.pasos[clave] + " ms" : detalle}</span></div>`;
      const estados = { pendiente: "en espera", en_curso: "en curso", completa: "terminada", fallida: "falló: repetí el cierre para retomarla" };
      caja.innerHTML = `<section class="card bloque"><header><h2>Puntuación de ${esc(id)}: ${esc(estados[pu.estado] || pu.estado)}</h2>${base("mongodb")}</header>
        <p>Resultado ${d.resultado.goles_local} - ${d.resultado.goles_visitante}. ${pu.pronosticos == null ? "" : `<strong>${pu.pronosticos}</strong> pronósticos puntuados.`}</p>
        <div class="avance">${paso("puntuar", "1. Puntuar pronósticos", "cálculo y ranking en Redis")}${paso("sumar", "2. Guardar puntajes", "persistencia en MongoDB sin duplicar")}${paso("foto", "3. Guardar el ranking", "versión histórica")}</div>
        <p style="margin-top:14px"><a class="btn btn-primary" href="#/ranking" style="text-decoration:none;display:inline-block">Ver el ranking</a></p></section>`;
      if (pu.estado === "completa" || pu.estado === "fallida") clearInterval(sondeo);
    } catch (e) { caja.innerHTML = cajaDeError(e); clearInterval(sondeo); }
  };
  await dibujarAvance();
  sondeo = setInterval(dibujarAvance, 1000);
}

// ---------- navegación ----------
const RUTAS = { ingreso: vistaIngreso, fixture: vistaFixture, grupos: vistaGrupos, "en-vivo": vistaEnVivo, ranking: vistaRanking, prodes: vistaProdes, admin: vistaAdmin };

async function navegar() {
  const version = ++navegacionActual;
  comentariosTimers.forEach(clearInterval); comentariosTimers = []; cerrarVivo();
  entradasVivo?.disconnect();
  clearInterval(sondeo);
  const [, seccion = "", parametro] = location.hash.split("/");
  if (claveAdmin && !administradorPreparado && seccion !== "ingreso") {
    contenido.innerHTML = '<p class="vacio" role="status">Preparando tu usuario de administrador…</p>';
    try {
      if (!preparacionAdmin) preparacionAdmin = iniciarAdministrador().finally(() => { preparacionAdmin = null; });
      await preparacionAdmin;
      if (version !== navegacionActual) return;
    } catch (e) {
      if (version !== navegacionActual) return;
      contenido.innerHTML = `<div class="titulo"><h1>No se pudo iniciar tu usuario</h1></div>${cajaDeError(e)}<p><a href="#/ingreso">Volver al ingreso</a></p>`;
      return;
    }
  }
  document.querySelectorAll("#menu a").forEach((a) => {
    a.getAttribute("href") === `#/${seccion}` ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current");
  });
  if (!sesion.usuario && !claveAdmin && seccion !== "ingreso") { location.hash = "#/ingreso"; return; }
  if (seccion === "partido" && parametro) vistaPartido(decodeURIComponent(parametro));
  else if (RUTAS[seccion]) RUTAS[seccion]();
  else { location.hash = sesion.usuario || claveAdmin ? "#/en-vivo" : "#/ingreso"; return; }
  contenido.focus({ preventScroll: true });
  window.scrollTo(0, 0);
  dibujarSalud();
}

document.querySelector?.(".saltar")?.addEventListener("click", ev => {
  ev.preventDefault();
  contenido.focus();
  contenido.scrollIntoView();
});
window.addEventListener("hashchange", navegar);
dibujarQuien();
navegar();
setInterval(dibujarSalud, 10000);
