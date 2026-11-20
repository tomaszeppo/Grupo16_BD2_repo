/* Prode Mundial 2030 — interfaz de demostración. Sin dependencias: habla con la API del mismo origen.
   Todo texto que viene de la API se inserta con esc() para que un nombre de usuario no pueda meter HTML. */
"use strict";

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
let intervalosTribuna = [];
let versionTribuna = 0;
let sondeo = null;        // consulta periódica del avance de la puntuación
let preparacionAdmin = null;
let administradorPreparado = false;
let navegacionActual = 0;

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
    if (admin && respuesta.status === 401) { claveAdmin = ""; localStorage.removeItem("admin_clave"); dibujarQuien(); }
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
  sesion.usuario = datos.usuario;
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
  document.getElementById("menu").hidden = !u && !claveAdmin;
  document.getElementById("menu-admin").hidden = !claveAdmin;
  document.getElementById("quien").innerHTML = u
    ? `<span><strong>${esc(u.nombre)}</strong> (${esc(u.id)})</span><button class="boton chico secundario" id="salir" style="border-color:#fff;color:#fff">Cambiar de usuario</button>`
    : claveAdmin ? `<span>Administración</span><button class="boton chico secundario" id="salir" style="border-color:#fff;color:#fff">Salir</button>` : `<a href="#/ingreso">Elegir usuario</a>`;
  document.getElementById("salir")?.addEventListener("click", () => { sesion.usuario = null; claveAdmin = ""; administradorPreparado = false; localStorage.removeItem("admin_clave"); location.hash = "#/ingreso"; dibujarQuien(); });
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
    <div class="titulo"><div><h1>Entrá al Prode</h1><p>Ingresá con tu identificador o creá una cuenta para seguir los partidos.</p></div></div>
    <div class="columnas">
      <section class="bloque"><header><h2>Usuario nuevo</h2>${base("mongodb")}</header>
        <form id="alta"><div><label for="nombre">Nombre</label><input id="nombre" required maxlength="60" autocomplete="off"></div>
        <div><label for="pais">País</label><select id="pais"><option>Cargando…</option></select></div>
        <button class="boton">Crear usuario y entrar</button><div id="alta-error"></div></form></section>
      <section class="bloque"><header><h2>Usuario existente</h2>${base("mongodb")}</header>
        <form id="entrar"><div><label for="uid">Identificador</label><input id="uid" placeholder="U0000001" pattern="[Uu][0-9]{7}" required autocomplete="off"></div>
        <button class="boton secundario">Entrar</button><div id="entrar-error" role="alert"></div></form></section>
      <section class="bloque"><header><h2>Administración</h2></header><form id="entrar-admin"><div><label for="clave-ingreso">Clave de administración</label><input id="clave-ingreso" type="password" required autocomplete="off"></div><button class="boton secundario">Entrar a administración</button><div id="ingreso-admin-error" role="alert"></div></form></section>
    </div>`;
  api("/equipos").then((d) => {
    document.getElementById("pais").innerHTML = d.equipos.map((e) => `<option value="${esc(e.codigo)}">${esc(e.nombre)}</option>`).join("");
  }).catch((e) => { document.getElementById("alta-error").innerHTML = cajaDeError(e); });

  const entrarCon = (u) => { claveAdmin = ""; administradorPreparado = false; localStorage.removeItem("admin_clave"); sesion.usuario = u; dibujarQuien(); location.hash = "#/en-vivo"; };
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
    try {
      const usuario = (await api(`/usuarios/${encodeURIComponent(document.getElementById("uid").value.trim().toUpperCase())}`)).usuario;
      entrarCon(usuario);
    } catch (e) { claveAdmin = ""; document.getElementById("entrar-error").innerHTML = cajaDeError(e); }
  });
  document.getElementById("entrar-admin").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    claveAdmin = document.getElementById("clave-ingreso").value;
    try { await iniciarAdministrador(); location.hash = "#/en-vivo"; }
    catch (e) { claveAdmin = ""; document.getElementById("ingreso-admin-error").innerHTML = cajaDeError(e); }
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
        <div class="arriba"><span>${esc(p.estadio.nombre)}, ${esc(p.estadio.ciudad)}</span>${pronosticoAbierto(p, d.pronosticos_hasta_inicio_real) ? '<strong>Hacer pronóstico →</strong>' : ""}</div>
      </a>`).join("") || `<p class="vacio">No hay partidos en esta fase.</p>`;
  } catch (e) { lista.innerHTML = cajaDeError(e); }
}

function iniciarComentarios(id, estadoPartido) {
  intervalosTribuna.forEach(clearInterval); intervalosTribuna = [];
  const version = ++versionTribuna;
  const caja = document.getElementById("comentarios");
  const usuario = sesion.usuario, pais = usuario?.pais || "ARG";
  const formulario = usuario ? `<form id="comentario-form" style="margin-top:16px"><label for="comentario-texto">Tu comentario</label><textarea id="comentario-texto" maxlength="280" rows="3" required placeholder="Sumate a la conversación"></textarea><button class="boton" id="comentario-enviar" ${estadoPartido === "En juego" ? "" : "disabled"}>Enviar comentario</button><p id="comentario-mensaje" role="status"></p></form>` : `<p><a href="#/ingreso">Ingresá</a> para comentar.</p>`;
  caja.innerHTML = `<section class="bloque tribuna"><header><div><h2>Comentarios</h2><p class="tribuna-subtitulo">Tribuna · ${esc(pais)}</p></div><span class="tribuna-estado" id="comentarios-estado" role="status">Conectando…</span></header><div id="comentarios-lista" class="comentarios-lista" role="log" aria-label="Comentarios recientes"><p class="vacio">Todavía no hay comentarios.</p></div>${formulario}</section>`;
  const cola = [], conocidos = new Set(), visibles = [];
  if (estadoPartido === "Finalizado") {
    const lista = document.getElementById("comentarios-lista");
    const estado = document.getElementById("comentarios-estado");
    const boton = document.createElement("button"); boton.type = "button"; boton.className = "boton secundario"; boton.textContent = "Ver comentarios anteriores"; boton.hidden = true;
    caja.querySelector("section").appendChild(boton);
    let cursor = null;
    async function cargarHistorial() {
      boton.disabled = true; estado.textContent = "Consultando…";
      try {
        const params = new URLSearchParams({pais}); if (cursor) params.set("cursor", cursor);
        const datos = await api(`/partidos/${encodeURIComponent(id)}/comentarios/historial?${params}`);
        if (!caja.isConnected) return;
        const nuevos = datos.items.slice().reverse().filter(c => !conocidos.has(c.comentario_id));
        nuevos.forEach(c => conocidos.add(c.comentario_id)); visibles.unshift(...nuevos);
        lista.innerHTML = visibles.map(v => `<article class="comentario"><span class="comentario-avatar" aria-hidden="true">${esc((v.usuario_nombre || "H").slice(0, 1).toUpperCase())}</span><div><strong>${esc(v.usuario_nombre)}</strong><p>${esc(v.contenido)}</p></div></article>`).join("") || `<p class="vacio">No hay comentarios en esta ventana.</p>`;
        cursor = datos.next_cursor; boton.hidden = !cursor;
        estado.textContent = visibles.length ? "Historial de comentarios" : "Sin comentarios en esta ventana";
      } catch (e) { if (caja.isConnected) estado.textContent = e.message; }
      finally { boton.disabled = false; }
    }
    boton.addEventListener("click", cargarHistorial); cargarHistorial(); return;
  }
  async function cargar() {
    try {
      const datos = await api(`/partidos/${encodeURIComponent(id)}/comentarios/recientes?pais=${encodeURIComponent(pais)}`);
      if (!caja.isConnected || version !== versionTribuna) return;
      caja.hidden = estadoPartido !== "En juego" && datos.items.length === 0;
      datos.items.slice().reverse().forEach(c => { if (!conocidos.has(c.comentario_id)) { conocidos.add(c.comentario_id); cola.push(c); } });
      if (cola.length > 40) cola.splice(0, cola.length - 40);
      if (conocidos.size > 500) { const conservar = Array.from(conocidos).slice(-250); conocidos.clear(); conservar.forEach(id => conocidos.add(id)); }
      document.getElementById("comentarios-estado").textContent = datos.items.length ? "Actualizado" : "Todavía no hay comentarios.";
    } catch (e) { const estado = document.getElementById("comentarios-estado"); if (estado) estado.textContent = e.message; }
  }
  document.getElementById("comentario-form")?.addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const texto = document.getElementById("comentario-texto"), boton = document.getElementById("comentario-enviar"), mensaje = document.getElementById("comentario-mensaje");
    const contenido = texto.value.trim(); if (!contenido) { mensaje.textContent = "Escribí un comentario."; return; }
    boton.disabled = true; boton.dataset.enviando = "si"; mensaje.textContent = "Enviando…";
    try {
      const comentario = await api(`/partidos/${encodeURIComponent(id)}/comentarios`, {metodo:"POST", cuerpo:{contenido}});
      if (!caja.isConnected) return;
      conocidos.add(comentario.comentario_id); cola.unshift(comentario); texto.value = ""; mensaje.textContent = "Comentario enviado.";
    } catch (e) { if (caja.isConnected) mensaje.textContent = e.message; }
    finally { if (boton.isConnected) { boton.dataset.enviando = "no"; boton.disabled = boton.dataset.cerrado === "si"; } }
  });
  cargar(); if (estadoPartido === "En juego") intervalosTribuna.push(setInterval(cargar, 8000));
  intervalosTribuna.push(setInterval(() => {
    const c = cola.shift(), lista = document.getElementById("comentarios-lista");
    if (!c || !lista) return; visibles.push(c); if (visibles.length > 20) visibles.shift();
    const seguir = lista.scrollHeight - lista.scrollTop - lista.clientHeight < 48;
    const anterior = lista.scrollTop;
    lista.innerHTML = visibles.map(v => `<article class="comentario"><span class="comentario-avatar" aria-hidden="true">${esc((v.usuario_nombre || "H").slice(0, 1).toUpperCase())}</span><div><strong>${esc(v.usuario_nombre)}</strong><p>${esc(v.contenido)}</p></div></article>`).join("");
    lista.scrollTop = seguir ? lista.scrollHeight : anterior;
  }, 500));
  comentariosTimers.push(...intervalosTribuna);
}

function iniciarRelato(id, partido) {
  const caja = document.getElementById("relato-lista");
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
  let consultando = false;
  async function actualizar() {
    if (consultando || !caja.isConnected) return;
    consultando = true;
    try {
      const datos = await api(`/partidos/${encodeURIComponent(id)}/jugadas/temporales`);
      if (!caja.isConnected) return;
      seccion.hidden = datos.jugadas.length === 0 && vistos.size === 0;
      datos.jugadas.forEach(j => { if (!vistos.has(j.evento_id)) { vistos.add(j.evento_id); cola.push(j); } });
      if (partido.estado === "Finalizado") { while (cola.length) mostrar(); }
      estado.textContent = datos.incompletas ? "Actualización incompleta" : "Actualizado";
    } catch (e) {
      if (caja.isConnected && e.estado !== 404) { seccion.hidden = false; estado.textContent = "No se pudo actualizar"; }
    } finally { consultando = false; }
  }
  function mostrar() {
    if (!caja.isConnected || !cola.length) return;
    const jugada = cola.shift();
    const vacio = caja.querySelector(".vacio"); if (vacio) vacio.remove();
    const seguir = caja.scrollHeight - caja.scrollTop - caja.clientHeight < 48;
    const fila = document.createElement("article"); fila.className = partido.estado === "Finalizado" ? "relato-accion sin-animacion" : "relato-accion";
    fila.innerHTML = `<span class="relato-minuto">${esc(jugada.minuto)}′</span><div><strong>${esc(textoJugada(jugada))}</strong><span>${esc(jugada.equipo_id)}</span></div>`;
    caja.appendChild(fila);
    if (seguir) caja.scrollTop = caja.scrollHeight;
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

async function vistaEnVivo() {
  contenido.innerHTML = `<section class="inicio-vivo"><div class="inicio-vivo-cabecera"><div><h1>Partidos en vivo</h1><p>Seguí el partido, las jugadas y la conversación.</p></div><span class="vivo-indicador"><span></span> En vivo</span></div><div id="lista-vivo" class="partidos inicio-vivo-lista"><p class="vacio">Buscando partidos…</p></div></section><section class="recientes"><div class="recientes-titulo"><div><h2>Últimos partidos</h2><p>Resultados y recorrido de jugadas.</p></div><a href="#/fixture">Ver fixture →</a></div><div id="recientes-lista" class="recientes-grilla"><p class="vacio">Cargando partidos…</p></div><button id="recientes-mas" class="boton secundario" type="button" hidden>Ver más partidos</button></section>`;
  const lista = document.getElementById("lista-vivo");
  async function actualizar() {
    try {
      const d = await api("/en-vivo/partidos");
      if (!lista.isConnected) return;
      lista.innerHTML = d.partidos.map(d => { const p=d.partido, m=d.marcador || {}; return `<a class="partido en-juego" href="#/partido/${esc(p.id)}"><div class="arriba"><span>${esc(p.id)}</span><span class="estado en-juego">En juego · ${esc(d.minuto ?? 0)}′</span></div><div class="cruce"><span>${nombreEquipo(p.local)}</span><b>${esc(m.local ?? 0)} - ${esc(m.visitante ?? 0)}</b><span>${nombreEquipo(p.visitante)}</span></div></a>`; }).join("") || `<div class="vivo-vacio"><div class="vivo-vacio-marca" aria-hidden="true"></div><h2>La cancha está tranquila</h2><p>No hay partidos en juego ahora. Cuando empiece uno, aparece acá.</p><a class="boton secundario" href="#/fixture">Ver fixture</a>${claveAdmin ? '<a class="vivo-admin" href="#/admin">Ir a administración</a>' : ''}</div>`;
    } catch (e) { if (lista.isConnected) lista.innerHTML = cajaDeError(e); }
  }
  actualizar(); comentariosTimers.push(setInterval(actualizar, 3000));
  const recientes = document.getElementById("recientes-lista");
  const mas = document.getElementById("recientes-mas");
  try {
    const datos = await api("/partidos?estado=Finalizado");
    if (!recientes.isConnected) return;
    const partidos = datos.partidos.slice().sort((a, b) => new Date(b.fecha_hora) - new Date(a.fecha_hora));
    let cantidad = 8;
    const dibujar = () => {
      recientes.innerHTML = partidos.slice(0, cantidad).map((p, i) => `<a class="reciente ${i % 5 === 0 ? "reciente-destacado" : ""}" href="#/partido/${esc(p.id)}"><span class="reciente-meta">${esc(p.fase)} · ${esc(fecha(p.fecha_hora))}</span><div class="reciente-equipos"><span>${nombreEquipo(p.local)}</span><strong>${esc(marcador(p))}</strong><span>${nombreEquipo(p.visitante)}</span></div><span class="reciente-pie">${esc(p.estadio?.nombre || "Partido finalizado")} <b>Ver partido →</b></span></a>`).join("") || '<p class="vacio">Todavía no hay partidos finalizados.</p>';
      mas.hidden = cantidad >= partidos.length;
    };
    mas.onclick = () => { cantidad += 8; dibujar(); }; dibujar();
  } catch (e) { if (recientes.isConnected) recientes.innerHTML = cajaDeError(e); }
}

// ---------- partido ----------
async function vistaPartido(id) {
  contenido.innerHTML = `<p class="vacio">Cargando el partido…</p>`;
  let partido;
  try {
    const datos = await api(`/partidos/${encodeURIComponent(id)}`);
    partido = { ...datos.partido, pronosticos_hasta_inicio_real: datos.pronosticos_hasta_inicio_real };
  }
  catch (e) { contenido.innerHTML = `<div class="titulo"><h1>Partido ${esc(id)}</h1>${base("neo4j")}</div>${cajaDeError(e)}<p><a href="#/fixture">Volver al fixture</a></p>`; return; }

  contenido.innerHTML = `
    <p class="nota"><a href="#/en-vivo">← Inicio</a></p>
    <section class="tablero marcador-partido">
      <div class="meta"><span>${esc(partido.id)} · ${esc(partido.fase)} · ${esc(fecha(partido.fecha_hora))}</span><span>${esc(partido.estadio.nombre)}, ${esc(partido.estadio.ciudad)} ${base("neo4j")}</span></div>
      <div class="equipos">
        <div class="equipo">${nombreEquipo(partido.local)}<small>local</small></div>
        <div class="goles" id="marcador-vivo">${esc(marcador(partido))}</div>
        <div class="equipo">${nombreEquipo(partido.visitante)}<small>visitante</small></div>
      </div>
      <div class="meta"><span class="estado marcador-estado" id="estado-vivo">${esc(partido.estado)}</span><span>${partido.inicio_real ? "Empezó " + esc(fecha(partido.inicio_real)) : ""}</span></div>
      <div class="ranking-accion" id="ranking-accion" ${partido.estado === "Finalizado" ? "" : "hidden"}><button class="boton secundario" id="abrir-ranking">Ver rankings</button></div>
    </section>
    <dialog id="ranking-modal" class="ranking-modal" aria-labelledby="ranking-modal-titulo"><div class="ranking-modal-cabecera"><div><h2 id="ranking-modal-titulo">Rankings</h2><p>Puntos acumulados en todos los partidos puntuados.</p></div><button class="boton secundario chico" id="cerrar-ranking" aria-label="Cerrar rankings">Cerrar</button></div><label for="ranking-selector">Elegí un ranking</label><select id="ranking-selector"><option value="general">General</option></select><div id="ranking-contenido" role="status"><p>Consultando ranking…</p></div></dialog>
    <div class="partido-en-vivo"><div id="pronostico"></div><div id="estadisticas"></div><section class="bloque relato" aria-labelledby="relato-titulo"><header><div><h2 id="relato-titulo">Minuto a minuto</h2><p class="relato-subtitulo">Las últimas acciones del partido</p></div><span id="relato-estado" class="relato-estado" role="status">Conectando…</span></header><div id="relato-lista" class="relato-lista" tabindex="0" aria-label="Historial de jugadas" aria-live="polite"><p class="vacio">Esperando la primera jugada.</p></div></section><div id="comentarios"></div><details class="partido-detalles"><summary>Recorrido de jugadas</summary><div id="jugadas"></div></details></div>`;

  const modal = document.getElementById("ranking-modal");
  const selector = document.getElementById("ranking-selector");
  const rankingContenido = document.getElementById("ranking-contenido");
  async function cargarRankingModal() {
    rankingContenido.innerHTML = '<p class="nota">Consultando ranking…</p>';
    try {
      const grupo = selector.value;
      const datos = grupo === "general" ? await api("/ranking?limit=20") : await api(`/prodes/${encodeURIComponent(grupo)}/tabla`);
      if (!modal.open || !rankingContenido.isConnected || selector.value !== grupo) return;
      const filas = grupo === "general" ? datos.ranking : datos.tabla;
      rankingContenido.innerHTML = `<p class="nota">${grupo === "general" ? "Primeros 20 puestos" : esc(datos.prode.nombre)} · El ranking puede actualizarse mientras se puntúa el partido.</p><div class="ranking-tabla">${tablaRanking(filas, sesion.usuario?.id)}</div>`;
    } catch (e) { if (modal.open && rankingContenido.isConnected) rankingContenido.innerHTML = cajaDeError(e); }
  }
  document.getElementById("abrir-ranking").addEventListener("click", async () => {
    modal.showModal();
    selector.innerHTML = '<option value="general">General</option>';
    cargarRankingModal();
    if (sesion.usuario) {
      try {
        const datos = await api(`/usuarios/${encodeURIComponent(sesion.usuario.id)}/prodes`);
        if (modal.open && selector.isConnected) selector.insertAdjacentHTML("beforeend", datos.prodes.map(p => `<option value="${esc(p.id)}">${esc(p.nombre)}</option>`).join(""));
      } catch (e) { if (modal.open) avisar(`No se pudieron cargar tus grupos: ${e.message}`, true); }
    }
  });
  document.getElementById("cerrar-ranking").addEventListener("click", () => modal.close());
  selector.addEventListener("change", cargarRankingModal);
  iniciarComentarios(id, partido.estado);
  const estadisticas = document.getElementById("estadisticas");
  estadisticas.innerHTML = bloque("Estadísticas", "influxdb", "<p>Consultando estadísticas…</p>");
  async function actualizarEstadisticas() {
    try {
      const d = await api(`/partidos/${encodeURIComponent(id)}/estadisticas`);
      if (!estadisticas.isConnected) return;
      const porCodigo = Object.fromEntries(d.equipos.map(e => [e.equipo_id, e]));
      const local = porCodigo[partido.local?.codigo], visitante = porCodigo[partido.visitante?.codigo];
      if (!local || !visitante) { estadisticas.innerHTML = ""; return; }
      const detalleCompleto = (e) => e.muestras != null && e.muestras_detalladas === e.muestras;
      const tienenDetalle = detalleCompleto(local) && detalleCompleto(visitante);
      const entero = (v) => v == null ? "—" : String(v);
      const porcentaje = (v) => v == null ? "—" : `${Number(v).toFixed(1)} %`;
      const fila = (nombre, a, b, textoA = entero(a), textoB = entero(b)) => {
        const total = Number(a) + Number(b), disponible = a != null && b != null;
        const proporción = disponible && total > 0 ? Math.max(0, Math.min(100, 100 * Number(a) / total)) : 50;
        if (a == null && b == null) return "";
        return `<div class="estadistica-fila"><div class="estadistica-valores"><strong>${esc(textoA)}</strong><span>${esc(nombre)}</span><strong>${esc(textoB)}</strong></div>${disponible ? `<div class="estadistica-barra" aria-hidden="true"><span style="width:${proporción}%"></span></div>` : ""}</div>`;
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
    } catch (e) { if (estadisticas.isConnected) estadisticas.innerHTML = e.estado === 404 ? "" : bloque("Estadísticas", "influxdb", cajaDeError(e)); }
  }
  actualizarEstadisticas(); comentariosTimers.push(setInterval(actualizarEstadisticas, 5000));
  iniciarRelato(id, partido);
  const marcadorVivo = document.getElementById("marcador-vivo");
  let jugadasArchivadas = false;
  let comentariosFinalizados = partido.estado === "Finalizado";
  async function actualizarVivo() {
    try { const d=await api(`/en-vivo/partidos/${encodeURIComponent(id)}`); if (!marcadorVivo.isConnected) return;
      marcadorVivo.textContent = `${d.marcador?.local ?? "—"} - ${d.marcador?.visitante ?? "—"}`;
      const estado=document.getElementById("estado-vivo"); if (estado) estado.textContent = `${d.estado} · ${d.minuto ?? 0}′`;
      if (d.archivo_estado === "completo" && !jugadasArchivadas) { jugadasArchivadas = true; dibujarJugadas(partido); }
      if (d.estado === "Finalizado" && !comentariosFinalizados) { comentariosFinalizados = true; iniciarComentarios(id, "Finalizado"); }
      if (d.estado && d.estado !== partido.estado) { partido.estado = d.estado; dibujarPronostico(partido); }
      if (d.estado === "Finalizado") document.getElementById("ranking-accion").hidden = false;
      const boton=document.getElementById("comentario-enviar"); if (boton) { boton.dataset.cerrado = d.estado === "En juego" ? "no" : "si"; boton.disabled = boton.dataset.cerrado === "si" || boton.dataset.enviando === "si"; }
    } catch (e) { if (e.estado !== 404 && marcadorVivo.isConnected) avisar(e.message, true); }
  }
  actualizarVivo(); comentariosTimers.push(setInterval(actualizarVivo, 3000));
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

async function dibujarPronostico(partido) {
  const caja = document.getElementById("pronostico");
  const u = sesion.usuario;
  if (!u) { caja.innerHTML = bloque("Tu pronóstico", "mongodb", `<p><a href="#/ingreso">Elegí un usuario</a> para pronosticar.</p>`); return; }
  let mio = null;
  try {
    let offset = 0, total;
    do {
      const d = await api(`/usuarios/${encodeURIComponent(u.id)}/pronosticos?limit=100&offset=${offset}`);
      mio = d.pronosticos.find((p) => p.partido_id === partido.id) || null;
      total = d.total;
      offset += d.pronosticos.length;
      if (!d.pronosticos.length) break;
    } while (!mio && offset < total);
  } catch (e) { caja.innerHTML = bloque("Tu pronóstico", "mongodb", cajaDeError(e)); return; }

  if (!caja.isConnected) return;
  const abierto = pronosticoAbierto(partido);
  if (!abierto) {
    const motivo = !partido.local || !partido.visitante ? "Todavía no están definidos los equipos." :
      partido.estado === "Programado" ? "Ya pasó el horario previsto y se cerraron los pronósticos." : "Los pronósticos se cerraron al empezar el partido.";
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
  try {
    const d = await api(`/partidos/${encodeURIComponent(partido.id)}/eventos`);
    if (!caja.isConnected) return;
    if (!d.eventos.length) { caja.innerHTML = ""; return; }
    const eventos = d.eventos, porId = new Map(eventos.map(e => [e.id, e]));
    const etiqueta = e => `${e.minuto}′ · ${e.tipo}${e.jugador ? " · " + [e.jugador.nombre, e.jugador.apellido].filter(Boolean).join(" ") : ""}`;
    caja.innerHTML = bloque("Recorrido de jugadas", "neo4j", `<p class="nota">Explorá cómo se conectan las acciones del partido.</p><details class="buscador-hilo"><summary>Buscar otra jugada</summary><label class="busqueda-jugadas" for="buscar-jugadas">Jugador, equipo, minuto o acción</label><input id="buscar-jugadas" type="search" placeholder="Ej.: gol, 23 o Suárez"><div class="jugadas-resultados" role="group" aria-label="Jugadas encontradas"></div></details><div id="cadena" class="recorrido" aria-live="polite"></div>`);
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
        return `<li><button type="button" class="hilo-paso ${x.id === id ? 'actual' : ''}" data-ir="${esc(x.id)}" aria-pressed="${x.id === id}"><span class="hilo-tiempo">${esc(x.minuto)}′</span><span class="hilo-cuerpo"><strong>${esc(x.tipo)}</strong><span>${esc(nombre)}${x.jugador?.equipo ? ' · ' + esc(x.jugador.equipo) : ''}</span>${anteriores.length ? `<small>Viene de ${anteriores.map(v => esc(v.tipo) + ' ' + esc(v.minuto) + '′').join(' y ')}</small>` : '<small>Inicio de esta secuencia</small>'}</span></button></li>`;
      }).join('')}</ol>${hilo.length === 1 ? '<p class="nota">Esta acción no tiene conexiones registradas.</p>' : ''}`;
      destino.querySelectorAll('[data-ir]').forEach(btn => btn.addEventListener('click', () => seleccionar(btn.dataset.ir)));
      resultados.querySelectorAll('[data-elegir]').forEach(btn => btn.setAttribute('aria-pressed', String(btn.dataset.elegir === id)));
    }
    function filtrar() {
      const texto = caja.querySelector('#buscar-jugadas').value.trim().toLocaleLowerCase('es');
      const encontrados = eventos.filter(e => `${etiqueta(e)} ${e.jugador?.equipo || ''}`.toLocaleLowerCase('es').includes(texto));
      resultados.innerHTML = encontrados.map(e => `<button type="button" data-elegir="${esc(e.id)}" aria-pressed="${e.id === seleccionado}">${esc(etiqueta(e))}</button>`).join('') || '<p class="nota">No encontramos jugadas con esa búsqueda.</p>';
      resultados.querySelectorAll('[data-elegir]').forEach(btn => btn.addEventListener('click', () => (seleccionar(btn.dataset.elegir), caja.querySelector('.buscador-hilo').open = false)));
    }
    caja.querySelector('#buscar-jugadas').addEventListener('input', filtrar); filtrar(); seleccionar(seleccionado);
  } catch (e) { if (caja.isConnected) caja.innerHTML = bloque("Jugadas", "neo4j", cajaDeError(e)); }
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
      <p class="nota" style="margin-top:10px">Tu puntaje acumula los partidos que pronosticaste y ya fueron puntuados.</p>`);
  } catch (e) {
    document.getElementById("mio").innerHTML = bloque("Tu puesto", "mongodb", e.estado === 404 ? `<p>Todavía no tenés puntaje: se calcula cuando termina un partido que hayas pronosticado.</p>` : cajaDeError(e));
  }
}

// ---------- prodes ----------
async function vistaProdes() {
  const u = sesion.usuario;
  if (!u) { contenido.innerHTML = `<div class="titulo"><h1>Mis prodes</h1></div><p><a href="#/ingreso">Elegí un usuario</a> para ver tus prodes.</p>`; return; }
  contenido.innerHTML = `<div class="prodes-pagina">
    <header class="prodes-encabezado"><div><h1>Mis prodes</h1><p>Compartí el mundial con tu gente. Un mismo pronóstico suma en todos tus grupos.</p></div><button type="button" id="prodes-ir-acciones" class="prodes-saltar">Crear o unirme a un grupo</button></header>
    <div class="prodes-distribucion">
      <section class="prodes-panel prodes-grupos" aria-labelledby="mis-grupos-titulo"><header class="prodes-panel-cabecera"><div><h2 id="mis-grupos-titulo">Tus grupos</h2><p>Elegí uno para ver sus posiciones.</p></div></header><div id="mios" aria-live="polite"><p class="prodes-estado">Cargando tus grupos…</p></div></section>
      <section class="prodes-panel prodes-ranking" aria-labelledby="titulo-tabla"><header class="prodes-panel-cabecera"><div><h2 id="titulo-tabla">Tabla de posiciones</h2><p>Los puntos se acumulan en cada partido.</p></div></header><div id="tabla" aria-live="polite"><p class="prodes-estado">Elegí un grupo para ver la tabla.</p></div></section>
    </div>
    <section id="prodes-acciones" class="prodes-acciones" aria-labelledby="prodes-acciones-titulo"><div class="prodes-acciones-intro"><h2 id="prodes-acciones-titulo">Sumá a tu gente</h2><p>Creá un grupo nuevo o usá el código que te compartieron. Cada grupo admite hasta 100 personas.</p></div><div class="prodes-formularios">
      <form id="crear" class="prodes-form"><div><h3>Crear un grupo</h3><p>Elegí un nombre y compartí el código.</p></div><label for="pnombre">Nombre del grupo</label><input id="pnombre" required maxlength="60" autocomplete="off" placeholder="Ej. La mesa del domingo"><button class="boton" type="submit">Crear grupo</button><div id="crear-error" role="alert"></div></form>
      <form id="unir" class="prodes-form"><div><h3>Unirme a un grupo</h3><p>Ingresá el código de invitación.</p></div><label for="codigo">Código de invitación</label><input id="codigo" required maxlength="8" autocomplete="off" placeholder="Ej. ABCD1234" style="text-transform:uppercase"><button class="boton secundario" type="submit">Unirme al grupo</button><div id="unir-error" role="alert"></div></form>
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
      tabla.innerHTML = `<div class="prodes-ranking-titulo"><div><h3>${esc(d.prode.nombre)}</h3><p>${d.tabla.length} ${d.tabla.length === 1 ? "integrante" : "integrantes"}</p></div><span class="prodes-ranking-nota">Ranking acumulado</span></div><div class="prodes-tabla-desplazable" tabindex="0" role="region" aria-label="Tabla de posiciones de ${esc(d.prode.nombre)}">${tablaRanking(d.tabla, u.id)}</div>`;
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
      lista.innerHTML = `<div class="prodes-lista">${d.prodes.map(p => `<button type="button" class="prodes-grupo" data-tabla="${esc(p.id)}" aria-pressed="${p.id === elegido}"><span class="prodes-grupo-info"><strong>${esc(p.nombre)}</strong><span>${p.integrantes.length} / 100 integrantes</span></span><span class="prodes-grupo-codigo"><small>Código</small><b>${esc(p.codigo)}</b></span></button>`).join("")}</div>`;
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
      <section class="bloque" style="max-width:520px"><form id="clave-form"><div><label for="clave">Clave de administración</label><input id="clave" type="password" required autocomplete="off"></div><button class="boton">Entrar a administración</button><div id="clave-error" role="alert"></div></form></section>`;
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
    <section class="bloque" style="margin-bottom:22px"><div class="fila"><div><label for="buscar-partido">Buscar por equipo o código</label><input id="buscar-partido" type="search" placeholder="Nigeria o P-14"></div><div><label for="apartido">Partido</label><select id="apartido"><option>Cargando…</option></select></div><button class="boton secundario" id="ver">Abrir vista del partido</button></div><div id="admin-error"></div></section>
    <div id="operacion"></div>
    <section class="bloque" style="margin-top:22px"><header><h2>Simulación completa</h2></header><p>En 90 segundos genera jugadas, estadísticas y comentarios, cierra el partido y puntúa los pronósticos.</p><button class="boton" id="simular" disabled>Iniciar simulación completa</button><p id="simulacion-estado" role="status"></p><button class="boton secundario" id="archivar-simulacion" type="button" hidden>Reintentar archivo histórico</button></section>`;
  let partidos = [];
  try { partidos = (await api("/partidos")).partidos; }
  catch (e) { document.getElementById("admin-error").innerHTML = cajaDeError(e); return; }
  const selector = document.getElementById("apartido");
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
      ? `<section class="bloque"><header><h2>Definir los equipos</h2>${base("neo4j")}</header><form id="equipos"><div class="fila"><div><label for="elocal">Local</label><select id="elocal"></select></div><div><label for="evisit">Visitante</label><select id="evisit"></select></div><button class="boton">Guardar equipos</button></div></form></section>`
      : `<div id="pronostico" style="margin-bottom:22px"></div><section class="bloque"><header><h2>${nombreEquipo(p.local)} vs ${nombreEquipo(p.visitante)}</h2>${base("neo4j")}</header><p>Programado para ${esc(fecha(p.fecha_hora))}. Al comenzar se cierran los pronósticos.</p><details style="margin-top:14px"><summary>Operación manual</summary><p class="nota">Este control solo inicia el partido; para generar datos y cerrarlo automáticamente, usá «Iniciar simulación completa».</p><button class="boton secundario" id="iniciar" type="button">Poner en juego manualmente</button></details></section>`;
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
        <div class="avance">${paso("puntuar", "1. Puntuar pronósticos", "cálculo y ranking en Redis")}${paso("sumar", "2. Guardar puntajes", "persistencia en MongoDB sin duplicar")}${paso("foto", "3. Guardar el ranking", "versión histórica")}</div>
        <p style="margin-top:14px"><a class="boton" href="#/ranking" style="text-decoration:none;display:inline-block">Ver el ranking</a></p></section>`;
      if (pu.estado === "completa" || pu.estado === "fallida") clearInterval(sondeo);
    } catch (e) { caja.innerHTML = cajaDeError(e); clearInterval(sondeo); }
  };
  await dibujarAvance();
  sondeo = setInterval(dibujarAvance, 1000);
}

// ---------- navegación ----------
const RUTAS = { ingreso: vistaIngreso, fixture: vistaFixture, "en-vivo": vistaEnVivo, ranking: vistaRanking, prodes: vistaProdes, admin: vistaAdmin };

async function navegar() {
  const version = ++navegacionActual;
  comentariosTimers.forEach(clearInterval); comentariosTimers = [];
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

window.addEventListener("hashchange", navegar);
dibujarQuien();
navegar();
setInterval(dibujarSalud, 10000);
