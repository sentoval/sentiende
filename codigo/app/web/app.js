// Sentiende · pantallas (v1.0). Sin librerías: todo funciona sin internet.
"use strict";

const S = { zoom: 1, info: null, estado: null, expedientes: [], doc: null, docId: null, pag: 1, ruta: "", editando: false };
const $ = (sel, el = document) => el.querySelector(sel);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const IC = {
  inbox: '<path d="M4 13h4l2 3h4l2-3h4"/><path d="M5 5h14l1 8v6H4v-6z"/>',
  motor: '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4M2 9h4M2 15h4M18 9h4M18 15h4"/>',
  check: '<path d="m5 12 5 5 9-10"/>', folder: '<path d="M3 6h7l2 2h9v11H3z"/>', user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
  bell: '<path d="M6 9a6 6 0 0 1 12 0c0 6 2 7 2 7H4s2-1 2-7"/><path d="M10 20a2 2 0 0 0 4 0"/>', limbo: '<circle cx="12" cy="12" r="8"/><path d="M8 12h8"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2 20c0-3.5 3-5.5 7-5.5s7 2 7 5.5"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7"/><path d="M18 14.8c2.4.6 4 2.3 4 5.2"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v4h16v-4"/>', search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>', trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>', tag: '<path d="M3 3h8l10 10-8 8L3 11z"/>',
  scan: '<path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3"/><path d="M7 12h10"/>',
  bt: '<path d="m7 7 10 10-5 5V2l5 5L7 17"/>', mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>', paste: '<rect x="7" y="4" width="10" height="4" rx="1"/><path d="M7 6H5v15h14V6h-2"/>',
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
  limbo: ["En el Limbo", "todo"], unido: ["Unido a otro", "todo"], duplicado: ["Duplicado", "warn"], separado: ["Separado", "todo"], error: ["Error", "bad"] };
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
  const r0 = S.ruta.split("/")[0] || "motor", r = r0 === "limbo" ? "motor" : r0;   // el Limbo está dentro del motor
  const item = (id, ic, txt, num, activo = true, prox = "") =>
    activo ? `<a href="#${id}" ${r === id ? 'aria-current="page"' : ""}>${ico(ic)}${txt}${num ? `<span class="num">${num}</span>` : ""}</a>`
           : `<a class="inactivo" aria-disabled="true" title="Llegará en una próxima versión">${ico(ic)}${txt}<span class="prox">${prox}</span></a>`;
  const abiertos = S.expedientes.filter(e => e.estado === "abierto").slice(0, 8);
  $("#lateral").innerHTML = `
    <div class="marca"><img class="logo" src="/api/logo" alt="" width="48" height="48"><span><b>${esc(v.nombre)}</b><span>con Sentiende</span></span></div>
    <div class="nav">
      ${item("expedientes", "folder", "Expedientes")}
      ${item("revision", "check", "Centro de revisión", c.revisar)}
      ${item("motor", "motor", "Motor de proceso", c.pendientes - (c.revisar || 0))}
      ${item("avisos", "bell", "Avisos", c.avisos)}
      ${item("", "chart", "Estadísticas", 0, false, "pronto")}
    </div>
    <div class="nav-iconos">
      <a class="inactivo" aria-disabled="true" title="Buscar en documentos (pronto)" aria-label="Buscar en documentos (pronto)">${ico("search", 20)}</a>
      <a href="#ajustes" title="Ajustes" aria-label="Ajustes" ${r === "ajustes" ? 'aria-current="page"' : ""}>${ico("gear", 20)}</a>
    </div>
    <div class="lat-zona" id="zona">
      <span class="ico">${ico("upload", 20)}</span>
      <b>Arrastra aquí</b>
      <span class="sub">PDF, fotos, Word o Excel. También Ctrl+V o la carpeta <code title="${esc(S.info.carpetas.entrada)}">Entrada</code>.</span>
      <label class="btn peq pri">${ico("upload", 15)}Elegir archivos…<input type="file" id="elegir" multiple hidden accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff,.heic,.docx,.xlsx"></label>
      <span class="lat-btns"><button class="btn peq" id="b-correo" title="Recoger los adjuntos de los correos nuevos">${ico("mail", 15)}Correo</button>
      <button class="btn peq" id="b-bt" title="Abrir la recepción por Bluetooth de Windows">${ico("bt", 15)}Bluetooth</button></span>
      <button class="btn peq lat-escaner" disabled title="Escanear directamente: en una próxima versión">${ico("scan", 15)}Escanear <span class="v11">pronto</span></button>
      ${CORREO_TXT ? `<span class="lat-estado">${esc(CORREO_TXT)}</span>` : ""}${BT?.activo ? `<span class="lat-estado">${ico("bt", 13)} ${esc(BT.mensaje)}</span>` : ""}
      ${S.estado?.trabajando ? '<span class="trabajando">El motor está trabajando…</span>' : ""}
    </div>
    <div class="pie">Motor ${esc(S.info.motor.version)} · ${esc(v.nombre)} ${esc(v.version)}</div>`;
  activarZona();
}
function activarZona() {
  const zona = $("#zona");
  ["dragenter", "dragover"].forEach(ev => zona.addEventListener(ev, e => { e.preventDefault(); zona.classList.add("encima"); }));
  ["dragleave", "drop"].forEach(ev => zona.addEventListener(ev, e => { e.preventDefault(); zona.classList.remove("encima"); }));
  zona.addEventListener("drop", e => { e.stopPropagation(); subir([...e.dataTransfer.files], "arrastrados"); });
  $("#elegir").addEventListener("change", e => subir([...e.target.files], "elegidos"));
  $("#b-correo").addEventListener("click", revisarCorreo);
  $("#b-bt").addEventListener("click", async () => {
    try { BT = await api("bluetooth", {}); aviso("Asistente de Bluetooth de Windows abierto: envía los archivos desde el móvil. Lo recibido entra solo."); vigilarBT(); }
    catch (e) { aviso(e.message, true); }
  });
}
// ---------------- Correo y Bluetooth (v1.1)
let CORREO_TXT = "", BT = null, CORREO = null;
async function revisarCorreo() {
  const c = await api("correo");
  if (!c.ajustes.servidor || !c.ajustes.hay_clave) { aviso("Primero configura tu correo en Ajustes."); location.hash = "ajustes"; return; }
  try { await api("correo/revisar", {}); } catch (e) { return aviso(e.message, true); }
  CORREO_TXT = "Revisando el correo…"; lateral();
  for (let i = 0; i < 300; i++) {
    await new Promise(r => setTimeout(r, 1500));
    const e = (await api("correo")).estado;
    if (e.trabajando) continue;
    CORREO_TXT = "";
    if (e.error) aviso("Correo: " + e.error, true);
    else { const r = e.resumen; aviso(r.adjuntos ? `Correo: ${r.adjuntos} adjunto(s) de ${r.lotes.length} correo(s)` + (r.ignorados.length ? ` · ${r.ignorados.length} ignorado(s), ver Avisos` : "") : `Correo: nada nuevo (${r.correos} correo(s) revisado(s))` + (r.ignorados.length ? ` · ${r.ignorados.length} adjunto(s) ignorado(s)` : "")); }
    await refrescar(true); return;
  }
}
async function vigilarBT() {
  while (BT && BT.activo) { lateral(); await new Promise(r => setTimeout(r, 2000)); BT = await api("bluetooth"); }
  if (BT) aviso(BT.mensaje); lateral();
}
// Soltar archivos en cualquier parte de la ventana también los recibe (y el navegador no los abre)
window.addEventListener("dragover", e => { if ([...(e.dataTransfer?.types || [])].includes("Files")) { e.preventDefault(); $("#zona")?.classList.add("encima"); } });
window.addEventListener("dragleave", e => { if (!e.relatedTarget) $("#zona")?.classList.remove("encima"); });
window.addEventListener("drop", e => { if (e.dataTransfer?.files?.length) { e.preventDefault(); $("#zona")?.classList.remove("encima"); subir([...e.dataTransfer.files], "arrastrados"); } });

// ------------------------------------------------------------------ Recibir archivos
async function subir(archivos, origen) {
  if (!archivos.length) return;
  aviso(`Recibiendo ${archivos.length} archivo(s)…`);
  const grupo = Date.now() + "-" + Math.random().toString(36).slice(2);   // lo soltado a la vez va al mismo lote
  for (const f of archivos) {
    try { await api("subir", f, { headers: { "X-Nombre": encodeURIComponent(f.name || "pegado.png"), "X-Origen": origen, "X-Grupo": grupo } }); }
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
function pestanasMotor(activa) {
  const n = S.estado.cuentas.limbo || 0;
  return `<nav class="pestanas" aria-label="Motor de proceso"><a href="#motor" ${activa === "motor" ? 'aria-current="page"' : ""}>${ico("motor", 16)}Proceso</a>
    <a href="#limbo" ${activa === "limbo" ? 'aria-current="page"' : ""}>${ico("limbo", 16)}Limbo${n ? `<span class="num">${n}</span>` : ""}</a></nav>`;
}
function vistaMotor() {
  const lotes = S.estado.lotes.filter(x => x.documentos.length);
  const pendiente = x => x.documentos.some(d => !["guardado", "limbo", "duplicado"].includes(d.estado));
  const l = lotes.find(x => x.id === LOTE) || lotes.find(pendiente) || lotes[0];
  if (!l) return `<div class="cab"><div><small>Motor de proceso</small><h1>Motor de proceso</h1></div></div>${pestanasMotor("motor")}<div class="tarjeta vacio">No hay ningún lote todavía. Arrastra documentos al cuadro de la izquierda.</div>`;
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
  ${pestanasMotor("motor")}
  ${parado ? `<div class="tarjeta" style="border-color:var(--bad);background:var(--badSoft)"><b>El motor se ha parado: ${esc(parado.motivo || "")}</b><span class="sub">Nada se ha perdido: el original sigue en Entrada\\. Corrige la causa y pulsa «Reanudar lo pendiente».</span></div>` : ""}
  <nav class="lotes" aria-label="Lotes">${lotes.slice(0, 12).map(x => `<a href="#motor/${x.id}" ${x.id === l.id ? 'aria-current="true"' : ""}>Lote ${x.id}${pendiente(x) ? " ·  en curso" : ""}</a>`).join("")}</nav>
  <section class="tarjeta"><div class="cab"><div><h2>Lote ${l.id} · ${esc(l.origen)}</h2><span class="sub">${titulo}</span></div><b style="font-size:22px;color:${parado ? "var(--bad)" : "var(--accent)"}">${pct} %</b></div>
    <div class="progreso"><i style="width:${pct}%;${parado ? "background:var(--bad)" : ""}"></i></div>
    <div class="ubic"><span>${ico("folder", 14)} Originales: <code>Entrada\\</code> hasta guardar</span><span>${ico("folder", 14)} Copia de trabajo: <code>Datos\\Trabajo\\lote_${l.id}\\</code></span><span>${ico("folder", 14)} Al terminar: <code>SeDocumentos\\</code> y <code>Doc_original\\</code></span></div>
    <div class="pipeline" style="padding-bottom:230px;margin-bottom:-220px">${pipe}</div></section>
  <section class="tarjeta sinp"><div class="tcab"><h2>Documentos del lote</h2><span class="sub">Pulsa uno para revisarlo</span></div>
    <table class="tabla"><thead><tr><th>Documento</th><th>Fase</th><th>Tipo</th><th>Dónde está ahora</th><th>Estado</th></tr></thead><tbody>
    ${docs.map(d => `<tr ${["espera_emparejar", "parado"].includes(d.estado) ? `class="clic" data-doc="${d.id}"` : ""}><td>${esc(d.archivo)}${d.nombre_final ? `<div class="mono muted">${esc(d.nombre_final)}</div>` : ""}</td><td>${fbar(d.fase, d.estado)}</td><td>${esc(d.tipo ? nombreTipo(d.tipo) : "—")}</td>
      <td>${Object.entries(d.donde).filter(([, v]) => v).map(([k, v]) => `<div class="mono"><span class="muted">${esc(k)}:</span> ${esc(v)}</div>`).join("")}</td><td>${est(d.estado)}</td></tr>`).join("")}
    </tbody></table></section>`;
}
function activarMotor() {
  $("#reanudar")?.addEventListener("click", async () => { await api("procesar", {}); aviso("Reanudando…"); refrescar(true); });
  document.querySelectorAll("tr[data-doc]").forEach(tr => tr.addEventListener("click", () => (location.hash = "revision/" + tr.dataset.doc)));
}

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
  const fin = (S.info.finalidades_visibles || Object.keys(S.info.variante.finalidades))[0];
  S.rev = { tipo: d.tipo || "", persona: p0.completo ? 0 : -1, fecha: null, finalidad: fin,
    nuevo: { nombre: p0.nombre || "", ap1: p0.apellido1 || "", ap2: p0.apellido2 || "", dni: p0.dni || (datos.dni || [])[0] || "" } };
  const lm = !p0.completo && loteMayoritario(d);
  if (lm) usarLote(lm);      // sin ningún nombre leído: se propone como el resto del lote
}
function usarLote(lm) {
  const R = S.rev, p = lm.per;
  R.persona = -2; R.nuevo = { nombre: p.nombre || "", ap1: p.apellido1 || "", ap2: p.apellido2 || "", dni: p.dni || "" };
  R.destino = "e:" + lm.exp.id; R.dupOk = false;
}
function fechaAuto(d, clave) { const x = d.datos || {}; return clave ? x[clave] || (clave === "emision" ? (x.fechas || [])[0] : null) : null; }

// ---- personas ya fichadas (para no duplicar expedientes)
const normaliza = s => (s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toUpperCase().replace(/\s+/g, " ").trim();
function fichadas() {
  const m = new Map();
  S.expedientes.filter(e => e.estado !== "unido").forEach(e => e.personas.forEach(p => {
    if (!m.has(p.id)) m.set(p.id, { ...p, exps: [] });
    m.get(p.id).exps.push({ id: e.id, nombre: e.nombre, papel: p.papel, estado: e.estado });
  }));
  return [...m.values()];
}
function buscarFichada(P) {
  const f = fichadas(), n = normaliza(`${P.nombre} ${P.ap1} ${P.ap2}`);
  return f.find(x => P.dni && x.dni && x.dni.toUpperCase() === P.dni.toUpperCase()) || f.find(x => normaliza(`${x.nombre} ${x.apellido1} ${x.apellido2}`) === n) || null;
}
function parecidas(P, menos) {
  return fichadas().filter(x => (!menos || x.id !== menos.id) && normaliza(x.nombre) === normaliza(P.nombre) && normaliza(x.apellido1) === normaliza(P.ap1));
}

// Persona y expediente que más se repiten en lo ya confirmado del mismo lote
function loteMayoritario(d) {
  const lote = S.estado.lotes.find(l => l.id === d.lote_id);
  if (!lote) return null;
  const hechos = lote.documentos.filter(x => x.estado === "guardado" && x.expediente_id && x.persona_id);
  if (!hechos.length) return null;
  const cuenta = {};
  hechos.forEach(x => { const k = x.expediente_id + ":" + x.persona_id; cuenta[k] = (cuenta[k] || 0) + 1; });
  const [k, n] = Object.entries(cuenta).sort((a, b) => b[1] - a[1])[0];
  const [eid, pid] = k.split(":").map(Number);
  const exp = S.expedientes.find(e => e.id === eid && e.estado === "abierto");
  const per = exp && exp.personas.find(p => p.id === pid);
  return exp && per ? { exp, per, n, total: hechos.length } : null;
}
function vistaRevision() {
  const cola = colaRevision();
  if (!cola.length) return `<div class="cab"><div><small>Centro de revisión</small><h1>Centro de revisión</h1></div></div><div class="tarjeta vacio">No hay nada pendiente de revisar. ${S.estado.trabajando ? "El motor sigue trabajando: aparecerá aquí lo que necesite tu respuesta." : ""}</div>`;
  const d = S.doc;
  const lista = cola.map(x => `<a href="#revision/${x.id}" ${S.docId === x.id ? 'aria-current="true"' : ""}><b>${esc(x.archivo)}</b><small>${x.estado === "parado" ? esc(x.motivo) : x.tipo ? esc(nombreTipo(x.tipo)) + " · " + Math.round((x.confianza || 0) * 100) + " %" + (x.motivo ? " · revisar" : "") : "No reconocido"}</small></a>`).join("");
  if (!d || !S.rev) return `<div class="rev-abajo"><nav class="cola" aria-label="Pendientes">${lista}</nav><div class="tarjeta vacio">Cargando…</div></div>`;
  const datos = d.datos || {}, v = S.info.variante, R = S.rev, P = R.nuevo;
  const leidas = datos.personas || [];
  const pags = d.paginas_lista.length;
  // 1 · tipo
  const tipos = S.info.tipos.map(t => `<option value="${t.id}" ${t.id === R.tipo ? "selected" : ""}>${esc(t.nombre)}</option>`).join("");
  const extra = [["Ejercicio", datos.ejercicio], ["Entidad", d.entidad]].filter(([, x]) => x).map(([a, b]) => `${a}: <b>${esc(b)}</b>`).join(" · ");
  // 2 · persona
  const fich = buscarFichada(P);
  // la persona elegida va siempre la primera
  const chipsLeidas = leidas.map((p, i) => ({ sel: R.persona === i, html: `<button type="button" class="chip peq ${R.persona === i ? "sel" : ""}" data-persona="${i}">${esc(p.completo)}${p.dni ? `<small class="mono">${esc(p.dni)}</small>` : ""}</button>` }));
  const chipsPersona = [...chipsLeidas.filter(c => c.sel), ...chipsLeidas.filter(c => !c.sel)].map(c => c.html).join("")
    + `<button type="button" class="chip peq ${R.persona === -1 ? "sel" : ""}" data-persona="-1">Otra persona…</button>`;
  const lm = loteMayoritario(d);
  const chipLote = lm ? `<button type="button" class="chip peq lote ${R.persona === -2 ? "sel" : ""}" id="r-lote" title="Lo que más se repite en los documentos ya confirmados de este lote">Como el resto del lote: ${esc(`${lm.per.nombre} ${lm.per.apellido1}`)}<small>${lm.n} de ${lm.total}</small></button>` : "";
  const estadoPersona = fich ? `<span class="ok-txt">Ya fichada: ${esc(fich.exps.map(e => `${e.papel} en «${e.nombre}»`).join(" · "))}</span>`
    : `<span class="sub">Persona nueva: todavía no está en ningún expediente.</span>`;
  // 3 · fecha
  const clave = R.tipo ? (d.fecha_claves || {})[R.tipo] : null;
  const auto = fechaAuto(d, clave), elegida = R.fecha || auto;
  const fmt = clave === "periodo" ? fmtM : fmtF;
  const candidatas = [...new Set([auto, datos.periodo, datos.emision, datos.caducidad, ...(datos.fechas || [])].filter(Boolean))];
  const vistas = new Set(), chipsFecha = candidatas.filter(f => { const k = fmt(f); if (vistas.has(k)) return false; vistas.add(k); return true; })
    .map(f => `<button type="button" class="chip peq ${elegida && fmt(f) === fmt(elegida) ? "sel" : ""}" data-fecha="${f}" title="${f === auto ? "La que ha cogido el programa" : ""}">${fmt(f)}${f === auto ? " ·auto" : ""}</button>`).join("");
  // 4 · expediente
  const abiertos = S.expedientes.filter(e => e.estado === "abierto");
  const otrosFich = leidas.map(p => buscarFichada({ nombre: p.nombre, ap1: p.apellido1, ap2: p.apellido2, dni: p.dni })).filter(Boolean);
  const dePersona = e => fich && e.personas.some(p => p.id === fich.id);
  const deOtra = e => otrosFich.some(o => e.personas.some(p => p.id === o.id));
  const ordenados = [...abiertos].sort((a, b) => (dePersona(b) - dePersona(a)) || (deOtra(b) - deOtra(a)));
  if (R.destino === undefined) R.destino = ordenados.length && (dePersona(ordenados[0]) || deOtra(ordenados[0])) ? "e:" + ordenados[0].id : "nuevo";
  const nomP = esc(`${P.nombre} ${P.ap1}`.trim() || "esta persona");
  const cards = [], vistos = new Set();
  const add = (e, titulo, detalle) => { if (vistos.has(e.id)) return; vistos.add(e.id); cards.push({ val: "e:" + e.id, titulo, detalle }); };
  const papelDe = e => (fich && e.personas.find(p => p.id === fich.id) || {}).papel;
  ordenados.filter(dePersona).forEach(e => add(e, e.nombre, `Es de ${nomP} (${papelDe(e).toLowerCase()})`));
  if (lm) add(lm.exp, lm.exp.nombre, `Como el resto del lote (${lm.n} de ${lm.total} confirmados)` + (dePersona(lm.exp) ? "" : ` · se añadirá ${nomP} como cotitular`));
  ordenados.filter(e => !dePersona(e) && deOtra(e)).forEach(e => {
    const quien = e.personas.find(p => otrosFich.some(o => o.id === p.id));
    add(e, e.nombre, `Es de ${esc(`${quien.nombre} ${quien.apellido1}`)}, que también sale en el documento · se añadirá ${nomP} como cotitular`);
  });
  const resto = ordenados.filter(e => !vistos.has(e.id));
  const otroSel = R.destino.startsWith("e:") && resto.some(e => "e:" + e.id === R.destino);
  const opciones = cards.map(c => `<label class="dest ${R.destino === c.val ? "sel" : ""}"><input type="radio" name="destino" value="${c.val}" ${R.destino === c.val ? "checked" : ""}><span><b>${esc(c.titulo)}</b><small>${c.detalle}</small></span></label>`).join("")
    + `<label class="dest ${R.destino === "nuevo" ? "sel" : ""}"><input type="radio" name="destino" value="nuevo" ${R.destino === "nuevo" ? "checked" : ""}><span><b>Expediente nuevo</b><small>Para ${nomP}</small></span></label>`
    + (resto.length ? `<label class="dest ${otroSel ? "sel" : ""}"><input type="radio" name="destino" value="otro" ${otroSel ? "checked" : ""}><span><b>Otro expediente…</b>
        <select id="r-otro" aria-label="Otro expediente"><option value="">— Elegir —</option>${resto.map(e => `<option value="e:${e.id}" ${R.destino === "e:" + e.id ? "selected" : ""}>${esc(e.nombre)}</option>`).join("")}</select>
        ${otroSel ? `<small>Se añadirá ${nomP} como cotitular si no está.</small>` : ""}</span></label>` : "");
  const expSel = R.destino.startsWith("e:") ? abiertos.find(e => e.id === +R.destino.slice(2)) : null;
  const avisoDestino = "";
  // duplicados al crear expediente nuevo
  const dups = R.destino === "nuevo" ? [fich, ...parecidas(P, fich)].filter(x => x && x.exps.some(e => e.estado === "abierto")) : [];
  const avisoDup = dups.length ? `<div class="dup" role="alert"><b>¡Ojo! Puede ser un expediente duplicado.</b>
      ${dups.map(x => `<div>Ya existe <b>${esc(`${x.nombre} ${x.apellido1} ${x.apellido2 || ""}`)}</b>${x.dni ? ` (DNI ${esc(x.dni)})` : ""} en:
        ${x.exps.filter(e => e.estado === "abierto").map(e => `<button type="button" class="btn peq" data-ir-exp="${e.id}">Añadir a «${esc(e.nombre)}»</button>`).join(" ")}</div>`).join("")}
      <label class="check"><input type="checkbox" id="dup-ok" ${R.dupOk ? "checked" : ""}><span>Es otra persona o quiero otro expediente aparte</span></label></div>` : "";
  // datos de la persona (para persona nueva o expediente nuevo)
  const mostrarDatos = R.destino === "nuevo" || R.persona === -1 || !fich;
  const finalidades = Object.entries(v.finalidades).filter(([k]) => (S.info.finalidades_visibles || [k]).includes(k)).map(([k, n]) => `<button type="button" class="fin-pill ${R.finalidad === k ? "sel" : ""}" data-fin="${k}" aria-pressed="${R.finalidad === k}">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${FIN_ICO[k] || IC.folder}</svg>${esc(n)}</button>`).join("");
  const filaDatos = mostrarDatos ? `<div class="fila-rev"><span class="lab">${R.destino === "nuevo" ? "Expediente nuevo" : "Datos de la persona"}</span>
      <div class="campos-inline">
        <div class="campo"><label for="n-nom">Nombre</label><input id="n-nom" data-n="nombre" value="${esc(P.nombre)}"></div>
        <div class="campo"><label for="n-ap1">Primer apellido</label><input id="n-ap1" data-n="ap1" value="${esc(P.ap1)}"></div>
        <div class="campo"><label for="n-ap2">Segundo apellido</label><input id="n-ap2" data-n="ap2" value="${esc(P.ap2)}"></div>
        <div class="campo"><label for="n-dni">DNI / NIE</label><input id="n-dni" data-n="dni" value="${esc(P.dni)}"></div>
        ${R.destino === "nuevo" ? `<div class="campo"><span class="lab">Finalidad</span><div class="fin-pills">${finalidades}</div></div>` : ""}
      </div></div>` : "";
  // las demás personas del documento
  const otras = leidas.map((p, i) => ({ p, i })).filter(x => x.i !== R.persona).map(x => {
    const f = buscarFichada({ nombre: x.p.nombre, ap1: x.p.apellido1, ap2: x.p.apellido2, dni: x.p.dni });
    return { ...x, yaEsta: !!(f && expSel && expSel.personas.some(q => q.id === f.id)) };
  });
  const filaOtras = otras.length ? `<div class="fila-rev otras"><span class="lab">Más personas en el documento</span><div class="otras-lista">
      ${otras.map(x => `<div class="otra"><span><b>${esc(x.p.completo)}</b>${x.p.dni ? ` <span class="mono muted">${esc(x.p.dni)}</span>` : ""}</span>
        ${x.yaEsta ? '<span class="ok-txt">Ya está en este expediente</span>' : `<span class="seg">${[["cotitular", "Cotitular"], ["separado", "Expediente aparte"], ["tercero", "Tercero, no fichar"]]
          .map(([k, n]) => `<button type="button" class="${(R.otros || {})[x.i] === k ? "sel" : ""}" data-otro="${x.i}" data-acc="${k}">${n}</button>`).join("")}</span>`}</div>`).join("")}</div></div>` : "";
  const pendientesOtras = otras.filter(x => !x.yaEsta).length;
  const union = (() => { const pr = (S.prop || []).find(x => x.documentos.includes(d.id)); return pr ? `<div class="union-mini"><b>${pr.documentos.length} fotos parecen el mismo documento.</b> <a class="btn pri peq" href="#unir/${pr.documentos.join(",")}">Ver y unir</a></div>` : ""; })();
  return `
  <section class="barra-rev" aria-label="Revisar">
    <div class="barra-cab"><b>Revisar</b><span class="sub">${esc(d.nombre_recibido)} · ${d.motivo ? esc(d.motivo) : "clasificado con " + Math.round((d.confianza || 0) * 100) + " %"} · ${cola.length} pendiente(s)</span>${union}</div>
    <div class="barra-pasos">
      <div class="paso"><span class="lab">1 · Tipo</span><select id="r-tipo">${R.tipo ? "" : '<option value="">— Elegir —</option>'}${tipos}</select>
        ${(d.alternativas || []).length ? `<span class="chips">${d.alternativas.map(a => `<button type="button" class="chip mini" data-tipo="${a.tipo}">${esc(nombreTipo(a.tipo))}</button>`).join("")}</span>` : ""}
        ${extra ? `<span class="sub">${extra}</span>` : ""}</div>
      <div class="paso"><span class="lab">2 · ¿De quién es?</span><span class="chips">${R.persona >= 0 ? chipsPersona.replace(/(<\/button>)/, "$1" + chipLote) : chipLote + chipsPersona}</span>${estadoPersona}</div>
      <div class="paso"><span class="lab">3 · ${clave ? FECHA_TXT[clave][0] : "Fecha"}</span>
        ${clave ? `<span class="chips">${chipsFecha || '<span class="sub">No ha leído ninguna.</span>'}</span><input type="date" id="r-fecha" aria-label="Otra fecha" value="${R.fecha && !candidatas.includes(R.fecha) ? R.fecha : ""}">` : '<span class="sub">Este tipo no lleva fecha en el nombre.</span>'}</div>
      <div class="paso"><span class="lab">4 · Expediente</span><div class="destinos" role="radiogroup" aria-label="Expediente">${opciones}</div></div>
      <div class="paso acciones-rev">
        <a class="btn peq" href="#unir/${d.id}">Unir…</a>
        <button class="btn peq" id="r-limbo">${ico("limbo", 15)}Limbo</button>
        <hr class="sep-acc">
        <div class="ambito" role="radiogroup" aria-label="De quién es el documento">
          <button type="button" class="btn peq ${R.comun ? "" : "sel"}" data-comun="0" aria-pressed="${!R.comun}" title="Documento de la persona elegida en el paso 2">${ico("user", 15)}Individual</button>
          <button type="button" class="btn peq ${R.comun ? "sel" : ""}" data-comun="1" aria-pressed="${!!R.comun}" title="Documento de todo el expediente: nota simple, tasación, arras, escritura del inmueble…">${ico("users", 15)}Colectivo</button>
        </div>
      </div>
    </div>
    ${avisoDup}${filaDatos}
    <div class="pie-rev ${filaOtras ? "con-otras" : ""}">
      <div class="pie-izq">${filaOtras}</div>
      <div class="pie-der">
        <div class="pie-btns">${pendientesOtras > 1 ? '<button type="button" class="btn peq" id="todos-terceros">Todos: tercero</button>' : ""}<button class="btn pri" id="r-ok">${ico("check")}Confirmar y guardar</button></div>
        <label class="check mini"><input type="checkbox" id="r-priv" ${R.priv ? "checked" : ""}><span><b>PRIVADO</b>, No compartir</span></label>
      </div>
    </div>
  </section>
  <div class="rev-abajo">
    <nav class="cola" aria-label="Pendientes">${lista}</nav>
    <section class="visor" aria-label="Documento">
      <div class="pie-v"><span>${esc(d.nombre_recibido)} · página ${S.pag} de ${pags}</span>
        <span class="acciones"><button class="btn peq" id="pant" ${S.pag <= 1 ? "disabled" : ""} aria-label="Página anterior">${ico("left", 15)}</button><button class="btn peq" id="psig" ${S.pag >= pags ? "disabled" : ""} aria-label="Página siguiente">${ico("right", 15)}</button>
          <span class="sep"></span><button class="btn peq" id="v-menos" aria-label="Alejar">−</button><span id="v-nivel" class="nivel">${Math.round(S.zoom * 100)} %</span><button class="btn peq" id="v-mas" aria-label="Acercar">+</button>
          <button class="btn peq" id="v-ajustar">Ajustar</button><button class="btn peq" id="v-grande">Pantalla completa</button></span></div>
      <div class="lienzo" id="v-lienzo"><img id="v-img" style="width:${S.zoom * 100}%" alt="Página ${S.pag} de ${esc(d.nombre_recibido)}" src="/api/vista/${d.id}/${S.pag}?grande=1&t=${d.actualizado}"></div>
      <span class="sub" style="padding:6px 14px">Ctrl + rueda del ratón para acercar o alejar · doble clic para verlo a pantalla completa.</span>
      <details style="padding:0 14px 14px"><summary class="muted" style="cursor:pointer;padding:10px 0">Ver el texto leído de esta página</summary><div class="campo"><textarea readonly>${esc(d.texto_paginas[S.pag - 1] || "")}</textarea></div></details>
    </section>
  </div>${zoomModal()}`;
}
async function cargarDoc(id) {
  if (S.docId !== id) { S.pag = 1; S.rev = null; }
  S.docId = id;
  try { S.doc = await api("documento/" + id); if (!S.rev) iniciarRevision(S.doc); } catch (e) { S.doc = null; aviso(e.message, true); }
  pintar();
}
function activarRevision() {
  const vimg = $("#v-img");
  if (vimg) {
    const poner = n => { S.zoom = Math.min(5, Math.max(0.3, n)); vimg.style.width = (S.zoom * 100) + "%"; $("#v-nivel").textContent = Math.round(S.zoom * 100) + " %"; };
    $("#v-mas").addEventListener("click", () => poner(S.zoom * 1.25));
    $("#v-menos").addEventListener("click", () => poner(S.zoom / 1.25));
    $("#v-ajustar").addEventListener("click", () => poner(1));
    $("#v-lienzo").addEventListener("wheel", e => { if (!e.ctrlKey) return; e.preventDefault(); poner(S.zoom * (e.deltaY < 0 ? 1.1 : 1 / 1.1)); }, { passive: false });
    const abrir = activarZoomModal();
    $("#v-grande").addEventListener("click", () => abrir(vimg.src));
    vimg.addEventListener("dblclick", () => abrir(vimg.src));
  }
  const R = S.rev;
  if (!R) return;
  $("#pant")?.addEventListener("click", () => { S.pag--; pintar(); });
  $("#psig")?.addEventListener("click", () => { S.pag++; pintar(); });
  $("#r-ok")?.addEventListener("click", confirmar);
  $("#r-limbo")?.addEventListener("click", async () => {
    try { const r = await api("limbo", { documento: S.docId }); aviso("Al Limbo: " + r.nombre_final); siguiente(); } catch (e) { aviso(e.message, true); }
  });
  $("#r-tipo")?.addEventListener("change", e => { R.tipo = e.target.value; R.fecha = null; pintar(); });
  document.querySelectorAll("[data-tipo]").forEach(b => b.addEventListener("click", () => { R.tipo = b.dataset.tipo; R.fecha = null; pintar(); }));
  document.querySelectorAll('input[name="destino"]').forEach(r => r.addEventListener("change", () => {
    if (r.value === "otro") { const s = $("#r-otro"); if (s.value) R.destino = s.value; else { s.focus(); return; } } else R.destino = r.value;
    R.dupOk = false; pintar();
  }));
  $("#r-otro")?.addEventListener("change", e => { if (e.target.value) { R.destino = e.target.value; R.dupOk = false; pintar(); } });
  $("#r-lote")?.addEventListener("click", () => { const lm = loteMayoritario(S.doc); if (lm) { usarLote(lm); pintar(); } });
  document.querySelectorAll("[data-ir-exp]").forEach(b => b.addEventListener("click", () => { R.destino = "e:" + b.dataset.irExp; pintar(); }));
  $("#dup-ok")?.addEventListener("change", e => (R.dupOk = e.target.checked));
  document.querySelectorAll("[data-comun]").forEach(b => b.addEventListener("click", () => { R.comun = b.dataset.comun === "1"; pintar(); }));
  $("#r-priv")?.addEventListener("change", e => (R.priv = e.target.checked));
  document.querySelectorAll("[data-persona]").forEach(b => b.addEventListener("click", () => {
    const i = +b.dataset.persona;
    R.persona = i; if (R.otros) delete R.otros[i];
    if (i >= 0) { const p = S.doc.datos.personas[i]; R.nuevo = { nombre: p.nombre || "", ap1: p.apellido1 || "", ap2: p.apellido2 || "", dni: p.dni || "" }; }
    else R.nuevo = { nombre: "", ap1: "", ap2: "", dni: "" };
    R.destino = undefined; R.dupOk = false; pintar();
  }));
  document.querySelectorAll("[data-otro]").forEach(b => b.addEventListener("click", () => { R.otros = { ...(R.otros || {}), [b.dataset.otro]: b.dataset.acc }; pintar(); }));
  $("#todos-terceros")?.addEventListener("click", () => { R.otros = {}; (S.doc.datos.personas || []).forEach((p, i) => { if (i !== R.persona) R.otros[i] = "tercero"; }); pintar(); });
  document.querySelectorAll("[data-fecha]").forEach(b => b.addEventListener("click", () => { R.fecha = b.dataset.fecha; pintar(); }));
  $("#r-fecha")?.addEventListener("change", e => { if (e.target.value) { R.fecha = e.target.value; pintar(); } });
  document.querySelectorAll("[data-fin]").forEach(b => b.addEventListener("click", () => { R.finalidad = b.dataset.fin; pintar(); }));
  document.querySelectorAll("[data-n]").forEach(i => {
    i.addEventListener("input", () => { R.nuevo[i.dataset.n] = i.value; });
    i.addEventListener("change", () => pintar());      // al salir del campo se recalcula si ya está fichada
  });
  document.querySelectorAll(".barra-rev input, .barra-rev select").forEach(el => {
    el.addEventListener("focus", () => (S.editando = true)); el.addEventListener("blur", () => (S.editando = false));
  });
}
async function confirmar() {
  const R = S.rev, tipo = R.tipo, P = R.nuevo;
  if (!tipo) return aviso("Elige el tipo de documento.", true);
  if (!P.nombre.trim() || !P.ap1.trim()) return aviso("Falta el nombre o el primer apellido de la persona.", true);
  const leidas = (S.doc.datos || {}).personas || [];
  const expSel = R.destino.startsWith("e:") ? S.expedientes.find(e => e.id === +R.destino.slice(2)) : null;
  const pendientes = leidas.map((p, i) => ({ p, i })).filter(x => x.i !== R.persona).filter(x => {
    const f = buscarFichada({ nombre: x.p.nombre, ap1: x.p.apellido1, ap2: x.p.apellido2, dni: x.p.dni });
    return !(f && expSel && expSel.personas.some(q => q.id === f.id));
  });
  if (pendientes.some(x => !(R.otros || {})[x.i])) return aviso("Hay más personas en el documento: indica qué es cada una.", true);
  const otrosEnvio = pendientes.map(x => ({ persona: { nombre: x.p.nombre, apellido1: x.p.apellido1, apellido2: x.p.apellido2, dni: x.p.dni }, accion: R.otros[x.i] }));
  const persona_datos = { nombre: P.nombre.trim(), apellido1: P.ap1.trim(), apellido2: P.ap2.trim(), dni: P.dni.trim().toUpperCase() || null };
  const fich = buscarFichada(P);
  let expediente, persona = null;
  try {
    if (R.destino === "nuevo") {
      const dups = [fich, ...parecidas(P, fich)].filter(x => x && x.exps.some(e => e.estado === "abierto"));
      if (dups.length && !R.dupOk) return aviso("Esta persona ya tiene expediente: añade el documento a ese expediente o marca que quieres otro aparte.", true);
      const r = await api("expediente", { persona: persona_datos, finalidad: R.finalidad, confirmado: !!R.dupOk });
      expediente = r.expediente; persona = r.persona; aviso("Expediente creado: " + r.carpeta);
    } else { expediente = +R.destino.slice(2); persona = fich ? fich.id : null; }
    const g = await api("emparejar", { documento: S.docId, expediente, persona, persona_datos: persona ? null : persona_datos,
      comun: !!R.comun, tipo, privado: !!R.priv, fecha: R.fecha, otros: otrosEnvio });
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

// ------------------------------------------------------------------ Unir varias fotos en un PDF
function zoomModal() {
  return `<div id="zoom" class="zoom" hidden><div class="zoom-barra"><button class="btn peq" id="z-menos" aria-label="Alejar">−</button><span id="z-nivel">100 %</span>
    <button class="btn peq" id="z-mas" aria-label="Acercar">+</button><button class="btn peq" id="z-ajustar">Ajustar</button><button class="btn peq" id="z-cerrar">${ico("x", 14)} Cerrar</button></div>
    <div class="zoom-lienzo" id="z-lienzo"><img id="z-img" alt="Vista ampliada"></div></div>`;
}
function activarZoomModal() {
  const img = $("#z-img"), caja = $("#zoom");
  if (!img) return () => {};
  let z = 1;
  const poner = n => { z = Math.min(6, Math.max(0.25, n)); img.style.width = (z * 100) + "%"; $("#z-nivel").textContent = Math.round(z * 100) + " %"; };
  $("#z-mas").addEventListener("click", () => poner(z * 1.25));
  $("#z-menos").addEventListener("click", () => poner(z / 1.25));
  $("#z-ajustar").addEventListener("click", () => poner(1));
  $("#z-cerrar").addEventListener("click", () => (caja.hidden = true));
  $("#z-lienzo").addEventListener("wheel", e => { e.preventDefault(); poner(z * (e.deltaY < 0 ? 1.1 : 1 / 1.1)); }, { passive: false });
  document.onkeydown = e => { if (e.key === "Escape") caja.hidden = true; };
  return src => { img.src = src; caja.hidden = false; poner(1); };
}
let UNIR = [];
function vistaUnir() {
  const cola = colaRevision().filter(x => x.estado === "espera_emparejar");
  const porId = Object.fromEntries(cola.map(x => [x.id, x]));
  UNIR = UNIR.filter(id => porId[id]);
  const resto = cola.filter(x => !UNIR.includes(x.id));
  const tarjeta = (x, i) => `<figure class="pag">
      <button type="button" class="miniatura" data-zoom="${x.id}" aria-label="Ver ${esc(x.archivo)} en grande"><img src="/api/vista/${x.id}/1" alt="" loading="lazy"></button>
      <figcaption><b>${i + 1}.</b> ${esc(x.archivo)}<br><span class="muted">${esc(nombreTipo(x.tipo))}</span></figcaption>
      <span class="acciones"><button class="btn peq" data-mover="${i}" data-dir="-1" ${i === 0 ? "disabled" : ""} aria-label="Antes">${ico("left", 14)}</button>
      <button class="btn peq" data-mover="${i}" data-dir="1" ${i === UNIR.length - 1 ? "disabled" : ""} aria-label="Después">${ico("right", 14)}</button>
      <button class="btn peq" data-sacar="${x.id}" aria-label="Quitar">${ico("x", 14)}</button></span></figure>`;
  return `<div class="cab"><div><small><a href="#revision">Centro de revisión</a> › Unir</small><h1>Unir en un solo PDF</h1>
    <div class="sub">Ordena las páginas, pulsa una para verla en grande con zoom y une. Las fotos originales se guardan en Doc_original al terminar.</div></div>
    <div class="acciones"><a class="btn" href="#revision">Cancelar</a><button class="btn pri" id="unir-ok" ${UNIR.length < 2 ? "disabled" : ""}>${ico("check")}Unir en un PDF (${UNIR.length} páginas)</button></div></div>
  <section class="tarjeta"><h2>Páginas del documento, en orden</h2><div class="pags">${UNIR.map((id, i) => tarjeta(porId[id], i)).join("") || '<span class="sub">Añade abajo las fotos que forman el documento.</span>'}</div></section>
  ${resto.length ? `<section class="tarjeta"><h2>Otros documentos pendientes</h2><div class="pags">${resto.map(x => `<figure class="pag otro-doc">
      <button type="button" class="miniatura" data-zoom="${x.id}" aria-label="Ver ${esc(x.archivo)} en grande"><img src="/api/vista/${x.id}/1" alt="" loading="lazy"></button>
      <figcaption>${esc(x.archivo)}<br><span class="muted">${esc(nombreTipo(x.tipo))}</span></figcaption>
      <button class="btn peq" data-meter="${x.id}">Añadir al final</button></figure>`).join("")}</div></section>` : ""}
  ${zoomModal()}`;
}
function activarUnir() {
  document.querySelectorAll("[data-mover]").forEach(b => b.addEventListener("click", () => {
    const i = +b.dataset.mover, j = i + +b.dataset.dir; [UNIR[i], UNIR[j]] = [UNIR[j], UNIR[i]]; pintar();
  }));
  document.querySelectorAll("[data-sacar]").forEach(b => b.addEventListener("click", () => { UNIR = UNIR.filter(x => x !== +b.dataset.sacar); pintar(); }));
  document.querySelectorAll("[data-meter]").forEach(b => b.addEventListener("click", () => { UNIR.push(+b.dataset.meter); pintar(); }));
  const abrir = activarZoomModal();
  document.querySelectorAll("[data-zoom]").forEach(b => b.addEventListener("click", () => abrir(`/api/vista/${b.dataset.zoom}/1?grande=1`)));
  $("#unir-ok")?.addEventListener("click", async () => {
    try { const r = await api("unir", { documentos: UNIR }); aviso("Unido en un PDF: se está leyendo"); UNIR = []; await refrescar(false); location.hash = "revision/" + r.documento; }
    catch (e) { aviso(e.message, true); }
  });
}

// ------------------------------------------------------------------ Expedientes
function vistaExpedientes() {
  const v = S.info.variante;
  return `<div class="cab"><div><small>Expedientes</small><h1>Expedientes</h1><div class="sub">Se crean desde el Centro de revisión al emparejar el primer documento.</div></div></div>
  ${S.expedientes.length ? `<section class="tarjeta sinp"><table class="tabla"><thead><tr><th>Expediente</th><th>Finalidad</th><th>Personas</th><th>Checklist</th><th>Carpeta</th></tr></thead><tbody>
  ${[...S.expedientes.filter(e => e.estado === "abierto"), ...S.expedientes.filter(e => e.estado !== "abierto")].map(e => `<tr class="clic ${e.estado !== "abierto" ? "apagada" : ""}" data-exp="${e.id}"><td><b>${esc(e.nombre)}</b>${e.estado === "unido" ? ' <span class="pill p-todo">Unido a otro</span>' : ""}</td><td>${esc(v.finalidades[e.finalidad] || e.finalidad)}</td>
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
    <div class="acciones"><button class="btn" id="rehacer">${ico("play")}Rehacer archivo de texto</button>${e.estado === "abierto" ? `<button class="btn" id="unir-exp">${ico("users")}Unir con otro expediente…</button>` : ""}</div></div>
  ${e.estado === "unido" ? '<div class="tarjeta"><b>Este expediente se unió a otro.</b> <span class="sub">Sus personas y documentos están ahora en el expediente de destino.</span></div>' : ""}
  ${ARR.unir ? panelUnirExp(e) : ""}
  <section class="tarjeta sinp"><div class="tcab"><h2>Checklist · ${ck.recibidos} de ${ck.total}</h2></div>
    <table class="tabla"><thead><tr><th>Documento</th><th>De</th><th>Estado</th><th>Detalle</th><th>Archivo</th></tr></thead><tbody>
    ${ck.filas.map(f => `<tr><td>${esc(f.documento)}${f.importancia === "imprescindible" ? ' <span class="pill p-acc">Imprescindible</span>' : ""}</td><td>${esc(f.quien)}</td><td>${pill(f.estado, c[f.estado] || "todo")}</td><td>${esc(f.detalle)}</td><td class="mono">${esc(f.archivos.join(", "))}</td></tr>`).join("")}
    </tbody></table></section>
  ${ck.avisos_cliente.length ? `<section class="tarjeta"><h2>Avisos al cliente</h2>${ck.avisos_cliente.map(a => `<div class="dato"><span>${esc(a)}</span></div>`).join("")}</section>` : ""}
  ${tarjetaDocsExp(e)}`;
}
// ---------------- arreglar lo ya guardado (v1.1)
const ARR = { unir: false, destino: "", mover: null, exp: "", persona: "", comun: false };
function abiertosMenos(id) { return S.expedientes.filter(x => x.estado === "abierto" && x.id !== id); }
function panelUnirExp(e) {
  const otros = abiertosMenos(e.id), dst = otros.find(x => x.id === +ARR.destino);
  return `<section class="tarjeta arreglo"><h2>Unir «${esc(e.nombre)}» con otro expediente</h2>
    <span class="sub">Para cuando se ha creado dos veces el mismo expediente. Todas las personas y documentos de este pasan al que elijas y este queda cerrado como «Unido a otro». No se borra ningún documento ni ningún original: se mueven de carpeta y se renombran si hace falta.</span>
    <div class="fila-arreglo"><select id="arr-destino"><option value="">— Elegir el expediente que se queda —</option>${otros.map(x => `<option value="${x.id}" ${x.id === +ARR.destino ? "selected" : ""}>${esc(x.nombre)} · ${esc(x.carpeta)}</option>`).join("")}</select>
      <button class="btn pri" id="arr-unir" ${dst ? "" : "disabled"}>${ico("check")}Unir</button><button class="btn" id="arr-cancelar">Cancelar</button></div>
    ${dst ? `<span class="sub">Quedará «${esc(dst.nombre)}» con ${esc([...new Set([...dst.personas, ...e.personas].map(p => `${p.nombre} ${p.apellido1}`))].join(", "))}.</span>` : ""}</section>`;
}
function tarjetaDocsExp(e) {
  if (!EXP.docs) return "";
  const d0 = EXP.docs.find(d => d.id === ARR.mover);
  const filas = EXP.docs.map(d => `<tr><td class="mono">${esc(d.nombre_final)}</td><td>${esc(nombreTipo(d.tipo))}</td><td>${d.de_expediente ? "Todo el expediente" : esc(d.persona)}${d.privado ? ' <span class="pill p-todo">Privado</span>' : ""}</td>
    <td class="der">${e.estado === "abierto" ? `<button class="btn peq" data-mover="${d.id}">${ico("play", 14)}Mover…</button>` : ""}</td></tr>
    ${d0 && d0.id === d.id ? `<tr class="fila-mover"><td colspan="4">${panelMover(e, d)}</td></tr>` : ""}`).join("");
  return `<section class="tarjeta sinp"><div class="tcab"><h2>Documentos guardados · ${EXP.docs.length}</h2></div>
    ${EXP.docs.length ? `<table class="tabla"><thead><tr><th>Archivo</th><th>Tipo</th><th>De</th><th></th></tr></thead><tbody>${filas}</tbody></table>` : '<div class="vacio">Sin documentos guardados.</div>'}</section>`;
}
function panelMover(e, d) {
  const exps = S.expedientes.filter(x => x.estado === "abierto");
  const dst = exps.find(x => x.id === +(ARR.exp || e.id));
  const pers = dst ? dst.personas : [];
  const yaEsta = pers.some(p => p.id === d.persona_id);
  const opP = (yaEsta ? [] : [`<option value="${d.persona_id}" ${+ARR.persona === d.persona_id ? "selected" : ""}>${esc(d.persona)} (se añadirá como cotitular)</option>`])
    .concat(pers.map(p => `<option value="${p.id}" ${+ARR.persona === p.id ? "selected" : ""}>${esc(`${p.nombre} ${p.apellido1}`)} (${esc(p.papel)})</option>`)).join("");
  return `<div class="arreglo mover"><b>Mover «${esc(d.nombre_final)}»</b>
    <div class="fila-arreglo">
      <label>Expediente <select id="arr-exp">${exps.map(x => `<option value="${x.id}" ${x.id === dst?.id ? "selected" : ""}>${esc(x.nombre)}${x.id === e.id ? " (este)" : ""}</option>`).join("")}</select></label>
      <span class="ambito fila"><button type="button" class="btn peq ${ARR.comun ? "" : "sel"}" data-arr-comun="0">${ico("user", 15)}Individual</button><button type="button" class="btn peq ${ARR.comun ? "sel" : ""}" data-arr-comun="1">${ico("users", 15)}Colectivo</button></span>
      ${ARR.comun ? "" : `<label>De <select id="arr-persona">${opP}</select></label>`}
      <button class="btn pri" id="arr-mover">${ico("check")}Mover</button><button class="btn" id="arr-cancelar">Cancelar</button></div>
    <span class="sub">El archivo y su original se mueven a la carpeta de ese expediente y se renombran con el código de la persona. No se borra nada.</span></div>`;
}
function activarExpediente(id) {
  $("#rehacer")?.addEventListener("click", async () => { await api("textos", { expediente: id }); aviso("Archivo de texto rehecho"); });
  $("#unir-exp")?.addEventListener("click", () => { ARR.unir = true; ARR.destino = ""; pintar(); });
  $("#arr-destino")?.addEventListener("change", ev => { ARR.destino = ev.target.value; pintar(); });
  document.querySelectorAll("#arr-cancelar").forEach(b => b.addEventListener("click", () => { ARR.unir = false; ARR.mover = null; pintar(); }));
  $("#arr-unir")?.addEventListener("click", async () => {
    const dst = S.expedientes.find(x => x.id === +ARR.destino);
    if (!confirm(`¿Unir «${EXP.e.nombre}» con «${dst.nombre}»? Todo pasará a «${dst.nombre}».`)) return;
    try { await api("arreglo", { accion: "unir_expedientes", origen: id, destino: dst.id }); ARR.unir = false; aviso("Expedientes unidos"); S.expedientes = await api("expedientes"); location.hash = "expediente/" + dst.id; }
    catch (e) { aviso(e.message, true); }
  });
  document.querySelectorAll("[data-mover]").forEach(b => b.addEventListener("click", () => {
    const d = EXP.docs.find(x => x.id === +b.dataset.mover);
    Object.assign(ARR, { mover: d.id, exp: String(id), persona: String(d.persona_id), comun: !!d.de_expediente }); pintar();
  }));
  $("#arr-exp")?.addEventListener("change", ev => { ARR.exp = ev.target.value; pintar(); });
  $("#arr-persona")?.addEventListener("change", ev => (ARR.persona = ev.target.value));
  document.querySelectorAll("[data-arr-comun]").forEach(b => b.addEventListener("click", () => { ARR.comun = b.dataset.arrComun === "1"; pintar(); }));
  $("#arr-mover")?.addEventListener("click", async () => {
    try {
      const r = await api("arreglo", { accion: "mover", documento: ARR.mover, expediente: +ARR.exp, persona: ARR.comun ? null : +ARR.persona, de_expediente: ARR.comun });
      ARR.mover = null; aviso("Movido: " + r.nombre_final); S.expedientes = await api("expedientes"); cargarExpediente(id);
    } catch (e) { aviso(e.message, true); }
  });
}
async function cargarExpediente(id) {
  EXP = null; pintar();
  const e = S.expedientes.find(x => x.id === id) || (await api("expedientes")).find(x => x.id === id);
  const [ck, docs] = await Promise.all([api("checklist/" + id), api("documentos_expediente/" + id)]);
  EXP = { e, ck, docs }; ARR.unir = false; ARR.mover = null; pintar();
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
  return `<div class="cab"><div><small>Motor de proceso › Limbo</small><h1>Limbo</h1><div class="sub">Documentos sin expediente todavía, guardados en <code>${esc(S.info.carpetas.documentos)}\\_Limbo\\</code>.</div></div></div>
  ${pestanasMotor("limbo")}
  ${docs.length ? `<section class="tarjeta sinp"><table class="tabla"><thead><tr><th>Archivo recibido</th><th>Tipo</th><th>Nombre en el Limbo</th><th></th></tr></thead><tbody>${docs.map(d => `<tr><td>${esc(d.archivo)}</td><td>${esc(nombreTipo(d.tipo))}</td><td class="mono">${esc(d.nombre_final)}</td>
    <td class="der"><button type="button" class="btn peq" data-sacar="${d.id}">${ico("check", 14)} Revisar y asignar expediente</button></td></tr>`).join("")}</tbody></table>
    <div class="pie-tabla sub">«Revisar y asignar expediente» lo devuelve al Centro de revisión con lo que ya se había leído; al confirmar se guarda en su expediente y el original sale de <code>_Limbo</code>.</div></section>` : '<div class="tarjeta vacio">El Limbo está vacío.</div>'}`;
}
function activarLimbo() {
  document.querySelectorAll("[data-sacar]").forEach(b => b.addEventListener("click", async () => {
    b.disabled = true;
    try {
      await api("sacar_limbo", { documento: +b.dataset.sacar });
      S.estado = await api("estado"); S.doc = null; S.docId = null;
      location.hash = "revision/" + b.dataset.sacar;
    } catch (e) { b.disabled = false; aviso(e.message, true); }
  }));
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
  ${tarjetaCorreo()}
  ${tarjetaRepetidas()}
  ${tarjetaFinalidades()}
  <section class="tarjeta"><h2>Mejorar el reconocimiento</h2>
    <span class="sub">Guarda en un archivo de texto lo que el programa ha leído de cada documento y lo que ha deducido (DNI, nombres, fechas). Lleva datos personales: compártelo solo con quien vaya a ajustar el reconocimiento.</span>
    <div class="acciones"><button class="btn" id="exportar">Exportar los textos leídos</button></div></section>
  <section class="tarjeta"><h2>Versiones</h2><div class="dato"><span>Motor Sentiende</span><span>${esc(S.info.motor.version)} · contrato ${S.info.motor.contrato}.x</span></div>
    <div class="dato"><span>Variante</span><span>${esc(S.info.variante.nombre)} ${esc(S.info.variante.version)}</span></div></section>`;
}
let FIN = null, FIN_ABIERTA = null, REP = null;
function tarjetaCorreo() {
  if (!CORREO) return "";
  const f = CORREO.form, pv = CORREO.proveedores, p = pv[f.proveedor] || pv.otro, e = CORREO.estado;
  const campo = (id, et, val, tipo = "text", extra = "") => `<div class="campo"><label for="co-${id}">${et}</label><input id="co-${id}" type="${tipo}" value="${esc(val ?? "")}" ${extra}></div>`;
  return `<section class="tarjeta"><div><h2>Recibir por correo</h2><span class="sub">El programa entra en tu buzón, recoge los adjuntos (PDF, fotos, Word y Excel) de los correos nuevos y los mete en el motor, un lote por correo. <b>Solo lee</b>: nunca envía, borra ni mueve correos; no los marca como leídos y solo les pone la etiqueta «SeFinancia» para no recogerlos dos veces. Los adjuntos con macros o ejecutables se ignoran.</span></div>
    <div class="campos-inline">
      <div class="campo"><label for="co-proveedor">Proveedor</label><select id="co-proveedor">${Object.entries(pv).map(([k, x]) => `<option value="${k}" ${k === f.proveedor ? "selected" : ""}>${esc(x.nombre)}</option>`).join("")}</select></div>
      ${campo("servidor", "Servidor IMAP", f.servidor, "text", 'placeholder="imap.tuproveedor.es"')}${campo("puerto", "Puerto", f.puerto, "number", 'min="1" style="max-width:100px"')}
    </div>
    <span class="sub">${esc(p.nota)}</span>
    <div class="campos-inline">${campo("usuario", "Usuario (tu dirección de correo)", f.usuario, "email", 'autocomplete="off"')}${campo("clave", "Contraseña", f.clave, "password", `autocomplete="new-password" placeholder="${CORREO.ajustes.hay_clave ? "•••••••• (guardada; escribe otra para cambiarla)" : ""}"`)}</div>
    <div class="campos-inline">${campo("carpeta", "Carpeta del buzón", f.carpeta)}${campo("dias", "Mirar correos de los últimos (días)", f.dias, "number", 'min="1" max="365"')}${campo("remitentes", "Solo de estos remitentes (opcional, separados por comas)", f.remitentes, "text", 'placeholder="@banco.es, gestor@ejemplo.com"')}</div>
    <div class="campos-inline"><div class="campo"><label for="co-cada">Revisar solo</label><select id="co-cada">${[[0, "Solo cuando pulse «Correo»"], [5, "Cada 5 minutos"], [15, "Cada 15 minutos"], [30, "Cada 30 minutos"], [60, "Cada hora"]].map(([v, n]) => `<option value="${v}" ${+f.cada_minutos === v ? "selected" : ""}>${n}</option>`).join("")}</select></div></div>
    <div class="acciones"><button class="btn pri" id="co-guardar">${ico("check")}Guardar</button><button class="btn" id="co-probar">Probar conexión</button>${CORREO.ajustes.servidor && CORREO.ajustes.hay_clave ? `<button class="btn" id="co-revisar">${ico("mail")}Revisar ahora</button>` : ""}</div>
    ${e.ultimo ? `<span class="sub">Última revisión: ${esc(e.ultimo.replace("T", " ").slice(0, 16))}${e.error ? " · error: " + esc(e.error) : e.resumen ? ` · ${e.resumen.adjuntos} adjunto(s) recogido(s)` : ""}</span>` : ""}
    <span class="sub">La contraseña se guarda cifrada con tu usuario de Windows: no sirve en otro equipo ni con otro usuario.</span></section>`;
}
function leerCorreoForm() {
  const f = CORREO.form;
  ["servidor", "puerto", "usuario", "clave", "carpeta", "dias", "remitentes"].forEach(k => { const el = $("#co-" + k); if (el) f[k] = el.value; });
  f.cada_minutos = +($("#co-cada")?.value || 0); f.activo = true;
  return f;
}
function tarjetaRepetidas() {
  const fp = p => `<b>${esc(`${p.nombre} ${p.apellido1} ${p.apellido2 || ""}`.trim())}</b> <span class="mono muted">${esc(p.dni || "sin DNI")}</span>`;
  return `<section class="tarjeta"><div><h2>Fichas de personas repetidas</h2><span class="sub">Personas que parecen la misma (mismo DNI, o mismo nombre y apellidos). Al unirlas, todos sus documentos y expedientes pasan a la ficha que se queda y los archivos se renombran con su código. Para unir expedientes repetidos o mover un documento, entra en el expediente.</span></div>
    ${!REP ? '<span class="sub">Cargando…</span>' : !REP.length ? '<span class="sub">No hay fichas repetidas.</span>' : REP.map((x, i) => `<div class="repe">
      <div class="repe-par"><span>${fp(x.a)}</span><span class="muted">y</span><span>${fp(x.b)}</span><span class="pill ${x.dni_distinto ? "p-warn" : "p-todo"}">${x.dni_distinto ? "DNI distinto" : esc(x.por)}</span></div>
      <div class="acciones"><button class="btn peq" data-repe="${i}" data-queda="a">Quedarse con ${esc(x.a.dni || "la 1.ª")}</button><button class="btn peq" data-repe="${i}" data-queda="b">Quedarse con ${esc(x.b.dni || "la 2.ª")}</button></div></div>`).join("")}</section>`;
}
function tarjetaFinalidades() {
  if (!FIN) return '<section class="tarjeta"><h2>Finalidades de los expedientes</h2><span class="sub">Cargando…</span></section>';
  const opTipos = sel => S.info.tipos.map(t => `<option value="${t.id}" ${t.id === sel ? "selected" : ""}>${esc(t.nombre)}</option>`).join("");
  return `<section class="tarjeta"><div><h2>Finalidades de los expedientes</h2><span class="sub">Las que se eligen al crear un expediente, con los documentos que pide cada una. Son tuyas: las actualizaciones no las cambian.</span></div>
    ${FIN.map(f => `<div class="fin-ed ${FIN_ABIERTA === f.id ? "abierta" : ""}">
      <button type="button" class="fin-cab" data-abrir="${f.id}"><b>${esc(f.nombre)}${f.oculta ? ' <span class="pill p-todo">Oculta</span>' : ""}</b><span class="sub">${f.documentos.length} documento(s) · ${f.documentos.filter(d => d.importancia === "imprescindible").length} imprescindible(s) · ${f.expedientes} expediente(s)</span></button>
      ${FIN_ABIERTA === f.id ? `<div class="fin-cuerpo">
        <div class="campo"><label for="fn-${f.id}">Nombre</label><input id="fn-${f.id}" value="${esc(f.nombre)}"></div>
        <table class="tabla"><thead><tr><th>Documento</th><th>De</th><th>Condición</th><th>Imprescindible</th><th></th></tr></thead><tbody>
        ${f.documentos.map((d, i) => `<tr><td><select data-ed="${i}" data-campo="tipo">${opTipos(d.tipo)}</select></td>
          <td><select data-ed="${i}" data-campo="por"><option value="titular" ${d.por === "titular" ? "selected" : ""}>Cada titular</option><option value="expediente" ${d.por === "expediente" ? "selected" : ""}>Todo el expediente</option></select></td>
          <td>${condicionEd(d, i)}</td>
          <td><input type="checkbox" data-ed="${i}" data-campo="importancia" ${d.importancia === "imprescindible" ? "checked" : ""} aria-label="Imprescindible"></td>
          <td><button type="button" class="btn peq" data-quitar-doc="${i}" aria-label="Quitar">${ico("x", 14)}</button></td></tr>`).join("") || '<tr><td colspan="5" class="muted">Sin documentos todavía: añade los que pide esta finalidad.</td></tr>'}
        </tbody></table>
        <div class="acciones"><button type="button" class="btn" id="fin-add">Añadir documento</button><button type="button" class="btn pri" id="fin-guardar">Guardar</button>
          ${f.expedientes ? `<button type="button" class="btn" id="fin-ocultar" data-oculta="${f.oculta ? 0 : 1}">${f.oculta ? "Mostrar otra vez" : "Ocultar"}</button>
            <span class="sub">La usan ${f.expedientes} expediente(s): no se puede quitar, pero sí ocultar (no saldrá al crear expedientes; los que la tienen la conservan).</span>`
            : `<button type="button" class="btn peligro" id="fin-quitar">Quitar finalidad</button>`}</div>
      </div>` : ""}</div>`).join("")}
    <div class="fila" style="align-items:flex-end"><div class="campo" style="flex:1 1 240px"><label for="fin-nueva">Nueva finalidad</label><input id="fin-nueva" placeholder="Por ejemplo: Reunificación de deudas"></div>
      <button type="button" class="btn" id="fin-crear" style="flex:0 0 auto">Añadir finalidad</button></div>
    <span class="sub">Una finalidad nueva empieza sin documentos. Si ningún expediente la usa se puede quitar; si la usan, se puede ocultar.</span></section>`;
}
const CONDICIONES = [["", "Sin condición"], ["en_vigor", "En vigor (no caducado)"], ["ultimos_meses", "Últimos N meses"], ["ultimo_ejercicio", "Último ejercicio"], ["max_dias", "Antigüedad máxima (días)"]];
function condicionEd(d, i) {
  const c = d.condicion || {}, k = Object.keys(c)[0] || "";
  const num = k === "ultimos_meses" || k === "max_dias";
  return `<span class="fila" style="gap:6px;flex-wrap:nowrap"><select data-cond="${i}" aria-label="Condición">${CONDICIONES.map(([v, n]) => `<option value="${v}" ${v === k ? "selected" : ""}>${n}</option>`).join("")}</select>
    ${num ? `<input type="number" min="1" data-condn="${i}" value="${c[k]}" aria-label="${k === "max_dias" ? "Días" : "Meses"}" style="width:70px;height:34px;border-radius:6px;border:1px solid var(--border);background:var(--bg);padding:0 6px">` : ""}</span>`;
}
function activarFinalidades() {
  const f = (FIN || []).find(x => x.id === FIN_ABIERTA);
  document.querySelectorAll("[data-abrir]").forEach(b => b.addEventListener("click", () => { FIN_ABIERTA = FIN_ABIERTA === b.dataset.abrir ? null : b.dataset.abrir; pintar(); }));
  document.querySelectorAll("[data-ed]").forEach(el => el.addEventListener("change", () => {
    const d = f.documentos[+el.dataset.ed];
    if (el.dataset.campo === "importancia") d.importancia = el.checked ? "imprescindible" : "recomendable"; else d[el.dataset.campo] = el.value;
  }));
  document.querySelectorAll("[data-cond]").forEach(el => el.addEventListener("change", () => {
    const d = f.documentos[+el.dataset.cond], k = el.value;
    d.condicion = !k ? {} : { [k]: k === "ultimos_meses" ? 3 : k === "max_dias" ? 90 : true }; pintar();
  }));
  document.querySelectorAll("[data-condn]").forEach(el => el.addEventListener("change", () => {
    const d = f.documentos[+el.dataset.condn], k = Object.keys(d.condicion)[0]; d.condicion = { [k]: Math.max(1, +el.value || 1) };
  }));
  $("#fin-ocultar")?.addEventListener("click", async e => {
    const ocultar = e.currentTarget.dataset.oculta === "1";
    try { await api("finalidad", { id: f.id, ocultar }); aviso(ocultar ? "Finalidad oculta" : "Finalidad visible otra vez"); await recargarFinalidades(); } catch (er) { aviso(er.message, true); }
  });
  document.querySelectorAll("[data-quitar-doc]").forEach(b => b.addEventListener("click", () => { f.documentos.splice(+b.dataset.quitarDoc, 1); pintar(); }));
  $("#fin-add")?.addEventListener("click", () => { f.documentos.push({ tipo: S.info.tipos[0].id, por: "titular", importancia: "imprescindible", condicion: {} }); pintar(); });
  $("#fin-guardar")?.addEventListener("click", async () => {
    try { await api("finalidad", { id: f.id, nombre: $("#fn-" + f.id).value, documentos: f.documentos }); aviso("Finalidad guardada"); await recargarFinalidades(); } catch (e) { aviso(e.message, true); }
  });
  $("#fin-quitar")?.addEventListener("click", async () => {
    if (!confirm(`¿Quitar la finalidad «${f.nombre}»?`)) return;
    try { await api("finalidad", { quitar: f.id }); FIN_ABIERTA = null; aviso("Finalidad quitada"); await recargarFinalidades(); } catch (e) { aviso(e.message, true); }
  });
  $("#fin-crear")?.addEventListener("click", async () => {
    try { const r = await api("finalidad", { nombre: $("#fin-nueva").value }); FIN_ABIERTA = r.id; aviso("Finalidad creada: añade sus documentos"); await recargarFinalidades(); } catch (e) { aviso(e.message, true); }
  });
}
async function recargarFinalidades() { [FIN, S.info] = await Promise.all([api("finalidades"), api("info")]); pintar(); }
function activarAjustes() {
  activarFinalidades();
  $("#co-proveedor")?.addEventListener("change", ev => { const f = leerCorreoForm(), p = CORREO.proveedores[ev.target.value]; f.proveedor = ev.target.value; if (p.servidor) { f.servidor = p.servidor; f.puerto = p.puerto; } pintar(); });
  $("#co-guardar")?.addEventListener("click", async () => { try { CORREO.ajustes = await api("correo/guardar", leerCorreoForm()); CORREO.form.clave = ""; aviso("Correo guardado"); pintar(); } catch (e) { aviso(e.message, true); } });
  $("#co-probar")?.addEventListener("click", async ev => {
    const b = ev.currentTarget; b.disabled = true; aviso("Conectando…");
    try { const r = await api("correo/probar", leerCorreoForm()); aviso(`Conexión correcta: ${r.mensajes} correo(s) en la carpeta`); } catch (e) { aviso(e.message, true); }
    b.disabled = false;
  });
  $("#co-revisar")?.addEventListener("click", revisarCorreo);
  document.querySelectorAll("[data-repe]").forEach(b => b.addEventListener("click", async () => {
    const x = REP[+b.dataset.repe], queda = b.dataset.queda === "a" ? x.a : x.b, quita = b.dataset.queda === "a" ? x.b : x.a;
    const txt = x.dni_distinto ? `Tienen DNI distintos. Si uno está mal leído, se quedará el DNI ${queda.dni} y desaparecerá el ${quita.dni}. ¿Unir?` : `¿Unir las dos fichas? Se queda la de ${queda.dni || "sin DNI"}.`;
    if (!confirm(txt)) return;
    try { await api("arreglo", { accion: "unir_personas", quitar: quita.id, quedar: queda.id, forzar: x.dni_distinto }); aviso("Fichas unidas"); REP = await api("personas_repetidas"); S.expedientes = await api("expedientes"); pintar(); }
    catch (e) { aviso(e.message, true); }
  }));
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
  const vistas = { motor: [vistaMotor, activarMotor], revision: [vistaRevision, activarRevision],
    expedientes: [vistaExpedientes, () => document.querySelectorAll("[data-exp]").forEach(tr => tr.addEventListener("click", () => (location.hash = "expediente/" + tr.dataset.exp)))],
    expediente: [vistaExpediente, () => activarExpediente(+id)],
    unir: [vistaUnir, activarUnir], avisos: [vistaAvisos, () => {}], limbo: [vistaLimbo, activarLimbo], ajustes: [vistaAjustes, activarAjustes] };
  const [v, act] = vistas[r] || vistas.motor;
  const y = $("#vista").scrollTop;
  $("#vista").innerHTML = v();
  $("#vista").scrollTop = y;
  act();
}
async function ir() {
  S.ruta = location.hash.slice(1).replace(/^bandeja/, "motor") || "motor";
  const [r, id] = S.ruta.split("/");
  if (r === "motor") LOTE = id ? +id : null;
  if (r === "revision") {
    const cola = colaRevision();
    const objetivo = id ? +id : cola[0]?.id;
    if (objetivo) { if (objetivo !== S.docId || !S.doc) return cargarDoc(objetivo); }
    else { S.doc = null; S.docId = null; }
  }
  if (r === "expediente") return cargarExpediente(+id);
  if (r === "unir") UNIR = (id || "").split(",").filter(Boolean).map(Number);
  if (r === "revision" || r === "unir") S.prop = await api("propuestas_union");
  if (r === "avisos") AV = await api("avisos");
  if (r === "ajustes") { [TMP, FIN, REP, CORREO] = await Promise.all([api("temporales"), api("finalidades"), api("personas_repetidas"), api("correo")]); CORREO.form = { ...CORREO.ajustes, clave: "" }; }
  pintar();
}
async function refrescar(repintar) {
  const antes = JSON.stringify(S.estado);
  [S.estado, S.expedientes] = await Promise.all([api("estado"), api("expedientes")]);
  const cambio = antes !== JSON.stringify(S.estado);
  const r = S.ruta.split("/")[0] || "motor";
  if (repintar || (cambio && ["motor", "limbo", ""].includes(r))) pintar();
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
