/* Prode Mundial 2030 — interfaz de demostración. Sin dependencias: habla con la API del mismo origen.
   Todo texto que viene de la API se inserta con esc() para que un nombre de usuario no pueda meter HTML. */
"use strict";

const contenido = document.getElementById("contenido");
const sesion = {
  get usuario() { try { return JSON.parse(sessionStorage.getItem("usuario")); } catch { return null; } },
  set usuario(u) { u ? sessionStorage.setItem("usuario", JSON.stringify(u)) : sessionStorage.removeItem("usuario"); },
};
let claveAdmin = "";      // solo en memoria: se pierde al recargar la página
let sondeo = null;        // consulta periódica del avance de la puntuación

// ---------- utilidades ----------
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const base = (fuente) => {
  const clase = fuente === "mongodb" ? "mongodb" : fuente === "neo4j" ? "neo4j" : "otra";
  const nombre = { mongodb: "MongoDB", neo4j: "Neo4j" }[fuente] || fuente;
  return `<span class="base ${clase}" title="Base que respondió este bloque">${esc(nombre)}</span>`;
};
const fecha = (iso) => new Date(iso).toLocaleString("es-AR", { weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
const claseEstado = (e) => e === "En juego" ? "en-juego" : e === "Finalizado" ? "finalizado" : "programado";
const nombreEquipo = (e) => e ? esc(e.nombre) : "Por definir";
const marcador = (p) => p.goles_local == null ? "–" : `${p.goles_local} - ${p.goles_visitante}`;
const duracion = (seg) => seg >= 86400 ? `${(seg / 86400).toFixed(1)} d` : seg >= 3600 ? `${(seg / 3600).toFixed(1)} h` : `${Math.round(seg / 60)} min`;

class ErrorDeApi extends Error {
  constructor(estado, codigo, mensaje) { super(mensaje); this.estado = estado; this.codigo = codigo; }
}

async function api(ruta, { metodo = "GET", cuerpo, admin = false } = {}) {
  const encabezados = {};
  if (cuerpo !== undefined) encabezados["Content-Type"] = "application/json";
  if (sesion.usuario) encabezados["X-Usuario-Id"] = sesion.usuario.id;
  if (admin) encabezados["X-Admin-Clave"] = claveAdmin;
  let respuesta;
  try {
    respuesta = await fetch(ruta, { method: metodo, headers: encabezados, body: cuerpo === undefined ? undefined : JSON.stringify(cuerpo) });
  } catch {
    throw new ErrorDeApi(0, "SIN_CONEXION", "No se pudo conectar con la API. Revisá que esté levantada.");
  }
  const datos = await respuesta.json().catch(() => ({}));
  if (!respuesta.ok) {
    const e = datos.error || {};
    const detalle = (e.detalle || []).map((d) => `${d.campo}: ${d.motivo}`).join("; ");
    throw new ErrorDeApi(respuesta.status, e.codigo || "ERROR", [e.mensaje || `La API respondió ${respuesta.status}.`, detalle].filter(Boolean).join(" "));
  }
  datos._estado = respuesta.status;
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
const cajaDeError = (e) => `<p class="error" role="alert">${esc(e.message)}${e.estado === 503 || e.estado === 504 ? " La base que atiende este bloque no está respondiendo." : ""}</p>`;

function bloque(titulo, fuente, cuerpo, extra = "") {
  return `<section class="bloque"><header><h2>${esc(titulo)}</h2>${extra}${fuente ? base(fuente) : ""}</header>${cuerpo}</section>`;
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
  document.getElementById("quien").innerHTML = u
    ? `<span><strong>${esc(u.nombre)}</strong> (${esc(u.id)})</span><button class="boton chico secundario" id="salir" style="border-color:#fff;color:#fff">Cambiar de usuario</button>`
    : `<a href="#/ingreso">Elegir usuario</a>`;
  document.getElementById("salir")?.addEventListener("click", () => { sesion.usuario = null; location.hash = "#/ingreso"; dibujarQuien(); });
}

async function dibujarSalud() {
  const caja = document.getElementById("salud");
  try {
    const s = await api("/health/dependencias");
    const una = (nombre, d) => `<b class="${d.estado === "ok" ? "ok" : "caida"}">${nombre}: ${d.estado === "ok" ? "responde" : "no responde"}</b>`;
    const cal = s.calendario;
    const copia = !cal.cargado ? "sin copia del calendario todavía"
      : `copia del calendario de hace ${Math.round(cal.antiguedad_segundos)} s${cal.desactualizado ? " (no se pudo renovar)" : ""}`;
    caja.innerHTML = `${una("MongoDB", s.mongodb)}${una("Neo4j", s.neo4j)} ${esc(copia)}`;
  } catch (e) {
    caja.innerHTML = `<b class="caida">API: no responde</b>`;
  }
}

// ---------- ingreso ----------
async function vistaIngreso() {
  contenido.innerHTML = `
    <div class="titulo"><div><h1>¿Quién pronostica?</h1><p>Acceso de laboratorio: no hay contraseñas. La API recibe el identificador del usuario en un encabezado; las sesiones reales llegan con Redis.</p></div></div>
    <div class="columnas">
      <section class="bloque"><header><h2>Usuario nuevo</h2>${base("mongodb")}</header>
        <form id="alta"><div><label for="nombre">Nombre</label><input id="nombre" required maxlength="60" autocomplete="off"></div>
        <div><label for="pais">País</label><select id="pais"><option>Cargando…</option></select></div>
        <button class="boton">Crear usuario y entrar</button><div id="alta-error"></div></form></section>
      <section class="bloque"><header><h2>Usuario existente</h2>${base("mongodb")}</header>
        <form id="entrar"><div><label for="uid">Identificador</label><input id="uid" placeholder="U0000001" pattern="U[0-9]{7}" required autocomplete="off"></div>
        <button class="boton secundario">Entrar</button><div id="entrar-error"></div></form></section>
    </div>`;
  api("/equipos").then((d) => {
    document.getElementById("pais").innerHTML = d.equipos.map((e) => `<option value="${esc(e.codigo)}">${esc(e.nombre)}</option>`).join("");
  }).catch((e) => { document.getElementById("alta-error").innerHTML = cajaDeError(e); });

  const entrarCon = (u) => { sesion.usuario = u; dibujarQuien(); location.hash = "#/fixture"; };
  document.getElementById("alta").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    try {
      const d = await api("/usuarios", { metodo: "POST", cuerpo: { nombre: document.getElementById("nombre").value, pais: document.getElementById("pais").value } });
      avisar(`Usuario ${d.usuario.id} creado.`);
      entrarCon(d.usuario);
    } catch (e) { document.getElementById("alta-error").innerHTML = cajaDeError(e); }
  });
  document.getElementById("entrar").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    try { entrarCon((await api(`/usuarios/${encodeURIComponent(document.getElementById("uid").value.trim())}`)).usuario); }
    catch (e) { document.getElementById("entrar-error").innerHTML = cajaDeError(e); }
  });
}

// ---------- fixture ----------
const FASES = ["Fase de grupos", "Dieciseisavos", "Octavos", "Cuartos", "Semifinal", "Tercer puesto", "Final"];
let faseElegida = "Fase de grupos";

async function vistaFixture() {
  contenido.innerHTML = `
    <div class="titulo"><div><h1>Fixture</h1><p>Elegí un partido para pronosticarlo o seguir sus jugadas.</p></div>${base("neo4j")}</div>
    <div class="filtros" role="group" aria-label="Fase">${FASES.map((f) => `<button aria-pressed="${f === faseElegida}" data-fase="${esc(f)}">${esc(f)}</button>`).join("")}</div>
    <div id="lista" class="partidos"><p class="vacio">Cargando…</p></div>`;
  contenido.querySelectorAll("[data-fase]").forEach((b) => b.addEventListener("click", () => { faseElegida = b.dataset.fase; vistaFixture(); }));
  const lista = document.getElementById("lista");
  try {
    const d = await api(`/partidos?fase=${encodeURIComponent(faseElegida)}`);
    lista.innerHTML = d.partidos.map((p) => `
      <a class="partido ${claseEstado(p.estado)}" href="#/partido/${esc(p.id)}">
        <div class="arriba"><span>${esc(p.id)} · ${esc(fecha(p.fecha_hora))}</span><span class="estado ${claseEstado(p.estado)}">${esc(p.estado)}</span></div>
        <div class="cruce"><span>${nombreEquipo(p.local)}</span><b>${esc(marcador(p))}</b><span>${nombreEquipo(p.visitante)}</span></div>
        <div class="arriba"><span>${esc(p.estadio.nombre)}, ${esc(p.estadio.ciudad)}</span></div>
      </a>`).join("") || `<p class="vacio">No hay partidos en esta fase.</p>`;
  } catch (e) { lista.innerHTML = cajaDeError(e); }
}

// ---------- partido ----------
async function vistaPartido(id) {
  contenido.innerHTML = `<p class="vacio">Cargando el partido…</p>`;
  let partido;
  try { partido = (await api(`/partidos/${encodeURIComponent(id)}`)).partido; }
  catch (e) { contenido.innerHTML = `<div class="titulo"><h1>Partido ${esc(id)}</h1>${base("neo4j")}</div>${cajaDeError(e)}<p><a href="#/fixture">Volver al fixture</a></p>`; return; }

  contenido.innerHTML = `
    <p class="nota"><a href="#/fixture">← Fixture</a></p>
    <section class="tablero" style="margin:10px 0 22px">
      <div class="meta"><span>${esc(partido.id)} · ${esc(partido.fase)} · ${esc(fecha(partido.fecha_hora))}</span><span>${esc(partido.estadio.nombre)}, ${esc(partido.estadio.ciudad)} ${base("neo4j")}</span></div>
      <div class="equipos">
        <div class="equipo">${nombreEquipo(partido.local)}<small>local</small></div>
        <div class="goles">${esc(marcador(partido))}</div>
        <div class="equipo">${nombreEquipo(partido.visitante)}<small>visitante</small></div>
      </div>
      <div class="meta"><span class="estado">${esc(partido.estado)}</span><span>${partido.inicio_real ? "Empezó " + esc(fecha(partido.inicio_real)) : ""}</span></div>
    </section>
    <div class="columnas"><div class="pila"><div id="pronostico"></div><div id="comentarios"></div></div><div class="pila"><div id="jugadas"></div></div></div>`;

  document.getElementById("comentarios").innerHTML = `<section class="bloque apagado"><header><h2>Comentarios</h2><span class="base otra">Cassandra</span></header><p>Comentarios: se conectan con Cassandra.</p></section>`;
  dibujarPronostico(partido);
  dibujarJugadas(partido);
}

async function dibujarPronostico(partido) {
  const caja = document.getElementById("pronostico");
  const u = sesion.usuario;
  if (!u) { caja.innerHTML = bloque("Tu pronóstico", "mongodb", `<p><a href="#/ingreso">Elegí un usuario</a> para pronosticar.</p>`); return; }
  let mio = null;
  try {
    const d = await api(`/usuarios/${u.id}/pronosticos?limit=100`);
    mio = d.pronosticos.find((p) => p.partido_id === partido.id) || null;
  } catch (e) { caja.innerHTML = bloque("Tu pronóstico", "mongodb", cajaDeError(e)); return; }

  const abierto = partido.estado === "Programado" && partido.local && partido.visitante && new Date(partido.fecha_hora) > new Date();
  if (!abierto) {
    const motivo = !partido.local ? "Todavía no están definidos los equipos." : "El partido ya empezó: los pronósticos están cerrados.";
    const resultado = !mio ? "<p>No pronosticaste este partido.</p>"
      : `<p>Pronosticaste <strong>${mio.goles_local} - ${mio.goles_visitante}</strong>.</p>` +
        (mio.puntos === undefined ? "" : mio.anulado ? `<p class="error">No cuenta: se cargó cuando el partido ya había empezado.</p>`
          : `<p>Sumaste <strong>${mio.puntos} ${mio.puntos === 1 ? "punto" : "puntos"}</strong>${mio.exacto ? " (resultado exacto)" : ""} y ${esc(duracion(mio.tiempo_seg))} de anticipación para el desempate.</p>`);
    caja.innerHTML = bloque("Tu pronóstico", "mongodb", `<p class="nota">${esc(motivo)}</p>${resultado}`);
    return;
  }
  const g = { local: mio ? mio.goles_local : 0, visitante: mio ? mio.goles_visitante : 0 };
  const paso = (lado, nombre) => `<div class="paso-grupo"><div class="nombre">${nombre}</div><div class="paso">
      <button type="button" data-lado="${lado}" data-d="-1" aria-label="Un gol menos para ${nombre}">−</button>
      <output id="g-${lado}" aria-live="polite">${g[lado]}</output>
      <button type="button" data-lado="${lado}" data-d="1" aria-label="Un gol más para ${nombre}">+</button></div></div>`;
  caja.innerHTML = bloque("Tu pronóstico", "mongodb", `
    <div class="pasos">${paso("local", nombreEquipo(partido.local))}${paso("visitante", nombreEquipo(partido.visitante))}</div>
    <div class="fila"><button class="boton" id="guardar">${mio ? "Corregir pronóstico" : "Guardar pronóstico"}</button>
    <p class="nota">${mio ? "Cargado " + esc(fecha(mio.cargado_en)) + ". " : ""}Vale para el prode general y para todos tus prodes. Se puede corregir hasta que empiece el partido.</p></div><div id="pron-error"></div>`);
  caja.querySelectorAll("[data-lado]").forEach((b) => b.addEventListener("click", () => {
    const lado = b.dataset.lado;
    g[lado] = Math.min(20, Math.max(0, g[lado] + Number(b.dataset.d)));
    document.getElementById(`g-${lado}`).textContent = g[lado];
  }));
  document.getElementById("guardar").addEventListener("click", async () => {
    try {
      const d = await api(`/partidos/${partido.id}/pronostico`, { metodo: "PUT", cuerpo: { goles_local: g.local, goles_visitante: g.visitante } });
      avisar(d._estado === 201 ? "Pronóstico guardado." : "Pronóstico corregido.");
      dibujarPronostico(partido);
    } catch (e) { document.getElementById("pron-error").innerHTML = cajaDeError(e); }
  });
}

async function dibujarJugadas(partido) {
  const caja = document.getElementById("jugadas");
  caja.innerHTML = await cargarBloque("Jugadas", "neo4j", api(`/partidos/${partido.id}/eventos`), (d) => {
    if (!d.eventos.length) return `<p class="vacio">Todavía no hay jugadas cargadas para este partido.</p>`;
    const clase = (t) => t === "Gol" ? "gol" : t === "Tarjeta roja" ? "roja" : "";
    return `<p class="nota">Tocá “¿De dónde vino?” para recorrer en el grafo las jugadas que llevaron a esa.</p>
      <ul class="jugadas">${d.eventos.map((e) => `<li><span class="min">${e.minuto}'</span>
        <span><span class="tipo ${clase(e.tipo)}">${esc(e.tipo)}</span><small>${e.jugador ? esc(e.jugador.nombre + " " + e.jugador.apellido) + " (" + esc(e.jugador.equipo) + ")" : ""}</small></span>
        <button class="boton chico secundario" data-cadena="${esc(e.id)}">¿De dónde vino?</button></li>`).join("")}</ul><div id="cadena"></div>`;
  });
  caja.querySelectorAll("[data-cadena]").forEach((b) => b.addEventListener("click", async () => {
    const destino = document.getElementById("cadena");
    try {
      const d = await api(`/partidos/${partido.id}/eventos/${encodeURIComponent(b.dataset.cadena)}/cadena`);
      destino.innerHTML = d.cadena.length === 1
        ? `<p class="nota" style="margin-top:12px">Esta jugada no tiene otras que la hayan provocado.</p>`
        : `<div class="cadena" aria-label="Cadena de jugadas">${d.cadena.map((e) => `<div>${esc(e.tipo)} ${e.minuto}'<small>${e.jugador ? esc(e.jugador.apellido) : ""}</small></div>`).join("")}</div>`;
    } catch (e) { destino.innerHTML = cajaDeError(e); }
  }));
}

// ---------- ranking ----------
const filaRanking = (f, yo) => `<tr class="${f.usuario_id === yo ? "yo" : ""}"><td class="puesto">${f.puesto}</td><td>${esc(f.nombre || f.usuario_id)}</td>
  <td class="n">${f.puntos}</td><td class="n">${f.exactos}</td><td class="n">${esc(duracion(f.tiempo_seg))}</td></tr>`;
const tablaRanking = (filas, yo) => filas.length
  ? `<table><thead><tr><th>Puesto</th><th>Usuario</th><th class="n">Puntos</th><th class="n">Exactos</th><th class="n">Anticipación</th></tr></thead><tbody>${filas.map((f) => filaRanking(f, yo)).join("")}</tbody></table>`
  : `<p class="vacio">Todavía no se cerró ningún partido con pronósticos: el ranking está vacío.</p>`;

async function vistaRanking() {
  const yo = sesion.usuario?.id;
  contenido.innerHTML = `<div class="titulo"><div><h1>Ranking general</h1><p>Orden: puntos, resultados exactos y anticipación acumulada. 3 puntos por resultado exacto, 1 por acertar ganador o empate.</p></div></div>
    <div class="columnas"><div id="top"></div><div class="pila"><div id="mio"></div></div></div>`;
  document.getElementById("top").innerHTML = await cargarBloque("Primeros 20", "mongodb", api("/ranking?limit=20"), (d) => tablaRanking(d.ranking, yo));
  if (!yo) { document.getElementById("mio").innerHTML = bloque("Tu puesto", "mongodb", `<p><a href="#/ingreso">Elegí un usuario</a> para ver tu puesto.</p>`); return; }
  try {
    const d = await api(`/ranking/usuarios/${yo}`);
    document.getElementById("mio").innerHTML = bloque("Tu puesto", d.fuente, `<div class="mi-puesto"><span><b>${d.puesto}°</b> de ${d.total_usuarios}</span><span>${d.puntos} ${d.puntos === 1 ? "punto" : "puntos"} · ${d.exactos} ${d.exactos === 1 ? "exacto" : "exactos"}</span></div>
      <p class="nota" style="margin-top:10px">Para saber el puesto, MongoDB tiene que contar cuántos usuarios tienen mejor puntaje. Es la consulta que va a pasar a Redis.</p>`);
  } catch (e) {
    document.getElementById("mio").innerHTML = bloque("Tu puesto", "mongodb", e.estado === 404 ? `<p>Todavía no tenés puntaje: se calcula cuando termina un partido que hayas pronosticado.</p>` : cajaDeError(e));
  }
}

// ---------- prodes ----------
async function vistaProdes() {
  const u = sesion.usuario;
  if (!u) { contenido.innerHTML = `<div class="titulo"><h1>Mis prodes</h1></div><p><a href="#/ingreso">Elegí un usuario</a> para ver tus prodes.</p>`; return; }
  contenido.innerHTML = `<div class="titulo"><div><h1>Mis prodes</h1><p>Un prode privado admite hasta 100 personas. Tu pronóstico de cada partido es uno solo y vale en todos.</p></div></div>
    <div class="columnas"><div class="pila"><div id="mios"></div><div id="tabla"></div></div>
    <div class="pila">
      <section class="bloque"><header><h2>Crear un prode</h2>${base("mongodb")}</header><form id="crear"><div><label for="pnombre">Nombre</label><input id="pnombre" required maxlength="60" autocomplete="off"></div><button class="boton">Crear prode</button><div id="crear-error"></div></form></section>
      <section class="bloque"><header><h2>Unirme con un código</h2>${base("mongodb")}</header><form id="unir"><div><label for="codigo">Código de invitación</label><input id="codigo" required maxlength="8" autocomplete="off" style="text-transform:uppercase"></div><button class="boton secundario">Unirme al prode</button><div id="unir-error"></div></form></section>
    </div></div>`;
  const listar = async () => {
    document.getElementById("mios").innerHTML = await cargarBloque("Prodes en los que estoy", "mongodb", api(`/usuarios/${u.id}/prodes`), (d) => d.prodes.length
      ? `<table><thead><tr><th>Prode</th><th>Código</th><th class="n">Integrantes</th><th></th></tr></thead><tbody>${d.prodes.map((p) => `<tr><td>${esc(p.nombre)}</td><td><span class="codigo">${esc(p.codigo)}</span></td><td class="n">${p.integrantes.length} / 100</td><td><button class="boton chico secundario" data-tabla="${esc(p.id)}">Ver tabla</button></td></tr>`).join("")}</tbody></table>`
      : `<p class="vacio">Todavía no estás en ningún prode privado. Creá uno o pedí un código de invitación.</p>`);
    document.querySelectorAll("[data-tabla]").forEach((b) => b.addEventListener("click", async () => {
      document.getElementById("tabla").innerHTML = await cargarBloque("Tabla del prode", "mongodb", api(`/prodes/${b.dataset.tabla}/tabla`),
        (d) => `<h3 style="margin-bottom:8px">${esc(d.prode.nombre)}</h3>${tablaRanking(d.tabla, u.id)}`);
    }));
  };
  listar();
  document.getElementById("crear").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    try { const d = await api("/prodes", { metodo: "POST", cuerpo: { nombre: document.getElementById("pnombre").value } }); avisar(`Prode creado. Código de invitación: ${d.prode.codigo}`); ev.target.reset(); document.getElementById("crear-error").innerHTML = ""; listar(); }
    catch (e) { document.getElementById("crear-error").innerHTML = cajaDeError(e); }
  });
  document.getElementById("unir").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    try { const d = await api("/prodes/unirse", { metodo: "POST", cuerpo: { codigo: document.getElementById("codigo").value.trim().toUpperCase() } }); avisar(d.resultado === "unido" ? `Te uniste a ${d.prode.nombre}.` : `Ya estabas en ${d.prode.nombre}.`); ev.target.reset(); document.getElementById("unir-error").innerHTML = ""; listar(); }
    catch (e) { document.getElementById("unir-error").innerHTML = cajaDeError(e); }
  });
}

// ---------- administración ----------
const TIPOS = ["Pase", "Tiro", "Gol", "Falta", "Tarjeta amarilla", "Tarjeta roja", "Cambio", "Inicio", "Final"];

async function vistaAdmin() {
  if (!claveAdmin) {
    contenido.innerHTML = `<div class="titulo"><div><h1>Administración</h1><p>Para operar un partido hace falta la clave de administración (ADMIN_CLAVE del archivo .env). Se guarda solo mientras esta página esté abierta.</p></div></div>
      <section class="bloque" style="max-width:520px"><form id="clave-form"><div><label for="clave">Clave de administración</label><input id="clave" type="password" required autocomplete="off"></div><button class="boton">Entrar a administración</button></form></section>`;
    document.getElementById("clave-form").addEventListener("submit", (ev) => { ev.preventDefault(); claveAdmin = document.getElementById("clave").value; vistaAdmin(); });
    return;
  }
  contenido.innerHTML = `<div class="titulo"><div><h1>Administración</h1><p>Operá un partido: ponerlo en juego cierra los pronósticos, las jugadas van al grafo y el cierre dispara la puntuación.</p></div></div>
    <section class="bloque" style="margin-bottom:22px"><div class="fila"><div><label for="apartido">Partido</label><select id="apartido"><option>Cargando…</option></select></div><button class="boton secundario" id="ver">Ver en el fixture</button></div><div id="admin-error"></div></section>
    <div id="operacion"></div>`;
  let partidos = [];
  try { partidos = (await api("/partidos")).partidos; }
  catch (e) { document.getElementById("admin-error").innerHTML = cajaDeError(e); return; }
  const selector = document.getElementById("apartido");
  const pendientes = partidos.filter((p) => p.estado !== "Finalizado");
  selector.innerHTML = pendientes.map((p) => `<option value="${esc(p.id)}">${esc(p.id)} — ${nombreEquipo(p.local)} vs ${nombreEquipo(p.visitante)} (${esc(p.estado)})</option>`).join("");
  const guardado = sessionStorage.getItem("admin-partido");
  if (guardado && pendientes.some((p) => p.id === guardado)) selector.value = guardado;
  selector.addEventListener("change", () => { sessionStorage.setItem("admin-partido", selector.value); operar(selector.value); });
  document.getElementById("ver").addEventListener("click", () => { location.hash = `#/partido/${selector.value}`; });
  if (selector.value) operar(selector.value);
}

async function operar(id) {
  clearInterval(sondeo);
  const caja = document.getElementById("operacion");
  let p;
  try { p = (await api(`/partidos/${id}`)).partido; } catch (e) { caja.innerHTML = cajaDeError(e); return; }
  const intentar = async (accion, mensaje) => {
    try { await accion(); if (mensaje) avisar(mensaje); operar(id); }
    catch (e) { if (e.estado === 401) { claveAdmin = ""; avisar("La clave de administración no es correcta.", true); vistaAdmin(); } else avisar(e.message, true); }
  };

  if (p.estado === "Programado") {
    const sinEquipos = !p.local || !p.visitante;
    caja.innerHTML = sinEquipos
      ? `<section class="bloque"><header><h2>Definir los equipos</h2>${base("neo4j")}</header><form id="equipos"><div class="fila"><div><label for="elocal">Local</label><select id="elocal"></select></div><div><label for="evisit">Visitante</label><select id="evisit"></select></div><button class="boton">Guardar equipos</button></div></form></section>`
      : `<section class="bloque"><header><h2>${nombreEquipo(p.local)} vs ${nombreEquipo(p.visitante)}</h2>${base("neo4j")}</header><p>Programado para ${esc(fecha(p.fecha_hora))}. Al ponerlo en juego se cierran los pronósticos y queda registrado el momento real de inicio.</p><p style="margin-top:14px"><button class="boton" id="iniciar">Poner en juego</button></p></section>`;
    if (sinEquipos) {
      const equipos = (await api("/equipos")).equipos;
      const opciones = equipos.map((e) => `<option value="${esc(e.codigo)}">${esc(e.nombre)}</option>`).join("");
      document.getElementById("elocal").innerHTML = opciones;
      document.getElementById("evisit").innerHTML = opciones;
      document.getElementById("evisit").selectedIndex = 1;
      document.getElementById("equipos").addEventListener("submit", (ev) => { ev.preventDefault(); intentar(() => api(`/partidos/${id}/equipos`, { metodo: "POST", admin: true, cuerpo: { local: document.getElementById("elocal").value, visitante: document.getElementById("evisit").value } }), "Equipos definidos."); });
    } else {
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
    caja.innerHTML = `<div class="columnas">
      <section class="bloque"><header><h2>Cargar una jugada</h2>${base("neo4j")}</header>
        <form id="jugada"><div class="fila"><div><label for="jtipo">Tipo</label><select id="jtipo">${TIPOS.map((t) => `<option>${t}</option>`).join("")}</select></div>
          <div><label for="jmin">Minuto</label><input id="jmin" type="number" min="0" max="130" value="${eventos.length ? eventos[eventos.length - 1].minuto + 1 : 1}" required></div></div>
          <div><label for="jjug">Jugador</label><select id="jjug"><option value="">(sin jugador)</option>${jugadores(local, p.local)}${jugadores(visitante, p.visitante)}</select></div>
          <div><label for="jprev">Vino de la jugada</label><select id="jprev"><option value="">(ninguna)</option>${eventos.slice().reverse().map((e) => `<option value="${esc(e.id)}">${e.minuto}' ${esc(e.tipo)}${e.jugador ? " de " + esc(e.jugador.apellido) : ""}</option>`).join("")}</select></div>
          <button class="boton">Cargar jugada</button><p class="nota">Se guarda como ${esc(proximo)}.</p></form></section>
      <section class="bloque"><header><h2>Cerrar el partido</h2>${base("mongodb")}</header>
        <p>Goles cargados como jugadas: <strong>${goles(p.local.codigo)} - ${goles(p.visitante.codigo)}</strong>. El marcador tiene que coincidir.</p>
        <form id="cierre" style="margin-top:12px"><div class="fila"><div><label for="cl">${nombreEquipo(p.local)}</label><input id="cl" type="number" min="0" max="30" value="${goles(p.local.codigo)}" required></div>
          <div><label for="cv">${nombreEquipo(p.visitante)}</label><input id="cv" type="number" min="0" max="30" value="${goles(p.visitante.codigo)}" required></div></div>
          ${p.fase === "Fase de grupos" ? "" : `<div><label for="cc">Si empatan, clasifica</label><select id="cc"><option value="">(define el marcador)</option><option value="${esc(p.local.codigo)}">${nombreEquipo(p.local)}</option><option value="${esc(p.visitante.codigo)}">${nombreEquipo(p.visitante)}</option></select></div>`}
          <button class="boton">Cerrar partido y puntuar</button></form></section></div>`;
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
      caja.innerHTML = `<section class="bloque"><header><h2>Puntuación de ${esc(id)}: ${esc(estados[pu.estado] || pu.estado)}</h2>${base("mongodb")}</header>
        <p>Resultado ${d.resultado.goles_local} - ${d.resultado.goles_visitante}. ${pu.pronosticos == null ? "" : `<strong>${pu.pronosticos}</strong> pronósticos puntuados.`}</p>
        <div class="avance">${paso("puntuar", "1. Puntuar pronósticos", "una actualización dentro de MongoDB")}${paso("sumar", "2. Sumar a los puntajes", "solo si el partido no estaba sumado")}${paso("foto", "3. Guardar el ranking", "versión histórica")}</div>
        <p style="margin-top:14px"><a class="boton" href="#/ranking" style="text-decoration:none;display:inline-block">Ver el ranking</a></p></section>`;
      if (pu.estado === "completa" || pu.estado === "fallida") clearInterval(sondeo);
    } catch (e) { caja.innerHTML = cajaDeError(e); clearInterval(sondeo); }
  };
  await dibujarAvance();
  sondeo = setInterval(dibujarAvance, 1000);
}

// ---------- navegación ----------
const RUTAS = { ingreso: vistaIngreso, fixture: vistaFixture, ranking: vistaRanking, prodes: vistaProdes, admin: vistaAdmin };

function navegar() {
  clearInterval(sondeo);
  const [, seccion = "", parametro] = location.hash.split("/");
  document.querySelectorAll("#menu a").forEach((a) => {
    a.getAttribute("href") === `#/${seccion}` ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current");
  });
  if (seccion === "partido" && parametro) vistaPartido(decodeURIComponent(parametro));
  else if (RUTAS[seccion]) RUTAS[seccion]();
  else { location.hash = sesion.usuario ? "#/fixture" : "#/ingreso"; return; }
  contenido.focus({ preventScroll: true });
  window.scrollTo(0, 0);
  dibujarSalud();
}

window.addEventListener("hashchange", navegar);
dibujarQuien();
navegar();
setInterval(dibujarSalud, 10000);
