/* device-check · núcleo compartido
 * Detecta el dispositivo con las APIs del navegador. Lo usan todas las versiones (android, ios, macos, windows).
 * No envía datos a ningún lado.
 */
(() => {
  "use strict";

  // Referencia del benchmark: Samsung Galaxy Tab S4 (Snapdragon 835, 2018)
  const REFERENCIA = { nombre: "Galaxy Tab S4", single: 726, multi: 4652 };

  const PAGINAS = { android: "android/", ios: "ios/", macos: "macos/", windows: "windows/" };
  const URL_PUBLICA = "https://bridemirci.github.io/device-check/";

  // GPU Adreno → chip Snapdragon (solo los casos sin ambigüedad)
  const ADRENO = {
    "506": "Snapdragon 625/450", "509": "Snapdragon 636", "512": "Snapdragon 660",
    "530": "Snapdragon 820/821", "540": "Snapdragon 835", "615": "Snapdragon 670",
    "616": "Snapdragon 710/712", "618": "Snapdragon 720G/730G/732G", "620": "Snapdragon 765G/768G",
    "630": "Snapdragon 845", "640": "Snapdragon 855/860", "642L": "Snapdragon 778G",
    "650": "Snapdragon 865/870", "660": "Snapdragon 888", "730": "Snapdragon 8 Gen 1",
    "740": "Snapdragon 8 Gen 2", "750": "Snapdragon 8 Gen 3", "830": "Snapdragon 8 Elite",
  };

  const MACOS = { 26: "Tahoe", 15: "Sequoia", 14: "Sonoma", 13: "Ventura", 12: "Monterey", 11: "Big Sur" };

  // iPhone por tamaño de pantalla en puntos (lado corto x lado largo @ escala). Varios modelos comparten tamaño.
  const IPHONES = {
    "440x956@3": "iPhone 16 Pro Max / 17 Pro Max",
    "420x912@3": "iPhone Air",
    "402x874@3": "iPhone 16 Pro / 17 / 17 Pro",
    "430x932@3": "iPhone 14 Pro Max / 15 Plus / 15 Pro Max / 16 Plus",
    "393x852@3": "iPhone 14 Pro / 15 / 15 Pro / 16",
    "428x926@3": "iPhone 12 Pro Max / 13 Pro Max / 14 Plus",
    "390x844@3": "iPhone 12 / 13 / 14 / 16e",
    "375x812@3": "iPhone X / XS / 11 Pro / 12 mini / 13 mini",
    "414x896@3": "iPhone XS Max / 11 Pro Max",
    "414x896@2": "iPhone XR / 11",
    "414x736@3": "iPhone 6s Plus / 7 Plus / 8 Plus",
    "375x667@2": "iPhone 6s / 7 / 8 / SE (2.ª y 3.ª gen)",
    "320x568@2": "iPhone SE (1.ª gen)",
  };

  const esc = s => String(s ?? "").replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

  function bytes(b) {
    const u = ["B", "KB", "MB", "GB", "TB"]; let i = 0;
    while (b >= 1024 && i < u.length - 1) { b /= 1024; i++; }
    return (i >= 3 ? b.toFixed(1) : Math.round(b)) + " " + u[i];
  }

  function duracion(seg) {
    const total = Math.round(seg / 60), h = Math.floor(total / 60), m = total % 60;
    return h ? `${h} h ${m} min` : `${m} min`;
  }

  /* ---------- GPU ---------- */

  function gpuCruda() {
    try {
      const gl = document.createElement("canvas").getContext("webgl");
      if (!gl) return "";
      const ext = gl.getExtension("WEBGL_debug_renderer_info");
      const r = gl.getParameter(ext ? ext.UNMASKED_RENDERER_WEBGL : gl.RENDERER) || "";
      gl.getExtension("WEBGL_lose_context")?.loseContext();
      return r;
    } catch { return ""; }
  }

  // "ANGLE (NVIDIA, NVIDIA GeForce RTX 3060 (0x00002504) Direct3D11 vs_5_0 ps_5_0, D3D11)" → "NVIDIA GeForce RTX 3060"
  // "ANGLE (Apple, ANGLE Metal Renderer: Apple M2 Pro, Unspecified Version)" → "Apple M2 Pro"
  function limpiarGpu(r) {
    const angle = r.match(/^ANGLE \(([^,]+), (.+?)(?:, [^,]+)?\)$/);
    if (angle) r = angle[2];
    return r
      .replace(/ANGLE Metal Renderer:\s*/i, "")
      .replace(/\s*\(0x[0-9a-f]+\)/gi, "")
      .replace(/\s*Direct3D.*$/i, "")
      .replace(/\s*OpenGL.*$/i, "")
      .replace(/\s*,\s*Unspecified Version/i, "")
      .replace(/\((?:R|TM)\)/gi, " ")
      .replace(/\s+/g, " ")
      .trim();
  }

  function chipPorGpu(gpu, so) {
    if (!gpu) return null;
    const apple = gpu.match(/Apple (M\d+(?: (?:Pro|Max|Ultra))?)/);
    if (apple) return { nombre: `Apple ${apple[1]}`, probable: false };
    const adreno = gpu.match(/Adreno\s*(\d{3}L?)/i);
    if (adreno && ADRENO[adreno[1]]) return { nombre: `Qualcomm ${ADRENO[adreno[1]]}`, probable: true };
    if (/Adreno.*X1/i.test(gpu)) return { nombre: "Qualcomm Snapdragon X", probable: true };
    if (so === "Android" && /Mali|Immortalis/i.test(gpu)) return { nombre: "Exynos, Tensor o MediaTek (GPU Mali)", probable: true };
    if (so === "Android" && /PowerVR|IMG/i.test(gpu)) return { nombre: "MediaTek (GPU PowerVR)", probable: true };
    return null;
  }

  /* ---------- Navegador ---------- */

  function navegador(ua, marcas) {
    const conocidas = ["Samsung Internet", "Microsoft Edge", "Opera", "Brave", "Google Chrome", "Chromium"];
    for (const n of conocidas) {
      const m = marcas?.find(b => b.brand === n);
      if (m) return `${n === "Google Chrome" ? "Chrome" : n === "Microsoft Edge" ? "Edge" : n} ${m.version.split(".")[0]}`;
    }
    const reglas = [[/SamsungBrowser\/(\d+)/, "Samsung Internet"], [/Firefox\/(\d+)/, "Firefox"], [/FxiOS\/(\d+)/, "Firefox"],
      [/EdgA?\/(\d+)/, "Edge"], [/EdgiOS\/(\d+)/, "Edge"], [/OPR\/(\d+)/, "Opera"], [/CriOS\/(\d+)/, "Chrome"],
      [/Chrome\/(\d+)/, "Chrome"], [/Version\/(\d+(?:\.\d+)?).*Safari/, "Safari"]];
    for (const [re, n] of reglas) { const m = ua.match(re); if (m) return `${n} ${m[1]}`; }
    return "Desconocido";
  }

  /* ---------- Detección principal ---------- */

  async function detectar() {
    const ua = navigator.userAgent;
    const uad = navigator.userAgentData;
    let alta = {};
    try {
      alta = await uad?.getHighEntropyValues(["model", "platformVersion", "architecture", "bitness", "fullVersionList"]) ?? {};
    } catch {}
    const plataforma = uad?.platform || "";
    const d = { ua, modelo: "", modeloProbable: false, notas: [] };

    const android = ua.match(/Android\s([\d.]+)(?:;\s*([^;)]+))?/);
    const ios = ua.match(/(iPhone|iPad|iPod).*?OS (\d+[_\d]*)/);
    const pv = alta.platformVersion || "";
    const pvMayor = parseInt(pv, 10);

    if (plataforma === "Android" || android) {
      d.so = "Android"; d.clave = "android";
      d.versionNum = (pv || android?.[1] || "").split(".")[0];
      d.version = d.versionNum ? `Android ${d.versionNum}` : "Android";
      // Chrome reduce el modelo a "K" y Firefox pone "Mobile": no sirven como modelo
      const modeloUA = android?.[2]?.replace(/\sBuild.*/, "").replace(/^SAMSUNG\s+/i, "").trim();
      d.modelo = alta.model || (modeloUA && !["K", "Mobile", "Tablet"].includes(modeloUA) ? modeloUA : "");
    } else if (ios) {
      d.so = ios[1] === "iPad" ? "iPadOS" : "iOS"; d.clave = "ios";
      d.versionNum = ios[2].replace(/_/g, ".");
      d.version = `${d.so} ${d.versionNum}`;
      d.modelo = ios[1];
    } else if (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1) {
      d.so = "iPadOS"; d.clave = "ios"; d.modelo = "iPad";
      d.versionNum = ua.match(/Version\/([\d.]+)/)?.[1] || "";
      d.version = d.versionNum ? `iPadOS ${d.versionNum}` : "iPadOS";
    } else if (plataforma === "Windows" || /Windows/.test(ua)) {
      d.so = "Windows"; d.clave = "windows";
      if (pv) d.version = pvMayor >= 13 ? "Windows 11" : pvMayor > 0 ? "Windows 10" : "Windows 7 / 8.1";
      else { d.version = /Windows NT 10/.test(ua) ? "Windows 10 u 11" : "Windows"; d.notas.push("Tu navegador no distingue Windows 10 de 11."); }
    } else if (plataforma === "macOS" || /Mac OS X|Macintosh/.test(ua)) {
      d.so = "macOS"; d.clave = "macos";
      if (pvMayor >= 11) { d.versionNum = pv.split(".").slice(0, 2).join("."); d.version = `macOS ${pvMayor}${MACOS[pvMayor] ? ` ${MACOS[pvMayor]}` : ""}`; }
      else { d.version = "macOS"; d.notas.push("Safari y Firefox ocultan la versión exacta de macOS."); }
    } else if (plataforma === "Chrome OS" || /CrOS/.test(ua)) {
      d.so = "ChromeOS"; d.clave = "windows"; d.version = "ChromeOS";
    } else {
      d.so = plataforma || (/Linux/.test(ua) ? "Linux" : "Desconocido"); d.clave = "android"; d.version = d.so;
    }

    const corto = Math.min(screen.width, screen.height), largo = Math.max(screen.width, screen.height);
    d.tipo = d.so === "Android" ? (/Mobile/.test(ua) && corto < 600 ? "celular" : "tablet")
      : d.so === "iOS" ? "celular" : d.so === "iPadOS" ? "tablet" : "computadora";

    const dpr = window.devicePixelRatio || 1;
    if (d.so === "iOS") {
      const m = IPHONES[`${corto}x${largo}@${Math.round(dpr)}`];
      if (m) { d.modelo = m; d.modeloProbable = true; }
    }

    d.navegador = navegador(ua, alta.fullVersionList || uad?.brands);
    const arq = alta.architecture;
    d.arquitectura = arq ? `${arq === "arm" ? "ARM" : arq === "x86" ? "x86" : arq}${alta.bitness ? ` ${alta.bitness}-bit` : ""}` : "";

    d.gpuCruda = gpuCruda();
    d.gpu = limpiarGpu(d.gpuCruda) || null;
    const chip = chipPorGpu(d.gpu, d.so);
    if (chip) { d.chip = chip.nombre; d.chipProbable = chip.probable; }
    else if (d.so === "macOS" && arq) { d.chip = arq === "arm" ? "Apple Silicon" : "Intel"; d.chipProbable = false; }

    d.nucleos = navigator.hardwareConcurrency || null;
    // deviceMemory se redondea y tiene tope en 8 GB por privacidad
    d.ramGB = navigator.deviceMemory || null;
    d.ram = d.ramGB ? (d.ramGB >= 8 ? "8 GB o más" : `~${d.ramGB} GB`) : null;

    const w = Math.round(screen.width * dpr), h = Math.round(screen.height * dpr);
    d.resolucion = `${Math.max(w, h)}x${Math.min(w, h)}`;
    d.puntos = `${largo}x${corto}`;
    d.dpr = Math.round(dpr * 100) / 100;
    d.hdr = matchMedia("(dynamic-range: high)").matches;
    d.gamaP3 = matchMedia("(color-gamut: p3)").matches;
    d.colorBits = screen.colorDepth;
    d.tactil = navigator.maxTouchPoints || 0;
    d.oscuro = matchMedia("(prefers-color-scheme: dark)").matches;

    const c = navigator.connection;
    if (c) d.red = [c.type && c.type !== "unknown" ? c.type : "", c.effectiveType ? c.effectiveType.toUpperCase() : "", c.downlink ? `~${c.downlink} Mb/s` : ""].filter(Boolean).join(" · ");
    d.idioma = navigator.language;
    d.zona = Intl.DateTimeFormat().resolvedOptions().timeZone;
    d.hz = null;
    return d;
  }

  // Frecuencia de la pantalla: contamos cuadros durante un segundo
  function medirHz() {
    return new Promise(res => {
      let cuadros = 0, inicio = null;
      const paso = t => {
        if (inicio === null) inicio = t;
        cuadros++;
        if (t - inicio < 1000) requestAnimationFrame(paso);
        else {
          const f = (cuadros - 1) * 1000 / (t - inicio);
          res([30, 48, 60, 75, 90, 100, 120, 144, 165, 240].reduce((a, b) => Math.abs(b - f) < Math.abs(a - f) ? b : a));
        }
      };
      requestAnimationFrame(paso);
    });
  }

  /* ---------- Batería ---------- */

  async function bateria(alCambiar) {
    try {
      const b = await navigator.getBattery?.();
      if (!b) return null;
      if (alCambiar) ["levelchange", "chargingchange", "chargingtimechange", "dischargingtimechange"].forEach(ev => b.addEventListener(ev, alCambiar));
      return b;
    } catch { return null; }
  }

  function infoBateria(b) {
    if (!b) return null;
    const porcentaje = Math.round(b.level * 100);
    const t = b.charging ? b.chargingTime : b.dischargingTime;
    // Las computadoras sin batería informan 100 % y cargando con tiempo 0
    const sinBateria = porcentaje === 100 && b.charging && b.chargingTime === 0;
    return {
      porcentaje, cargando: b.charging, sinBateria,
      estado: sinBateria ? "Enchufado" : b.charging ? (porcentaje === 100 ? "Completa" : "Cargando") : "Descargando",
      tiempo: Number.isFinite(t) && t > 0 ? t : null,
      tiempoTexto: Number.isFinite(t) && t > 0 ? `${b.charging ? "llena en" : "dura"} ~${duracion(t)}` : null,
    };
  }

  /* ---------- Filas para el bloque tipo neofetch ---------- */

  function filas(d, bat) {
    const cpu = [d.nucleos ? `${d.nucleos} núcleos` : null, d.arquitectura || null].filter(Boolean).join(" · ") || "?";
    const pantalla = `${d.resolucion}${d.hz ? ` @ ${d.hz}Hz` : ""} · x${d.dpr}${d.hdr ? " · HDR" : ""}`;
    const b = infoBateria(bat);
    return [
      ["Dispositivo", d.modelo ? `${d.modelo}${d.modeloProbable ? " (probable)" : ""}` : "no informado por el navegador"],
      ["Tipo", d.tipo],
      ["Sistema", d.version],
      ["Chip", d.chip ? `${d.chip}${d.chipProbable ? " (probable)" : ""}` : "no se pudo deducir"],
      ["CPU", cpu],
      ["GPU", d.gpu || "?"],
      ["Memoria", d.ram || "no informada"],
      ["Pantalla", pantalla],
      ["Batería", b ? (b.sinBateria ? "enchufado / sin batería" : `${b.porcentaje}% · ${b.estado.toLowerCase()}`) : "no disponible"],
      d.red && ["Red", d.red],
      ["Navegador", d.navegador],
      ["Idioma", `${d.idioma} · ${d.zona}`],
    ].filter(Boolean);
  }

  /* ---------- Benchmark ---------- */

  const NUCLEO_BENCH = `
const unidad = () => { let x = 1, s = 0; for (let i = 0; i < 100000; i++) { x = Math.imul(x ^ (x >>> 15), 2246822507) + i | 0; s += Math.sqrt(i) * (x & 255); } return s; };
const correr = ms => { const fin = performance.now() + ms; let n = 0, s = 0; while (performance.now() < fin) { s += unidad(); n++; } return n / (ms / 1000); };
onmessage = e => postMessage(correr(e.data));`;

  function correrWorkers(cantidad, ms) {
    const url = URL.createObjectURL(new Blob([NUCLEO_BENCH], { type: "text/javascript" }));
    return Promise.all(Array.from({ length: cantidad }, () => new Promise((res, rej) => {
      const w = new Worker(url);
      w.onmessage = e => { res(e.data); w.terminate(); };
      w.onerror = err => { rej(err); w.terminate(); };
      w.postMessage(ms);
    }))).finally(() => URL.revokeObjectURL(url)).then(v => v.reduce((a, b) => a + b, 0));
  }

  /** Corre el benchmark (~5 s). alProgresar(etapa, total, resultadoParcial) con etapa 1 = un núcleo, 2 = multinúcleo. */
  async function benchmark(alProgresar = () => {}) {
    const n = navigator.hardwareConcurrency || 4;
    alProgresar(1, n, null);
    const single = Math.round(await correrWorkers(1, 2000));
    alProgresar(2, n, { single });
    const multi = Math.round(await correrWorkers(n, 2500));
    return { single, multi, nucleos: n, vsSingle: Math.round(100 * (single / REFERENCIA.single - 1)), vsMulti: Math.round(100 * (multi / REFERENCIA.multi - 1)) };
  }

  /* ---------- Compartir ---------- */

  function informe(d, bat, bench) {
    const lineas = filas(d, bat).map(([k, v]) => `${k}: ${v}`);
    if (bench) lineas.push(`Benchmark: ${bench.single} (1 núcleo) · ${bench.multi} (multi)`);
    return `device-check\n${lineas.join("\n")}\n${URL_PUBLICA}`;
  }

  /** Devuelve "compartido", "copiado", "cancelado" o "error". */
  async function compartir(texto) {
    try {
      if (navigator.share) { await navigator.share({ title: "Mi dispositivo", text: texto }); return "compartido"; }
      await navigator.clipboard.writeText(texto);
      return "copiado";
    } catch (e) {
      return e?.name === "AbortError" ? "cancelado" : "error";
    }
  }

  /** Links a las otras versiones, relativos a la página actual (que vive en <raíz>/<clave>/). */
  function versiones(actual) {
    const nombres = { android: "Android", ios: "iOS", macos: "macOS", windows: "Windows" };
    return Object.keys(PAGINAS).map(k => ({ clave: k, nombre: nombres[k], url: `../${PAGINAS[k]}`, actual: k === actual }));
  }

  window.DC = { REFERENCIA, PAGINAS, URL_PUBLICA, esc, bytes, duracion, detectar, medirHz, bateria, infoBateria, filas, benchmark, informe, compartir, versiones, limpiarGpu, chipPorGpu, navegador };
})();
