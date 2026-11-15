// Sentiende · pantallas (v1.0). Sin librerías: todo funciona sin internet.
"use strict";

const S = { info: null, estado: null, expedientes: [], doc: null, docId: null, pag: 1, ruta: "", editando: false };
const $ = (sel, el = document) => el.querySelector(sel);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const IC = {
  inbox: '<path d="M4 13h4l2 3h4l2-3h4"/><path d="M5 5h14l1 8v6H4v-6z"/>',
  motor: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
  check: '<path d="m5 12 5 5 9-10"/>', folder: '<path d="M3 6h7l2 2h9v11H3z"/>', user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
  bell: '<path d="M6 9a6 6 0 0 1 12 0c0 6 2 7 2 7H4s2-1 2-7"/><path d="M10 20a2 2 0 0 0 4 0"/>', limbo: '<circle cx="12" cy="12" r="8"/><path d="M8 12h8"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v4h16v-4"/>', search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>', trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>', tag: '<path d="M3 3h8l10 10-8 8L3 11z"/>',
  scan: '<path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3"/><path d="M7 12h10"/>',
  bt: '<path d="m7 7 10 10-5 5V2l5 5L7 17"/>', paste: '<rect x="7" y="4" width="10" height="4" rx="1"/><path d="M7 6H5v15h14V6h-2"/>',
  left: '<path d="m15 6-6 6 6 6"/>', right: '<path d="m9 6 6 6-6 6"/>', play: '<path d="M8 5v14l11-7z"/>', x: '<path d="M6 6l12 12M18 6 6 18"/>',
  logo: '<path d="M12 3c-3 0-5 2-5 4.5C5 8 4 10 4 12c0 2.5 2 4.5 4.5 4.5H9v3h6v-3h.5c2.5 0 4.5-2 4.5-4.5 0-2-1-4-3-4.5C17 5 15 3 12 3z"/><path d="M12 7v10M9 11h6"/>',
};
const ico = (n, s = 18) => `<svg width="${s}" height="${s}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${IC[n] || ""}</svg>`;

// Las 10 fases, explicadas (lo mismo que en el diseño del motor de proceso)
const FASES = [
  ["Recibir", "Mueve lo recibido a Entrada\\, calcula su huella y mira si ya se había procesado.", "Original: Entrada\\ (movido desde tu carpeta)", "Archivo dañado o no admitido: aviso en Avisos. El archivo no se toca."],
  ["Leer", "Usa el texto del PDF digital; si es escaneo o foto, OCR en este equipo. Lo ya leído no se relee.", "Original: Entrada\\ sin tocar · copia de trabajo: Datos\\Trabajo\\lote_N\\", "Lectura pobre: aviso; volver a escanear o revisar a mano."],
  ["Separar", "Si el PDF trae varios documentos, los separa (numeración «pág. X de N» y tipo de cada página) y aparta las páginas en blanco.", "Copia de trabajo: Datos\\Trabajo\\lote_N\\", "Corte dudoso: se revisa en el Centro de revisión."],
  ["Orientar", "Gira o endereza solo las páginas que lo necesitan y las vuelve a leer.", "Copia de trabajo: Datos\\Trabajo\\lote_N\\", "Página ilegible tras girar: aviso."],
  ["Extraer datos", "Saca fechas, periodos, DNI, nombres, importes e IBAN y los normaliza para comparar.", "Datos leídos: base de datos (Datos\\)", "Dato ilegible: el documento sigue y se marca «revisar»."],
  ["Clasificar", "Tipo de documento y entidad, provisional hasta emparejar. Por debajo del 75 % pide revisión.", "Copia de trabajo: Datos\\Trabajo\\lote_N\\", "No reconocido: se elige el tipo en el Centro de revisión."],
  ["Emparejar", "Busca la persona y el expediente por DNI o nombre. Siempre pregunta.", "Espera tu respuesta en el Centro de revisión", "Sin datos suficientes: al Limbo (SeDocumentos\\_Limbo\\)."],
  ["Renombrar", "Forma el nombre con las reglas de la variante: IMG678_nomina_1026.pdf.", "Copia de trabajo con su nombre nuevo", "Dato distintivo ilegible: usa la fecha de entrada y marca «revisar»."],
  ["Checklist", "Marca «aportado», lo coloca en su periodo y comprueba caducidades.", "Avisos al cliente si falta algo o caducó", "Caducado o incompleto: Avisos Cliente."],
  ["Guardar", "El editado va a SeDocumentos\\<expediente>\\ y el original de Entrada\\ a Doc_original\\<expediente>\\. Se vacía la copia de trabajo.", "SeDocumentos\\ y Doc_original\\", "Sin permiso o disco lleno: se para aquí, nada se pierde. Reintentar."],
];

async function api(p, cuerpo, opciones = {}) {
  const r = await fetch("/api/" + p, cuerpo !== undefined ? { method: "POST", body: typeof cuerpo === "string" || cuerpo instanceof Blob ? cuerpo : JSON.stringify(cuerpo), ...opciones } : {});
  const j = await r.json();
  if (!r.ok) throw new Error(j.error || "Error");
  return j;
}
function aviso(txt, mal = false) {
  const a = $("#aviso"); a.textContent = txt; a.className = "si" + (mal ? " mal" : "");
  clearTimeout(aviso.t); aviso.t = setTimeout(() => (a.className = ""), mal ? 6000 : 3000);
}
const pill = (t, c = "todo") => `<span class="pill p-${c}">${esc(t)}</span>`;
const nombreTipo = id => (S.info.tipos.find(t => t.id === id) || {}).nombre || id || "—";
const ESTADOS = { en_proceso: ["Trabajando", "acc"], espera_emparejar: ["Para revisar", "warn"], parado: ["Parado", "bad"], guardado: ["Guardado", "ok"],
  limbo: ["En el Limbo", "todo"], duplicado: ["Duplicado", "warn"], separado: ["Separado", "todo"], error: ["Error", "bad"] };
const est = e => pill(...(ESTADOS[e] || [e, "todo"]));
function fbar(fase, estado) {
  const n = estado === "guardado" || estado === "limbo" ? 10 : fase;
  const cls = estado === "parado" ? "bad" : estado === "espera_emparejar" || estado === "duplicado" ? "warn" : "on";
  let s = '<span class="fbar" aria-hidden="true">';
  for (let i = 0; i < 10; i++) s += `<i class="${i < n ? cls : ""}"></i>`;
  const lab = estado === "espera_emparejar" ? "7 de 10 · espera tu respuesta" : `${n} de 10 · ${FASES[Math.max(n, 1) - 1][0]}`;
  return s + `</span><span class="flab">${lab}</span>`;
}

// ------------------------------------------------------------------ barra lateral
function lateral() {
  const v = S.info.variante, c = S.estado?.cuentas || {};
  const r = S.ruta.split("/")[0] || "bandeja";
  const item = (id, ic, txt, num, activo = true, prox = "") =>
    activo ? `<a href="#${id}" ${r === id ? 'aria-current="page"' : ""}>${ico(ic)}${txt}${num ? `<span class="num">${num}</span>` : ""}</a>`
           : `<a class="inactivo" aria-disabled="true" title="Llegará en una próxima versión">${ico(ic)}${txt}<span class="prox">${prox}</span></a>`;
  const abiertos = S.expedientes.filter(e => e.estado === "abierto").slice(0, 8);
  $("#lateral").innerHTML = `
    <div class="marca"><img class="logo" src="/api/logo" alt="" width="60" height="60"><span><b>${esc(v.nombre)}</b><span>con Sentiende</span></span></div>
    <div class="nav">
      ${item("expedientes", "folder", "Expedientes")}
      ${item("bandeja", "inbox", "Bandeja de entrada", c.pendientes)}
      ${item("motor", "motor", "Motor de proceso")}
      ${item("revision", "check", "Centro de revisión", c.revisar)}
      ${item("avisos", "bell", "Avisos", c.avisos)}
      ${item("limbo", "limbo", "Limbo", c.limbo)}
      ${item("", "search", "Buscar en documentos", 0, false, "pronto")}
      ${item("", "chart", "Estadísticas", 0, false, "pronto")}
      ${item("ajustes", "gear", "Ajustes")}
    </div>
    <div class="lat-tit">Expedientes abiertos</div>
    <div class="nav">${abiertos.map(e => {
      const ck = e.checklist || { recibidos: 0, total: 0 }, pct = ck.total ? Math.round(100 * ck.recibidos / ck.total) : 0;
      return `<a class="lat-exp" href="#expediente/${e.id}"><b>${esc(e.nombre)}</b><small>${esc(v.finalidades[e.finalidad] || e.finalidad)} · ${ck.recibidos}/${ck.total}</small><span class="barrita"><i style="width:${pct}%"></i></span></a>`;
    }).join("") || '<span class="pie">Todavía no hay expedientes.</span>'}</div>
    <div class="pie">Motor ${esc(S.info.motor.version)} · ${esc(v.nombre)} ${esc(v.version)}</div>`;
}

// ------------------------------------------------------------------ Bandeja de entrada
function vistaBandeja() {
  const lotes = S.estado.lotes;
  const filas = l => l.documentos.map(d => `<tr class="clic" data-doc="${d.id}">
      <td>${esc(d.archivo)}</td><td>${fbar(d.fase, d.estado)}</td><td>${d.tipo ? esc(nombreTipo(d.tipo)) + (d.confianza != null ? ` <span class="muted">${Math.round(d.confianza * 100)} %</span>` : "") : "—"}</td>
      <td class="mono">${esc(d.nombre_final || "")}</td><td>${est(d.estado)}${d.motivo ? `<div class="muted" style="font-size:12px">${esc(d.motivo)}</div>` : ""}</td></tr>`).join("");
  return `
  <div class="cab"><div><small>Bandeja de entrada</small><h1>Bandeja de entrada</h1><div class="sub">Lo recibido, agrupado por lote. ${S.estado.trabajando ? "<b style='color:var(--accent)'>El motor está trabajando…</b>" : ""}</div></div>
    <div class="acciones"><a class="btn" href="#motor">${ico("motor")}Ver el motor de proceso</a><a class="btn pri" href="#revision">${ico("check")}Revisar (${S.estado.cuentas.revisar})</a></div></div>
  <div class="arrastre" id="zona">
    <span class="ico">${ico("upload", 22)}</span>
    <span style="flex:1 1 300px"><b>Arrastra aquí PDF, fotos, Word o Excel</b><span class="sub">También entra lo que dejes en <code>${esc(S.info.carpetas.entrada)}</code>, y puedes pegar con Ctrl+V.</span></span>
    <span class="acciones"><label class="btn">${ico("upload")}Elegir archivos…<input type="file" id="elegir" multiple hidden accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff,.heic,.docx,.xlsx"></label>
    <button class="btn" disabled title="Escanear directamente: en desarrollo">${ico("scan")}Escanear</button>
    <button class="btn" disabled title="Disponible en la versión 1.1">${ico("bt")}Bluetooth <span class="v11">v1.1</span></button></span>
  </div>
  ${lotes.length ? lotes.map(l => `<section class="tarjeta sinp"><div class="tcab"><div><h2>Lote ${l.id} · ${esc(l.creado.replace("T", " ").slice(0, 16))}</h2>
      <span class="sub">${esc(l.origen)} · ${l.documentos.length} documento(s)${l.separados.length ? ` · ${l.separados.length} PDF separado(s) en partes` : ""} · copia de trabajo en <code>Datos\\Trabajo\\lote_${l.id}\\</code></span></div></div>
      <table class="tabla"><thead><tr><th>Archivo recibido</th><th>Proceso</th><th>Tipo</th><th>Nombre final</th><th>Estado</th></tr></thead><tbody>${filas(l)}</tbody></table></section>`).join("")
    : '<div class="tarjeta vacio">Todavía no ha llegado nada. Arrastra documentos a la zona de arriba.</div>'}`;
}
function activarBandeja() {
  const zona = $("#zona");
  ["dragenter", "dragover"].forEach(ev => zona.addEventListener(ev, e => { e.preventDefault(); zona.classList.add("encima"); }));
  ["dragleave", "drop"].forEach(ev => zona.addEventListener(ev, e => { e.preventDefault(); zona.classList.remove("encima"); }));
  zona.addEventListener("drop", e => subir([...e.dataTransfer.files], "arrastrados"));
  $("#elegir").addEventListener("change", e => subir([...e.target.files], "elegidos"));
  document.querySelectorAll("tr[data-doc]").forEach(tr => tr.addEventListener("click", () => (location.hash = "revision/" + tr.dataset.doc)));
}
async function subir(archivos, origen) {
  if (!archivos.length) return;
  aviso(`Recibiendo ${archivos.length} archivo(s)…`);
  for (const f of archivos) {
    try { await api("subir", f, { headers: { "X-Nombre": encodeURIComponent(f.name || "pegado.png"), "X-Origen": origen } }); }
    catch (e) { aviso(`${f.name}: ${e.message}`, true); }
  }
  await refrescar(true);
}
document.addEventListener("paste", e => {
  if (S.editando || ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName)) return;
  const files = [...(e.clipboardData?.files || [])];
  if (files.length) { e.preventDefault(); subir(files.map((f, i) => f.name ? f : new File([f], `pegado_${Date.now()}_${i}.png`, { type: f.type })), "pegados"); }
});

// ------------------------------------------------------------------ Motor de proceso
let LOTE = null;
function vistaMotor() {
  const lotes = S.estado.lotes.filter(x => x.documentos.length);
  const pendiente = x => x.documentos.some(d => !["guardado", "limbo", "duplicado"].includes(d.estado));
  const l = lotes.find(x => x.id === LOTE) || lotes.find(pendiente) || lotes[0];
  if (!l) return `<div class="cab"><div><small>Motor de proceso</small><h1>Motor de proceso</h1></div></div><div class="tarjeta vacio">No hay ningún lote todavía.</div>`;
  const docs = l.documentos;
  const enFase = i => docs.filter(d => (d.estado === "guardado" || d.estado === "limbo" ? 10 : d.fase) === i + 1 || (i === 6 && d.estado === "espera_emparejar")).length;
  const minF = Math.min(...docs.map(d => d.estado === "guardado" || d.estado === "limbo" ? 10 : d.estado === "espera_emparejar" ? 7 : d.fase));
  const parado = docs.find(d => d.estado === "parado");
  const espera = docs.filter(d => d.estado === "espera_emparejar").length;
  const hechos = docs.filter(d => ["guardado", "limbo", "duplicado"].includes(d.estado)).length;
  const pct = Math.round(100 * docs.reduce((s, d) => s + (["guardado", "limbo", "duplicado"].includes(d.estado) ? 10 : d.fase), 0) / (10 * Math.max(docs.length, 1)));
  const pipe = FASES.map((f, i) => {
    const n = i + 1;
    let c = n < minF ? "hecha" : n === minF ? (parado ? "fallo" : espera && n === 7 ? "pregunta" : "ahora") : "";
    if (hechos === docs.length) c = "hecha";
    const k = enFase(i);
    return `<button class="fase ${c}" aria-label="Fase ${n}: ${f[0]}">${n < 10 ? '<span class="linea"></span>' : ""}<span class="bola">${c === "hecha" ? ico("check", 18) : c === "pregunta" ? "?" : c === "fallo" ? ico("x", 18) : n}</span>
      <span class="nom">${f[0]}</span><span class="cnt">${k ? k + " doc." : "—"}</span>
      <span class="tip" role="tooltip"><h4>Fase ${n} · ${f[0]}</h4><span class="s"><b>Qué se hace</b>${esc(f[1])}</span>
      <span class="s"><b>Dónde están los archivos</b>${esc(f[2].replace("lote_N", "lote_" + l.id))}</span><span class="s"><b>Si falla aquí</b>${esc(f[3])}</span></span></button>`;
  }).join("");
  const titulo = parado ? `Parado · fase ${parado.fase + 1} de 10` : hechos === docs.length ? "Terminado" : espera ? `Espera tu respuesta · ${espera} documento(s) para emparejar` : S.estado.trabajando ? `En marcha · fase ${minF} de 10` : "En pausa";
  return `
  <div class="cab"><div><small>Motor de proceso</small><h1>Motor de proceso</h1><div class="sub">Pasa el ratón por una fase para ver qué hace, dónde están los archivos y qué hacer si falla.</div></div>
    <div class="acciones">${espera ? `<a class="btn pri" href="#revision">${ico("check")}Responder ahora</a>` : ""}<button class="btn" id="reanudar">${ico("play")}Reanudar lo pendiente</button></div></div>
  ${parado ? `<div class="tarjeta" style="border-color:var(--bad);background:var(--badSoft)"><b>El motor se ha parado: ${esc(parado.motivo || "")}</b><span class="sub">Nada se ha perdido: el original sigue en Entrada\\. Corrige la causa y pulsa «Reanudar lo pendiente».</span></div>` : ""}
  <nav class="lotes" aria-label="Lotes">${lotes.slice(0, 12).map(x => `<a href="#motor/${x.id}" ${x.id === l.id ? 'aria-current="true"' : ""}>Lote ${x.id}${pendiente(x) ? " ·  en curso" : ""}</a>`).join("")}</nav>
  <section class="tarjeta"><div class="cab"><div><h2>Lote ${l.id} · ${esc(l.origen)}</h2><span class="sub">${titulo}</span></div><b style="font-size:22px;color:${parado ? "var(--bad)" : "var(--accent)"}">${pct} %</b></div>
    <div class="progreso"><i style="width:${pct}%;${parado ? "background:var(--bad)" : ""}"></i></div>
    <div class="ubic"><span>${ico("folder", 14)} Originales: <code>Entrada\\</code> hasta guardar</span><span>${ico("folder", 14)} Copia de trabajo: <code>Datos\\Trabajo\\lote_${l.id}\\</code></span><span>${ico("folder", 14)} Al terminar: <code>SeDocumentos\\</code> y <code>Doc_original\\</code></span></div>
    <div class="pipeline" style="padding-bottom:230px;margin-bottom:-220px">${pipe}</div></section>
  <section class="tarjeta sinp"><div class="tcab"><h2>Documentos del lote</h2><a href="#bandeja">Ver en la Bandeja</a></div>
    <table class="tabla"><thead><tr><th>Documento</th><th>Fase</th><th>Tipo</th><th>Dónde está ahora</th><th>Estado</th></tr></thead><tbody>
    ${docs.map(d => `<tr><td>${esc(d.archivo)}</td><td>${fbar(d.fase, d.estado)}</td><td>${esc(d.tipo ? nombreTipo(d.tipo) : "—")}</td>
      <td>${Object.entries(d.donde).filter(([, v]) => v).map(([k, v]) => `<div class="mono"><span class="muted">${esc(k)}:</span> ${esc(v)}</div>`).join("")}</td><td>${est(d.estado)}</td></tr>`).join("")}
    </tbody></table></section>`;
}
function activarMotor() { $("#reanudar")?.addEventListener("click", async () => { await api("procesar", {}); aviso("Reanudando…"); refrescar(true); }); }

// ------------------------------------------------------------------ Centro de revisión
function colaRevision() {
  return S.estado.lotes.flatMap(l => l.documentos).filter(d => d.estado === "espera_emparejar" || d.estado === "parado");
}
const FECHA_TXT = { periodo: ["Mes del documento", "Se usa el mes: elige cualquier día de ese mes."], emision: ["Fecha de emisión", "La fecha en que se hizo el documento."], caducidad: ["Válido hasta", "Fecha de caducidad."] };
const FIN_ICO = { hipotecario: '<path d="M3 11 12 4l9 7"/><path d="M5 10v10h14V10"/><path d="M10 20v-6h4v6"/>',
  pyme: '<rect x="3" y="7" width="18" height="13" rx="2"/><path d="M9 7V5h6v2M3 13h18"/>',
  licencia_taxi: '<path d="M5 16 6.5 10h11L19 16"/><rect x="3" y="16" width="18" height="4" rx="1"/><path d="M10 10V7h4v3"/><circle cx="7.5" cy="20" r="1"/><circle cx="16.5" cy="20" r="1"/>' };
const fmtF = iso => iso ? iso.slice(8, 10) + "/" + iso.slice(5, 7) + "/" + iso.slice(0, 4) : "";
const fmtM = iso => iso ? iso.slice(5, 7) + "/" + iso.slice(0, 4) : "";

function iniciarRevision(d) {
  const datos = d.datos || {}, p0 = (datos.personas || [])[0] || {};
  const fin = Object.keys(S.info.variante.finalidades)[0];
  S.rev = { tipo: d.tipo || "", persona: p0.completo ? 0 : -1, fecha: null, finalidad: fin,
    nuevo: { nombre: p0.nombre || "", ap1: p0.apellido1 || "", ap2: p0.apellido2 || "", dni: p0.dni || (datos.dni || [])[0] || "" } };
}
function fechaAuto(d, clave) { const x = d.datos || {}; return clave ? x[clave] || (clave === "emision" ? (x.fechas || [])[0] : null) : null; }

function vistaRevision() {
  const cola = colaRevision();
  if (!cola.length) return `<div class="cab"><div><small>Centro de revisión</small><h1>Centro de revisión</h1></div></div><div class="tarjeta vacio">No hay nada pendiente de revisar. ${S.estado.trabajando ? "El motor sigue trabajando: aparecerá aquí lo que necesite tu respuesta." : ""}</div>`;
  const d = S.doc;
  const lista = cola.map(x => `<a href="#revision/${x.id}" ${S.docId === x.id ? 'aria-current="true"' : ""}><b>${esc(x.archivo)}</b><small>${x.estado === "parado" ? esc(x.motivo) : x.tipo ? esc(nombreTipo(x.tipo)) + " · " + Math.round((x.confianza || 0) * 100) + " %" + (x.motivo ? " · revisar" : "") : "No reconocido"}</small></a>`).join("");
  if (!d || !S.rev) return `<div class="rev"><nav class="cola" aria-label="Pendientes">${lista}</nav><div class="tarjeta vacio">Cargando…</div></div>`;
  const datos = d.datos || {}, v = S.info.variante, R = S.rev;
  const tipos = S.info.tipos.map(t => `<option value="${t.id}" ${t.id === R.tipo ? "selected" : ""}>${esc(t.nombre)}</option>`).join("");
  const leidas = datos.personas || [];
  const sug = d.sugerencias || [];
  const expsSug = sug.flatMap(s => s.expedientes.map(e => ({ ...e, persona: s.persona, por: s.por })));
  const otros = S.expedientes.filter(e => e.estado === "abierto" && !expsSug.some(x => x.id === e.id));
  const opExp = expsSug.map((e, i) => `<label class="opcion"><input type="radio" name="destino" value="e:${e.id}:${e.persona.id}" ${i === 0 ? "checked" : ""}><span><b>${esc(e.nombre)}</b><br><span class="sub">${esc(e.persona.nombre)} ${esc(e.persona.apellido1)} · ${esc(e.papel)} · coincide por ${esc(e.por)}</span></span></label>`).join("");
  const pags = d.paginas_lista.length;
  // persona leída: se elige con un clic
  const chipsPersona = leidas.map((p, i) => `<button type="button" class="chip ${R.persona === i ? "sel" : ""}" data-persona="${i}">${esc(p.completo)}${p.dni ? ` <span class="mono">${esc(p.dni)}</span>` : ""}<small>${esc(p.por)}</small></button>`).join("");
  const dnisSueltos = (datos.dni || []).filter(x => !leidas.some(p => p.dni === x));
  // fecha del documento según el tipo elegido
  const clave = R.tipo ? (d.fecha_claves || {})[R.tipo] : null;
  const auto = fechaAuto(d, clave), elegida = R.fecha || auto;
  const fmt = clave === "periodo" ? fmtM : fmtF;
  const candidatas = [...new Set([auto, datos.periodo, datos.emision, datos.caducidad, ...(datos.fechas || [])].filter(Boolean))];
  const vistas = new Set(), chipsFecha = candidatas.filter(f => { const k = fmt(f); if (vistas.has(k)) return false; vistas.add(k); return true; })
    .map(f => `<button type="button" class="chip ${elegida && fmt(f) === fmt(elegida) ? "sel" : ""}" data-fecha="${f}">${fmt(f)}${f === auto ? "<small>la que ha cogido</small>" : ""}</button>`).join("");
  const otrosDatos = [["Ejercicio", datos.ejercicio], ["IBAN", (datos.iban || []).join(", ")], ["Entidad", d.entidad]].filter(([, x]) => x)
    .map(([a, b]) => `<div class="dato"><span>${a}</span><span class="mono">${esc(b)}</span></div>`).join("");
  const N = R.nuevo;
  const finalidades = Object.entries(v.finalidades).map(([k, n]) => `<button type="button" class="fin ${R.finalidad === k ? "sel" : ""}" data-fin="${k}" aria-pressed="${R.finalidad === k}">
      <svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${FIN_ICO[k] || IC.folder}</svg><span>${esc(n)}</span></button>`).join("");
  return `
  <div class="cab"><div><small>Centro de revisión</small><h1>Centro de revisión</h1><div class="sub">${cola.length} pendiente(s). Comprueba lo leído, elige con un clic y confirma; el resto lo hace el motor.</div></div>
    <div class="acciones"><a class="btn" href="#motor">${ico("motor")}Ver en el motor</a></div></div>
  <div class="rev">
    <nav class="cola" aria-label="Pendientes">${lista}</nav>
    <section class="visor" aria-label="Documento">
      <div class="lienzo"><img alt="Página ${S.pag} de ${esc(d.nombre_recibido)}" src="/api/vista/${d.id}/${S.pag}?t=${d.actualizado}"></div>
      <div class="pie-v"><span>${esc(d.nombre_recibido)} · página ${S.pag} de ${pags}</span>
        <span class="acciones"><button class="btn peq" id="pant" ${S.pag <= 1 ? "disabled" : ""} aria-label="Página anterior">${ico("left", 15)}</button><button class="btn peq" id="psig" ${S.pag >= pags ? "disabled" : ""} aria-label="Página siguiente">${ico("right", 15)}</button></span></div>
      <details style="padding:0 14px 14px"><summary class="muted" style="cursor:pointer;padding:10px 0">Ver el texto leído de esta página</summary><div class="campo"><textarea readonly>${esc(d.texto_paginas[S.pag - 1] || "")}</textarea></div></details>
    </section>
    <section class="tarjeta" aria-label="Revisar">
      <div><h2>Revisar</h2><span class="sub">${d.motivo ? esc(d.motivo) : "Clasificado con " + Math.round((d.confianza || 0) * 100) + " %"}</span></div>
      <div class="campo"><label for="r-tipo">1 · Tipo de documento</label><select id="r-tipo">${R.tipo ? "" : '<option value="">— Elegir —</option>'}${tipos}</select>
        ${(d.alternativas || []).length ? `<span class="chips">${d.alternativas.map(a => `<button type="button" class="chip peq" data-tipo="${a.tipo}">${esc(nombreTipo(a.tipo))}</button>`).join("")}</span>` : ""}</div>
      <div class="campo"><span class="lab">2 · ¿De quién es?</span>
        ${leidas.length ? `<span class="chips">${chipsPersona}</span><span class="sub">${leidas.length > 1 ? "Ha leído varios nombres: pulsa el del titular." : "Si no es correcto, cámbialo abajo en «Expediente nuevo»."}</span>` : '<span class="sub">No ha encontrado ningún nombre: escríbelo abajo en «Expediente nuevo».</span>'}
        ${dnisSueltos.length ? `<span class="chips">${dnisSueltos.map(x => `<button type="button" class="chip peq ${N.dni === x ? "sel" : ""}" data-dni="${x}">DNI ${x}</button>`).join("")}</span>` : ""}</div>
      ${clave ? `<div class="campo"><span class="lab">3 · ${FECHA_TXT[clave][0]}</span>
        ${chipsFecha ? `<span class="chips">${chipsFecha}</span>` : '<span class="sub">No ha encontrado ninguna fecha.</span>'}
        <span class="fila" style="align-items:center"><span class="sub" style="flex:0 0 auto">u otra:</span><input type="date" id="r-fecha" value="${R.fecha && !candidatas.includes(R.fecha) ? R.fecha : ""}" style="height:34px;border-radius:6px;border:1px solid var(--border);background:var(--bg);padding:0 8px;flex:0 1 180px"></span>
        <span class="sub">${FECHA_TXT[clave][1]}</span></div>` : ""}
      ${otrosDatos ? `<div>${otrosDatos}</div>` : ""}
      <div class="campo"><span class="lab">${clave ? 4 : 3} · ¿A qué expediente va?</span>
        ${opExp}
        ${otros.length ? `<div class="opcion"><input type="radio" name="destino" value="otro" id="d-otro" ${opExp ? "" : "checked"}><div style="flex:1;display:flex;flex-direction:column;gap:6px"><label for="d-otro"><b>Otro expediente abierto</b></label><div class="campo"><select id="r-otro" aria-label="Otro expediente abierto">${otros.map(e => `<option value="${e.id}">${esc(e.nombre)}</option>`).join("")}</select></div></div></div>` : ""}
        <div class="opcion"><input type="radio" name="destino" value="nuevo" id="d-nuevo" ${!opExp && !otros.length ? "checked" : ""}><div style="flex:1;display:flex;flex-direction:column;gap:10px"><label for="d-nuevo"><b>Expediente nuevo</b></label>
          <div class="fila"><div class="campo"><label for="n-nom">Nombre</label><input id="n-nom" data-n="nombre" value="${esc(N.nombre)}"></div><div class="campo"><label for="n-dni">DNI / NIE</label><input id="n-dni" data-n="dni" value="${esc(N.dni)}"></div></div>
          <div class="fila"><div class="campo"><label for="n-ap1">Primer apellido</label><input id="n-ap1" data-n="ap1" value="${esc(N.ap1)}"></div><div class="campo"><label for="n-ap2">Segundo apellido</label><input id="n-ap2" data-n="ap2" value="${esc(N.ap2)}"></div></div>
          <div class="campo"><span class="lab">Finalidad</span><div class="fines">${finalidades}</div></div></div></div>
      </div>
      <label class="check"><input type="checkbox" id="r-comun"><span><b>Es de todo el expediente</b><br><span class="sub">Arras, tasación, nota simple… Se nombra con el código del primer titular.</span></span></label>
      <label class="check"><input type="checkbox" id="r-priv"><span><b>No compartir</b><br><span class="sub">Añade PRIVADO_NO_COMPARTIR_ y lo deja fuera de los envíos.</span></span></label>
      <div class="acciones"><button class="btn pri" id="r-ok">${ico("check")}Confirmar y guardar</button><button class="btn" id="r-limbo">${ico("limbo")}Al Limbo</button></div>
    </section>
  </div>`;
}
async function cargarDoc(id) {
  if (S.docId !== id) { S.pag = 1; S.rev = null; }
  S.docId = id;
  try { S.doc = await api("documento/" + id); if (!S.rev) iniciarRevision(S.doc); } catch (e) { S.doc = null; aviso(e.message, true); }
  pintar();
}
function marcarDestinoNuevo() { const r = $("#d-nuevo"); if (r) { r.checked = true; S.rev.destino = "nuevo"; } }
function activarRevision() {
  if (S.rev?.destino) { const r = document.querySelector(`input[name="destino"][value="${S.rev.destino}"]`); if (r) r.checked = true; }
  document.querySelectorAll('input[name="destino"]').forEach(r => r.addEventListener("change", () => (S.rev.destino = r.value)));
  $("#r-otro")?.addEventListener("change", () => { const r = $("#d-otro"); r.checked = true; S.rev.destino = "otro"; });
  $("#pant")?.addEventListener("click", () => { S.pag--; pintar(); });
  $("#psig")?.addEventListener("click", () => { S.pag++; pintar(); });
  $("#r-ok")?.addEventListener("click", confirmar);
  $("#r-limbo")?.addEventListener("click", async () => {
    try { const r = await api("limbo", { documento: S.docId }); aviso("Al Limbo: " + r.nombre_final); siguiente(); } catch (e) { aviso(e.message, true); }
  });
  $("#r-tipo")?.addEventListener("change", e => { S.rev.tipo = e.target.value; S.rev.fecha = null; pintar(); });
  document.querySelectorAll("[data-tipo]").forEach(b => b.addEventListener("click", () => { S.rev.tipo = b.dataset.tipo; S.rev.fecha = null; pintar(); }));
  document.querySelectorAll("[data-persona]").forEach(b => b.addEventListener("click", () => {
    const p = S.doc.datos.personas[+b.dataset.persona];
    S.rev.persona = +b.dataset.persona;
    S.rev.nuevo = { nombre: p.nombre || "", ap1: p.apellido1 || "", ap2: p.apellido2 || "", dni: p.dni || S.rev.nuevo.dni };
    pintar(); if (!document.querySelector('input[name="destino"][value^="e:"]')) marcarDestinoNuevo();
  }));
  document.querySelectorAll("[data-dni]").forEach(b => b.addEventListener("click", () => { S.rev.nuevo.dni = b.dataset.dni; pintar(); }));
  document.querySelectorAll("[data-fecha]").forEach(b => b.addEventListener("click", () => { S.rev.fecha = b.dataset.fecha; pintar(); }));
  $("#r-fecha")?.addEventListener("change", e => { if (e.target.value) { S.rev.fecha = e.target.value; pintar(); } });
  document.querySelectorAll("[data-fin]").forEach(b => b.addEventListener("click", () => {
    S.rev.finalidad = b.dataset.fin;
    document.querySelectorAll("[data-fin]").forEach(x => { x.classList.toggle("sel", x === b); x.setAttribute("aria-pressed", x === b); });
    marcarDestinoNuevo();
  }));
  document.querySelectorAll("[data-n]").forEach(i => i.addEventListener("input", () => { S.rev.nuevo[i.dataset.n] = i.value; marcarDestinoNuevo(); }));
  document.querySelectorAll("#vista .tarjeta input, #vista .tarjeta select").forEach(el => {
    el.addEventListener("focus", () => (S.editando = true)); el.addEventListener("blur", () => (S.editando = false));
  });
}
async function confirmar() {
  const R = S.rev, tipo = R.tipo;
  if (!tipo) return aviso("Elige el tipo de documento.", true);
  const dest = (document.querySelector('input[name="destino"]:checked') || {}).value;
  if (!dest) return aviso("Elige a qué expediente va.", true);
  let expediente, persona = null;
  try {
    if (dest === "nuevo") {
      const N = R.nuevo;
      if (!N.nombre.trim() || !N.ap1.trim()) return aviso("Escribe al menos el nombre y el primer apellido.", true);
      const r = await api("expediente", { persona: { nombre: N.nombre.trim(), apellido1: N.ap1.trim(), apellido2: N.ap2.trim(), dni: N.dni.trim().toUpperCase() || null }, finalidad: R.finalidad });
      expediente = r.expediente; persona = r.persona; aviso("Expediente creado: " + r.carpeta);
    } else if (dest === "otro") expediente = +$("#r-otro").value;
    else { const [, e, p] = dest.split(":"); expediente = +e; persona = +p; }
    const g = await api("emparejar", { documento: S.docId, expediente, persona, comun: $("#r-comun").checked, tipo, privado: $("#r-priv").checked, fecha: R.fecha });
    aviso("Guardado: " + g.nombre_final);
    siguiente();
  } catch (e) { aviso(e.message, true); }
}

async function siguiente() {
  await refrescar(false);
  const cola = colaRevision();
  location.hash = cola.length ? "revision/" + cola[0].id : "revision";
  if (cola.length && S.docId === cola[0].id) cargarDoc(cola[0].id);
}

// ------------------------------------------------------------------ Expedientes
function vistaExpedientes() {
  const v = S.info.variante;
  return `<div class="cab"><div><small>Expedientes</small><h1>Expedientes</h1><div class="sub">Se crean desde el Centro de revisión al emparejar el primer documento.</div></div></div>
  ${S.expedientes.length ? `<section class="tarjeta sinp"><table class="tabla"><thead><tr><th>Expediente</th><th>Finalidad</th><th>Personas</th><th>Checklist</th><th>Carpeta</th></tr></thead><tbody>
  ${S.expedientes.map(e => `<tr class="clic" data-exp="${e.id}"><td><b>${esc(e.nombre)}</b></td><td>${esc(v.finalidades[e.finalidad] || e.finalidad)}</td>
    <td>${e.personas.map(p => esc(`${p.nombre} ${p.apellido1}`) + ` <span class="muted">(${esc(p.papel)})</span>`).join("<br>")}</td>
    <td>${e.checklist ? `${e.checklist.recibidos} de ${e.checklist.total}` : "—"}</td><td class="mono">${esc(e.carpeta)}</td></tr>`).join("")}</tbody></table></section>`
    : '<div class="tarjeta vacio">Todavía no hay expedientes.</div>'}`;
}
let EXP = null;
function vistaExpediente() {
  if (!EXP) return '<div class="tarjeta vacio">Cargando…</div>';
  const { e, ck } = EXP, v = S.info.variante;
  const c = { Recibido: "ok", Incompleto: "warn", Caducado: "bad", Pendiente: "todo" };
  return `<div class="cab"><div><small><a href="#expedientes">Expedientes</a> › ${esc(e.nombre)}</small><h1>${esc(e.nombre)}</h1>
    <div class="sub">${esc(v.finalidades[e.finalidad] || e.finalidad)} · carpeta <code>${esc(S.info.carpetas.documentos)}\\${esc(e.carpeta)}\\</code></div></div>
    <div class="acciones"><button class="btn" id="rehacer">${ico("play")}Rehacer archivo de texto</button></div></div>
  <section class="tarjeta sinp"><div class="tcab"><h2>Checklist · ${ck.recibidos} de ${ck.total}</h2></div>
    <table class="tabla"><thead><tr><th>Documento</th><th>De</th><th>Estado</th><th>Detalle</th><th>Archivo</th></tr></thead><tbody>
    ${ck.filas.map(f => `<tr><td>${esc(f.documento)}</td><td>${esc(f.quien)}</td><td>${pill(f.estado, c[f.estado] || "todo")}</td><td>${esc(f.detalle)}</td><td class="mono">${esc(f.archivos.join(", "))}</td></tr>`).join("")}
    </tbody></table></section>
  ${ck.avisos_cliente.length ? `<section class="tarjeta"><h2>Avisos al cliente</h2>${ck.avisos_cliente.map(a => `<div class="dato"><span>${esc(a)}</span></div>`).join("")}</section>` : ""}`;
}
async function cargarExpediente(id) {
  EXP = null; pintar();
  const e = S.expedientes.find(x => x.id === id) || (await api("expedientes")).find(x => x.id === id);
  EXP = { e, ck: await api("checklist/" + id) }; pintar();
}

// ------------------------------------------------------------------ Avisos, Limbo, Ajustes
let AV = null, TMP = null;
function vistaAvisos() {
  if (!AV) return '<div class="tarjeta vacio">Cargando…</div>';
  return `<div class="cab"><div><small>Avisos</small><h1>Avisos</h1><div class="sub">Avisos Cliente: lo que falta o caducó. Avisos Se: problemas del programa o de los archivos.</div></div></div>
  <section class="tarjeta"><h2>Avisos Cliente</h2>${AV.cliente.map(a => `<div class="dato"><span>${esc(a.mensaje)}</span><span class="muted">expediente ${a.expediente_id}</span></div>`).join("") || '<span class="sub">Nada pendiente.</span>'}</section>
  <section class="tarjeta"><h2>Avisos Se</h2>${AV.se.slice().reverse().map(a => `<div class="dato"><span>${esc(a.mensaje)}</span><span class="muted">${esc(a.fecha.replace("T", " ").slice(0, 16))}</span></div>`).join("") || '<span class="sub">Nada pendiente.</span>'}</section>`;
}
function vistaLimbo() {
  const docs = S.estado.lotes.flatMap(l => l.documentos).filter(d => d.estado === "limbo");
  return `<div class="cab"><div><small>Limbo</small><h1>Limbo</h1><div class="sub">Documentos sin expediente todavía, guardados en <code>${esc(S.info.carpetas.documentos)}\\_Limbo\\</code>.</div></div></div>
  ${docs.length ? `<section class="tarjeta sinp"><table class="tabla"><thead><tr><th>Archivo recibido</th><th>Tipo</th><th>Nombre</th></tr></thead><tbody>${docs.map(d => `<tr><td>${esc(d.archivo)}</td><td>${esc(nombreTipo(d.tipo))}</td><td class="mono">${esc(d.nombre_final)}</td></tr>`).join("")}</tbody></table></section>` : '<div class="tarjeta vacio">El Limbo está vacío.</div>'}`;
}
function vistaAjustes() {
  const c = S.info.carpetas, mb = b => (b / 1e6).toFixed(1).replace(".", ",") + " MB";
  return `<div class="cab"><div><small>Ajustes</small><h1>Ajustes</h1><div class="sub">${esc(S.info.compatibilidad)}</div></div></div>
  <section class="tarjeta"><h2>Carpetas</h2>${Object.entries(c).map(([k, p]) => `<div class="dato"><span>${esc(k)}</span><span class="mono">${esc(p)}</span></div>`).join("")}
    <span class="sub">Cambiar carpetas desde aquí llegará en la siguiente entrega; ahora se cambian en Datos\\ajustes.json.</span></section>
  <section class="tarjeta"><h2>Datos temporales</h2>${TMP ? `
    <div class="dato"><span>Copia de trabajo</span><span>${TMP.trabajo_archivos} archivos · ${mb(TMP.trabajo_bytes)}</span></div>
    <div class="dato"><span>Sin uso (restos de lotes terminados)</span><span>${TMP.trabajo_sin_uso} archivos · ${mb(TMP.trabajo_sin_uso_bytes)}</span></div>
    <div class="dato"><span>Documentos en proceso</span><span>${TMP.en_proceso}</span></div>
    <div class="dato"><span>Memoria de textos reconocidos</span><span>${TMP.textos_paginas} páginas · ${mb(TMP.textos_bytes)}</span></div>` : "Cargando…"}
    <div class="acciones"><button class="btn pri" data-vaciar="trabajo">Vaciar lo que no se usa</button><button class="btn peligro" data-vaciar="trabajo-todo">Vaciar toda la copia de trabajo…</button><button class="btn" data-vaciar="textos">Vaciar la memoria de textos…</button></div>
    <span class="sub">Toda la copia de trabajo: lo que esté a medias se vuelve a leer desde el principio. Memoria de textos: los archivos de texto de los expedientes se conservan.</span></section>
  <section class="tarjeta"><h2>Mejorar el reconocimiento</h2>
    <span class="sub">Guarda en un archivo de texto lo que el programa ha leído de cada documento y lo que ha deducido (DNI, nombres, fechas). Lleva datos personales: compártelo solo con quien vaya a ajustar el reconocimiento.</span>
    <div class="acciones"><button class="btn" id="exportar">Exportar los textos leídos</button></div></section>
  <section class="tarjeta"><h2>Versiones</h2><div class="dato"><span>Motor Sentiende</span><span>${esc(S.info.motor.version)} · contrato ${S.info.motor.contrato}.x</span></div>
    <div class="dato"><span>Variante</span><span>${esc(S.info.variante.nombre)} ${esc(S.info.variante.version)}</span></div></section>`;
}
function activarAjustes() {
  $("#exportar")?.addEventListener("click", async () => { try { const r = await api("exportar_textos", {}); aviso("Guardado en " + r.ruta); } catch (e) { aviso(e.message, true); } });
  document.querySelectorAll("[data-vaciar]").forEach(b => b.addEventListener("click", async () => {
    const q = b.dataset.vaciar;
    if (q !== "trabajo" && !confirm(q === "textos" ? "¿Vaciar la memoria de textos? Los archivos de texto de los expedientes se conservan." : "¿Vaciar toda la copia de trabajo? Lo que esté a medias se volverá a leer.")) return;
    const r = await api("vaciar", { que: q }); aviso(`Vaciado: ${r.vaciado}`); TMP = await api("temporales"); pintar(); refrescar(true);
  }));
}

// ------------------------------------------------------------------ navegación
function pintar() {
  lateral();
  const [r, id] = S.ruta.split("/");
  const vistas = { bandeja: [vistaBandeja, activarBandeja], motor: [vistaMotor, activarMotor], revision: [vistaRevision, activarRevision],
    expedientes: [vistaExpedientes, () => document.querySelectorAll("[data-exp]").forEach(tr => tr.addEventListener("click", () => (location.hash = "expediente/" + tr.dataset.exp)))],
    expediente: [vistaExpediente, () => $("#rehacer")?.addEventListener("click", async () => { await api("textos", { expediente: +id }); aviso("Archivo de texto rehecho"); })],
    avisos: [vistaAvisos, () => {}], limbo: [vistaLimbo, () => {}], ajustes: [vistaAjustes, activarAjustes] };
  const [v, act] = vistas[r] || vistas.bandeja;
  const y = $("#vista").scrollTop;
  $("#vista").innerHTML = v();
  $("#vista").scrollTop = y;
  act();
}
async function ir() {
  S.ruta = location.hash.slice(1) || "bandeja";
  const [r, id] = S.ruta.split("/");
  if (r === "motor") LOTE = id ? +id : null;
  if (r === "revision") {
    const cola = colaRevision();
    const objetivo = id ? +id : cola[0]?.id;
    if (objetivo) { if (objetivo !== S.docId || !S.doc) return cargarDoc(objetivo); }
    else { S.doc = null; S.docId = null; }
  }
  if (r === "expediente") return cargarExpediente(+id);
  if (r === "avisos") AV = await api("avisos");
  if (r === "ajustes") TMP = await api("temporales");
  pintar();
}
async function refrescar(repintar) {
  const antes = JSON.stringify(S.estado);
  [S.estado, S.expedientes] = await Promise.all([api("estado"), api("expedientes")]);
  const cambio = antes !== JSON.stringify(S.estado);
  const r = S.ruta.split("/")[0] || "bandeja";
  if (repintar || (cambio && ["bandeja", "motor", "limbo", ""].includes(r))) pintar();
  else if (cambio) { lateral(); if (r === "revision" && !S.editando && !S.doc) ir(); }
}
async function inicio() {
  S.info = await api("info");
  const c = S.info.variante.colores || {}, st = document.documentElement.style;
  [["--marco", c.marco], ["--accent", c.acento], ["--lateral", c.lateral], ["--lateralActivo", c.lateral_activo], ["--lateralBorde", c.lateral_borde], ["--lateralTenue", c.lateral_tenue]]
    .forEach(([k, v]) => v && st.setProperty(k, v));
  document.title = `${S.info.variante.nombre} · con Sentiende`;
  [S.estado, S.expedientes] = await Promise.all([api("estado"), api("expedientes")]);
  window.addEventListener("hashchange", ir);
  await ir();
  setInterval(() => refrescar(false).catch(() => {}), 1500);
}
inicio().catch(e => { document.body.innerHTML = `<p style="padding:30px">No se ha podido abrir: ${esc(e.message)}</p>`; });
