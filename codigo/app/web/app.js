// Sentiende · pantallas (v1.0). Sin librerías: todo funciona sin internet.
"use strict";

const S = { zoom: 1, info: null, estado: null, expedientes: [], doc: null, docId: null, pag: 1, ruta: "", editando: false };
const $ = (sel, el = document) => el.querySelector(sel);
const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const IC = {
  inbox: '<path d="M4 13h4l2 3h4l2-3h4"/><path d="M5 5h14l1 8v6H4v-6z"/>',
  motor: '<path d="M12 2.5l1.6.3.4 2.1a7 7 0 0 1 1.9.8l1.8-1.2 1.2 1.1-1.2 1.8a7 7 0 0 1 .8 1.9l2.1.4.3 1.6-.3 1.6-2.1.4a7 7 0 0 1-.8 1.9l1.2 1.8-1.2 1.2-1.8-1.2a7 7 0 0 1-1.9.8l-.4 2.1-1.6.3-1.6-.3-.4-2.1a7 7 0 0 1-1.9-.8l-1.8 1.2-1.2-1.2 1.2-1.8a7 7 0 0 1-.8-1.9l-2.1-.4L2.5 12l.3-1.6 2.1-.4a7 7 0 0 1 .8-1.9L4.5 6.3l1.2-1.1 1.8 1.2a7 7 0 0 1 1.9-.8l.4-2.1z"/><circle cx="12" cy="12" r="3.2"/>',
  check: '<path d="m5 12 5 5 9-10"/>', folder: '<path d="M3 6h7l2 2h9v11H3z"/>', user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c1.5-4 4.5-6 8-6s6.5 2 8 6"/>',
  bell: '<path d="M6 9a6 6 0 0 1 12 0c0 6 2 7 2 7H4s2-1 2-7"/><path d="M10 20a2 2 0 0 0 4 0"/>', limbo: '<circle cx="12" cy="12" r="8"/><path d="M8 12h8"/>',
  edit: '<path d="M4 20h4l10-10-4-4L4 16v4z"/><path d="M13.5 6.5l4 4"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 4-6 8-6s8 2 8 6"/>',
  users: '<circle cx="9" cy="8" r="3.5"/><path d="M2 20c0-3.5 3-5.5 7-5.5s7 2 7 5.5"/><path d="M16 4.5a3.5 3.5 0 0 1 0 7"/><path d="M18 14.8c2.4.6 4 2.3 4 5.2"/>',
  gear: '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1 7 17M17 7l2.1-2.1"/>',
  upload: '<path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 16v4h16v-4"/>', search: '<circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/>',
  chart: '<path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>', trash: '<path d="M4 7h16M9 7V4h6v3M6 7l1 13h10l1-13"/>', tag: '<path d="M3 3h8l10 10-8 8L3 11z"/>',
  scan: '<path d="M4 8V5a1 1 0 0 1 1-1h3M16 4h3a1 1 0 0 1 1 1v3M20 16v3a1 1 0 0 1-1 1h-3M8 20H5a1 1 0 0 1-1-1v-3"/><path d="M7 12h10"/>',
  bt: '<path d="m7 7 10 10-5 5V2l5 5L7 17"/>', mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m3 7 9 6 9-6"/>', paste: '<rect x="7" y="4" width="10" height="4" rx="1"/><path d="M7 6H5v15h14V6h-2"/>',
  left: '<path d="m15 6-6 6 6 6"/>', right: '<path d="m9 6 6 6-6 6"/>', play: '<path d="M8 5v14l11-7z"/>', x: '<path d="M6 6l12 12M18 6 6 18"/>',
  ia: '<path d="M12 3l1.8 4.6L18 9l-4.2 1.4L12 15l-1.8-4.6L6 9l4.2-1.4z"/><path d="M18.5 15l.8 2 2 .8-2 .8-.8 2-.8-2-2-.8 2-.8z"/>',
  pause: '<path d="M9 5v14M15 5v14"/>', undo: '<path d="M9 14 4 9l5-5"/><path d="M4 9h10a6 6 0 0 1 0 12h-3"/>', eye: '<path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/>',
  lock: '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V7a4 4 0 0 1 8 0v4"/>', key: '<circle cx="8" cy="15" r="4"/><path d="m11 12 9-9M17 6l3 3"/>',
  download: '<path d="M12 4v12M7 11l5 5 5-5"/><path d="M4 20h16"/>', link: '<path d="M10 14a4 4 0 0 0 5.7 0l3-3a4 4 0 0 0-5.7-5.7l-1 1"/><path d="M14 10a4 4 0 0 0-5.7 0l-3 3a4 4 0 0 0 5.7 5.7l1-1"/>',
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
// «(130/131) Pago fraccionado…»: si se sabe el modelo del documento, solo el suyo («(131) …»)
const nombreTipo = (id, modelo) => { const n = (S.info.tipos.find(t => t.id === id) || {}).nombre || id || "—"; return modelo && /^\([\d/]+\) /.test(n) && n.includes(modelo) ? n.replace(/^\([\d/]+\)/, `(${modelo})`) : n; };
const ESTADOS = { en_proceso: ["Trabajando", "acc"], espera_emparejar: ["Para revisar", "warn"], parado: ["Parado", "bad"], guardado: ["Guardado", "ok"], contacto: ["Contacto de banco", "ok"],
  limbo: ["En el Limbo", "todo"], unido: ["Unido a otro", "todo"], deshecho: ["Deshecho", "todo"], sustituido: ["Sustituido", "todo"], duplicado: ["Duplicado", "warn"], separado: ["Separado", "todo"], error: ["Error", "bad"] };
const est = e => pill(...(ESTADOS[e] || [e, "todo"]));
function fbar(fase, estado) {
  const n = ["guardado", "limbo", "contacto"].includes(estado) ? 10 : fase;
  const cls = estado === "parado" ? "bad" : estado === "espera_emparejar" || estado === "duplicado" ? "warn" : "on";
  let s = '<span class="fbar" aria-hidden="true">';
  for (let i = 0; i < 10; i++) s += `<i class="${i < n ? cls : ""}"></i>`;
  const lab = estado === "espera_emparejar" ? "7 de 10 · espera tu respuesta" : `${n} de 10 · ${FASES[Math.max(n, 1) - 1][0]}`;
  return s + `</span><span class="flab">${lab}</span>`;
}

// ------------------------------------------------------------------ barra lateral
function lateral() {
  const v = S.info.variante, c = S.estado?.cuentas || {};
  const r0 = S.ruta.split("/")[0] || "motor";
  const r = ({ limbo: "motor", cuarentena: "motor", avisos_cliente: "expedientes", expediente: "expedientes", documentacion: "expedientes", persona: "personas", separar: "revision", reglas: "ajustes", ia: "ajustes", ia_informe: "motor", ia_envio: "motor", ia_mirar: "motor" })[r0] || r0;
  const item = (id, ic, txt, num, activo = true, prox = "") =>
    activo ? `<a href="#${id}" ${r === id ? 'aria-current="page"' : ""}>${ico(ic)}${txt}${num ? `<span class="num">${num}</span>` : ""}</a>`
           : `<a class="inactivo" aria-disabled="true" title="Llegará en una próxima versión">${ico(ic)}${txt}<span class="prox">${prox}</span></a>`;
  const abiertos = S.expedientes.filter(e => e.estado === "abierto").slice(0, 8);
  $("#lateral").innerHTML = `
    <div class="marca"><img class="logo" src="/api/logo" alt="" width="48" height="48"><span><b>${esc(v.nombre)}</b><span>con Sentiende</span></span></div>
    <div class="lat-estado-zona">${engranajes(true)}
    ${(c.avisos_se || c.notificaciones) ? `<a href="#avisos_se" class="campana-se ${r === "avisos_se" ? "activa" : ""}" title="Avisos del programa y expedientes creados solos">${ico("bell", 18)}<span>Avisos del programa</span><b>${(c.avisos_se || 0) + (c.notificaciones || 0)}</b></a>` : ""}</div>
    <div class="nav">
      ${item("expedientes", "folder", "Expedientes")}
      ${item("personas", "user", "Personas")}
      ${item("revision", "check", "Centro de revisión", c.revisar)}
      ${item("motor", "motor", "Motor de proceso", (c.pendientes - (c.revisar || 0)) + (c.cuarentena || 0))}
      ${item("estadisticas", "chart", "Estadísticas")}
    </div>
    <div class="nav-iconos">
      <a href="#ajustes" title="Ajustes" aria-label="Ajustes" ${r === "ajustes" ? 'aria-current="page"' : ""}>${ico("gear", 20)}</a>
      <a href="#papelera" title="Papelera" aria-label="Papelera" ${r === "papelera" ? 'aria-current="page"' : ""}>${ico("trash", 20)}</a>
      <a href="#buscar" title="Buscar en documentos" aria-label="Buscar en documentos" ${r === "buscar" ? 'aria-current="page"' : ""}>${ico("search", 20)}</a>
    </div>
    ${botonIA()}
    <div class="lat-zona" id="zona">
      <span class="ico">${ico("upload", 20)}</span>
      <b>Arrastra aquí</b>
      <span class="sub">PDF, fotos, Word o Excel. También Ctrl+V o la carpeta <code title="${esc(S.info.carpetas.entrada)}">Entrada</code>.</span>
      <span class="lat-iconos">
        <label class="btn pri" title="Elegir archivos" aria-label="Elegir archivos">${ico("folder", 22)}<input type="file" id="elegir" multiple hidden accept=".pdf,.jpg,.jpeg,.png,.tif,.tiff,.heic,.docx,.xlsx"></label>
        <button class="btn" id="b-correo" title="Recibir por correo" aria-label="Recibir por correo">${ico("mail", 22)}</button>
        <button class="btn" id="b-bt" title="Recibir por Bluetooth" aria-label="Recibir por Bluetooth">${ico("bt", 22)}</button>
        <button class="btn" id="b-scan" title="Escanear" aria-label="Escanear">${ico("scan", 22)}</button></span>
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
  $("#b-ia")?.addEventListener("click", pulsarIA);
  $("#b-scan").addEventListener("click", abrirEscaner);
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
  const n = S.estado.cuentas.limbo || 0, q = S.estado.cuentas.cuarentena || 0;
  return `<nav class="pestanas" aria-label="Motor de proceso"><a href="#motor" ${activa === "motor" ? 'aria-current="page"' : ""}>${ico("motor", 16)}Proceso</a>
    <a href="#limbo" ${activa === "limbo" ? 'aria-current="page"' : ""}>${ico("limbo", 16)}Limbo${n ? `<span class="num">${n}</span>` : ""}</a>
    <a href="#cuarentena" ${activa === "cuarentena" ? 'aria-current="page"' : ""}>${ico("mail", 16)}Correo por revisar${q ? `<span class="num">${q}</span>` : ""}</a></nav>`;
}
// 3.0.3 · Centro de revisión vacío: tres bailaoras (A, B y C, con la cabeza de la A) que se alternan con un fundido suave
const BAILAORAS = [`<g transform="translate(0,0)"><circle cx="72" cy="46" r="11"/><path d="M80 38c6-2 9 2 8 7"/><circle cx="86" cy="36" r="4"/></g><path d="M72 57l-2 10"/><path d="M70 67c-8 10-9 26-6 40"/><path d="M76 67c4 12 4 26 2 40"/><path d="M70 70c-14-10-20-30-12-50c4-8 10-12 16-10"/><path d="M76 70c10 4 16 12 14 22c-1 6-8 8-12 4"/><path d="M64 107c-12 18-24 40-30 70c16 8 32 10 50 8"/><path d="M78 107c10 18 30 38 56 50c-10 18-30 28-50 28"/><path d="M40 150c14 6 30 6 44 2"/><path d="M36 168c18 8 38 8 56 2c14-4 30-10 40-18"/><path d="M60 185l-4 50"/><path d="M76 185l6 50"/><path d="M52 236h8"/><path d="M80 236h8"/>`, `<g transform="translate(3,2)"><circle cx="72" cy="46" r="11"/><path d="M80 38c6-2 9 2 8 7"/><circle cx="86" cy="36" r="4"/></g><path d="M75 59v8"/><path d="M70 67c-4 14-4 26-2 38"/><path d="M80 67c4 14 4 26 2 38"/><path d="M70 70c-16-8-26-24-26-44"/><path d="M80 70c16-8 26-24 26-44"/><path d="M44 26c-2-4 2-8 6-6"/><path d="M106 26c2-4-2-8-6-6"/><path d="M68 105c-30 6-52 26-56 56c22 14 48 22 78 20c30-2 52-16 62-34c-14-22-40-38-72-42"/><path d="M20 150c20 14 50 20 80 16c20-2 36-10 46-20"/><path d="M30 168c24 10 52 12 78 6"/><path d="M66 181l-2 52"/><path d="M84 181l2 52"/><path d="M58 234h8"/><path d="M84 234h8"/>`, `<g transform="translate(-2,0)"><circle cx="72" cy="46" r="11"/><path d="M80 38c6-2 9 2 8 7"/><circle cx="86" cy="36" r="4"/></g><path d="M70 57c2 10-2 21-4 31c10 6 22 2 30-6c8-10 12-28 4-46"/><path d="M66 88c-10 2-22-6-26-18c-4-12 2-28 14-36"/><path d="M66 88c-4 22-14 44-34 66c18 20 46 28 76 22c22-4 38-16 46-32c-24-10-48-28-64-56"/><path d="M34 160c26 10 54 12 82 6c14-4 26-10 36-20"/><path d="M60 176l-6 58"/><path d="M84 176l10 58"/><path d="M48 234h10"/><path d="M90 234h10"/>`];
function bailaoras() {
  return `<div class="bailaoras" aria-hidden="true">${BAILAORAS.map((b, i) => `<svg viewBox="10 10 150 240" class="bailaora b${i}" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round"><g vector-effect="non-scaling-stroke">${b}</g></svg>`).join("")}</div>`;
}
// Engranajes del Motor de proceso: el del motor gira cuando el equipo trabaja; el de la IA, con los colores del botón IA
const ENGRANAJE = '<path d="M12 2.5l1.6.3.4 2.1a7 7 0 0 1 1.9.8l1.8-1.2 1.2 1.1-1.2 1.8a7 7 0 0 1 .8 1.9l2.1.4.3 1.6-.3 1.6-2.1.4a7 7 0 0 1-.8 1.9l1.2 1.8-1.2 1.2-1.8-1.2a7 7 0 0 1-1.9.8l-.4 2.1-1.6.3-1.6-.3-.4-2.1a7 7 0 0 1-1.9-.8l-1.8 1.2-1.2-1.2 1.2-1.8a7 7 0 0 1-.8-1.9l-2.1-.4L2.5 12l.3-1.6 2.1-.4a7 7 0 0 1 .8-1.9L4.5 6.3l1.2-1.1 1.8 1.2a7 7 0 0 1 1.9-.8l.4-2.1z"/><circle cx="12" cy="12" r="3.2"/>';
function engranajes(lateral = false) {
  const ia = S.estado?.ia || {}, motor = !!S.estado?.trabajando;
  const iaCls = !ia.activo ? "apagado" : ia.estado === "pausa" ? "pausa" : ia.estado === "trabajando" ? "on gira" : "on";
  const iaTxt = !ia.activo ? "IA apagada" : ia.estado === "pausa" ? "IA en pausa" : ia.estado === "trabajando" ? "La IA está trabajando" : "IA encendida, en espera";
  const svg = t => `<svg viewBox="0 0 24 24" width="${t}" height="${t}" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round">${ENGRANAJE}</svg>`;
  if (lateral)        // 3.1.2 · boceto de Joan: «Motor ⚙ ⚙ IA» debajo de la marca, siempre a la vista
    return `<a href="#motor" class="lat-engranajes" title="Motor de proceso"><small>Motor</small><span class="eng motor ${motor ? "gira" : ""}" title="${motor ? "El motor está trabajando" : "El motor está parado"}">${svg(24)}</span>
      <span class="eng ia ${iaCls}" title="${iaTxt}">${svg(24)}</span><small>IA</small></a>`;
  return `<div class="engranajes"><span class="eng motor ${motor ? "gira" : ""}" title="${motor ? "El motor está trabajando" : "El motor está parado"}">${svg(88)}<small>Motor</small></span>
    <span class="eng ia ${iaCls}" title="${iaTxt}">${svg(88)}<small>IA</small></span></div>`;
}
function vistaMotor() {
  const lotes = S.estado.lotes.filter(x => x.documentos.length);
  const pendiente = x => x.documentos.some(d => !["guardado", "limbo", "duplicado", "contacto"].includes(d.estado));
  const l = lotes.find(x => x.id === LOTE) || lotes.find(pendiente) || lotes[0];
  if (!l) return `<div class="cab cab-motor"><div><small>Motor de proceso</small><h1>Motor de proceso</h1></div>${engranajes()}<div class="acciones"></div></div>${pestanasMotor("motor")}<div class="tarjeta vacio">No hay ningún lote todavía. Arrastra documentos al cuadro de la izquierda.</div>`;
  const docs = l.documentos;
  const enFase = i => docs.filter(d => (["guardado", "limbo", "contacto"].includes(d.estado) ? 10 : d.fase) === i + 1 || (i === 6 && d.estado === "espera_emparejar")).length;
  const minF = Math.min(...docs.map(d => ["guardado", "limbo", "contacto"].includes(d.estado) ? 10 : d.estado === "espera_emparejar" ? 7 : d.fase));
  const parado = docs.find(d => d.estado === "parado");
  const espera = docs.filter(d => d.estado === "espera_emparejar").length;
  const hechos = docs.filter(d => ["guardado", "limbo", "duplicado", "contacto"].includes(d.estado)).length;
  // 3.0.3: unidos, separados, sustituidos o deshechos ya están terminados (los sustituyen otros documentos): antes el lote se quedaba en 91 %
  const pct = Math.round(100 * docs.reduce((s, d) => s + (["guardado", "limbo", "duplicado", "contacto", "unido", "separado", "sustituido", "deshecho", "papelera"].includes(d.estado) ? 10 : d.fase), 0) / (10 * Math.max(docs.length, 1)));
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
  <div class="cab cab-motor"><div><small>Motor de proceso</small><h1>Motor de proceso</h1><div class="sub">Pasa el ratón por una fase para ver qué hace, dónde están los archivos y qué hacer si falla.</div></div>
    ${engranajes()}
    <div class="acciones">${espera ? `<a class="btn pri" href="#revision">${ico("check")}Responder ahora</a>` : ""}<button class="btn" id="reanudar">${ico("play")}Reanudar lo pendiente</button></div></div>
  ${pestanasMotor("motor")}
  ${avisoPausaIA()}
  ${parado ? `<div class="tarjeta" style="border-color:var(--bad);background:var(--badSoft)"><b>El motor se ha parado: ${esc(parado.motivo || "")}</b><span class="sub">Nada se ha perdido: el original sigue en Entrada\\. Corrige la causa y pulsa «Reanudar lo pendiente».</span></div>` : ""}
  <nav class="lotes" aria-label="Lotes">${lotes.slice(0, 12).map(x => `<a href="#motor/${x.id}" ${x.id === l.id ? 'aria-current="true"' : ""}>Lote ${x.id}${pendiente(x) ? " ·  en curso" : ""}</a>`).join("")}</nav>
  <section class="tarjeta"><div class="cab"><div><h2>Lote ${l.id} · ${esc(l.origen)}</h2><span class="sub">${titulo}</span></div>
    <div class="acciones">${botonesLoteIA(l)}<b style="font-size:22px;color:${parado ? "var(--bad)" : "var(--accent)"}">${pct} %</b></div></div>
    <div class="progreso"><i style="width:${pct}%;${parado ? "background:var(--bad)" : ""}"></i></div>
    <div class="ubic"><span>${ico("folder", 14)} Originales: <code>Entrada\\</code> hasta guardar</span><span>${ico("folder", 14)} Copia de trabajo: <code>Datos\\Trabajo\\lote_${l.id}\\</code></span><span>${ico("folder", 14)} Al terminar: <code>SeDocumentos\\</code> y <code>Doc_original\\</code></span></div>
    <div class="pipeline" style="padding-bottom:230px;margin-bottom:-220px">${pipe}</div></section>
  <section class="tarjeta sinp"><div class="tcab"><h2>Documentos del lote</h2><span class="sub">Pulsa uno para revisarlo</span></div>
    <table class="tabla"><thead><tr><th>Documento</th><th>Fase</th><th>Tipo</th><th>Dónde está ahora</th><th>Estado</th></tr></thead><tbody>
    ${docs.map(d => `<tr ${["espera_emparejar", "parado"].includes(d.estado) ? `class="clic" data-doc="${d.id}"` : ""}><td>${esc(d.archivo)}${d.nombre_final ? `<div class="mono muted">${esc(d.nombre_final)}</div>` : ""}</td><td>${fbar(d.fase, d.estado)}</td><td>${esc(d.tipo ? nombreTipo(d.tipo, d.modelo) : "—")}</td>
      <td>${Object.entries(d.donde).filter(([, v]) => v).map(([k, v]) => `<div class="mono"><span class="muted">${esc(k)}:</span> ${esc(v)}</div>`).join("")}</td><td>${est(d.estado)}</td></tr>`).join("")}
    </tbody></table></section>`;
}
function activarMotor() {
  $("#reanudar")?.addEventListener("click", async () => {
    try {
      const r = await api("procesar", {});
      const n = (r.en_cola || 0) + (r.a_revision || 0);
      aviso(!n ? "No había nada pendiente: todo está procesado o esperando tu respuesta en el Centro de revisión."
        : [r.en_cola ? `${r.en_cola} en proceso` : "", r.a_revision ? `${r.a_revision} vuelven al Centro de revisión` : ""].filter(Boolean).join(" · "));
    } catch (e) { aviso(e.message, true); }
    refrescar(true);
  });
  activarAvisoPausaIA();
  $("#ia-pasar")?.addEventListener("click", async e => { try { await api("ia/lote", { lote: +e.currentTarget.dataset.lote }); aviso("Pasando el lote a la IA…"); refrescar(true); } catch (er) { aviso(er.message, true); } });
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

// Documentos donde salen notarios, vendedores, representantes del banco…: nunca se elige a nadie solo
const TIPOS_VARIAS_PERSONAS = new Set(["escritura", "notasimple", "tasacion", "arras", "compraventa", "constitucion", "divorcio"]);
function iniciarRevision(d) {
  const datos = d.datos || {}, leidas = datos.personas || [];
  const fin = (S.info.finalidades_visibles || Object.keys(S.info.variante.finalidades))[0];
  const otros = {};
  leidas.forEach((p, i) => { if (p.tercero_lote) otros[i] = "tercero"; });        // ya marcados como terceros en este lote
  const candidatas = leidas.map((p, i) => ({ p, i })).filter(x => !x.p.tercero_lote);
  const variasPersonas = candidatas.length > 1 || TIPOS_VARIAS_PERSONAS.has(d.tipo);
  const elegida = !variasPersonas && candidatas[0];
  S.rev = { tipo: d.tipo || "", persona: elegida ? elegida.i : -3, fecha: null, finalidad: fin, otros,
    nuevo: elegida ? { nombre: elegida.p.nombre || "", ap1: elegida.p.apellido1 || "", ap2: elegida.p.apellido2 || "", dni: elegida.p.dni || (datos.dni || [])[0] || "" }
                   : { nombre: "", ap1: "", ap2: "", dni: "" } };
  const lm = !elegida && loteMayoritario(d);
  if (lm) usarLote(lm);      // sin persona clara: se propone como el resto del lote
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
const aliasDe = x => { try { return JSON.parse(x.alias || "[]").map(normaliza); } catch { return []; } };
function buscarFichada(P) {
  const f = fichadas(), n = normaliza(`${P.nombre} ${P.ap1} ${P.ap2 || ""}`), dni = (P.dni || "").toUpperCase();
  return f.find(x => dni && x.dni && x.dni.toUpperCase() === dni)
    || f.find(x => normaliza(`${x.nombre} ${x.apellido1} ${x.apellido2 || ""}`) === n)
    || f.find(x => aliasDe(x).includes(n))                         // otras formas de escribirla ya confirmadas
    // mismo nombre y primer apellido y a uno de los dos le falta el segundo (sin DNI distinto): es la misma
    || f.find(x => !(dni && x.dni && x.dni.toUpperCase() !== dni) && normaliza(x.nombre) === normaliza(P.nombre) && normaliza(x.apellido1) === normaliza(P.ap1)
         && (!normaliza(P.ap2) || !normaliza(x.apellido2))) || null;
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
  if (!cola.length) return `<div class="cab"><div><small>Centro de revisión</small><h1>Centro de revisión</h1></div></div><div class="tarjeta vacio revision-vacia">${bailaoras()}<span>No hay nada pendiente de revisar. ${S.estado.trabajando ? "El motor sigue trabajando: aparecerá aquí lo que necesite tu respuesta." : ""}</span></div>`;
  const d = S.doc;
  const lista = cola.map(x => `<a href="#revision/${x.id}" ${S.docId === x.id ? 'aria-current="true"' : ""}><b>${esc(x.archivo)}</b><small>${x.estado === "parado" ? esc(x.motivo) : x.tipo ? esc(nombreTipo(x.tipo, x.modelo)) + " · " + Math.round((x.confianza || 0) * 100) + " %" + (x.motivo ? " · revisar" : "") : "No reconocido"}</small></a>`).join("");
  if (!d || !S.rev) return `<div class="rev-abajo"><nav class="cola" aria-label="Pendientes">${lista}</nav><div class="tarjeta vacio">Cargando…</div></div>`;
  const datos = d.datos || {}, v = S.info.variante, R = S.rev, P = R.nuevo;
  const leidas = datos.personas || [];
  const pags = d.paginas_lista.length;
  // 1 · tipo
  const tipos = S.info.tipos.map(t => `<option value="${t.id}" ${t.id === R.tipo ? "selected" : ""}>${esc(t.nombre)}</option>`).join("");
  const extra = [["Ejercicio", datos.ejercicio], ["Entidad", d.entidad]].filter(([, x]) => x).map(([a, b]) => `${a}: <b>${esc(b)}</b>`).join(" · ");
  // 2 · persona
  const fich = R.ignorarFicha ? null : buscarFichada(P);
  // la persona elegida va siempre la primera
  const esTercero = i => (R.otros || {})[i] === "tercero";
  const chipsLeidas = leidas.map((p, i) => ({ sel: R.persona === i, html: esTercero(i)
      ? `<span class="chip peq tercero" title="Marcado como tercero: no se ficha">${esc(p.completo)}<small>tercero</small><button type="button" class="x-chip" data-no-tercero="${i}" aria-label="Ya no es tercero">↺</button></span>`
      : `<span class="chip-par"><button type="button" class="chip peq ${R.persona === i ? "sel" : ""}" data-persona="${i}">${esc(p.completo)}${p.dni ? `<small class="mono">${esc(p.dni)}</small>` : ""}</button><button type="button" class="x-chip" data-tercero="${i}" title="Es un tercero (notario, vendedor, banco…): no se ficha" aria-label="Marcar ${esc(p.completo)} como tercero">Tercero</button></span>` }));
  const chipsPersona = [...chipsLeidas.filter(c => c.sel), ...chipsLeidas.filter(c => !c.sel)].map(c => c.html).join("")
    + `<button type="button" class="chip peq ${R.persona === -1 ? "sel" : ""}" data-persona="-1">Otra persona…</button>`;
  const lm = loteMayoritario(d);
  const chipLote = lm ? `<button type="button" class="chip peq lote ${R.persona === -2 ? "sel" : ""}" id="r-lote" title="Lo que más se repite en los documentos ya confirmados de este lote">Como el resto del lote: ${esc(`${lm.per.nombre} ${lm.per.apellido1}`)}<small>${lm.n} de ${lm.total}</small></button>` : "";
  const reconocidaComo = fich && normaliza(`${fich.nombre} ${fich.apellido1} ${fich.apellido2 || ""}`) !== normaliza(`${P.nombre} ${P.ap1} ${P.ap2}`)
    ? `<span class="ok-txt">≈ Reconocida como <b>${esc(`${fich.nombre} ${fich.apellido1} ${fich.apellido2 || ""}`)}</b> (ya fichada)</span>` : "";
  const estadoPersona = reconocidaComo + (R.persona === -3 ? `<span class="warn-txt">Este documento nombra a varias personas: elige de quién es (o «Colectivo» si es de todo el expediente).</span>` : fich ? `<span class="ok-txt">Ya fichada: ${esc(fich.exps.map(e => `${e.papel} en «${e.nombre}»`).join(" · "))}</span>`
    : `<span class="sub">Persona nueva: todavía no está en ningún expediente.</span>`);
  // discrepancia: la ficha coincide por nombre pero el DNI leído es otro (pantalla 14)
  const discrepa = fich && P.dni && fich.dni && P.dni.toUpperCase() !== fich.dni.toUpperCase() && !R.discrepanciaVista;
  const avisoDiscrepancia = discrepa ? `<div class="dup discrepancia" role="alert"><b>Discrepancia: ¿es la misma persona?</b>
      <div class="lado"><div><small>En la ficha</small><b>${esc(`${fich.nombre} ${fich.apellido1} ${fich.apellido2 || ""}`)}</b><span class="mono">${esc(fich.dni)}</span></div>
      <div><small>Leído en el documento</small><b>${esc(`${P.nombre} ${P.ap1} ${P.ap2}`)}</b><span class="mono">${esc(P.dni)}</span></div></div>
      <div class="acciones"><button class="btn peq" id="dis-misma">Es la misma: dejar el DNI de la ficha</button><button class="btn peq" id="dis-corregir">Es la misma: corregir la ficha con ${esc(P.dni)}</button><button class="btn peq" id="dis-otra">Es otra persona</button></div></div>` : "";
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
  const mostrarDatos = R.destino === "nuevo" || R.persona === -1 || (!fich && R.persona !== -3);
  const finalidades = Object.entries(v.finalidades).filter(([k]) => (S.info.finalidades_visibles || [k]).includes(k)).map(([k, n]) => `<button type="button" class="fin-pill ${R.finalidad === k ? "sel" : ""}" data-fin="${k}" aria-pressed="${R.finalidad === k}">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${FIN_ICO[k] || IC.folder}</svg>${esc(n)}</button>`).join("");
  const filaDatos = mostrarDatos ? `<div class="fila-rev"><span class="lab">${R.destino === "nuevo" ? "Expediente nuevo" : "Datos de la persona"} <button type="button" class="btn peq vaciar" id="r-vaciar" title="Borrar los cuatro campos">${ico("x", 13)}Vaciar</button></span>
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
          .map(([k, n]) => `<button type="button" class="${(R.otros || {})[x.i] === k ? "sel" : ""}" data-otro="${x.i}" data-acc="${k}">${n}</button>`).join("")}${expSel ? `<select class="misma ${String((R.otros || {})[x.i] || "").startsWith("misma:") ? "sel" : ""}" data-misma="${x.i}" aria-label="Es la misma que…"><option value="">Es la misma que…</option>${expSel.personas.map(q => `<option value="${q.id}" ${(R.otros || {})[x.i] === "misma:" + q.id ? "selected" : ""}>${esc(`${q.nombre} ${q.apellido1} ${q.apellido2 || ""}`)}</option>`).join("")}</select>` : ""}</span>`}</div>`).join("")}</div></div>` : "";
  const pendientesOtras = otras.filter(x => !x.yaEsta).length;
  const union = (() => { const pr = (S.prop || []).find(x => x.documentos.includes(d.id)); return pr ? `<div class="union-mini"><b>${pr.documentos.length} hojas parecen el mismo documento${pr.porcentaje ? ` (${pr.porcentaje} %)` : ""}.</b> <span class="muted">${esc((pr.motivos || []).join(" · "))}</span>
    <a class="btn pri peq" href="#unir/${pr.documentos.join(",")}">${ico("check", 14)}Unir páginas</a> <button type="button" class="btn peq" id="no-unir" data-docs="${pr.documentos.join(",")}" title="No se volverá a proponer y el programa aprende de ello">No, son distintos</button></div>` : ""; })();
  // ¿tarjeta de visita? Se pregunta siempre, arriba y en grande: no se puede confirmar sin responder
  const tj = datos.tarjeta && !datos.tarjeta_descartada ? datos.tarjeta : null;
  if (tj && !R.tj) { const lm2 = loteMayoritario(d); R.tj = { ...tj, expediente: lm2 ? lm2.exp.id : (abiertos[0] || {}).id || "" }; }
  const T = R.tj || {};
  const preguntaTarjeta = tj ? `<section class="tarjeta-preg" role="alertdialog" aria-labelledby="tj-tit">
    <div class="tj-cab"><span class="tj-ico">☎</span><div><h2 id="tj-tit">¿Es una TARJETA DE VISITA o datos de contacto de un banco?</h2>
      <span>Este documento tiene muy poco texto, con teléfono o correo y algo de banco o cargo. Si es la tarjeta del gestor, del director o de la oficina, se guarda como contacto del banco en el expediente. <b>Responde antes de seguir.</b></span></div></div>
    <div class="tj-campos">
      <div class="campo"><label for="tj-entidad">Banco</label><input id="tj-entidad" list="tj-bancos" value="${esc(T.entidad || "")}"><datalist id="tj-bancos">${S.info.bancos.map(b => `<option value="${esc(b)}">`).join("")}</datalist></div>
      ${[["nombre", "Nombre"], ["cargo", "Cargo"], ["movil", "Móvil"], ["telefono", "Teléfono"], ["email", "Correo"], ["oficina", "Oficina"], ["direccion", "Dirección"]]
        .map(([k, l]) => `<div class="campo"><label for="tj-${k}">${l}</label><input id="tj-${k}" data-tj="${k}" value="${esc(T[k] || "")}"></div>`).join("")}
      <div class="campo"><label for="tj-exp">Expediente</label><select id="tj-exp">${abiertos.map(e => `<option value="${e.id}" ${+T.expediente === e.id ? "selected" : ""}>${esc(e.nombre)}</option>`).join("")}</select></div>
    </div>
    <div class="acciones"><button class="btn pri" id="tj-si">${ico("check")}Sí, guardar como contacto del banco</button><button class="btn" id="tj-no">No, es un documento normal</button></div></section>` : "";
  R.tarjetaPendiente = !!tj;
  return `${preguntaTarjeta}${bannerSerie(d)}${bannerIA(d)}
  <section class="barra-rev ${tj ? "bloqueada" : ""}" aria-label="Revisar">
    <div class="barra-cab"><b>Revisar</b><span class="sub">${esc(d.nombre_recibido)} · ${d.motivo ? esc(d.motivo) : "clasificado con " + Math.round((d.confianza || 0) * 100) + " %"} · ${cola.length} pendiente(s)</span>${union}</div>
    <div class="barra-pasos">
      <div class="paso"><span class="lab">1 · Tipo</span><select id="r-tipo">${R.tipo ? "" : '<option value="">— Elegir —</option>'}${tipos}</select>
        ${(d.alternativas || []).length ? `<span class="chips">${d.alternativas.map(a => `<button type="button" class="chip mini" data-tipo="${a.tipo}">${esc(nombreTipo(a.tipo))}</button>`).join("")}</span>` : ""}
        ${extra ? `<span class="sub">${extra}</span>` : ""}</div>
      <div class="paso"><span class="lab">2 · ¿De quién es?</span><span class="chips">${R.persona >= 0 ? chipsPersona.replace(/(<\/span>)/, "$1" + chipLote) : chipLote + chipsPersona}</span>${estadoPersona}</div>
      <div class="paso"><span class="lab">3 · ${clave ? FECHA_TXT[clave][0] : "Fecha"}</span>
        ${clave ? `<span class="chips">${chipsFecha || '<span class="sub">No ha leído ninguna.</span>'}</span><input type="date" id="r-fecha" aria-label="Otra fecha" value="${R.fecha && !candidatas.includes(R.fecha) ? R.fecha : ""}">` : '<span class="sub">Este tipo no lleva fecha en el nombre.</span>'}</div>
      <div class="paso"><span class="lab">4 · Expediente</span><div class="destinos" role="radiogroup" aria-label="Expediente">${opciones}</div>
        ${R.verMover ? `<div class="mover-rev"><label for="r-mover-sel">Mover a otro expediente</label><select id="r-mover-sel"><option value="">— Elegir —</option>${abiertos.map(e => `<option value="e:${e.id}" ${R.destino === "e:" + e.id ? "selected" : ""}>${esc(e.nombre)} · ${esc(e.personas.map(p => p.nombre + " " + p.apellido1).join(", "))}</option>`).join("")}</select></div>` : ""}</div>
      <div class="paso acciones-rev">
        <a class="btn peq" href="#unir/${d.id}" title="Juntar varias fotos u hojas en un solo PDF">Unir páginas</a>
        <button type="button" class="btn peq" id="r-mover" title="Llevar este documento a cualquier expediente">Mover a otro expediente…</button>
        <button class="btn peq" id="r-limbo">${ico("limbo", 15)}Limbo</button>
        <hr class="sep-acc">
        <div class="ambito" role="radiogroup" aria-label="De quién es el documento">
          <button type="button" class="btn peq ${R.comun ? "" : "sel"}" data-comun="0" aria-pressed="${!R.comun}" title="Documento de la persona elegida en el paso 2">${ico("user", 15)}Individual</button>
          <button type="button" class="btn peq ${R.comun ? "sel" : ""}" data-comun="1" aria-pressed="${!!R.comun}" title="Documento de todo el expediente: nota simple, tasación, arras, escritura del inmueble…">${ico("users", 15)}Colectivo</button>
        </div>
      </div>
    </div>
    ${avisoDiscrepancia}${avisoDup}${filaDatos}
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
          <button class="btn peq" id="v-ajustar">Ajustar</button><button class="btn peq" id="v-grande">Pantalla completa</button>
          <span class="sep"></span><button class="btn peq" data-girar="-90" title="Girar a la izquierda" aria-label="Girar a la izquierda">↺</button><button class="btn peq" data-girar="90" title="Girar a la derecha" aria-label="Girar a la derecha">↻</button>
          ${pags > 1 ? `<a class="btn peq" href="#separar/${d.id}" title="Partir este PDF en varios documentos">✂ Separar</a>` : ""}<button class="btn peq peligro" id="r-papelera" title="Enviar a la Papelera">${ico("trash", 14)}</button></span></div>
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
  $("#no-unir")?.addEventListener("click", async ev => {
    const b = ev.currentTarget; b.disabled = true;
    try { await api("no_unir", { documentos: b.dataset.docs.split(",").map(Number) }); S.prop = await api("propuestas_union"); aviso("Anotado: no se volverán a proponer juntas"); pintar(); }
    catch (e) { b.disabled = false; aviso(e.message, true); }
  });
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
  document.querySelectorAll("[data-tercero]").forEach(b => b.addEventListener("click", () => {
    const i = +b.dataset.tercero; R.otros = { ...(R.otros || {}), [i]: "tercero" };
    if (R.persona === i) { R.persona = -3; R.nuevo = { nombre: "", ap1: "", ap2: "", dni: "" }; R.destino = undefined; }
    pintar();
  }));
  document.querySelectorAll("[data-no-tercero]").forEach(b => b.addEventListener("click", () => { delete R.otros[+b.dataset.noTercero]; pintar(); }));
  $("#dis-misma")?.addEventListener("click", () => { R.nuevo.dni = buscarFichada({ ...R.nuevo, dni: "" })?.dni || R.nuevo.dni; R.discrepanciaVista = true; pintar(); });
  $("#dis-corregir")?.addEventListener("click", async () => {
    const f = buscarFichada({ ...R.nuevo, dni: "" });
    try { await api("persona", { id: f.id, dni: R.nuevo.dni }); S.expedientes = await api("expedientes"); aviso("Ficha corregida y documentos renombrados"); R.discrepanciaVista = true; pintar(); } catch (e) { aviso(e.message, true); }
  });
  $("#dis-otra")?.addEventListener("click", () => { R.ignorarFicha = true; R.discrepanciaVista = true; R.destino = "nuevo"; R.dupOk = true; pintar(); });
  document.querySelectorAll("[data-girar]").forEach(b => b.addEventListener("click", async () => {
    await api("girar", { documento: S.docId, pos: S.pag, grados: +b.dataset.girar }); S.doc = await api("documento/" + S.docId); pintar();
  }));
  $("#r-papelera")?.addEventListener("click", async () => {
    if (!confirm("¿Enviar este documento a la Papelera? Se puede restaurar.")) return;
    try { await api("eliminar", { documento: S.docId }); aviso("A la Papelera"); siguiente(); } catch (e) { aviso(e.message, true); }
  });
  $("#r-vaciar")?.addEventListener("click", () => { R.nuevo = { nombre: "", ap1: "", ap2: "", dni: "" }; R.persona = -1; R.destino = undefined; pintar(); $("#n-nom")?.focus(); });
  $("#r-mover")?.addEventListener("click", () => { R.verMover = !R.verMover; pintar(); });
  $("#r-mover-sel")?.addEventListener("change", e => { if (e.target.value) { R.destino = e.target.value; R.dupOk = false; R.verMover = false; pintar(); } });
  document.querySelectorAll("[data-tj]").forEach(i => i.addEventListener("input", () => (R.tj[i.dataset.tj] = i.value)));
  $("#tj-entidad")?.addEventListener("input", e => (R.tj.entidad = e.target.value));
  $("#tj-exp")?.addEventListener("change", e => (R.tj.expediente = e.target.value));
  $("#tj-si")?.addEventListener("click", async () => {
    const T = R.tj;
    if (!T.entidad.trim()) return aviso("Indica de qué banco es la tarjeta.", true);
    if (!T.expediente) return aviso("Elige el expediente (o crea antes el expediente del cliente).", true);
    try { const r = await api("tarjeta", { documento: S.docId, expediente: +T.expediente, entidad: T.entidad.trim(), contacto: T });
      aviso(`Contacto guardado en ${T.entidad}: ${r.nombre_final}`); siguiente(); } catch (e) { aviso(e.message, true); }
  });
  $("#tj-no")?.addEventListener("click", async () => { await api("tarjeta", { documento: S.docId, no: true }); R.tj = null; S.doc = await api("documento/" + S.docId); pintar(); });
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
  document.querySelectorAll("[data-misma]").forEach(s => s.addEventListener("change", () => {
    const i = +s.dataset.misma; R.otros = { ...(R.otros || {}) };
    if (s.value) R.otros[i] = "misma:" + s.value; else delete R.otros[i];
    pintar();
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
  if (R.tarjetaPendiente) return aviso("Primero responde arriba: ¿es una tarjeta de visita?", true);
  if (!tipo) return aviso("Elige el tipo de documento.", true);
  const colectivoSinPersona = R.comun && R.destino.startsWith("e:") && (R.persona === -3 || !P.nombre.trim());
  if (R.persona === -3 && !colectivoSinPersona) return aviso("Elige de quién es el documento (paso 2), o «Colectivo» si es de todo el expediente.", true);
  if (!colectivoSinPersona && (!P.nombre.trim() || !P.ap1.trim())) return aviso("Falta el nombre o el primer apellido de la persona.", true);
  const leidas = (S.doc.datos || {}).personas || [];
  const expSel = R.destino.startsWith("e:") ? S.expedientes.find(e => e.id === +R.destino.slice(2)) : null;
  const pendientes = leidas.map((p, i) => ({ p, i })).filter(x => x.i !== R.persona && !(colectivoSinPersona && x.i === R.persona)).filter(x => {
    const f = buscarFichada({ nombre: x.p.nombre, ap1: x.p.apellido1, ap2: x.p.apellido2, dni: x.p.dni });
    return !(f && expSel && expSel.personas.some(q => q.id === f.id));
  });
  if (pendientes.some(x => !(R.otros || {})[x.i])) return aviso("Hay más personas en el documento: indica qué es cada una.", true);
  const otrosEnvio = pendientes.map(x => { const acc = R.otros[x.i], misma = String(acc).startsWith("misma:");
    return { persona: { nombre: x.p.nombre, apellido1: x.p.apellido1, apellido2: x.p.apellido2, dni: x.p.dni }, accion: misma ? "misma" : acc, persona_id: misma ? +acc.slice(6) : null }; });
  const persona_datos = { nombre: P.nombre.trim(), apellido1: P.ap1.trim(), apellido2: P.ap2.trim(), dni: P.dni.trim().toUpperCase() || null };
  const fich = R.ignorarFicha ? null : buscarFichada(P);
  let expediente, persona = null;
  try {
    if (R.destino === "nuevo") {
      const dups = [fich, ...parecidas(P, fich)].filter(x => x && x.exps.some(e => e.estado === "abierto"));
      if (dups.length && !R.dupOk) return aviso("Esta persona ya tiene expediente: añade el documento a ese expediente o marca que quieres otro aparte.", true);
      const r = await api("expediente", { persona: persona_datos, finalidad: R.finalidad, confirmado: !!R.dupOk });
      expediente = r.expediente; persona = r.persona; aviso("Expediente creado: " + r.carpeta);
    } else {
      expediente = +R.destino.slice(2); persona = colectivoSinPersona ? null : fich ? fich.id : null;
      const exp = S.expedientes.find(e => e.id === expediente);
      if (!colectivoSinPersona && !(fich && exp.personas.some(q => q.id === fich.id))
          && !confirm(`¿Añadir a ${P.nombre} ${P.ap1} como COTITULAR del expediente «${exp.nombre}»?\n\nSi no es titular de la operación (notario, vendedor, banco…), pulsa Cancelar y márcalo como «Tercero».`)) return;
    }
    let segunda = null, nombre_previsto = null;
    if (R.destino !== "nuevo") {
      const pv = await api("nombre_previsto", { documento: S.docId, expediente, persona, tipo, fecha: R.fecha, privado: !!R.priv, comun: !!R.comun });
      if (pv.existe) {
        segunda = await preguntarSegunda(pv);
        if (!segunda) return;
        nombre_previsto = pv.nombre;
      }
    }
    const g = await api("emparejar", { documento: S.docId, expediente, persona, persona_datos: persona || colectivoSinPersona ? null : persona_datos, segunda, nombre_previsto,
      comun: !!R.comun, tipo, privado: !!R.priv, fecha: R.fecha, otros: otrosEnvio });
    aviso("Guardado: " + g.nombre_final);
    siguiente();
  } catch (e) { aviso(e.message, true); }
}

// Segunda aportación (pantalla 19): ya hay un documento con ese nombre en el expediente
function preguntarSegunda(pv) {
  return new Promise(res => {
    const caja = document.createElement("div");
    caja.className = "zoom informe";
    caja.innerHTML = `<div class="tarjeta"><h2>Ya hay un «${esc(pv.nombre)}» en este expediente</h2>
      <span class="sub">Llegó el ${pv.previo ? fmtF(pv.previo.creado) : "—"}. ¿Qué es el que estás guardando ahora?</span>
      <div class="opciones-2">
        <button class="btn pri" data-s="sustituir">Sustituye al anterior<small>el anterior pasa a llamarse …-ant y deja de contar</small></button>
        <button class="btn" data-s="secundaria">Es otro más (secundario)<small>se guarda como …-2</small></button>
        <button class="btn" data-s="duplicado">Es el mismo, repetido<small>va a la Papelera</small></button>
        <button class="btn" data-s="limbo">No lo sé todavía<small>al Limbo</small></button></div>
      <div class="acciones"><button class="btn" data-s="">Cancelar</button></div></div>`;
    document.body.appendChild(caja);
    caja.querySelectorAll("[data-s]").forEach(b => b.addEventListener("click", () => { caja.remove(); res(b.dataset.s || null); }));
  });
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
      <figcaption><b>${i + 1}.</b> ${esc(x.archivo)}<br><span class="muted">${esc(nombreTipo(x.tipo, x.modelo))}</span></figcaption>
      <span class="acciones"><button class="btn peq" data-mover="${i}" data-dir="-1" ${i === 0 ? "disabled" : ""} aria-label="Antes">${ico("left", 14)}</button>
      <button class="btn peq" data-mover="${i}" data-dir="1" ${i === UNIR.length - 1 ? "disabled" : ""} aria-label="Después">${ico("right", 14)}</button>
      <button class="btn peq" data-sacar="${x.id}" aria-label="Quitar">${ico("x", 14)}</button></span></figure>`;
  return `<div class="cab"><div><small><a href="#revision">Centro de revisión</a> › Unir</small><h1>Unir en un solo PDF</h1>
    <div class="sub">Ordena las páginas, pulsa una para verla en grande con zoom y une. Las fotos originales se guardan en Doc_original al terminar.</div></div>
    <div class="acciones"><a class="btn" href="#revision">Cancelar</a><button class="btn pri" id="unir-ok" ${UNIR.length < 2 ? "disabled" : ""}>${ico("check")}Unir en un PDF (${UNIR.length} páginas)</button></div></div>
  <section class="tarjeta"><h2>Páginas del documento, en orden</h2><div class="pags">${UNIR.map((id, i) => tarjeta(porId[id], i)).join("") || '<span class="sub">Añade abajo las fotos que forman el documento.</span>'}</div></section>
  ${resto.length ? `<section class="tarjeta"><h2>Otros documentos pendientes</h2><div class="pags">${resto.map(x => `<figure class="pag otro-doc">
      <button type="button" class="miniatura" data-zoom="${x.id}" aria-label="Ver ${esc(x.archivo)} en grande"><img src="/api/vista/${x.id}/1" alt="" loading="lazy"></button>
      <figcaption>${esc(x.archivo)}<br><span class="muted">${esc(nombreTipo(x.tipo, x.modelo))}</span></figcaption>
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
  const { e } = EXP, v = S.info.variante;
  const titulares = e.personas.filter(p => ["Titular", "Cotitular"].includes(p.papel)).length;
  // 3.1.2 · cabecera según el boceto de Joan: sección en verde, nombre con ★ y campanita, datos en una línea,
  // botones de trabajo debajo y, a la derecha, «Documentación» grande con «zip» y «carpeta» en columna
  return `<div class="exp-cab">
    <div class="exp-cab-izq">
      <a class="seccion" href="#expedientes">Expedientes</a>
      <div class="exp-titulo"><h1>${esc(e.nombre)}</h1>
        <button type="button" class="marca-b ${e.marcas?.favorito ? "on" : ""}" id="exp-fav" title="Favorito">${e.marcas?.favorito ? "★" : "☆"}</button>
        <button type="button" class="marca-b prio-${e.marcas?.prioridad || "no"} ${e.marcas?.prioridad ? "on" : ""}" id="exp-prio" title="${PRIO[e.marcas?.prioridad || ""]} (pulsa para cambiar)">${ico("bell", 18)}</button></div>
      <div class="cab-exp"><span title="${titulares} titular(es)">${ico("user", 15)} ${titulares}</span><span>creado el ${fmtF(e.creado)}</span>
        <span title="Carpeta del expediente">${ico("edit", 14)} <code>${esc(e.carpeta)}</code></span>
        <select id="exp-finalidad" title="Tipo de financiación (pulsa para cambiarlo)">${Object.entries(v.finalidades).map(([k, n]) => `<option value="${k}" ${k === e.finalidad ? "selected" : ""}>${esc(n)}</option>`).join("")}</select>
        <button type="button" class="estado-b ${e.estado}" id="op-estado" title="Estado y datos de la operación">${esc(EXP.op?.etiqueta || e.etiqueta || "Abierto")} · cambiar estado</button></div>
      <div class="exp-botones"><button class="btn peligro icono" id="exp-eliminar" title="Eliminar el expediente (va a la Papelera)" aria-label="Eliminar">${ico("trash", 18)}</button>
        ${e.estado === "abierto" ? `<button class="btn" id="unir-exp">${ico("users")}Unir con otro exp.</button>` : ""}<button class="btn" id="rehacer">${ico("play")}Rehacer texto</button></div>
    </div>
    <div class="exp-cab-der">
      <a class="btn pri btn-doc-grande" href="#documentacion/${e.id}">${ico("folder", 30)}Documentación<span class="num">${(EXP.docs || []).length}</span></a>
      <div class="exp-mini"><button class="btn" id="exp-exportar" title="Exportar el expediente en un zip">zip</button>
        <button class="btn icono" id="exp-carpeta" title="Abrir la carpeta del expediente" aria-label="Abrir carpeta">${ico("folder", 20)}</button></div>
    </div></div>
  ${OPV && EXP.op ? panelOperacion(e) : ""}
  ${e.estado === "unido" ? '<div class="tarjeta"><b>Este expediente se unió a otro.</b> <span class="sub">Sus personas y documentos están ahora en el expediente de destino.</span></div>' : ""}
  ${ARR.unir ? panelUnirExp(e) : ""}
  ${tarjetaDatosLeidos()}
  ${EXP.neg ? `<div class="exp-notas">${panelNegBanco(e)}${panelNegCliente(e)}</div>` : ""}
  <div class="exp-cuerpo">
    <div class="exp-izq">${tarjetaPersonasExp(e)}</div>
    <aside class="exp-der">${tarjetaChecklist(e)}</aside>
  </div>${INFORME ? modalInforme() : ""}${dialogoEstado()}`;
}
// 3.1.0 · datos principales leídos en los documentos (personas del expediente y contactos del banco)
function tarjetaDatosLeidos() {
  const D = EXP.datos;
  if (!D) return "";
  const v = x => x ? esc(x) : '<span class="muted">—</span>';
  const pers = D.personas.map(p => `<div class="dl-persona"><div class="dl-cab"><b>${esc(`${p.nombre} ${p.apellido1} ${p.apellido2}`)}</b>${pill(p.papel, p.papel === "Titular" ? "ok" : "todo")}${p.manual ? ' <span class="pill p-todo" title="Datos metidos a mano: referencia segura">Manual</span>' : ""}</div>
      <dl><dt>DNI / NIE</dt><dd class="mono">${v(p.dni)}</dd><dt>Teléfono</dt><dd class="mono">${p.telefonos.length ? p.telefonos.map(esc).join("<br>") : v("")}</dd>
      <dt>Correo</dt><dd>${p.correos.length ? p.correos.map(esc).join("<br>") : v("")}</dd><dt>Dirección</dt><dd>${v(p.direccion)}</dd></dl></div>`).join("");
  const bancos = D.bancos.map(c => `<div class="dl-persona banco"><div class="dl-cab"><b>${esc(c.nombre || "Contacto")}</b>${c.cargo ? `<span class="sub">${esc(c.cargo)}</span>` : ""}<span class="pill p-ia">${esc(c.banco || "Banco")}</span></div>
      <dl><dt>Teléfono</dt><dd class="mono">${[c.movil, c.telefono].filter(Boolean).map(esc).join("<br>") || v("")}</dd><dt>Correo</dt><dd>${v(c.email)}</dd>
      <dt>Oficina</dt><dd>${v([c.oficina, c.direccion].filter(Boolean).join(" · "))}</dd></dl></div>`).join("");
  return `<section class="tarjeta datos-leidos"><div class="tcab"><h2>Datos leídos</h2><span class="sub">De los documentos de cada persona y de los contactos del banco. Para corregir un nombre o un DNI, entra en su ficha (Personas).</span></div>
    <div class="dl-grid">${pers}${bancos || '<div class="dl-persona banco vacio-dl"><span class="sub">Sin contactos del banco todavía (se añaden en Negociación banco o con una tarjeta de visita).</span></div>'}</div></section>`;
}
// 3.1.0 · pantalla «Documentación» del expediente (archivo, tipo, de quién, Abrir, Mover y Papelera)
function vistaDocumentacion() {
  if (!EXP) return '<div class="tarjeta vacio">Cargando…</div>';
  const { e } = EXP;
  return `<div class="cab"><div><small><a href="#expedientes">Expedientes</a> › <a href="#expediente/${e.id}">${esc(e.nombre)}</a></small><h1>Documentación</h1>
    <div class="sub">Todos los documentos guardados de este expediente. «Mover…» los lleva a otro expediente o a otra persona; la papelera nunca borra.</div></div>
    <div class="acciones"><button class="btn" id="exp-carpeta">${ico("folder")}Abrir carpeta</button><a class="btn" href="#expediente/${e.id}">Volver al expediente</a></div></div>
  ${tarjetaDocsExp(e)}`;
}
// ---------------- negociación banco (varios bancos, contactos) y negociación cliente (F-17)
const NEG = { banco: 0, verBanco: false, contacto: null, historial: { banco: false, cliente: false } };
function notasLista(tipo, notas) {
  if (!notas.length) return '<span class="sub">Sin notas todavía.</span>';
  const banco = id => (EXP.neg.bancos.find(b => b.id === id) || {}).entidad;
  const una = n => `<div class="nota"><span class="nota-f">${fmtF(n.fecha)} · ${n.fecha.slice(11, 16)}${tipo === "banco" && n.banco_id && !NEG.banco ? ` · <b>${esc(banco(n.banco_id) || "")}</b>` : ""}</span><span>${esc(n.texto)}</span></div>`;
  const resto = notas.slice(2);
  return notas.slice(0, 2).map(una).join("") + (resto.length ? `<details class="historial" ${NEG.historial[tipo] ? "open" : ""} data-hist="${tipo}"><summary>Historial · ${resto.length} anterior(es)</summary>${resto.map(una).join("")}</details>` : "");
}
function panelNegBanco(e) {
  const n = EXP.neg, sel = n.bancos.find(b => b.id === NEG.banco);
  const notas = n.notas.filter(x => x.tipo === "banco" && (!sel || x.banco_id === sel.id));
  const c0 = NEG.contacto;
  const fichaContacto = c => `<div class="contacto">
      <div><b>${esc(c.nombre || "Sin nombre")}</b>${c.cargo ? ` <span class="muted">· ${esc(c.cargo)}</span>` : ""}</div>
      <div class="contacto-datos">${c.movil ? `<span>${ico("user", 13)} ${esc(c.movil)}</span>` : ""}${c.telefono ? `<span>☎ ${esc(c.telefono)}</span>` : ""}${c.email ? `<span>✉ ${esc(c.email)}</span>` : ""}${c.oficina ? `<span>Oficina ${esc(c.oficina)}</span>` : ""}${c.direccion ? `<span>${esc(c.direccion)}</span>` : ""}</div>
      ${c.notas ? `<div class="sub">${esc(c.notas)}</div>` : ""}
      <div class="acciones"><button class="btn peq" data-ed-contacto="${c.id}">Editar</button><button class="btn peq" data-quitar-contacto="${c.id}">Quitar</button>${c.documento_id ? '<span class="sub">De una tarjeta de visita</span>' : ""}</div></div>`;
  const formContacto = c => `<div class="contacto form">${[["nombre", "Nombre y apellidos"], ["cargo", "Cargo (gestor, director…)"], ["movil", "Móvil"], ["telefono", "Teléfono"], ["email", "Correo"], ["oficina", "Oficina"], ["direccion", "Dirección"], ["notas", "Notas"]]
      .map(([k, l]) => `<div class="campo"><label for="ct-${k}">${l}</label><input id="ct-${k}" value="${esc(c[k] || "")}"></div>`).join("")}
      <div class="acciones"><button class="btn pri peq" id="ct-guardar">${ico("check", 14)}Guardar contacto</button><button class="btn peq" id="ct-cancelar">Cancelar</button></div></div>`;
  return `<section class="tarjeta neg banco"><div class="neg-cab"><h2>${ico("folder", 17)} Negociación banco</h2><span class="sub">${n.notas.filter(x => x.tipo === "banco").length} notas · ${n.bancos.length} banco(s)</span>
      <button class="btn peq" id="neg-add-banco">＋ Banco</button></div>
    ${NEG.verBanco ? `<div class="fila-arreglo"><input id="neg-entidad" list="lista-bancos" placeholder="Escribe o elige el banco"><datalist id="lista-bancos">${S.info.bancos.map(b => `<option value="${esc(b)}">`).join("")}</datalist>
      <button class="btn pri peq" id="neg-banco-ok">Añadir</button><button class="btn peq" id="neg-banco-no">Cancelar</button></div>` : ""}
    ${n.bancos.length ? `<div class="bancos-chips"><button type="button" class="chip peq ${!sel ? "sel" : ""}" data-banco="0">Todos</button>${n.bancos.map(b => `<button type="button" class="chip peq ${sel && sel.id === b.id ? "sel" : ""}" data-banco="${b.id}">${esc(b.entidad)}<small>${esc(b.estado)}</small></button>`).join("")}</div>` : '<span class="sub">Añade los bancos con los que negocias este expediente: cada uno con su estado, sus contactos y sus notas.</span>'}
    ${sel ? `<div class="banco-ficha"><div class="fila-arreglo"><label>Estado con ${esc(sel.entidad)} <select id="neg-estado">${n.estados_banco.map(s => `<option ${s === sel.estado ? "selected" : ""}>${s}</option>`).join("")}</select></label>
        <button class="btn peq" id="neg-add-contacto">＋ Contacto</button></div>
      ${c0 && !c0.id ? formContacto(c0) : ""}
      ${sel.contactos.map(c => c0 && c0.id === c.id ? formContacto(c0) : fichaContacto(c)).join("") || (c0 ? "" : '<span class="sub">Sin contactos: gestor, director, oficina… (también desde una tarjeta de visita).</span>')}</div>` : ""}
    <div class="neg-nueva"><input id="nota-banco" placeholder="Escribe una nota${sel ? " sobre " + esc(sel.entidad) : ""}… (se guarda con la fecha y la hora)"><button class="btn peq" data-nota="banco">Añadir</button></div>
    ${notasLista("banco", notas)}</section>`;
}
function panelNegCliente() {
  const notas = EXP.neg.notas.filter(x => x.tipo === "cliente");
  return `<section class="tarjeta neg cliente"><div class="neg-cab"><h2>${ico("user", 17)} Negociación cliente</h2><span class="sub">${notas.length} notas</span></div>
    <div class="neg-nueva"><input id="nota-cliente" placeholder="Escribe una nota…"><button class="btn peq" data-nota="cliente">Añadir</button></div>
    ${notasLista("cliente", notas)}</section>`;
}
// ---------------- checklist con marcas (Aportado lo pone el programa; Solicitado y Sin pedir, a mano)
let CK_TAB = null, INFORME = null;
const PAPELES = ["Titular", "Cotitular", "Avalista", "Beneficiario", "Cónyuge o pareja no titular", "Administrador", "Titular anterior", "Tercero"];
function estadoCheck(f) {
  const m = (EXP.neg?.marcas || {})[f.clave];
  if (f.estado === "Recibido") return ["Aportado", "ok", "✓"];
  if (f.estado === "Caducado") return ["Caducado", "bad", "!"];
  if (f.estado === "Incompleto") return ["Incompleto", "warn", "!"];
  if (m?.estado === "solicitado") return ["Solicitado", "sol", "◷"];
  if (m?.estado === "sin_pedir") return ["Sin pedir", "nop", "–"];
  return ["Pendiente", "todo", "○"];
}
function tarjetaChecklist(e) {
  const ck = EXP.ck, v = S.info.variante;
  const grupos = [];
  e.personas.filter(p => ck.filas.some(f => f.persona_id === p.id)).forEach(p => grupos.push({ id: String(p.id), nombre: `${p.nombre} ${p.apellido1}`, filas: ck.filas.filter(f => f.persona_id === p.id) }));
  const comunes = ck.filas.filter(f => !f.persona_id);
  if (comunes.length) grupos.push({ id: "exp", nombre: "Comunes a la operación", filas: comunes });
  if (!grupos.some(g => g.id === CK_TAB)) CK_TAB = grupos[0]?.id;
  const g = grupos.find(x => x.id === CK_TAB);
  const marcas = EXP.neg?.marcas || {};
  const solicitados = ck.filas.filter(f => marcas[f.clave]?.estado === "solicitado").length;
  const cuenta = gr => `${gr.filas.filter(f => f.estado === "Recibido").length}/${gr.filas.length}`;
  const fila = f => { const [txt, cls, ic] = estadoCheck(f); const libre = f.estado !== "Recibido";
    return `<div class="ck-fila ${cls}"><span class="ck-ico">${ic}</span><div class="ck-txt"><span class="ck-nom">${esc(f.documento)}${f.importancia === "imprescindible" ? ' <span class="ck-imp" title="Imprescindible">•</span>' : ""}</span>
      ${f.archivos.length || f.detalle || ["sol", "nop"].includes(cls) ? `<small>${esc(f.archivos.join(", ") || f.detalle || txt)}${f.archivos.length && f.detalle ? " · " + esc(f.detalle) : ""}</small>` : ""}</div>
      ${libre ? `<span class="ck-acc"><button type="button" class="${marcas[f.clave]?.estado === "solicitado" ? "sel" : ""}" data-marca="${f.clave}" data-estado="solicitado" title="Ya se lo he pedido al cliente">Solicitado</button><button type="button" class="${marcas[f.clave]?.estado === "sin_pedir" ? "sel" : ""}" data-marca="${f.clave}" data-estado="sin_pedir" title="No hace falta pedirlo en este expediente">Sin pedir</button></span>` : `<span class="ck-estado">${txt}</span>`}</div>`; };
  return `<section class="tarjeta checklist"><div class="neg-cab"><h2>Checklist · ${esc(v.finalidades[e.finalidad] || e.finalidad)}</h2><span class="sub">${ck.recibidos} de ${ck.total} aportados${solicitados ? ` · ${solicitados} solicitados` : ""}</span></div>
    ${solicitados ? `<div class="progreso fino"><i style="width:${Math.round(100 * ck.recibidos / Math.max(1, ck.recibidos + solicitados))}%"></i></div>` : ""}
    <div class="ck-tabs2">${grupos.map(x => `<button type="button" data-ck-tab="${x.id}" class="${x.id === CK_TAB ? "sel" : ""}">${esc(x.id === "exp" ? "Comunes" : x.nombre)} <small>${cuenta(x)}</small></button>`).join("")}</div>
    ${g ? (() => { const fam = {}; g.filas.forEach(f => (fam[f.familia || "Otros"] = fam[f.familia || "Otros"] || []).push(f));
        return Object.entries(fam).map(([k, fs], n) => `<div class="ck-grupo g${n % 6}" title="${esc(k)}">${fs.map(fila).join("")}</div>`).join(""); })() : '<span class="sub">La finalidad no tiene documentos: se configuran en Ajustes → Finalidades.</span>'}
    ${ck.avisos_cliente.length ? `<div class="ck-avisos"><b>Avisos al cliente</b>${ck.avisos_cliente.map(a => `<span>${esc(a)}</span>`).join("")}</div>` : ""}
    <button class="btn" id="ck-informe">${ico("mail", 16)}Generar informe de lo que falta y enviar</button></section>`;
}
function textoInforme() {
  const { e, ck } = EXP, falta = ck.filas.filter(f => f.estado !== "Recibido" && (EXP.neg?.marcas || {})[f.clave]?.estado !== "sin_pedir");
  const titulares = e.personas.filter(p => ["Titular", "Cotitular"].includes(p.papel));
  const saludo = titulares.length > 1 ? `Hola, ${titulares.map(p => p.nombre).join(" y ")}:` : `Hola, ${(titulares[0] || e.personas[0] || {}).nombre || ""}:`;
  const fin = (S.info.variante.finalidades[e.finalidad] || "operación").toLowerCase();
  const por = {}; falta.forEach(f => (por[f.quien] = por[f.quien] || []).push(`  · ${f.documento}${f.detalle && f.estado !== "Pendiente" ? " (" + f.detalle + ")" : ""}`));
  const lista = Object.entries(por).map(([q, l]) => (Object.keys(por).length > 1 || q === "Expediente" ? `${q === "Expediente" ? "De la operación" : "De " + q}:\n` : "") + l.join("\n")).join("\n\n");
  if (!falta.length) return `${saludo}\n\n¡Buenas noticias! Ya tenemos toda la documentación para tu ${fin}. En cuanto haya novedades te lo contamos.\n\nMuchas gracias y un saludo.`;
  return `${saludo}\n\nEspero que estés muy bien. Para seguir avanzando con tu ${fin}, todavía nos falta la siguiente documentación:\n\n${lista}\n\nPuedes enviárnosla respondiendo a este mensaje; valen fotos con el móvil o PDF, siempre que se lean bien y se vean enteros. Si tienes cualquier duda con algún documento, dímelo y te ayudo.\n\nMuchas gracias y un saludo.`;
}
function modalInforme() {
  const c = EXP.op?.datos || {};
  return `<div class="zoom informe"><div class="tarjeta"><h2>Enviar lo que falta</h2>
    <div class="op-campos"><div class="campo"><label for="inf-mail">Correo del cliente</label><input id="inf-mail" type="email" value="${esc(c.contacto_email || "")}" placeholder="cliente@correo.es"></div>
      <div class="campo"><label for="inf-tel">Móvil (WhatsApp)</label><input id="inf-tel" value="${esc(c.contacto_tel || "")}" placeholder="600 000 000"></div>
      <div class="campo"><label for="inf-asunto">Asunto</label><input id="inf-asunto" value="Documentación pendiente · ${esc(EXP.e.nombre)}"></div></div>
    <textarea id="inf-txt" rows="15">${esc(INFORME)}</textarea>
    <span class="sub">Puedes cambiar el texto. «Correo» abre tu programa de correo con el mensaje preparado; «WhatsApp» abre WhatsApp con el texto listo. No se envía nada sin que tú lo pulses allí.</span>
    <div class="acciones"><button class="btn pri" id="inf-correo">${ico("mail")}Enviar por correo</button><button class="btn pri" id="inf-wa">Enviar por WhatsApp</button><button class="btn" id="inf-copiar">${ico("check")}Copiar</button><button class="btn" id="inf-cerrar">Cerrar</button></div></div></div>`;
}
function tarjetaPersonasExp(e) {
  const docsDe = id => (EXP.docs || []).filter(d => d.persona_id === id && !d.de_expediente).length;
  return `<section class="tarjeta sinp"><div class="tcab"><h2>Personas del expediente · ${e.personas.length}</h2></div>
    <table class="tabla"><tbody>${e.personas.map(p => { const n = docsDe(p.id);
      return `<tr><td><a href="#persona/${p.id}"><b>${esc(`${p.nombre} ${p.apellido1} ${p.apellido2 || ""}`)}</b></a></td><td><select data-papel="${p.id}" aria-label="Papel">${PAPELES.map(x => `<option ${x === p.papel ? "selected" : ""}>${x}</option>`).join("")}</select></td><td class="mono">${esc(p.dni || "sin DNI")}</td><td>${n} documento(s)</td>
      <td class="der">${e.personas.length > 1 ? `<select class="misma" data-misma-exp="${p.id}" aria-label="Es la misma que…"><option value="">Es la misma que…</option>${e.personas.filter(q => q.id !== p.id).map(q => `<option value="${q.id}">${esc(`${q.nombre} ${q.apellido1} ${q.apellido2 || ""}`)}</option>`).join("")}</select>` : ""}
        ${e.estado === "abierto" && e.personas.length > 1 ? `<button class="btn peq" data-quitar-persona="${p.id}" ${n ? `disabled title="Tiene documentos: muévelos antes con «Mover…»"` : ""}>Quitar del expediente</button>` : ""}</td></tr>`; }).join("")}</tbody></table></section>`;
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
  const filas = EXP.docs.map(d => `<tr><td class="mono">${esc(d.nombre_final)}</td><td>${esc(nombreTipo(d.tipo, d.modelo))}</td><td>${d.de_expediente ? "Todo el expediente" : esc(d.persona)}${d.privado ? ' <span class="pill p-todo">Privado</span>' : ""}</td>
    <td class="der"><button class="btn peq" data-abrir-doc="${esc(d.ruta_final || "")}" title="Ver en la carpeta">Abrir</button> ${e.estado === "abierto" ? `<button class="btn peq" data-mover="${d.id}">${ico("play", 14)}Mover…</button>` : ""} <button class="btn peq" data-eliminar-doc="${d.id}" title="A la Papelera">${ico("trash", 14)}</button></td></tr>
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
  const recargar = async () => { S.expedientes = await api("expedientes"); EXP.e = S.expedientes.find(x => x.id === id) || EXP.e; await cargarExpediente(id, true); };
  $("#exp-finalidad")?.addEventListener("change", async ev => {
    const fin = ev.target.value, n = S.info.variante.finalidades[fin];
    if (!confirm(`¿Cambiar el tipo de financiación de este expediente a «${n}»? La checklist pasará a ser la de «${n}».`)) { ev.target.value = EXP.e.finalidad; return; }
    try { await api("finalidad_expediente", { expediente: id, finalidad: fin }); aviso("Tipo de financiación cambiado"); await recargar(); } catch (er) { aviso(er.message, true); }
  });
  activarOperacion(id, recargar);
  const n = EXP?.neg;
  document.querySelectorAll("[data-nota]").forEach(b => b.addEventListener("click", async () => {
    const tipo = b.dataset.nota, inp = $("#nota-" + tipo);
    try { await api("nota", { expediente: id, tipo, texto: inp.value, banco: tipo === "banco" ? NEG.banco || null : null }); aviso("Nota guardada"); await recargar(); } catch (e) { aviso(e.message, true); }
  }));
  ["banco", "cliente"].forEach(tp => $("#nota-" + tp)?.addEventListener("keydown", ev => { if (ev.key === "Enter") document.querySelector(`[data-nota="${tp}"]`).click(); }));
  document.querySelectorAll("details[data-hist]").forEach(dt => dt.addEventListener("toggle", () => (NEG.historial[dt.dataset.hist] = dt.open)));
  $("#neg-add-banco")?.addEventListener("click", () => { NEG.verBanco = true; pintar(); $("#neg-entidad")?.focus(); });
  $("#neg-banco-no")?.addEventListener("click", () => { NEG.verBanco = false; pintar(); });
  $("#neg-banco-ok")?.addEventListener("click", async () => {
    try { const r = await api("banco", { expediente: id, entidad: $("#neg-entidad").value }); NEG.verBanco = false; NEG.banco = r.id; await recargar(); } catch (e) { aviso(e.message, true); }
  });
  document.querySelectorAll("[data-banco]").forEach(b => b.addEventListener("click", () => { NEG.banco = +b.dataset.banco; NEG.contacto = null; pintar(); }));
  $("#neg-estado")?.addEventListener("change", async ev => { await api("banco", { expediente: id, id: NEG.banco, estado: ev.target.value }); await recargar(); });
  $("#neg-add-contacto")?.addEventListener("click", () => { NEG.contacto = {}; pintar(); $("#ct-nombre")?.focus(); });
  document.querySelectorAll("[data-ed-contacto]").forEach(b => b.addEventListener("click", () => {
    NEG.contacto = { ...n.bancos.flatMap(x => x.contactos).find(c => c.id === +b.dataset.edContacto) }; pintar();
  }));
  document.querySelectorAll("[data-quitar-contacto]").forEach(b => b.addEventListener("click", async () => {
    if (!confirm("¿Quitar este contacto?")) return;
    await api("contacto", { quitar: +b.dataset.quitarContacto }); await recargar();
  }));
  $("#ct-cancelar")?.addEventListener("click", () => { NEG.contacto = null; pintar(); });
  $("#ct-guardar")?.addEventListener("click", async () => {
    const c = { ...NEG.contacto }; ["nombre", "cargo", "movil", "telefono", "email", "oficina", "direccion", "notas"].forEach(k => (c[k] = $("#ct-" + k).value));
    try { await api("contacto", { ...c, banco: NEG.banco }); NEG.contacto = null; aviso("Contacto guardado"); await recargar(); } catch (e) { aviso(e.message, true); }
  });
  document.querySelectorAll("[data-ck-tab]").forEach(a => a.addEventListener("click", () => { CK_TAB = a.dataset.ckTab; pintar(); }));
  document.querySelectorAll("[data-marca]").forEach(b => b.addEventListener("click", async () => {
    const actual = (n?.marcas || {})[b.dataset.marca]?.estado;
    await api("marca", { expediente: id, clave: b.dataset.marca, estado: actual === b.dataset.estado ? null : b.dataset.estado }); await recargar();
  }));
  $("#ck-informe")?.addEventListener("click", () => { INFORME = textoInforme(); pintar(); });
  $("#inf-cerrar")?.addEventListener("click", () => { INFORME = null; pintar(); });
  const enviar = async via => {
    const email = $("#inf-mail").value.trim(), tel = $("#inf-tel").value.replace(/\D/g, ""), texto = $("#inf-txt").value, asunto = $("#inf-asunto").value;
    if (via === "correo" && !email && !confirm("No has puesto el correo del cliente. ¿Abrir el mensaje igualmente?")) return;
    if (via === "wa" && !tel) return aviso("Pon el móvil del cliente.", true);
    try { await api("operacion", { expediente: EXP.e.id, datos: { contacto_email: email, contacto_tel: $("#inf-tel").value.trim() } }); } catch {}
    const url = via === "correo" ? `mailto:${encodeURIComponent(email)}?subject=${encodeURIComponent(asunto)}&body=${encodeURIComponent(texto)}`
                                 : `https://wa.me/${tel.length === 9 ? "34" + tel : tel}?text=${encodeURIComponent(texto)}`;
    try { await api("abrir_url", { url }); aviso(via === "correo" ? "Abriendo el correo…" : "Abriendo WhatsApp…"); } catch (e) { aviso(e.message, true); }
  };
  $("#inf-correo")?.addEventListener("click", () => enviar("correo"));
  $("#inf-wa")?.addEventListener("click", () => enviar("wa"));
  $("#inf-copiar")?.addEventListener("click", async () => { const tx = $("#inf-txt"); tx.select(); try { await navigator.clipboard.writeText(tx.value); } catch { document.execCommand("copy"); } aviso("Copiado: pégalo en el correo o el WhatsApp del cliente"); });
  document.querySelectorAll("[data-misma-exp]").forEach(s => s.addEventListener("change", async () => {
    if (!s.value) return;
    const quita = EXP.e.personas.find(x => x.id === +s.dataset.mismaExp), queda = EXP.e.personas.find(x => x.id === +s.value);
    const dniDistinto = quita.dni && queda.dni && quita.dni.toUpperCase() !== queda.dni.toUpperCase();
    if (!confirm(`¿${quita.nombre} ${quita.apellido1} ${quita.apellido2 || ""} es la misma persona que ${queda.nombre} ${queda.apellido1} ${queda.apellido2 || ""}?\n\nSus documentos pasarán a ${queda.nombre} ${queda.apellido1} y se renombrarán; la ficha sobrante desaparece.` + (dniDistinto ? `\n\nOJO: tienen DNI distintos (${quita.dni} y ${queda.dni}). Se quedará ${queda.dni}.` : ""))) { s.value = ""; return; }
    try { await api("arreglo", { accion: "unir_personas", quitar: quita.id, quedar: queda.id, forzar: !!dniDistinto }); aviso("Unidas: es la misma persona"); await recargar(); } catch (e) { aviso(e.message, true); s.value = ""; }
  }));
  document.querySelectorAll("[data-quitar-persona]").forEach(b => b.addEventListener("click", async () => {
    const p = EXP.e.personas.find(x => x.id === +b.dataset.quitarPersona);
    if (!confirm(`¿Quitar a ${p.nombre} ${p.apellido1} (${p.papel}) del expediente «${EXP.e.nombre}»?`)) return;
    try { const r = await api("arreglo", { accion: "quitar_persona", expediente: id, persona: p.id }); aviso("Quitada del expediente" + (r.ficha_borrada ? " y su ficha borrada" : "")); await recargar(); }
    catch (e) { aviso(e.message, true); }
  }));
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
async function cargarExpediente(id, suave) {
  if (!suave) { EXP = null; pintar(); }
  const e = S.expedientes.find(x => x.id === id) || (await api("expedientes")).find(x => x.id === id);
  const [ck, docs, neg, op, datos] = await Promise.all([api("checklist/" + id), api("documentos_expediente/" + id), api("negociacion/" + id), api("operacion/" + id), api("datos_expediente/" + id).catch(() => null)]);
  if (EXP?.e?.id !== id) { Object.assign(NEG, { banco: 0, verBanco: false, contacto: null }); OPV = false; DIALOGO = null; }
  EXP = { e, ck, docs, neg, op, datos }; ARR.unir = false; ARR.mover = null; pintar();
}

// ------------------------------------------------------------------ Avisos, Limbo, Ajustes
let AV = null, TMP = null;
function vistaAvisosCliente() {
  if (!AV) return '<div class="tarjeta vacio">Cargando…</div>';
  const exps = Object.fromEntries(S.expedientes.map(e => [e.id, e]));
  const por = {}; AV.cliente.forEach(a => (por[a.expediente_id] = por[a.expediente_id] || []).push(a));
  return `<div class="cab"><div><small><a href="#expedientes">Expedientes</a></small><h1>Avisos cliente</h1><div class="sub">Lo que falta o ha caducado en cada expediente. Desaparecen solos cuando llega el documento.</div></div></div>
  ${Object.keys(por).length ? Object.entries(por).map(([eid, l]) => `<section class="tarjeta"><div class="neg-cab"><h2><a href="#expediente/${eid}">${esc(exps[eid]?.nombre || "Expediente " + eid)}</a></h2><span class="sub">${l.length} aviso(s)</span></div>
    ${l.map(a => `<div class="dato aviso-cli-fila"><span>${esc(a.mensaje)}</span><span class="aviso-cli-acc"><span class="muted">desde ${fmtF(a.creado)}</span>
      <button type="button" class="btn peq" data-av-exp="${eid}" data-av-msg="${esc(a.mensaje)}" data-av-acc="ignorar" title="No vuelve a salir mientras siga igual">Ignorar</button>
      <select class="peq" data-av-exp="${eid}" data-av-msg="${esc(a.mensaje)}" data-av-acc="posponer" title="Lo esconde y vuelve a salir pasado este tiempo"><option value="">Posponer…</option><option value="1">1 día</option><option value="7">1 semana</option><option value="30">1 mes</option></select></span></div>`).join("")}</section>`).join("") : '<div class="tarjeta vacio">No hay avisos: no falta ni ha caducado nada.</div>'}
  ${(AV.apartados || []).length ? `<details class="tarjeta"><summary>Ignorados y pospuestos (${AV.apartados.length})</summary>
    ${AV.apartados.map(a => `<div class="dato aviso-cli-fila"><span><a href="#expediente/${a.expediente_id}">${esc(exps[a.expediente_id]?.nombre || "Expediente " + a.expediente_id)}</a> · ${esc(a.mensaje)}</span><span class="aviso-cli-acc"><span class="muted">${a.ignorado ? "ignorado" : "pospuesto hasta el " + fmtF(a.pospuesto)}</span>
      <button type="button" class="btn peq" data-av-exp="${a.expediente_id}" data-av-msg="${esc(a.mensaje)}" data-av-acc="mostrar">Volver a mostrar</button></span></div>`).join("")}</details>` : ""}`;
}
function activarAvisosCliente() {
  const enviar = async (el, dias) => {
    try {
      await api("aviso_cliente", { expediente: +el.dataset.avExp, mensaje: el.dataset.avMsg, accion: el.dataset.avAcc, dias });
      [AV, S.estado, S.expedientes] = await Promise.all([api("avisos"), api("estado"), api("expedientes")]); pintar();
    } catch (e) { aviso(e.message, true); }
  };
  document.querySelectorAll("button[data-av-acc]").forEach(b => b.addEventListener("click", () => { b.disabled = true; enviar(b); }));
  document.querySelectorAll("select[data-av-acc]").forEach(s => s.addEventListener("change", () => { if (s.value) enviar(s, +s.value); }));
}
function vistaAvisosSe() {
  if (!AV) return '<div class="tarjeta vacio">Cargando…</div>';
  const nuevos = S.estado.cuentas.avisos_se || 0;
  return `<div class="cab"><div><h1>Avisos del programa</h1><div class="sub">Problemas del motor, de la versión o de los archivos (Avisos Se). La campanita del menú solo aparece cuando hay alguno nuevo.</div></div>
    <div class="acciones">${nuevos ? `<button class="btn pri" id="se-vistos">${ico("check")}Marcar como vistos</button>` : ""}</div></div>
  ${notificacionesHTML()}
  <section class="tarjeta">${AV.se.slice().reverse().map((a, i) => `<div class="dato ${i < nuevos ? "nuevo" : ""}"><span>${esc(a.mensaje)}</span><span class="aviso-se-der">${botonLecturaPobre(a.mensaje)}<span class="muted">${esc(a.fecha.replace("T", " ").slice(0, 16))}</span></span></div>`).join("") || '<span class="sub">Ningún problema.</span>'}</section>`;
}
// 3.1.2 · «Aceptar con este umbral»: el aviso de lectura pobre deja de salir para las páginas que se leen a este % o más
function botonLecturaPobre(msg) {
  const m = /lectura pobre \((\d+) %\)/.exec(msg || "");
  if (!m) return "";
  const pct = +m[1], umbral = Math.round((S.ajustes?.ocr?.lectura_pobre ?? .6) * 100);
  if (pct < 5) return '<span class="muted" title="Una página leída casi al 0 % suele estar en blanco o muy mal escaneada">vuelve a escanearla</span>';
  if (pct >= umbral) return `<span class="pill p-ok" title="Desde ahora no se avisa de lecturas de ${umbral} % o más">aceptado</span>`;
  return `<button type="button" class="btn peq" data-acepta-lectura="${pct}" title="Las páginas que se lean al ${pct} % o más dejarán de dar este aviso (ahora se avisa por debajo del ${umbral} %). Se puede cambiar en Ajustes › OCR.">${ico("check", 14)} Aceptar con este umbral (${pct} %)</button>`;
}
function vistaLimbo() {
  const docs = S.estado.lotes.flatMap(l => l.documentos).filter(d => d.estado === "limbo");
  return `<div class="cab"><div><small>Motor de proceso › Limbo</small><h1>Limbo</h1><div class="sub">Documentos sin expediente todavía, guardados en <code>${esc(S.info.carpetas.documentos)}\\_Limbo\\</code>.</div></div></div>
  ${pestanasMotor("limbo")}
  ${docs.length ? `<section class="tarjeta sinp"><table class="tabla"><thead><tr><th>Archivo recibido</th><th>Tipo</th><th>Nombre en el Limbo</th><th></th></tr></thead><tbody>${docs.map(d => `<tr><td>${esc(d.archivo)}</td><td>${esc(nombreTipo(d.tipo, d.modelo))}</td><td class="mono">${esc(d.nombre_final)}</td>
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
  <section class="tarjeta ia-tarjeta-aj"><div class="cab"><div><h2>${ico("ia")} Controlador IA <span class="pill p-ia">3.0</span></h2><span class="sub">Resuelve solo, con la API de Anthropic, lo que el programa no sabe, sin enviar datos personales. Viene apagado.</span></div>
    <a class="btn" href="#ia">Abrir ajustes de la IA</a></div></section>
  ${tarjetaContexto()}
  <section class="tarjeta"><h2>Carpetas</h2>
    ${[["entrada", "Entrada (lo que llega)"], ["documentos", "SeDocumentos (los ordenados)"], ["originales", "Doc_original (originales sin tocar)"], ["papelera", "Papelera"]]
      .map(([k, l]) => `<div class="fila-carpeta"><label for="cp-${k}">${l}</label><input id="cp-${k}" data-carpeta="${k}" value="${esc(c[k])}"><button class="btn peq" data-abrir="${esc(c[k])}">Abrir</button></div>`).join("")}
    <div class="dato"><span>Datos (base de datos y ajustes)</span><span class="mono">${esc(c.datos)}</span></div>
    <div class="acciones"><button class="btn pri" id="cp-ok">${ico("check")}Guardar carpetas</button></div>
    <span class="sub">Lo que ya está guardado no se mueve: las carpetas nuevas se usan desde ahora. Si cambias SeDocumentos o Doc_original, mueve antes las carpetas de los expedientes con el Explorador de Windows.</span></section>
  <section class="tarjeta"><h2>Reconocimiento (OCR)</h2>
    <div class="campos-inline"><div class="campo"><label for="oc-rev">Pedir revisión por debajo de (%)</label><input id="oc-rev" type="number" min="5" max="99" value="${Math.round((S.ajustes?.umbrales?.revisar || .75) * 100)}"></div>
      <div class="campo"><label for="oc-no">«No reconocido» por debajo de (%)</label><input id="oc-no" type="number" min="5" max="99" value="${Math.round((S.ajustes?.umbrales?.no_reconocido || .4) * 100)}"></div>
      <div class="campo"><label for="oc-lp">Avisar de «lectura pobre» por debajo de (%)</label><input id="oc-lp" type="number" min="5" max="95" value="${Math.round((S.ajustes?.ocr?.lectura_pobre ?? .6) * 100)}"></div></div>
    <div class="chips">${[["spa", "Castellano"], ["cat", "Valenciano / catalán"], ["eus", "Euskera"], ["glg", "Gallego"], ["eng", "Inglés"]]
      .map(([k, n]) => `<label class="check mini"><input type="checkbox" data-idioma="${k}" ${(S.ajustes?.ocr?.idiomas || []).includes(k) ? "checked" : ""}><span>${n}</span></label>`).join("")}</div>
    <span class="sub">Idiomas que usa el OCR en las fotos y escaneos. Menos idiomas = un poco más rápido.</span>
    <div class="acciones"><button class="btn pri" id="oc-ok">${ico("check")}Guardar</button><a class="btn" href="#reglas">Ver reglas de nombres y tipos de documento</a></div></section>
  <section class="tarjeta"><h2>Apariencia</h2>
    <div class="fila-carpeta"><label for="ap-t">Tamaño del texto</label><input id="ap-t" type="range" min="80" max="140" step="5" value="${S.ajustes?.apariencia?.tamano || 100}"><b id="ap-v">${S.ajustes?.apariencia?.tamano || 100} %</b></div></section>
  <section class="tarjeta"><h2>Copia de seguridad</h2><span class="sub">Guarda en un zip la base de datos, las finalidades y los ajustes (no los documentos, que ya están en sus carpetas) en <code>${esc(c.datos)}\\Copias</code>.</span>
    <div class="acciones"><button class="btn" id="copia">Hacer copia ahora</button></div></section>
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
    <div class="sub reglas-correo"><b>Reglas al recoger</b> · espera 1 minuto desde que llega cada correo · remitente conocido (en «Correos» de una ficha) con adjuntos: entra; sin adjuntos: aviso ·
      desconocido sin adjuntos o con fotos que no se reconocen: etiqueta «No_Apto_SeFina» · con Word/Excel y sin PDF: te pregunta en la campanita sin abrirlos ·
      con algún PDF: entra (si solo trae PDF y nada se relaciona con lo registrado, vuelve a la bandeja de entrada) · lo que entra se mueve a la carpeta «procesadosMMAA» del buzón. Nunca se borra nada.</div>
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
  document.querySelectorAll("[data-abrir]").forEach(b => b.addEventListener("click", () => abrirRuta(b.dataset.abrir)));
  $("#cp-ok")?.addEventListener("click", async () => {
    const carpetas = {}; document.querySelectorAll("[data-carpeta]").forEach(i => (carpetas[i.dataset.carpeta] = i.value.trim()));
    try { S.ajustes = await api("ajustes", { carpetas }); S.info = await api("info"); aviso("Carpetas guardadas"); pintar(); } catch (e) { aviso(e.message, true); }
  });
  $("#oc-ok")?.addEventListener("click", async () => {
    const idiomas = [...document.querySelectorAll("[data-idioma]:checked")].map(i => i.dataset.idioma);
    try { S.ajustes = await api("ajustes", { umbrales: { revisar: +$("#oc-rev").value / 100, no_reconocido: +$("#oc-no").value / 100 }, ocr: { idiomas, lectura_pobre: +$("#oc-lp").value / 100 } }); aviso("Ajustes del OCR guardados"); } catch (e) { aviso(e.message, true); }
  });
  $("#ap-t")?.addEventListener("input", e => { $("#ap-v").textContent = e.target.value + " %"; });
  $("#ctx-guardar")?.addEventListener("click", async () => {
    try {
      S.ajustes = await api("ajustes", { contexto: { activo: $("#ctx-act").checked, guardar: $("#ctx-g").checked, titular: +$("#ctx-t").value, cotitular: +$("#ctx-c").value, minimo_docs: +$("#ctx-m").value } });
      aviso("Ajustes del contexto del lote guardados");
    } catch (e) { aviso(e.message, true); }
  });
  $("#ap-t")?.addEventListener("change", async e => { S.ajustes = await api("ajustes", { apariencia: { tamano: +e.target.value } }); aplicarApariencia(); });
  $("#copia")?.addEventListener("click", async () => { try { const r = await api("copia", {}); aviso("Copia hecha: " + r.ruta.split(/[\\/]/).pop()); abrirRuta(r.ruta, true); } catch (e) { aviso(e.message, true); } });
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
    expedientes: [vistaExpedientes, activarExpedientes],
    expediente: [vistaExpediente, () => activarExpediente(+id)],
    documentacion: [vistaDocumentacion, () => activarExpediente(+id)],
    unir: [vistaUnir, activarUnir], avisos: [vistaAvisosSe, activarNotificaciones], avisos_se: [vistaAvisosSe, () => { activarNotificaciones(); activarLecturaPobre(); $("#se-vistos")?.addEventListener("click", async () => { await api("avisos_se_vistos", {}); await refrescar(true); aviso("Avisos marcados como vistos"); }); }],
    avisos_cliente: [vistaAvisosCliente, activarAvisosCliente], limbo: [vistaLimbo, activarLimbo], ajustes: [vistaAjustes, activarAjustes],
    cuarentena: [vistaCuarentena, activarCuarentena], personas: [vistaPersonas, activarPersonas], persona: [() => vistaPersona(+id), () => activarPersona(+id)],
    papelera: [vistaPapelera, activarPapelera], estadisticas: [vistaEstadisticas, () => {}], buscar: [vistaBuscar, activarBuscar], reglas: [vistaReglas, activarReglas],
    bienvenida: [vistaBienvenida, activarBienvenida], separar: [() => vistaSeparar(+id), () => activarSeparar(+id)],
    ia: [vistaIA, activarIA], ia_informe: [vistaInformeIA, activarInformeIA], ia_envio: [vistaEnvioIA, () => {}], ia_mirar: [vistaMirarIA, activarMirarIA] };
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
  if (r === "expediente" || r === "documentacion") return cargarExpediente(+id);
  if (r === "unir") UNIR = (id || "").split(",").filter(Boolean).map(Number);
  if (r === "revision" || r === "unir") S.prop = await api("propuestas_union");
  if (["avisos", "avisos_se", "avisos_cliente"].includes(r)) AV = await api("avisos");
  if (r === "cuarentena") CUA = await api("cuarentena");
  if (r === "personas" || r === "persona") PERS = await api("personas");
  if (r === "papelera") PAP = await api("papelera");
  if (r === "estadisticas") EST = await api("estadisticas");
  if (r === "reglas" && !REG) REG = await api("reglas");
  if (r === "ia") IAP = await api("ia");
  if (r === "ia_informe") INF = id ? await api("ia/informe/" + id) : null;
  if (r === "ia_envio") ENV = await api("ia/consulta/" + id);
  if (r === "ia_mirar") MIRAR = await api("ia/por_revisar");
  if (r === "separar") { SEP = { id: +id, doc: await api("documento/" + id), cortes: new Set() }; }
  if (r === "ajustes") { [TMP, FIN, REP, CORREO, S.ajustes] = await Promise.all([api("temporales"), api("finalidades"), api("personas_repetidas"), api("correo"), api("ajustes")]); CORREO.form = { ...CORREO.ajustes, clave: "" }; }
  pintar();
}
async function refrescar(repintar) {
  const antes = JSON.stringify(S.estado);
  [S.estado, S.expedientes] = await Promise.all([api("estado"), api("expedientes")]);
  const cambio = antes !== JSON.stringify(S.estado);
  const r = S.ruta.split("/")[0] || "motor";
  if (cambio && r === "ia_informe" && !repintar) return ir();
  if (repintar || (cambio && ["motor", "limbo", "cuarentena", ""].includes(r))) pintar();
  else if (cambio) { lateral(); if (r === "revision" && !S.editando && !S.doc) ir(); }
}
function aplicarApariencia() { document.body.style.zoom = ((S.ajustes?.apariencia?.tamano || 100) / 100).toString(); }
async function inicio() {
  S.info = await api("info");
  const c = S.info.variante.colores || {}, st = document.documentElement.style;
  [["--marco", c.marco], ["--accent", c.acento], ["--lateral", c.lateral], ["--lateralActivo", c.lateral_activo], ["--lateralBorde", c.lateral_borde], ["--lateralTenue", c.lateral_tenue]]
    .forEach(([k, v]) => v && st.setProperty(k, v));
  document.title = `${S.info.variante.nombre} · con Sentiende`;
  [S.estado, S.expedientes, S.ajustes] = await Promise.all([api("estado"), api("expedientes"), api("ajustes")]);
  aplicarApariencia();
  if (!S.ajustes.bienvenida_vista && !S.expedientes.length && !location.hash) location.hash = "bienvenida";
  window.addEventListener("hashchange", ir);
  await ir();
  setInterval(() => refrescar(false).catch(() => {}), 1500);
}
inicio().catch(e => { document.body.innerHTML = `<p style="padding:30px">No se ha podido abrir: ${esc(e.message)}</p>`; });

// ================================================================== pantallas de gestión (diseño 15–33)
const eur = v => v === null || v === undefined || v === "" || isNaN(+v) ? "—" : (+v).toLocaleString("es-ES", { maximumFractionDigits: 2 }) + " €";
const PRIO = { "": "Sin prioridad", baja: "Prioridad baja", media: "Prioridad media", alta: "Prioridad alta" };
const SIG_PRIO = { "": "baja", baja: "media", media: "alta", alta: "" };
async function abrirRuta(ruta, seleccionar) { try { await api("abrir", { ruta, seleccionar: !!seleccionar }); } catch (e) { aviso(e.message, true); } }

// ---------------- correo por revisar (remitentes nuevos, M-65)
let CUA = null;
function vistaCuarentena() {
  return `<div class="cab"><div><h1>Correo por revisar</h1><div class="sub">Adjuntos de remitentes nuevos. No entran en el motor hasta que los aceptas; si aceptas al remitente, sus próximos correos entran solos.</div></div></div>
  ${pestanasMotor("cuarentena")}
  ${!CUA ? '<div class="tarjeta vacio">Cargando…</div>' : !CUA.length ? '<div class="tarjeta vacio">No hay correos por revisar.</div>' : CUA.map(c => `<section class="tarjeta cua">
    <div class="neg-cab"><h2>${ico("mail", 17)} ${esc(c.asunto)}</h2><span class="sub">${esc(c.remitente)} · ${fmtF(c.fecha)} ${c.fecha.slice(11, 16)}</span></div>
    <div class="chips">${c.archivos.map(a => `<span class="chip peq">${esc(a)}</span>`).join("")}</div>
    <div class="acciones"><button class="btn pri" data-cua="${c.id}" data-acc="aceptar">${ico("check")}Aceptar y confiar en ${esc(c.remitente)}</button>
      <button class="btn" data-cua="${c.id}" data-acc="aceptar_una">Aceptar solo este correo</button>
      <button class="btn" data-cua="${c.id}" data-acc="rechazar">Rechazar (a la Papelera)</button>
      <button class="btn peligro" data-cua="${c.id}" data-acc="bloquear">Bloquear remitente</button>
      <button class="btn" data-abrir="${esc(c.carpeta)}">Ver los archivos</button></div></section>`).join("")}`;
}
function activarCuarentena() {
  document.querySelectorAll("[data-cua]").forEach(b => b.addEventListener("click", async () => {
    try { const r = await api("cuarentena", { id: +b.dataset.cua, accion: b.dataset.acc }); aviso(r.aceptados ? `${r.aceptados} adjunto(s) al motor` : "Hecho"); CUA = await api("cuarentena"); refrescar(true); }
    catch (e) { aviso(e.message, true); }
  }));
  document.querySelectorAll("[data-abrir]").forEach(b => b.addEventListener("click", () => abrirRuta(b.dataset.abrir)));
}

// ---------------- lista de expedientes con pestañas, favorito y prioridad (21, 26)
let EXP_TAB = "curso", NUEVO_EXP = null;
function vistaExpedientes() {
  const v = S.info.variante;
  const grupos = { curso: e => e.estado === "abierto", firmados: e => e.estado === "firmado", cerrados: e => e.estado === "cerrado", todos: () => true };
  const nombres = { curso: "En curso", firmados: "Firmados", cerrados: "Cerrados sin operación", todos: "Todos" };
  const peso = e => (e.marcas.prioridad === "alta" ? 0 : e.marcas.prioridad === "media" ? 1 : e.marcas.prioridad === "baja" ? 2 : 4) - (e.marcas.favorito ? 0.5 : 0);
  const lista = S.expedientes.filter(grupos[EXP_TAB]).sort((a, b) => peso(a) - peso(b) || b.id - a.id);
  return `<div class="cab"><div><h1>Expedientes</h1><div class="sub">Se crean desde el Centro de revisión al emparejar el primer documento, o aquí a mano. Primero los de campanita, luego los favoritos.</div></div>
    <div class="acciones"><a class="btn avisos-cli" href="#avisos_cliente">${ico("bell", 16)}Avisos cliente${S.estado.cuentas.avisos_cliente ? `<span class="num">${S.estado.cuentas.avisos_cliente}</span>` : ""}</a><button class="btn pri" id="exp-nuevo">＋ Nuevo expediente</button></div></div>
  ${NUEVO_EXP ? formNuevoExp() : ""}
  <nav class="pestanas">${Object.entries(nombres).map(([k, n]) => `<a href="javascript:void 0" data-exp-tab="${k}" ${k === EXP_TAB ? 'aria-current="page"' : ""}>${n}<span class="num">${S.expedientes.filter(grupos[k]).length}</span></a>`).join("")}</nav>
  ${lista.length ? `<section class="tarjeta sinp"><table class="tabla lista-exp"><thead><tr><th></th><th>Expediente</th><th>Estado</th><th>Personas</th><th>Checklist</th><th>Carpeta</th><th title="Avisos de cliente">Avisos</th></tr></thead><tbody>
  ${lista.map(e => `<tr class="clic prio-${e.marcas.prioridad || "no"} ${e.estado === "unido" ? "apagada" : ""}" data-exp="${e.id}">
    <td class="marcas-exp"><button type="button" class="marca-b ${e.marcas.favorito ? "on" : ""}" data-fav="${e.id}" title="Favorito">${e.marcas.favorito ? "★" : "☆"}</button><button type="button" class="marca-b ${e.marcas.prioridad ? "on" : ""}" data-prio="${e.id}" title="${PRIO[e.marcas.prioridad]} (pulsa para cambiar)">${ico("bell", 16)}</button></td>
    <td><b>${esc(e.nombre)}</b><div class="sub">${esc(v.finalidades[e.finalidad] || e.finalidad)}</div></td><td>${pill(e.etiqueta, e.estado === "firmado" ? "ok" : e.estado === "cerrado" ? "bad" : "todo")}</td>
    <td>${e.personas.map(p => esc(`${p.nombre} ${p.apellido1}`) + ` <span class="muted">(${esc(p.papel)})</span>`).join("<br>")}</td>
    <td>${e.checklist ? `${e.checklist.recibidos} de ${e.checklist.total}` : "—"}</td><td class="mono">${esc(e.carpeta)}</td>
    <td class="centro">${e.avisos ? `<a class="circ-avisos" href="#avisos_cliente" title="${e.avisos} aviso(s) de cliente">${e.avisos}</a>` : ""}</td></tr>`).join("")}</tbody></table></section>`
    : `<div class="tarjeta vacio">No hay expedientes ${EXP_TAB === "todos" ? "todavía" : "en «" + nombres[EXP_TAB] + "»"}.</div>`}`;
}
function formNuevoExp() {
  const f = NUEVO_EXP, fin = S.info.finalidades_visibles || Object.keys(S.info.variante.finalidades);
  const fila = (p, i) => `<div class="campos-inline">${[["nombre", "Nombre"], ["apellido1", "Primer apellido"], ["apellido2", "Segundo apellido"], ["dni", "DNI / NIE"], ["correo", "Correo (opcional)"]]
    .map(([k, l]) => `<div class="campo"><label>${l}</label><input data-ne="${i}" data-k="${k}" value="${esc(p[k] || "")}"></div>`).join("")}
    ${i ? `<div class="campo"><label>Papel</label><select data-ne="${i}" data-k="papel">${["Cotitular", "Avalista", "Beneficiario", "Cónyuge o pareja no titular", "Administrador", "Titular anterior"].map(x => `<option ${p.papel === x ? "selected" : ""}>${x}</option>`).join("")}</select></div>` : '<div class="campo"><label>Papel</label><input value="Titular" disabled></div>'}</div>`;
  return `<section class="tarjeta"><h2>Nuevo expediente (datos a mano)</h2><span class="sub">Lo que escribas aquí será la referencia segura: si después llegan documentos con un nombre o DNI muy parecido, se usarán estos datos y te avisará en la campanita para confirmarlo.</span>
    <div class="fin-pills">${fin.map(k => `<button type="button" class="fin-pill ${f.finalidad === k ? "sel" : ""}" data-ne-fin="${k}">${esc(S.info.variante.finalidades[k])}</button>`).join("")}</div>
    ${f.personas.map(fila).join("")}
    <div class="acciones"><button class="btn" id="ne-mas">＋ Otra persona</button><button class="btn pri" id="ne-ok">${ico("check")}Crear expediente</button><button class="btn" id="ne-no">Cancelar</button></div></section>`;
}
function activarExpedientes() {
  document.querySelectorAll("[data-exp]").forEach(tr => tr.addEventListener("click", ev => { if (!ev.target.closest("button, a")) location.hash = "expediente/" + tr.dataset.exp; }));
  document.querySelectorAll("[data-exp-tab]").forEach(a => a.addEventListener("click", () => { EXP_TAB = a.dataset.expTab; pintar(); }));
  document.querySelectorAll("[data-fav]").forEach(b => b.addEventListener("click", async () => { const e = S.expedientes.find(x => x.id === +b.dataset.fav); await api("marcar_expediente", { expediente: e.id, favorito: !e.marcas.favorito }); refrescar(true); }));
  document.querySelectorAll("[data-prio]").forEach(b => b.addEventListener("click", async () => { const e = S.expedientes.find(x => x.id === +b.dataset.prio); const p = SIG_PRIO[e.marcas.prioridad || ""]; await api("marcar_expediente", { expediente: e.id, prioridad: p }); aviso(PRIO[p]); refrescar(true); }));
  $("#exp-nuevo")?.addEventListener("click", () => { NUEVO_EXP = { finalidad: (S.info.finalidades_visibles || [])[0], personas: [{}] }; pintar(); });
  $("#ne-no")?.addEventListener("click", () => { NUEVO_EXP = null; pintar(); });
  document.querySelectorAll("[data-ne]").forEach(i => i.addEventListener("input", () => (NUEVO_EXP.personas[+i.dataset.ne][i.dataset.k] = i.value)));
  document.querySelectorAll("select[data-ne]").forEach(i => i.addEventListener("change", () => (NUEVO_EXP.personas[+i.dataset.ne].papel = i.value)));
  document.querySelectorAll("[data-ne-fin]").forEach(b => b.addEventListener("click", () => { NUEVO_EXP.finalidad = b.dataset.neFin; pintar(); }));
  $("#ne-mas")?.addEventListener("click", () => { NUEVO_EXP.personas.push({ papel: "Cotitular" }); pintar(); });
  $("#ne-ok")?.addEventListener("click", async () => {
    const [p0, ...otras] = NUEVO_EXP.personas;
    if (!p0.nombre || !p0.apellido1) return aviso("Falta el nombre o el primer apellido del titular.", true);
    try { const r = await api("expediente_manual", { persona: p0, otras, finalidad: NUEVO_EXP.finalidad }); NUEVO_EXP = null; S.expedientes = await api("expedientes"); location.hash = "expediente/" + r.expediente; }
    catch (e) { aviso(e.message, true); }
  });
}

// ---------------- estado y datos de la operación (23, 33)
let OPV = false, DIALOGO = null;
function panelOperacion(e) {
  const op = EXP.op, d = op.datos, cerrado = ["firmado", "cerrado"].includes(op.estado);
  const campo = (k, l, tipo = "text") => `<div class="campo"><label for="op-${k}">${l}</label><input id="op-${k}" type="${tipo}" data-op="${k}" value="${esc(d[k] || "")}"></div>`;
  return `<section class="tarjeta operacion"><div class="neg-cab"><h2>Estado y datos de la operación</h2><button class="btn peq" id="op-cerrar-panel">Cerrar</button></div>
    <div class="pasos-estado">${Object.entries(op.fases).map(([k, n]) => `<button type="button" class="paso-e ${!cerrado && d.fase === k ? "sel" : ""}" data-fase="${k}" ${cerrado ? "disabled" : ""}>${n}</button>`).join('<span class="flecha">›</span>')}
      <span class="flecha">›</span><button type="button" class="paso-e ${op.estado === "firmado" ? "sel ok" : ""}" id="op-firmar">Firmado</button>
      <button type="button" class="paso-e ${op.estado === "cerrado" ? "sel bad" : ""}" id="op-cerrar">Cerrar sin operación</button>
      ${cerrado ? '<button class="btn peq" id="op-reabrir">Reabrir</button>' : ""}</div>
    ${op.estado === "cerrado" ? `<div class="ck-avisos"><b>Cerrado sin operación</b><span>${esc(d.motivo_cierre || "")} · ${fmtF(d.fecha_cierre)}${d.entidad_cierre ? " · " + esc(d.entidad_cierre) : ""}${d.nota_cierre ? " · " + esc(d.nota_cierre) : ""}</span></div>` : ""}
    <div class="op-campos">${campo("importe_solicitado", "Importe solicitado (€)", "number")}${campo("importe_concedido", "Importe concedido (€)", "number")}
      <div class="campo"><label for="op-entidad">Entidad</label><input id="op-entidad" data-op="entidad" list="op-bancos" value="${esc(d.entidad || "")}"><datalist id="op-bancos">${[...new Set([...(EXP.neg?.bancos || []).map(b => b.entidad), ...S.info.bancos])].map(b => `<option value="${esc(b)}">`).join("")}</datalist></div>
      ${campo("fecha_envio", "Enviado al banco", "date")}${campo("fecha_aprobacion", "Aprobado", "date")}${campo("fecha_firma", "Firma", "date")}</div>
    <h3>Honorarios</h3>
    <div class="op-campos"><div class="campo"><label for="op-ht">Tipo</label><select id="op-ht" data-op="honorarios_tipo"><option value="porcentaje" ${d.honorarios_tipo !== "importe" ? "selected" : ""}>Porcentaje del importe</option><option value="importe" ${d.honorarios_tipo === "importe" ? "selected" : ""}>Importe fijo</option></select></div>
      ${campo("honorarios_valor", d.honorarios_tipo === "importe" ? "Importe (€)" : "Porcentaje (%)", "number")}
      <div class="campo"><label>Honorarios</label><input disabled value="${eur(d.honorarios_importe)}"></div>
      ${campo("factura_num", "N.º de factura")}${campo("factura_fecha", "Fecha de factura", "date")}${campo("fecha_cobro", "Fecha de cobro", "date")}</div>
    ${op.estado === "firmado" && d.honorarios_importe && !d.fecha_cobro ? '<span class="warn-txt">Honorarios pendientes de cobro.</span>' : ""}
    <div class="acciones"><button class="btn pri" id="op-guardar">${ico("check")}Guardar datos</button></div>
    ${op.historial.length ? `<details class="historial"><summary>Historial · ${op.historial.length}</summary>${op.historial.map(h => `<div class="nota"><span class="nota-f">${fmtF(h.fecha)} · ${h.fecha.slice(11, 16)}</span><span>${esc(h.nota)}</span></div>`).join("")}</details>` : ""}
  </section>`;
}
function dialogoEstado() {
  if (!DIALOGO) return "";
  const d = EXP.op.datos, bancos = [...new Set([...(EXP.neg?.bancos || []).map(b => b.entidad), ...S.info.bancos])];
  const lista = `<datalist id="dl-bancos">${bancos.map(b => `<option value="${esc(b)}">`).join("")}</datalist>`;
  if (DIALOGO === "firmar") return `<div class="zoom informe"><div class="tarjeta"><h2>Marcar como firmado</h2>
    <div class="op-campos"><div class="campo"><label>Importe concedido (€)</label><input id="df-imp" type="number" value="${esc(d.importe_concedido || d.importe_solicitado || "")}"></div>
    <div class="campo"><label>Entidad</label><input id="df-ent" list="dl-bancos" value="${esc(d.entidad || "")}">${lista}</div>
    <div class="campo"><label>Fecha de firma</label><input id="df-fecha" type="date" value="${new Date().toISOString().slice(0, 10)}"></div>
    <div class="campo"><label>Honorarios</label><select id="df-ht"><option value="porcentaje">Porcentaje</option><option value="importe" ${d.honorarios_tipo === "importe" ? "selected" : ""}>Importe fijo</option></select></div>
    <div class="campo"><label>Valor</label><input id="df-hv" type="number" value="${esc(d.honorarios_valor || "")}"></div></div>
    <span class="sub">Los honorarios quedan «pendientes de cobro» hasta que pongas la fecha de cobro.</span>
    <div class="acciones"><button class="btn pri" id="df-ok">${ico("check")}Marcar como firmado</button><button class="btn" id="dlg-no">Cancelar</button></div></div></div>`;
  return `<div class="zoom informe"><div class="tarjeta"><h2>Cerrar sin operación</h2>
    <div class="op-campos"><div class="campo"><label>Motivo</label><select id="dc-mot">${EXP.op.motivos.map(m => `<option>${m}</option>`).join("")}</select></div>
    <div class="campo"><label>Fecha</label><input id="dc-fecha" type="date" value="${new Date().toISOString().slice(0, 10)}"></div>
    <div class="campo"><label>Entidad (si aplica)</label><input id="dc-ent" list="dl-bancos">${lista}</div></div>
    <div class="campo"><label>Nota</label><input id="dc-nota"></div>
    <div class="acciones"><button class="btn peligro" id="dc-ok">Cerrar sin operación</button><button class="btn" id="dlg-no">Cancelar</button></div></div></div>`;
}
function activarOperacion(id, recargar) {
  $("#op-estado")?.addEventListener("click", () => { OPV = !OPV; pintar(); });
  $("#op-cerrar-panel")?.addEventListener("click", () => { OPV = false; pintar(); });
  const cambiar = async (estado, extra) => { try { EXP.op = await api("estado_expediente", { expediente: id, estado, extra }); DIALOGO = null; aviso(EXP.op.etiqueta); await recargar(); } catch (e) { aviso(e.message, true); } };
  document.querySelectorAll("[data-fase]").forEach(b => b.addEventListener("click", () => cambiar(b.dataset.fase)));
  $("#op-firmar")?.addEventListener("click", () => { DIALOGO = "firmar"; pintar(); });
  $("#op-cerrar")?.addEventListener("click", () => { DIALOGO = "cerrar"; pintar(); });
  $("#op-reabrir")?.addEventListener("click", () => confirm("¿Reabrir el expediente?") && cambiar("reabrir"));
  $("#dlg-no")?.addEventListener("click", () => { DIALOGO = null; pintar(); });
  $("#df-ok")?.addEventListener("click", () => cambiar("firmado", { importe_concedido: $("#df-imp").value, entidad: $("#df-ent").value, fecha_firma: $("#df-fecha").value, honorarios_tipo: $("#df-ht").value, honorarios_valor: $("#df-hv").value }));
  $("#dc-ok")?.addEventListener("click", () => cambiar("cerrado", { motivo: $("#dc-mot").value, fecha: $("#dc-fecha").value, entidad: $("#dc-ent").value, nota: $("#dc-nota").value }));
  $("#op-ht")?.addEventListener("change", () => { EXP.op.datos.honorarios_tipo = $("#op-ht").value; });
  $("#op-guardar")?.addEventListener("click", async () => {
    const datos = {}; document.querySelectorAll("[data-op]").forEach(i => (datos[i.dataset.op] = i.value));
    try { EXP.op = await api("operacion", { expediente: id, datos }); aviso("Datos de la operación guardados"); await recargar(); } catch (e) { aviso(e.message, true); }
  });
  $("#exp-fav")?.addEventListener("click", async () => { await api("marcar_expediente", { expediente: id, favorito: !EXP.e.marcas?.favorito }); await recargar(); });
  $("#exp-prio")?.addEventListener("click", async () => { const p = SIG_PRIO[EXP.e.marcas?.prioridad || ""]; await api("marcar_expediente", { expediente: id, prioridad: p }); aviso(PRIO[p]); await recargar(); });
  $("#exp-carpeta")?.addEventListener("click", () => abrirRuta(S.info.carpetas.documentos + (S.info.carpetas.documentos.includes("\\") ? "\\" : "/") + EXP.e.carpeta));
  $("#exp-exportar")?.addEventListener("click", async () => {
    const hayPriv = (EXP.docs || []).some(d => d.privado);
    const privados = hayPriv && confirm("Este expediente tiene documentos PRIVADOS (No compartir).\n\nAceptar: incluirlos en el zip.\nCancelar: dejarlos fuera.");
    try { const r = await api("exportar_expediente", { expediente: id, privados }); aviso(`Exportado: ${r.archivos} archivo(s)${r.privados_fuera ? ` (${r.privados_fuera} privados fuera)` : ""}`); abrirRuta(r.ruta, true); } catch (e) { aviso(e.message, true); }
  });
  $("#exp-eliminar")?.addEventListener("click", async () => {
    if (!confirm(`¿Enviar el expediente «${EXP.e.nombre}» a la Papelera?\n\nSe mueven sus carpetas de documentos y originales a la Papelera, con un archivo para recuperarlo. Se puede restaurar.`)) return;
    try { await api("eliminar", { expediente: id }); aviso("Expediente en la Papelera"); S.expedientes = await api("expedientes"); location.hash = "expedientes"; } catch (e) { aviso(e.message, true); }
  });
  document.querySelectorAll("[data-eliminar-doc]").forEach(b => b.addEventListener("click", async () => {
    if (!confirm("¿Enviar este documento (y su original) a la Papelera? Se puede restaurar.")) return;
    try { await api("eliminar", { documento: +b.dataset.eliminarDoc }); aviso("Documento en la Papelera"); await recargar(); } catch (e) { aviso(e.message, true); }
  }));
  document.querySelectorAll("[data-abrir-doc]").forEach(b => b.addEventListener("click", () => abrirRuta(b.dataset.abrirDoc, true)));
  document.querySelectorAll("[data-papel]").forEach(s => s.addEventListener("change", async () => { await api("papel", { expediente: id, persona: +s.dataset.papel, papel: s.value }); aviso("Papel cambiado"); await recargar(); }));
}

// ---------------- personas (25) y ficha de persona (15)
let PERS = null, FILTRO_P = "";
function vistaPersonas() {
  if (!PERS) return '<div class="tarjeta vacio">Cargando…</div>';
  const f = normaliza(FILTRO_P), lista = PERS.filter(p => !f || normaliza(`${p.nombre} ${p.apellido1} ${p.apellido2} ${p.dni || ""}`).includes(f));
  return `<div class="cab"><div><h1>Personas</h1><div class="sub">Todas las personas fichadas, con sus expedientes y papeles. Una persona puede estar en varios expedientes.</div></div>
    <div class="acciones"><button class="btn" id="p-exp-manual">${ico("folder", 16)}Expediente manual</button><button class="btn pri" id="p-nueva">＋ Nueva persona</button></div></div>
  ${NUEVA_P ? `<section class="tarjeta"><h2>Nueva persona (datos a mano)</h2><span class="sub">Queda como referencia segura: si llegan documentos con un nombre o DNI muy parecido, se usarán estos datos y te avisará en la campanita. Para abrirle un expediente a la vez, usa «Expediente manual».</span>
    <div class="campos-inline">${[["nombre", "Nombre"], ["apellido1", "Primer apellido"], ["apellido2", "Segundo apellido"], ["dni", "DNI / NIE"], ["correo", "Correo (opcional)"]].map(([k, l]) => `<div class="campo"><label>${l}</label><input data-np="${k}" value="${esc(NUEVA_P[k] || "")}"></div>`).join("")}</div>
    <div class="acciones"><button class="btn pri" id="np-ok">${ico("check")}Guardar persona</button><button class="btn" id="np-no">Cancelar</button></div></section>` : ""}
  <div class="neg-nueva"><input id="p-filtro" placeholder="Buscar por nombre o DNI…" value="${esc(FILTRO_P)}"></div>
  <section class="tarjeta sinp"><table class="tabla"><thead><tr><th>Persona</th><th>DNI / NIE</th><th>Expedientes</th><th>Documentos</th></tr></thead><tbody>
  ${lista.map(p => `<tr class="clic" data-persona-ir="${p.id}"><td><b>${esc(`${p.nombre} ${p.apellido1} ${p.apellido2 || ""}`)}</b></td><td class="mono">${esc(p.dni || "sin DNI")}</td>
    <td>${p.expedientes.map(e => `${esc(e.nombre)} <span class="muted">(${esc(e.papel)})</span>`).join("<br>") || '<span class="muted">Ninguno</span>'}</td><td>${p.documentos}</td></tr>`).join("") || '<tr><td colspan="4" class="muted">Nadie coincide.</td></tr>'}
  </tbody></table></section>`;
}
function vistaPersona(id) {
  const p = (PERS || []).find(x => x.id === id);
  if (!p) return '<div class="tarjeta vacio">Cargando…</div>';
  return `<div class="cab"><div><small><a href="#personas">Personas</a></small><h1>${esc(`${p.nombre} ${p.apellido1} ${p.apellido2 || ""}`)}</h1><div class="sub">Ficha de la persona. Si cambias el nombre o el DNI, sus documentos se renombran con el código nuevo.</div></div></div>
  <section class="tarjeta"><h2>Datos</h2><div class="campos-inline">${[["nombre", "Nombre"], ["apellido1", "Primer apellido"], ["apellido2", "Segundo apellido"], ["dni", "DNI / NIE"]]
    .map(([k, l]) => `<div class="campo"><label for="pf-${k}">${l}</label><input id="pf-${k}" value="${esc(p[k] || "")}"></div>`).join("")}</div>
    <div class="acciones"><button class="btn pri" id="pf-ok">${ico("check")}Guardar ficha</button></div></section>
  <section class="tarjeta"><h2>Correos</h2><span class="sub">Los correos de estas direcciones se dan por conocidos: si traen documentos, entran solos; si no traen, te avisa en la campanita.</span>
    <div class="campos-inline"><div class="campo" style="flex:2"><label for="pf-correo">Correo informado (a mano)</label><input id="pf-correo" placeholder="cliente@correo.es" value="${esc(p.correo_informado || "")}"></div>
    <div class="acciones" style="align-self:end"><button class="btn" id="pf-correo-ok">${ico("check")}Guardar correo</button></div></div>
    <div class="campo"><label>Correos recibidos (se apuntan solos cuando se guarda documentación que llegó desde ellos)</label>
    <div class="chips">${JSON.parse(p.correos_recibidos || "[]").map(c => `<span class="chip">${esc(c)} <button type="button" class="x" title="Quitar" data-quitar-correo="${esc(c)}">×</button></span>`).join("") || '<span class="sub">Ninguno todavía.</span>'}</div></div></section>
  <section class="tarjeta"><h2>Expedientes</h2>${p.expedientes.map(e => `<div class="dato"><a href="#expediente/${e.id}">${esc(e.nombre)}</a><span>${esc(e.papel)} · ${esc(e.estado)}</span></div>`).join("") || '<span class="sub">No está en ningún expediente.</span>'}</section>`;
}
let NUEVA_P = null;
function activarPersonas() {
  $("#p-nueva")?.addEventListener("click", () => { NUEVA_P = {}; pintar(); });
  $("#np-no")?.addEventListener("click", () => { NUEVA_P = null; pintar(); });
  $("#p-exp-manual")?.addEventListener("click", () => { NUEVO_EXP = { finalidad: (S.info.finalidades_visibles || [])[0], personas: [{}], manual: true }; location.hash = "expedientes"; });
  document.querySelectorAll("[data-np]").forEach(i => i.addEventListener("input", () => (NUEVA_P[i.dataset.np] = i.value)));
  $("#np-ok")?.addEventListener("click", async () => {
    if (!NUEVA_P.nombre || !NUEVA_P.apellido1) return aviso("Falta el nombre o el primer apellido.", true);
    try { const r = await api("persona_manual", NUEVA_P); NUEVA_P = null; PERS = await api("personas"); aviso(r.existia ? "Ya estaba fichada: queda marcada como dato manual" : "Persona guardada"); pintar(); }
    catch (e) { aviso(e.message, true); }
  });
  $("#p-filtro")?.addEventListener("input", e => { FILTRO_P = e.target.value; const pos = e.target.selectionStart; pintar(); const i = $("#p-filtro"); i.focus(); i.setSelectionRange(pos, pos); });
  document.querySelectorAll("[data-persona-ir]").forEach(tr => tr.addEventListener("click", () => (location.hash = "persona/" + tr.dataset.personaIr)));
}
function activarPersona(id) {
  $("#pf-correo-ok")?.addEventListener("click", async () => {
    try { await api("persona", { id, correo_informado: $("#pf-correo").value }); PERS = await api("personas"); aviso("Correo guardado"); pintar(); } catch (e) { aviso(e.message, true); }
  });
  document.querySelectorAll("[data-quitar-correo]").forEach(b => b.addEventListener("click", async () => {
    const p = PERS.find(x => x.id === id), lista = JSON.parse(p.correos_recibidos || "[]").filter(c => c !== b.dataset.quitarCorreo);
    try { await api("persona", { id, correos_recibidos: lista }); PERS = await api("personas"); aviso("Quitado: sus próximos correos se tratarán como de un desconocido"); pintar(); } catch (e) { aviso(e.message, true); }
  }));
  $("#pf-ok")?.addEventListener("click", async () => {
    const c = {}; ["nombre", "apellido1", "apellido2", "dni"].forEach(k => (c[k] = $("#pf-" + k).value));
    try { await api("persona", { id, ...c }); aviso("Ficha guardada"); PERS = await api("personas"); S.expedientes = await api("expedientes"); pintar(); } catch (e) { aviso(e.message, true); }
  });
}

// ---------------- Papelera (17, 18)
let PAP = null;
function vistaPapelera() {
  return `<div class="cab"><div><h1>Papelera</h1><div class="sub">Lo eliminado desde el programa: documentos y expedientes, con sus originales y un archivo de recuperación. Carpeta <code>${esc(S.info.carpetas.papelera)}</code>. Para borrarlo del todo, vacía esa carpeta desde Windows.</div></div>
    <div class="acciones"><button class="btn" id="pap-abrir">Abrir la carpeta Papelera</button></div></div>
  ${!PAP ? '<div class="tarjeta vacio">Cargando…</div>' : !PAP.length ? '<div class="tarjeta vacio">La Papelera está vacía.</div>' : `<section class="tarjeta sinp"><table class="tabla"><thead><tr><th>Qué</th><th>Nombre</th><th>Eliminado</th><th></th></tr></thead><tbody>
  ${PAP.map(x => `<tr><td>${x.tipo === "expediente" ? "Expediente" : "Documento"}</td><td><b>${esc(x.nombre)}</b></td><td>${fmtF(x.fecha)} ${x.fecha.slice(11, 16)}</td>
    <td class="der"><button class="btn peq" data-abrir="${esc(x.carpeta)}">Ver</button> <button class="btn peq pri" data-restaurar="${x.id}">Restaurar</button></td></tr>`).join("")}</tbody></table></section>`}`;
}
function activarPapelera() {
  $("#pap-abrir")?.addEventListener("click", () => abrirRuta(S.info.carpetas.papelera));
  document.querySelectorAll("[data-abrir]").forEach(b => b.addEventListener("click", () => abrirRuta(b.dataset.abrir)));
  document.querySelectorAll("[data-restaurar]").forEach(b => b.addEventListener("click", async () => {
    try { await api("restaurar", { id: +b.dataset.restaurar }); aviso("Restaurado"); PAP = await api("papelera"); refrescar(true); } catch (e) { aviso(e.message, true); }
  }));
}

// ---------------- Estadísticas (22)
let EST = null;
function vistaEstadisticas() {
  if (!EST) return '<div class="tarjeta vacio">Cargando…</div>';
  const s = EST, tarjeta = (n, t, sub = "") => `<div class="kpi"><b>${n}</b><span>${t}</span>${sub ? `<small>${sub}</small>` : ""}</div>`;
  const barras = (obj, val, fmt = x => x) => { const max = Math.max(1, ...Object.values(obj).map(val)); return Object.entries(obj).map(([k, v]) => `<div class="barra-h"><span>${esc(k)}</span><i style="width:${Math.round(100 * val(v) / max)}%"></i><b>${fmt(val(v))}</b></div>`).join("") || '<span class="sub">Sin datos todavía.</span>'; };
  return `<div class="cab"><div><h1>Estadísticas</h1><div class="sub">Con los estados y datos de la operación de cada expediente.</div></div></div>
  <div class="kpis">${tarjeta(s.cuenta.en_curso, "En curso")}${tarjeta(s.cuenta.firmados, "Firmados")}${tarjeta(s.cuenta.cerrados, "Cerrados sin operación")}
    ${tarjeta(eur(s.importe_solicitado), "Importe solicitado")}${tarjeta(eur(s.importe_firmado), "Importe firmado", "media " + eur(s.media_firmada))}
    ${tarjeta(s.dias_hasta_firmar ?? "—", "Días hasta firmar (media)")}${tarjeta(eur(s.honorarios_facturados), "Honorarios", "media " + eur(s.honorarios_medios))}${tarjeta(eur(s.honorarios_pendientes), "Pendiente de cobro")}</div>
  <div class="exp-notas"><section class="tarjeta"><h2>Por finalidad</h2>${barras(s.por_finalidad, v => v.total)}<span class="sub">${Object.entries(s.por_finalidad).map(([k, v]) => `${esc(k)}: ${v.firmados} firmados, ${v.cerrados} cerrados, ${eur(v.importe_firmado)}`).join(" · ")}</span></section>
    <section class="tarjeta"><h2>Por entidad</h2>${barras(s.por_entidad, v => v.firmados)}<span class="sub">${Object.entries(s.por_entidad).map(([k, v]) => `${esc(k)}: ${eur(v.importe)}${v.cerrados ? `, ${v.cerrados} cerrados` : ""}`).join(" · ")}</span></section>
    <section class="tarjeta"><h2>Motivos de cierre</h2>${barras(s.motivos_cierre, v => v)}</section>
    <section class="tarjeta"><h2>Documentos que más cuesta conseguir</h2>${barras(Object.fromEntries(s.documentos_que_faltan), v => v)}<span class="sub">Pendientes en los expedientes en curso.</span></section></div>`;
}

// ---------------- Buscar en documentos (30)
let BUS = { q: "", res: null };
function vistaBuscar() {
  return `<div class="cab"><div><h1>Buscar en documentos</h1><div class="sub">Busca en el texto leído de todos los documentos (no en los PRIVADOS). Sin tildes ni mayúsculas.</div></div></div>
  <div class="neg-nueva"><input id="b-q" placeholder="Por ejemplo: Mercadona, 46013, IBAN, nombre…" value="${esc(BUS.q)}"><button class="btn pri" id="b-ir">${ico("search", 16)}Buscar</button></div>
  ${BUS.res === null ? "" : !BUS.res.length ? '<div class="tarjeta vacio">No se ha encontrado nada.</div>' : `<section class="tarjeta sinp"><table class="tabla"><thead><tr><th>Documento</th><th>Expediente</th><th>Texto</th><th></th></tr></thead><tbody>
  ${BUS.res.map(r => `<tr><td><b>${esc(r.nombre)}</b><div class="sub">${esc(nombreTipo(r.tipo, r.modelo))} · ${esc(r.estado)}</div></td><td>${r.expediente_id ? `<a href="#expediente/${r.expediente_id}">${esc(r.expediente)}</a>` : '<span class="muted">—</span>'}</td>
    <td class="trozo">…${esc(r.trozo)}…</td><td class="der">${["espera_emparejar", "parado"].includes(r.estado) ? `<a class="btn peq" href="#revision/${r.id}">Revisar</a>` : `<button class="btn peq" data-abrir-doc="${esc(r.ruta)}">Abrir</button>`}</td></tr>`).join("")}</tbody></table></section>`}`;
}
function activarBuscar() {
  const ir = async () => { BUS.q = $("#b-q").value; try { BUS.res = await api("buscar?q=" + encodeURIComponent(BUS.q)); } catch (e) { aviso(e.message, true); } pintar(); };
  $("#b-ir")?.addEventListener("click", ir);
  $("#b-q")?.addEventListener("keydown", e => e.key === "Enter" && ir());
  $("#b-q")?.focus();
  document.querySelectorAll("[data-abrir-doc]").forEach(b => b.addEventListener("click", () => abrirRuta(b.dataset.abrirDoc, true)));
}

// ---------------- Reglas de nombres (6) y Tipos de documento (8)
let REG = null, FILTRO_T = "";
function vistaReglas() {
  if (!REG) return '<div class="tarjeta vacio">Cargando…</div>';
  const n = REG.nombres, f = normaliza(FILTRO_T);
  const tipos = REG.tipos.filter(t => !f || normaliza(`${t.nombre} ${t.corto} ${t.familia}`).includes(f));
  return `<div class="cab"><div><small><a href="#ajustes">Ajustes</a></small><h1>Reglas de nombres y tipos de documento</h1><div class="sub">Son de la variante ${esc(S.info.variante.nombre)}: se actualizan con ella.</div></div></div>
  <section class="tarjeta"><h2>Reglas de nombres</h2>
    <div class="dato"><span>Patrón</span><span class="mono">YYYXXX_nombrecorto_ZZZZ.pdf · p. ej. IMG678_nomina_1026.pdf</span></div>
    <div class="dato"><span>YYY</span><span>Iniciales de todos los nombres y apellidos</span></div>
    <div class="dato"><span>XXX</span><span>Últimas 3 cifras del DNI/NIE (empresas: siglas + S.L./S.A.)</span></div>
    <div class="dato"><span>ZZZZ</span><span>${Object.entries(n.dato_distintivo || {}).map(([k, v]) => `<code>${esc(k)}</code> = ${esc(v)}`).join(" · ")}</span></div>
    <div class="dato"><span>Sin DNI</span><span class="mono">${esc(n.sin_dni || "NOINFORMADO")}</span></div>
    <div class="dato"><span>Privado</span><span class="mono">${esc(n.prefijo_privado || "PRIVADO_NO_COMPARTIR_")}</span></div>
    <div class="dato"><span>Repetido / sustituido</span><span class="mono">-2, -3… / -ant</span></div>
    <div class="dato"><span>Carpeta de expediente</span><span class="mono">nombre1apellido1_DNI5_MMAA · IvanMorales_45678_1126</span></div></section>
  <section class="tarjeta sinp"><div class="tcab"><h2>Tipos de documento · ${REG.tipos.length}</h2><input id="t-filtro" class="filtro" placeholder="Filtrar…" value="${esc(FILTRO_T)}"></div>
    <table class="tabla"><thead><tr><th>Tipo</th><th>Nombre corto</th><th>Familia</th><th>Dato distintivo</th><th>Idiomas</th><th>También se llama</th></tr></thead><tbody>
    ${tipos.map(t => `<tr><td><b>${esc(t.nombre)}</b></td><td class="mono">${esc(t.corto)}</td><td>${esc(t.familia || "")}</td><td class="mono">${esc(t.zzzz || "")}</td><td>${esc(t.idiomas.join(", "))}</td><td class="sub">${esc(t.otros_nombres.join(" · "))}</td></tr>`).join("")}</tbody></table></section>`;
}
function activarReglas() {
  $("#t-filtro")?.addEventListener("input", e => { FILTRO_T = e.target.value; const pos = e.target.selectionStart; pintar(); const i = $("#t-filtro"); i.focus(); i.setSelectionRange(pos, pos); });
}

// ---------------- Primer arranque (31)
function vistaBienvenida() {
  const c = S.info.carpetas;
  return `<div class="bienvenida tarjeta"><img src="/api/logo" alt="" width="72" height="72"><h1>Bienvenido a ${esc(S.info.variante.nombre)}</h1>
    <p class="sub">Todo funciona en este equipo, sin internet (salvo el correo, si lo activas). Tres pasos y listo:</p>
    <ol class="pasos-bien"><li><b>Carpetas.</b> Los documentos entran por <code>${esc(c.entrada)}</code>; los ordenados van a <code>${esc(c.documentos)}</code> y los originales, sin tocar, a <code>${esc(c.originales)}</code>. Puedes cambiarlas en Ajustes.</li>
      <li><b>Finalidades.</b> Revisa qué documentos pide cada tipo de operación en Ajustes → Finalidades.</li>
      <li><b>Correo (opcional).</b> Si quieres que recoja los adjuntos de tu correo, configúralo en Ajustes → Recibir por correo.</li></ol>
    <div class="acciones"><button class="btn pri" id="bien-ok">${ico("check")}Empezar: arrastrar documentos</button><a class="btn" href="#ajustes" id="bien-aj">Ir a Ajustes</a></div></div>`;
}
function activarBienvenida() {
  const hecho = async () => { await api("ajustes", { bienvenida_vista: true }); S.ajustes.bienvenida_vista = true; };
  $("#bien-ok")?.addEventListener("click", async () => { await hecho(); location.hash = "motor"; });
  $("#bien-aj")?.addEventListener("click", hecho);
}

// ---------------- Separar un PDF a mano (5)
let SEP = null;
function vistaSeparar(id) {
  if (!SEP || SEP.id !== id) return '<div class="tarjeta vacio">Cargando…</div>';
  const d = SEP.doc, n = d.paginas_lista.length;
  let g = 1;
  return `<div class="cab"><div><small><a href="#revision/${id}">Centro de revisión</a></small><h1>Separar «${esc(d.nombre_recibido)}»</h1><div class="sub">Pulsa la tijera entre dos páginas para cortar ahí. Cada grupo será un documento distinto y se volverá a clasificar.</div></div>
    <div class="acciones"><a class="btn" href="#revision/${id}">Cancelar</a><button class="btn pri" id="sep-ok" ${SEP.cortes.size ? "" : "disabled"}>${ico("check")}Separar en ${SEP.cortes.size + 1} documentos</button></div></div>
  <section class="tarjeta"><div class="pags separar">${d.paginas_lista.map((p, i) => `${i && SEP.cortes.has(i) ? `<span class="grupo-ini">Documento ${++g}</span>` : i === 0 ? '<span class="grupo-ini">Documento 1</span>' : ""}<figure class="pag">
      <button type="button" class="miniatura" data-zoom-pos="${i + 1}"><img src="/api/vista/${id}/${i + 1}" alt="" loading="lazy"></button><figcaption>Página ${i + 1}</figcaption></figure>
      ${i < n - 1 ? `<button type="button" class="tijera ${SEP.cortes.has(i + 1) ? "on" : ""}" data-corte="${i + 1}" title="Cortar aquí">✂</button>` : ""}`).join("")}</div></section>${zoomModal()}`;
}
function activarSeparar(id) {
  document.querySelectorAll("[data-corte]").forEach(b => b.addEventListener("click", () => { const k = +b.dataset.corte; SEP.cortes.has(k) ? SEP.cortes.delete(k) : SEP.cortes.add(k); pintar(); }));
  const abrir = activarZoomModal();
  document.querySelectorAll("[data-zoom-pos]").forEach(b => b.addEventListener("click", () => abrir(`/api/vista/${id}/${b.dataset.zoomPos}?grande=1`)));
  $("#sep-ok")?.addEventListener("click", async () => {
    const sel = SEP.doc.paginas_lista, grupos = [[]];
    sel.forEach((p, i) => { if (i && SEP.cortes.has(i)) grupos.push([]); grupos[grupos.length - 1].push(p); });
    try { const r = await api("separar", { documento: id, grupos }); aviso(`Separado en ${r.documentos.length} documentos`); SEP = null; S.doc = null; S.docId = null; await refrescar(false); location.hash = "revision/" + r.documentos[0]; }
    catch (e) { aviso(e.message, true); }
  });
}

// ---------------- Escanear: USB, red/Wi-Fi instalados en Windows (WIA) y AirScan/eSCL por red sin instalar nada
const ESC = { lista: null, sel: null, dpi: 300, color: true, alimentador: false, ocupado: false };
async function abrirEscaner() {
  ESC.lista = null; pintarEscaner();
  try { ESC.lista = await fetch("/api/escaneres").then(r => r.json()); } catch { ESC.lista = []; }
  if (ESC.sel === null && ESC.lista.length) ESC.sel = 0;
  pintarEscaner();
}
function pintarEscaner() {
  let caja = $("#escaner"); if (!caja) { caja = document.createElement("div"); caja.id = "escaner"; caja.className = "zoom informe"; document.body.appendChild(caja); }
  const L = ESC.lista, opciones = L ? [...L, { via: "wia", id: null, nombre: "Cuadro de escaneo de Windows", conexion: "elige el escáner en Windows" }] : [];
  const s = opciones[ESC.sel ?? 0] || {};
  caja.innerHTML = `<div class="tarjeta escaner"><h2>${ico("scan")} Escanear</h2>
    ${!L ? '<span class="sub">Buscando escáneres: USB, red y Wi-Fi…</span>' : `<div class="destinos">${opciones.map((x, i) => `<label class="dest ${i === ESC.sel ? "sel" : ""}"><input type="radio" name="esc" value="${i}" ${i === ESC.sel ? "checked" : ""}><span><b>${esc(x.nombre)}</b><small>${esc(x.conexion || "")}${x.url ? " · " + esc(x.url.replace(/^https?:\/\//, "").split("/")[0]) : ""}</small></span></label>`).join("")}</div>
      ${L.length ? "" : '<span class="warn-txt">No se ha encontrado ningún escáner. Comprueba que está encendido y en la misma red (o Wi-Fi Direct), o escribe su IP.</span>'}`}
    <div class="op-campos"><div class="campo"><label>Color</label><select id="esc-color"><option value="1" ${ESC.color ? "selected" : ""}>Color</option><option value="0" ${!ESC.color ? "selected" : ""}>Grises</option></select></div>
      <div class="campo"><label>Resolución</label><select id="esc-dpi">${[200, 300, 600].map(d => `<option ${d === ESC.dpi ? "selected" : ""}>${d}</option>`).join("")}</select></div>
      ${s.via === "escl" ? `<div class="campo"><label>Origen</label><select id="esc-ali"><option value="0">Cristal (una hoja)</option><option value="1" ${ESC.alimentador ? "selected" : ""}>Alimentador (varias hojas)</option></select></div>` : ""}</div>
    <div class="fila-arreglo"><input id="esc-ip" placeholder="IP del escáner en la red, p. ej. 192.168.1.40"><button class="btn peq" id="esc-ip-ok">Añadir por IP</button><button class="btn peq" id="esc-buscar">Buscar otra vez</button><button class="btn peq" id="esc-win">Añadir en Windows…</button></div>
    <span class="sub">Salen los escáneres USB, los de red o Wi-Fi que Windows ya tiene instalados y los que tienen AirScan (eSCL), que se usan sin instalar nada. Para Wi-Fi Direct, conecta antes el equipo a la Wi-Fi del escáner.</span>
    <div class="acciones"><button class="btn pri" id="esc-ok" ${!L || ESC.ocupado ? "disabled" : ""}>${ico("scan")}${ESC.ocupado ? "Escaneando…" : "Escanear"}</button><button class="btn" id="esc-cerrar">Cerrar</button></div></div>`;
  caja.querySelectorAll('input[name="esc"]').forEach(r => r.addEventListener("change", () => { ESC.sel = +r.value; pintarEscaner(); }));
  caja.querySelector("#esc-color").addEventListener("change", e => (ESC.color = e.target.value === "1"));
  caja.querySelector("#esc-dpi").addEventListener("change", e => (ESC.dpi = +e.target.value));
  caja.querySelector("#esc-ali")?.addEventListener("change", e => (ESC.alimentador = e.target.value === "1"));
  caja.querySelector("#esc-cerrar").addEventListener("click", () => caja.remove());
  caja.querySelector("#esc-buscar").addEventListener("click", abrirEscaner);
  caja.querySelector("#esc-win").addEventListener("click", () => api("abrir_url", { url: "ms-settings:printers" }).catch(e => aviso(e.message, true)));
  caja.querySelector("#esc-ip-ok").addEventListener("click", async () => {
    const ip = caja.querySelector("#esc-ip").value.trim(); if (!ip) return;
    aviso("Buscando el escáner en " + ip + "…");
    try { const e = await api("escaner_ip", { direccion: ip }); aviso("Escáner añadido: " + e.nombre); ESC.sel = null; await abrirEscaner(); ESC.sel = ESC.lista.findIndex(x => x.url === e.url); pintarEscaner(); } catch (e) { aviso(e.message, true); }
  });
  caja.querySelector("#esc-ok").addEventListener("click", async () => {
    ESC.ocupado = true; pintarEscaner();
    try { const r = await api("escanear", { via: s.via, id: s.id, url: s.url, dpi: ESC.dpi, color: ESC.color, alimentador: ESC.alimentador });
      aviso(r.cancelado ? "Escaneo cancelado" : "Escaneado: " + r.archivo); if (!r.cancelado) { caja.remove(); refrescar(true); } }
    catch (e) { aviso(e.message, true); }
    ESC.ocupado = false; if ($("#escaner")) pintarEscaner();
  });
}


// ================================================================== Controlador IA (versión 3.0)
let IAP = null, INF = null, ENV = null, INF_FILTRO = "todo";
const eurIA = v => (+v || 0).toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: (+v || 0) < 0.1 ? 4 : 2 }) + " €";
const usd = v => (+v || 0).toLocaleString("es-ES", { minimumFractionDigits: 2, maximumFractionDigits: 3 }) + " $";
const fichasHTML = t => esc(t).replace(/\[[A-Z]+_[A-Z0-9]+\]/g, m => `<span class="ficha">${m}</span>`);

function botonIA() {
  const ia = S.estado?.ia;
  if (!ia) return "";
  const on = ia.activo, e = ia.estado;
  const cls = !on ? "apagado" : e === "pausa" ? "pausa" : e === "sin_conexion" ? "red" : "on";
  const sub = !on ? "" : e === "pausa" ? `En pausa: límite del ${ia.pausa?.motivo === "mes" ? "mes" : "día"} alcanzado`
    : e === "sin_conexion" ? "Sin conexión: sigue en local" : e === "trabajando" ? "Trabajando…" : `Activo · ${eurIA(ia.hoy)} de ${eurIA(ia.limites.dia)} hoy`;
  return `<div class="ia-lat"><button type="button" id="b-ia" class="ia-btn ${cls}" aria-pressed="${on}" title="${on ? "Pulsa para apagar el Controlador IA" : "Pulsa para encender el Controlador IA"}">
      <span class="ia-cab"><span class="ia-ico">${ico(on && e === "pausa" ? "pause" : "ia", 18)}</span>Controlador IA</span>${sub ? `<span class="ia-sub">${esc(sub)}</span>` : ""}</button>
    <a class="ia-enlace" href="#ia">Ajustes de la IA</a>${ia.por_revisar ? `<a class="ia-enlace" href="#ia_mirar"><b>${ia.por_revisar} para mirar</b></a>` : ""}</div>`;
}
async function pulsarIA() {
  const ia = S.estado?.ia;
  if (!ia) return;
  if (!ia.activo && !ia.tiene_clave) { aviso("Primero escribe tu clave de la API de Anthropic."); location.hash = "ia"; return; }
  try { S.estado.ia = await api("ia/encender", { activo: !ia.activo }); aviso(ia.activo ? "Controlador IA apagado: todo sigue en local" : "Controlador IA encendido"); lateral(); if (S.ruta.startsWith("ia")) ir(); }
  catch (e) { aviso(e.message, true); }
}
function avisoPausaIA() {
  const ia = S.estado?.ia;
  if (!ia?.activo || ia.estado !== "pausa") return "";
  const m = ia.pausa?.motivo === "mes" ? "mes" : "día";
  return `<div class="ia-pausa" role="status"><span>${ico("pause", 24)}</span><span class="t"><b>Controlador IA en pausa · límite del ${m} alcanzado (${eurIA(m === "mes" ? ia.limites.mes : ia.limites.dia)})</b>
    <span>El motor sigue trabajando en local. Lo pendiente espera en el Centro de revisión; ${m === "día" ? "mañana se reanuda solo" : "el mes que viene se reanuda solo"}, o puedes subir el límite.</span></span>
    ${m === "día" ? `<button class="btn" id="ia-subir">Subir límite de hoy…</button>` : `<a class="btn" href="#ia">Cambiar límites</a>`}<a class="btn" href="#revision">Pasar a revisión manual</a></div>`;
}
function activarAvisoPausaIA() {
  $("#ia-subir")?.addEventListener("click", async () => {
    const v = prompt("¿Cuántos euros más quieres permitir hoy?", "0,50");
    if (v === null) return;
    try { await api("ia/limite_hoy", { euros: v }); aviso("Límite de hoy subido: la IA sigue"); refrescar(true); } catch (e) { aviso(e.message, true); }
  });
}
function botonesLoteIA(l) {
  const ia = S.estado?.ia, b = [];
  if (l.ia || l.acciones) b.push(`<a class="btn ia-b" href="#ia_informe/${l.id}">${ico("ia", 16)}Informe del lote</a>`);
  if (ia?.activo && ia.estado !== "pausa" && l.documentos.some(d => d.estado === "espera_emparejar") && !ia.trabajando) b.push(`<button class="btn" id="ia-pasar" data-lote="${l.id}">${ico("ia", 16)}Pasar a la IA</button>`);
  if (l.ia?.estado === "trabajando" && ia?.trabajando) b.push(`<span class="pill p-ia">La IA está trabajando…</span>`);
  return b.join("");
}
// 3.0.3 · «N para mirar»: lo que hizo la IA con poca seguridad o te dejó a ti, todo junto
let MIRAR = null;
function vistaMirarIA() {
  const xs = MIRAR || [];
  return `<div class="cab"><div><small>Controlador IA</small><h1>Para mirar</h1><div class="sub">Lo que la IA hizo con poca seguridad o dejó para ti. Ábrelo, compruébalo y dale «Está bien» o «Deshacer».</div></div>
    <div class="acciones">${xs.length > 1 ? '<button class="btn" id="mirar-todo">Marcar todo como revisado</button>' : ""}</div></div>
  ${xs.length ? `<section class="tarjeta sinp"><table class="tabla"><thead><tr><th>Qué</th><th>Documento</th><th>Detalle</th><th></th></tr></thead><tbody>
  ${xs.map(x => `<tr><td>${pill(x.titulo, x.tipo === "para_ti" ? "warn" : "ia")}<div class="sub">${x.seguridad != null ? x.seguridad + " %" : ""}</div></td>
    <td>${esc(x.nombre_final || x.archivo || "—")}<div class="sub">${esc(x.estado_doc || "")}${x.lote_id ? " · lote " + x.lote_id : ""}</div></td><td class="sub">${esc(x.detalle || x.motivo || "")}</td>
    <td class="acciones">${x.estado_doc === "espera_emparejar" ? `<a class="btn peq" href="#revision/${x.documento_id}">Revisar</a>` : x.lote_id ? `<a class="btn peq" href="#ia_informe/${x.lote_id}">Informe</a>` : ""}
      ${x.tipo !== "para_ti" ? `<button class="btn peq" data-ia-deshacer="${x.id}">${ico("undo", 14)}Deshacer</button>` : ""}<button class="btn peq" data-ia-bien="${x.id}">Está bien</button></td></tr>`).join("")}</tbody></table></section>`
    : '<div class="tarjeta vacio">Nada para mirar.</div>'}`;
}
function activarMirarIA() {
  $("#mirar-todo")?.addEventListener("click", async () => {
    for (const x of MIRAR || []) await api("ia/revisada", { accion: x.id });
    aviso("Todo marcado como revisado"); await refrescar(false); await ir();
  });
}
function bannerSerie(d) {
  const serie = (d.datos || {}).serie;
  if (!serie) return "";
  const [, clase] = serie.split("|");
  const por = clase === "cuenta" ? "la misma cuenta" : clase === "préstamo" ? "el mismo préstamo" : "la misma entidad";
  return `<section class="ia-banner"><div class="cab"><div><b>${ico("motor", 16)} Documento de una serie</b>
      <span class="sub">Hay otros documentos de este lote del mismo tipo, con ${por} y de otros periodos. Al confirmar este, los demás se guardan con la misma decisión, cada uno con su mes (2.ª, 3.ª… entrada del mismo documento).</span></div></div></section>`;
}
function bannerIA(d) {
  const acc = d.ia_acciones || [], prop = (d.datos || {}).ia_propuesta;
  const misma = acc.filter(x => x.tipo === "misma_persona");
  const otras = acc.filter(x => x.tipo !== "misma_persona");
  if (!acc.length && !prop) return "";
  const local = prop && prop.origen === "local" && !acc.some(x => x.origen !== "local");
  return `<section class="ia-banner"><div class="cab"><div><b>${ico(local ? "motor" : "ia", 16)} ${local ? "Propuesta del contexto del lote" : "El Controlador IA ha mirado este documento"}</b>
      ${prop?.texto ? `<span class="sub">${esc(prop.texto)} · seguridad ${prop.seguridad} %</span>` : ""}</div>
      ${acc[0]?.lote_id ? `<a class="btn peq" href="#ia_informe/${acc[0].lote_id}">Ver el informe</a>` : ""}</div>
    ${misma.map(x => `<div class="ia-misma"><span><b>Misma persona</b> · ${esc(x.detalle)}</span><button class="btn peq" data-ia-deshacer="${x.id}">${ico("undo", 14)}Deshacer y decidir yo</button><button class="btn peq" data-ia-bien="${x.id}">Está bien</button></div>`).join("")}
    ${otras.map(x => `<div class="ia-fila-mini">${pill(x.titulo, x.estado === "para_ti" ? "warn" : "ia")}<span>${esc(x.detalle || "")}</span></div>`).join("")}</section>`;
}
document.addEventListener("click", async e => {
  const b = e.target.closest("[data-ia-deshacer],[data-ia-bien]");
  if (!b) return;
  try {
    if (b.dataset.iaDeshacer) { await api("ia/deshacer", { accion: +b.dataset.iaDeshacer }); aviso("Deshecho: decide tú"); }
    else { await api("ia/revisada", { accion: +b.dataset.iaBien }); aviso("Marcado como revisado"); }
    await refrescar(false);
    if (S.ruta.startsWith("revision")) { S.doc = null; await ir(); } else await ir();
  } catch (er) { aviso(er.message, true); }
});

// ---------------- Ajustes › Controlador IA
function vistaIA() {
  if (!IAP) return '<div class="tarjeta vacio">Cargando…</div>';
  const a = IAP.ajustes, r = IAP.resumen, M = IAP.modelos, F = IAP.funciones;
  const med = (t, u, l) => `<div class="ia-medidor"><span>${t}</span><b>${eurIA(u)} <small>de ${eurIA(l)}</small></b><span class="barra"><i style="width:${Math.min(100, Math.round(100 * u / (l || 1)))}%"></i></span></div>`;
  const tog = (id, on, tit, sub) => `<label class="ia-tog" for="${id}"><input type="checkbox" id="${id}" ${on ? "checked" : ""}><span class="sw" aria-hidden="true"></span><span><b>${tit}</b><span class="sub">${sub}</span></span></label>`;
  const tar = a.tarifas || {};
  const tarTxt = !tar.ultima ? "Todavía no se han comprobado." : tar.estado === "cambios" ? tar.detalle : tar.estado === "no_comprobado" ? tar.detalle : `Comprobado el ${tar.ultima.slice(8, 10)}/${tar.ultima.slice(5, 7)} a las ${tar.ultima.slice(11, 16)} · sin cambios.`;
  const comp = IAP.comparativa, maxH = Math.max(...comp.modelos.map(x => x.hasta));
  return `<div class="cab"><div><small>Ajustes › Controlador IA</small><h1>Controlador IA <span class="pill p-ia">3.0</span></h1><div class="sub">Resuelve solo lo que el programa no sabe y te informa de cada cosa que hace. Solo texto, sin datos personales.</div></div>
    <div class="acciones"><button class="btn" id="ia-saldo" title="Abre la página de facturación de la consola de la API en tu navegador">${ico("link", 15)}Ver saldo de la API</button><a class="btn" href="#ajustes">Volver a Ajustes</a><button class="btn pri" id="ia-guardar">${ico("check")}Guardar cambios</button></div></div>
  <div class="ia-cols"><div class="ia-col">
  <section class="tarjeta"><h2>Controlador IA</h2>
    <div class="ia-estado ${a.activo ? "on" : ""}"><span class="ia-ico">${ico("ia", 26)}</span><span><b>${a.activo ? "Encendido · modo automático" : "Apagado · todo en local"}</b><span class="sub">${a.activo ? "Resuelve solo lo que el programa no sabe; cada acción se puede deshacer." : "Se enciende con el botón «Controlador IA» de la barra lateral o aquí."}</span></span>
      <button class="btn" id="ia-onoff">${a.activo ? "Apagar" : "Encender"}</button></div>
    <div class="campos-inline"><div class="campo" style="flex:2 1 320px"><label for="ia-clave">Clave de la API de Anthropic</label><input id="ia-clave" type="password" autocomplete="off" placeholder="${a.tiene_clave ? "•••••••• (guardada; escribe otra para cambiarla)" : "sk-ant-…"}"></div>
      <button class="btn" id="ia-probar">${ico("link", 15)}Probar conexión</button>${a.tiene_clave ? `<button class="btn peligro" id="ia-quitar">Quitar clave</button>` : ""}</div>
    <span class="sub">Cifrada con tu usuario de Windows. Los créditos se compran en la consola de la API (platform.claude.com), no en claude.ai.</span>
    <div class="campos-inline"><div class="campo"><label for="ia-modelo">Modelo</label><select id="ia-modelo">${Object.entries(M).map(([k, m]) => `<option value="${k}" ${k === a.modelo ? "selected" : ""}>${esc(m.nombre)} · ${esc(m.desc)}</option>`).join("")}</select></div>
      <div class="campo"><label for="ia-actua">Cuándo actúa</label><select id="ia-actua"><option value="lote" ${a.actua === "lote" ? "selected" : ""}>Al terminar cada lote del motor</option><option value="manual" ${a.actua === "manual" ? "selected" : ""}>Solo cuando pulse «Pasar a la IA»</option></select></div>
      <div class="campo" style="max-width:170px"><label for="ia-umbral">Seguridad para no marcar (%)</label><input id="ia-umbral" type="number" min="50" max="100" value="${a.umbral}"></div></div></section>
  <section class="tarjeta"><div><h2>Qué puede resolver</h2><span class="sub">Lo que el programa ya resuelve en local no se envía nunca.</span></div>
    ${Object.entries(F).map(([k, f]) => tog("ia-f-" + k, a.funciones[k], f[0], f[1])).join("")}
    <div class="ia-nota warn">${ico("lock")}<span><b>Expedientes nuevos: siempre tú.</b> Si la IA cree que un documento es de alguien sin expediente, te lo deja con su propuesta. Tampoco añade personas a un expediente.</span></div></section>
  <section class="tarjeta"><div><h2>Instrucciones para la IA</h2><span class="sub">Tus reglas propias, escritas como se lo explicarías a una persona. Van en el manual que acompaña a cada consulta.</span></div>
    <textarea id="ia-instr" rows="7">${esc(a.instrucciones)}</textarea>
    <span class="sub">Con las reglas del programa, los tipos de documento y ${IAP.ejemplos} ejemplo(s) anónimo(s) de tus correcciones. No hace falta entrenar el modelo.</span>
    <div class="acciones"><button class="btn" id="ia-manual">${ico("eye", 15)}Ver el manual completo</button><button class="btn" id="ia-serie">Restaurar instrucciones de serie</button></div>
    <pre id="ia-manual-txt" class="ia-pre" hidden></pre></section>
  </div><div class="ia-col estrecha">
  <section class="tarjeta"><div><h2>Gasto</h2><span class="sub">Lo que cobra Anthropic, calculado consulta a consulta.</span></div>
    <div class="ia-medidores">${med("Hoy", r.hoy, r.limites.dia)}${med("Este mes", r.mes, r.limites.mes)}</div>
    <div class="campos-inline"><div class="campo"><label for="ia-ld">Límite por día (€)</label><input id="ia-ld" value="${String(a.limite_dia).replace(".", ",")}"></div>
      <div class="campo"><label for="ia-lm">Límite por mes (€)</label><input id="ia-lm" value="${String(a.limite_mes).replace(".", ",")}"></div>
      <div class="campo"><label for="ia-ll">Límite por lote (€)</label><input id="ia-ll" value="${String(a.limite_lote).replace(".", ",")}"></div></div>
    ${tog("ia-pausar", a.pausar, "Pausar y avisar al llegar al límite", "La IA se para; el programa sigue en local y lo pendiente espera en el Centro de revisión.")}
    <div class="dato"><span>Consultas este mes</span><span>${r.consultas_mes} · media ${eurIA(IAP.media)}</span></div></section>
  <section class="tarjeta"><div><h2>Tarifas</h2><span class="sub">Precio por modelo y comparativa para elegir.</span></div>
    <table class="tabla ia-tarifas"><thead><tr><th>Modelo</th><th>Entrada</th><th>Salida</th><th>Caché</th></tr></thead><tbody>
    ${Object.entries(M).map(([k, m]) => { const p = a.precios[k] || {}; return `<tr><td><b>${esc(m.nombre.replace("Claude ", ""))}</b>${k.includes("haiku") ? '<br><span class="muted" style="font-size:11.5px">hasta 100.000 tokens</span>' : ""}</td>${["entrada", "salida", "cache"].map(c => `<td><input class="ia-precio" data-m="${k}" data-c="${c}" value="${String(p[c] ?? "").replace(".", ",")}" aria-label="${m.nombre} ${c}"></td>`).join("")}</tr>`; }).join("")}</tbody></table>
    <span class="sub">Dólares por millón de tokens, como cobra Anthropic. Editable por si cambian.</span>
    <div class="campos-inline"><div class="campo" style="max-width:170px"><label for="ia-cambio">1 $ son (€)</label><input id="ia-cambio" value="${String(a.cambio).replace(".", ",")}"></div></div>
    <div class="ia-nota ${tar.estado === "cambios" ? "warn" : tar.estado === "no_comprobado" ? "" : "ok"}">${ico(tar.estado === "cambios" ? "bell" : "check")}<span>${esc(tarTxt)} Como máximo una vez al día: al encender la IA si hoy aún no se ha comprobado, o a las 24 h si sigue encendida.</span></div>
    ${tar.estado === "cambios" ? `<div class="acciones"><button class="btn pri" id="ia-act-tar">Actualizar la tabla con las tarifas nuevas</button></div>` : ""}
    <div class="ia-comp"><b>Lote de ${comp.documentos} documentos típicos, todos consultados</b><span class="sub">Cálculo del ${comp.fecha}: ${esc(comp.supuesto)}. El tramo alto es con documentos largos (rentas enteras) o sin la rebaja de caché.</span>
      ${comp.modelos.map(x => `<div class="ia-barra-m ${x.modelo === a.modelo ? "sel" : ""}"><span>${esc(M[x.modelo].nombre.replace("Claude ", ""))}</span><span class="barra"><i style="width:${Math.max(4, Math.round(100 * x.hasta / maxH))}%"></i></span><b>${usd(x.desde)} – ${usd(x.hasta)}</b></div>`).join("")}
      <span class="sub">Con el límite de ${eurIA(a.limite_dia)} al día: unos ${Math.floor(a.limite_dia / (comp.modelos[0].hasta * a.cambio))} lotes con Haiku, ${Math.floor(a.limite_dia / (comp.modelos[1].hasta * a.cambio))} con Sonnet o ${Math.floor(a.limite_dia / (comp.modelos[2].hasta * a.cambio))} con Opus.</span></div>
    <div class="acciones"><button class="btn" id="ia-tar">${ico("link", 15)}Comprobar ahora</button><button class="btn" id="ia-consola">${ico("key", 15)}Comprar créditos en la consola</button></div></section>
  <section class="tarjeta"><div><h2>Datos personales bloqueados</h2><span class="sub">Se sustituyen por fichas antes de salir del equipo.</span></div>
    ${IAP.fichas.map(([t, f]) => `<div class="dato"><span>${esc(t)}</span><span class="mono ia-ficha-t">${esc(f)}</span></div>`).join("")}
    <div class="dato"><span>Importes y fechas del documento</span><span style="color:var(--ok);font-weight:600">se envían</span></div>
    <div class="ia-nota">${ico("lock")}<span>La tabla que traduce las fichas al dato real se queda en este equipo. Para comparar se envían pistas de parecido: «[DNI_2] ≈ DNI de [PERSONA_1]: 8 de 8 cifras iguales, falta la letra».</span></div>
    <div class="acciones">${IAP.ultima_consulta ? `<a class="btn" href="#ia_envio/${IAP.ultima_consulta}">${ico("eye", 15)}Ver lo que se envía</a>` : '<span class="sub">«Ver lo que se envía» estará disponible tras la primera consulta.</span>'}</div></section>
  <section class="tarjeta"><h2>Aprendizaje</h2>
    ${tog("ia-aprender", a.aprender, "Aprender de mis correcciones", "Cada vez que deshaces o corriges algo de la IA se guarda como ejemplo anónimo, en este equipo.")}
    <div class="dato"><span>Ejemplos guardados</span><b>${IAP.ejemplos}</b></div>
    <div class="acciones"><button class="btn" id="ia-exp">${ico("download", 15)}Exportar aprendizaje</button><label class="btn">Importar<input type="file" id="ia-imp" accept=".json" hidden></label><button class="btn peligro" id="ia-borrar">Borrar</button></div>
    <span class="sub">El archivo exportado no lleva datos personales: sirve para otro equipo o para otra variante.</span></section>
  </div></div>`;
}
function leerIA() {
  const v = id => $("#" + id)?.value ?? "";
  const precios = {};
  document.querySelectorAll(".ia-precio").forEach(i => { (precios[i.dataset.m] ||= {})[i.dataset.c] = i.value; });
  const funciones = {};
  Object.keys(IAP.funciones).forEach(k => (funciones[k] = !!$("#ia-f-" + k)?.checked));
  return { modelo: v("ia-modelo"), actua: v("ia-actua"), umbral: v("ia-umbral"), limite_dia: v("ia-ld"), limite_mes: v("ia-lm"), limite_lote: v("ia-ll"),
    cambio: v("ia-cambio"), pausar: !!$("#ia-pausar")?.checked, aprender: !!$("#ia-aprender")?.checked, instrucciones: v("ia-instr"), funciones, precios };
}
function activarIA() {
  if (!IAP) return;
  const recargar = async () => { IAP = await api("ia"); S.estado.ia = IAP.resumen; pintar(); };
  $("#ia-guardar")?.addEventListener("click", async () => {
    try { const d = leerIA(); const c = $("#ia-clave").value.trim(); if (c) d.clave = c; IAP = await api("ia/ajustes", d); S.estado.ia = IAP.resumen; aviso("Ajustes de la IA guardados"); pintar(); } catch (e) { aviso(e.message, true); }
  });
  $("#ia-onoff")?.addEventListener("click", async () => {
    try { const c = $("#ia-clave").value.trim(); if (c) await api("ia/ajustes", { clave: c }); await api("ia/encender", { activo: !IAP.ajustes.activo }); await recargar(); } catch (e) { aviso(e.message, true); }
  });
  $("#ia-probar")?.addEventListener("click", async ev => {
    const b = ev.currentTarget; b.disabled = true; aviso("Conectando con la API…");
    try { const r = await api("ia/probar", { clave: $("#ia-clave").value.trim() }); aviso(`Conexión correcta · ${r.modelos.length} modelos disponibles`); } catch (e) { aviso(e.message, true); }
    b.disabled = false;
  });
  $("#ia-quitar")?.addEventListener("click", async () => { if (!confirm("¿Quitar la clave? El Controlador IA se apagará.")) return; try { await api("ia/ajustes", { clave: "" }); await recargar(); aviso("Clave quitada"); } catch (e) { aviso(e.message, true); } });
  $("#ia-manual")?.addEventListener("click", async () => { const pre = $("#ia-manual-txt"); if (!pre.hidden) { pre.hidden = true; return; } pre.textContent = (await api("ia/manual")).texto; pre.hidden = false; });
  $("#ia-serie")?.addEventListener("click", () => { $("#ia-instr").value = IAP.instrucciones_serie; aviso("Instrucciones de serie puestas: pulsa «Guardar cambios»"); });
  $("#ia-tar")?.addEventListener("click", async ev => { ev.currentTarget.disabled = true; aviso("Comprobando las tarifas…"); try { await api("ia/tarifas", {}); await recargar(); aviso("Tarifas comprobadas"); } catch (e) { aviso(e.message, true); } });
  $("#ia-act-tar")?.addEventListener("click", async () => { try { IAP = await api("ia/actualizar_tarifas", {}); pintar(); aviso("Tabla de tarifas actualizada"); } catch (e) { aviso(e.message, true); } });
  $("#ia-consola")?.addEventListener("click", () => api("ia/consola", {}).catch(e => aviso(e.message, true)));
  $("#ia-saldo")?.addEventListener("click", () => api("ia/consola", {}).then(() => aviso("Abriendo el saldo de la API en el navegador…")).catch(e => aviso(e.message, true)));
  $("#ia-exp")?.addEventListener("click", async () => { try { const r = await api("ia/exportar", {}); aviso("Guardado en " + r.ruta); abrirRuta(r.ruta, true); } catch (e) { aviso(e.message, true); } });
  $("#ia-imp")?.addEventListener("change", async e => {
    const f = e.target.files[0]; if (!f) return;
    try { const r = await api("ia/importar", { datos: JSON.parse(await f.text()) }); aviso(`${r.importados} ejemplo(s) importado(s)`); await recargar(); } catch (er) { aviso("No se ha podido importar: " + er.message, true); }
  });
  $("#ia-borrar")?.addEventListener("click", async () => { if (!confirm("¿Borrar todos los ejemplos aprendidos?")) return; await api("ia/borrar_aprendizaje", {}); await recargar(); });
}

// ---------------- Informe del lote
function vistaInformeIA() {
  if (!INF) return '<div class="tarjeta vacio">No hay informe de la IA para este lote.</div>';
  const c = INF.cuentas, acc = INF.acciones;
  const grupos = { todo: () => true, clasificar: x => x.tipo === "clasificado", separar: x => ["separado", "ordenado", "unido"].includes(x.tipo),
    personas: x => ["misma_persona", "tercero", "cotitular"].includes(x.tipo), asignar: x => ["asignado", "limbo", "expediente_creado"].includes(x.tipo), ti: x => x.tipo === "para_ti" };
  const nombres = { todo: "Todo", clasificar: "Clasificar", separar: "Separar y unir", personas: "Personas", asignar: "Asignar", ti: "Para ti" };
  const vis = acc.filter(x => x.tipo !== "para_ti" && grupos[INF_FILTRO](x) || INF_FILTRO === "ti" && x.tipo === "para_ti" || INF_FILTRO === "todo" && x.tipo === "para_ti");
  const paraTi = acc.filter(x => x.tipo === "para_ti" && x.estado !== "deshecha" && !x.revisada);
  const ICO_T = { expediente_creado: "folder", cotitular: "user", clasificado: "check", separado: "scan", ordenado: "scan", unido: "link", misma_persona: "user", tercero: "user", asignado: "folder", limbo: "limbo", para_ti: "lock" };
  const fila = x => {
    const d = x.documento, des = x.estado === "deshecha";
    const ver = !d ? (x.expediente_id && x.estado !== "deshecha" ? `#expediente/${x.expediente_id}` : "") : d.estado === "guardado" && d.expediente_id ? `#expediente/${d.expediente_id}` : ["espera_emparejar", "parado"].includes(d.estado) ? `#revision/${d.id}` : "";
    return `<div class="ia-fila ${des ? "deshecha" : ""}"><span class="ia-fico">${ico(ICO_T[x.tipo] || "ia", 17)}</span>
      <span class="ia-que">${x.origen === "local" ? pill("Local", "ok") : pill("IA", "ia")}${pill(x.titulo, x.tipo === "para_ti" ? "warn" : "ia")}${x.estado === "por_revisar" && !des ? pill("Para mirar", "warn") : ""}${des ? pill("Deshecho", "todo") : ""}${x.revisada && !des && x.tipo !== "para_ti" ? pill("Revisado", "ok") : ""}
        <b>${esc(d?.archivo || "")}</b><span>${esc(x.detalle || "")}</span></span>
      <span class="ia-porque"><b>Por qué:</b> ${esc(x.motivo || "—")}</span>
      <span class="ia-seg">Seguridad<b style="color:${x.seguridad >= (IAP?.ajustes?.umbral || 90) ? "var(--ok)" : "var(--warn)"}">${x.seguridad} %</b></span>
      <span class="ia-acc">${!des && x.tipo !== "para_ti" ? `<button class="btn peq" data-ia-des="${x.id}">${ico("undo", 14)}Deshacer</button>` : ""}${ver ? `<a class="btn peq" href="${ver}">${ico("eye", 14)}Ver</a>` : ""}${x.consulta_id ? `<a class="btn peq" href="#ia_envio/${x.consulta_id}" title="Lo que se envió a la IA">Envío</a>` : ""}</span></div>`;
  };
  const tile = (t, v, col) => `<div class="ia-tile"><span>${t}</span><b style="color:${col}">${v}</b></div>`;
  return `<div class="cab"><div><small>Motor de proceso › Lote ${INF.lote}</small><h1>Informe del lote</h1><div class="sub">Lo que ha hecho el contexto del lote (Local) y el Controlador IA (IA). Todo se puede deshacer.</div>${INF.estado?.estado?.startsWith("limite") ? `<div class="sub" style="color:var(--warn)">La IA se paró en este lote: ${INF.estado.estado === "limite_lote" ? "límite del lote" : "límite de gasto"} alcanzado.</div>` : INF.estado?.estado === "error" ? `<div class="sub" style="color:var(--bad)">La IA se paró por un error: ${esc(JSON.parse(INF.estado.nota || "{}").parado || "")}</div>` : ""}</div>
    <div class="acciones"><a class="btn" href="#motor/${INF.lote}">Volver al lote</a><button class="btn peligro" id="ia-des-todo">${ico("undo")}Deshacer todo lo de la IA</button><button class="btn pri" id="ia-revisado">${ico("check")}Dar por revisado</button></div></div>
  <div class="ia-tiles">${tile("Documentos del lote", c.documentos, "var(--text)")}${tile("Resueltos en local", c.local, "var(--ok)")}${tile("Resueltos por la IA", c.ia, "#C4B5FD")}${tile("Para ti", c.para_ti, "var(--warn)")}${tile("Coste del lote", eurIA(INF.coste), "var(--text)")}</div>
  ${paraTi.length ? `<div class="ia-pausa">${ico("lock", 22)}<span class="t"><b>${paraTi.length} cosa(s) esperan tu decisión</b><span>${paraTi.slice(0, 3).map(x => esc(x.titulo + ": " + (x.detalle || ""))).join(" · ")}</span></span>
    ${paraTi[0].documento && ["espera_emparejar", "parado"].includes(paraTi[0].documento.estado) ? `<a class="btn pri" href="#revision/${paraTi[0].documento.id}">Decidir ahora</a>` : ""}</div>` : ""}
  <section class="tarjeta"><div><h2>Lo que ha hecho la IA</h2><span class="sub">Cada acción con su motivo. «Deshacer» la devuelve al Centro de revisión y la guarda como ejemplo para la próxima vez.</span></div>
    <div class="chips">${Object.keys(grupos).map(k => `<button class="chip ${INF_FILTRO === k ? "sel" : ""}" data-ia-filtro="${k}">${nombres[k]} · ${acc.filter(grupos[k]).length}</button>`).join("")}</div>
    ${vis.map(fila).join("") || '<span class="sub">Nada en este apartado.</span>'}</section>
  <div class="ia-nota">${ico("ia")}<span>Los documentos que ha tocado la IA llevan su marca en el Centro de revisión hasta que los des por revisados.</span></div>`;
}
function activarInformeIA() {
  document.querySelectorAll("[data-ia-filtro]").forEach(b => b.addEventListener("click", () => { INF_FILTRO = b.dataset.iaFiltro; pintar(); }));
  document.querySelectorAll("[data-ia-des]").forEach(b => b.addEventListener("click", async () => {
    try { await api("ia/deshacer", { accion: +b.dataset.iaDes }); aviso("Deshecho: vuelve al Centro de revisión"); await refrescar(false); await ir(); } catch (e) { aviso(e.message, true); }
  }));
  $("#ia-des-todo")?.addEventListener("click", async () => {
    if (!confirm("¿Deshacer todo lo que ha hecho la IA en este lote? Los documentos vuelven al Centro de revisión.")) return;
    try { const r = await api("ia/deshacer_lote", { lote: INF.lote }); aviso(`${r.deshechas} acción(es) deshecha(s)` + (r.fallos.length ? ` · ${r.fallos.length} no se han podido` : "")); await refrescar(false); await ir(); } catch (e) { aviso(e.message, true); }
  });
  $("#ia-revisado")?.addEventListener("click", async () => { await api("ia/revisada", { lote: INF.lote }); aviso("Lote dado por revisado"); await refrescar(false); await ir(); });
}

// ---------------- Lo que se envía a la IA
function vistaEnvioIA() {
  if (!ENV) return '<div class="tarjeta vacio">Cargando…</div>';
  const e = ENV, mapa = Object.entries(e.mapa || {});
  return `<div class="cab"><div><small>Controlador IA › Lote ${e.lote_id ?? "—"} › Consulta ${e.id}</small><h1>Lo que se envía a la IA</h1></div>
    <div class="acciones"><button class="btn" id="ia-copiar">Copiar texto</button><a class="btn pri" href="${e.lote_id ? "#ia_informe/" + e.lote_id : "#ia"}">Cerrar</a></div></div>
  <div class="ia-cols"><div class="ia-col">
    <section class="tarjeta"><div><h2>Texto enviado</h2><span class="sub">Exactamente lo que sale del equipo: solo texto, sin imágenes ni archivos. Las fichas moradas sustituyen a los datos personales. Además va el manual (reglas, tipos de documento, tus instrucciones y ${e.manual.ejemplos} ejemplo(s) anónimo(s)).</span></div>
      <pre class="ia-pre">${fichasHTML(e.enviado || "")}</pre></section>
    <section class="tarjeta"><div><h2>Respuesta recibida</h2><span class="sub">${e.error ? "La consulta falló: " + esc(e.error) : "Se traduce en el equipo con la tabla de la derecha antes de aplicarla."}</span></div>
      <pre class="ia-pre">${fichasHTML(e.respuesta || "—")}</pre></section></div>
  <div class="ia-col estrecha">
    <section class="tarjeta"><div><h2>Tabla de traducción · solo en este equipo</h2><span class="sub">Para que tú veas a quién corresponde cada ficha.</span></div>
      ${mapa.map(([f, v]) => `<div class="dato"><span class="mono ia-ficha-t">${esc(f)}</span><span>${esc(v)}</span></div>`).join("") || '<span class="sub">Sin datos tapados.</span>'}
      <div class="ia-nota">${ico("lock")}<span>Esta tabla nunca se envía.</span></div></section>
    <section class="tarjeta"><h2>Esta consulta</h2>
      ${[["Modelo", (IAP?.modelos?.[e.modelo]?.nombre) || e.modelo], ["Tokens enviados", (e.t_entrada + e.t_cache + e.t_escritura).toLocaleString("es-ES") + (e.t_cache ? ` (${e.t_cache.toLocaleString("es-ES")} del manual en caché)` : "")],
         ["Tokens de respuesta", (e.t_salida || 0).toLocaleString("es-ES")], ["Coste", eurIA(e.coste_eur)], ["Tiempo", e.segundos ? String(e.segundos).replace(".", ",") + " s" : "—"]]
        .map(([a, b]) => `<div class="dato"><span>${a}</span><b>${esc(b)}</b></div>`).join("")}</section></div></div>`;
}
document.addEventListener("click", e => { if (e.target.closest("#ia-copiar") && ENV) { navigator.clipboard?.writeText(ENV.enviado || ""); aviso("Texto copiado"); } });


// ---------------- Contexto del lote (3.0.2): ajustes y avisos de expedientes creados solos
function tarjetaContexto() {
  const c = (S.ajustes && S.ajustes.contexto) || {};
  const v = (k, d) => (c[k] ?? d);
  return `<section class="tarjeta"><div class="cab"><div><h2>${ico("motor")} Contexto del lote <span class="pill p-ia">3.0.2</span></h2>
      <span class="sub">Antes de decidir, mira todo el lote junto: de quién es la mayoría, el cotitular y los terceros. Si el expediente no existe, lo crea y te avisa en la campanita. En local, sin IA.</span></div>
      <button class="btn pri" id="ctx-guardar">${ico("check")}Guardar</button></div>
    <label class="ia-tog" for="ctx-act"><input type="checkbox" id="ctx-act" ${v("activo", true) ? "checked" : ""}><span class="sw"></span><span><b>Usar el contexto del lote</b><span class="sub">Si lo apagas, cada documento se decide solo como antes.</span></span></label>
    <label class="ia-tog" for="ctx-g"><input type="checkbox" id="ctx-g" ${v("guardar", true) ? "checked" : ""}><span class="sw"></span><span><b>Guardar solo lo que está claro</b><span class="sub">Tipo seguro y persona del expediente clara. Lo demás queda propuesto en el Centro de revisión. Todo se puede deshacer en el informe del lote.</span></span></label>
    <div class="campos-inline"><div class="campo"><label for="ctx-t">Titular: % de documentos del lote</label><input id="ctx-t" type="number" min="30" max="100" value="${v("titular", 60)}"></div>
      <div class="campo"><label for="ctx-c">Cotitular: % de documentos compartidos</label><input id="ctx-c" type="number" min="10" max="100" value="${v("cotitular", 50)}"></div>
      <div class="campo"><label for="ctx-m">Mínimo de documentos para crear expediente</label><input id="ctx-m" type="number" min="1" max="20" value="${v("minimo_docs", 2)}"></div></div>
    <span class="sub">Un DNI solo se da por bueno si aparece en al menos 2 documentos del lote. El cotitular se busca solo en documentos compartidos (renta, padrón, cuentas, préstamos, escrituras…), nunca en nóminas.</span></section>`;
}
function activarLecturaPobre() {
  document.querySelectorAll("[data-acepta-lectura]").forEach(b => b.addEventListener("click", async () => {
    b.disabled = true;
    try {
      S.ajustes = await api("aceptar_lectura", { porcentaje: +b.dataset.aceptaLectura });
      aviso(`Aceptado: ya no se avisará de lecturas del ${b.dataset.aceptaLectura} % o más`); pintar();
    } catch (e) { b.disabled = false; aviso(e.message, true); }
  }));
}
function notificacionesHTML() {
  const ns = (AV && AV.notificaciones) || [];
  if (!ns.length) return "";
  const nuevas = ns.filter(n => !n.visto), viejas = ns.filter(n => n.visto).slice(0, 5);
  const fila = n => `<div class="dato ${n.visto ? "" : "nuevo"}"><span>${ico(n.tipo === "parecido" ? "user" : n.tipo.startsWith("correo") ? "mail" : "folder", 15)} ${esc(n.mensaje)}</span><span class="acciones">
      ${n.tipo === "correo_apto" && n.lote_id ? `<a class="btn peq" href="#motor/${n.lote_id}">Ver lote</a>` : ""}
      ${n.expediente_id && n.expediente ? `<a class="btn peq" href="#expediente/${n.expediente_id}">Revisar expediente</a>` : ""}
      ${n.tipo === "parecido" && !n.visto && n.datos && /"(nombre|dni)"/.test(n.datos) ? `<button class="btn peq" data-noti-cambiar="${n.id}">Cambiar por los del documento</button>` : ""}
      ${n.tipo === "correo_office" && !n.visto ? `<button class="btn peq pri" data-correo-resp="si" data-id="${n.id}">${ico("check", 14)}Sí, es apto</button><button class="btn peq" data-correo-resp="no" data-id="${n.id}">No</button><button class="btn peq peligro" data-correo-resp="bloquear" data-id="${n.id}">No y bloquear remitente</button>` : ""}
      ${n.visto ? '<span class="muted">visto</span>' : n.tipo === "correo_office" ? "" : `<button class="btn peq" data-noti-visto="${n.id}">${ico("check", 14)}${n.tipo === "parecido" ? "Visto (dejar los míos)" : "Visto"}</button>`}</span></div>`;
  return `<section class="tarjeta"><div class="cab"><div><h2>Avisos del contexto y del correo</h2><span class="sub">Expedientes creados solos, datos parecidos a los que metiste a mano y correos que necesitan tu decisión. Dales «Visto» (o contesta) para que salgan de la campanita.</span></div>
    ${nuevas.length > 1 ? `<button class="btn" data-noti-visto="todas">Marcar todos como vistos</button>` : ""}</div>
    ${nuevas.map(fila).join("") || '<span class="sub">Nada nuevo.</span>'}${viejas.length ? `<details><summary class="sub">Vistos antes</summary>${viejas.map(fila).join("")}</details>` : ""}</section>`;
}
function activarNotificaciones() {
  document.querySelectorAll("[data-correo-resp]").forEach(b => b.addEventListener("click", async () => {
    const r = b.dataset.correoResp;
    if (r === "bloquear" && !confirm("¿Bloquear a este remitente? Sus correos se ignorarán siempre.")) return;
    try { await api("correo_respuesta", { id: +b.dataset.id, respuesta: r }); aviso(r === "si" ? "Aceptado: se recoge la documentación del correo" : "Ignorado: se le quita la etiqueta al correo"); }
    catch (e) { aviso(e.message, true); }
    await refrescar(false); await ir();
  }));
  document.querySelectorAll("[data-noti-cambiar]").forEach(b => b.addEventListener("click", async () => {
    if (!confirm("¿Cambiar el nombre o el DNI de la ficha por los leídos en el documento? Se renombran sus archivos.")) return;
    try { await api("notificacion_cambiar", { id: +b.dataset.notiCambiar }); aviso("Ficha cambiada"); } catch (e) { aviso(e.message, true); }
    await refrescar(false); await ir();
  }));
  document.querySelectorAll("[data-noti-visto]").forEach(b => b.addEventListener("click", async () => {
    await api("notificacion_vista", b.dataset.notiVisto === "todas" ? {} : { id: +b.dataset.notiVisto });
    await refrescar(false); await ir();
  }));
}
