/* Observatorio BitRate — frontend estático (sin dependencias). */
(() => {
  "use strict";
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];
  const PAGE = 20;
  const STALE_HOURS = 6;
  const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  const MESES_L = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const defang = (s) => String(s).replace(/^http/i, "hxxp").replace(/\./g, "[.]");
  const safeUrl = (u) => { try { const x = new URL(u); return /^https?:$/.test(x.protocol) ? x.href : null; } catch { return null; } };
  const fmtDate = (d) => (d ? d.slice(0, 10).split("-").reverse().join("/") : "—");
  const vDate = (v) => v.published || v.discovered || v.first_seen || "";
  const toDate = (d) => new Date(d.replace(" ", "T") + (/[zZ]|[+-]\d\d:?\d\d$/.test(d) ? "" : "Z"));
  const daysAgo = (d) => (Date.now() - toDate(d)) / 864e5;
  const nf = new Intl.NumberFormat("es-AR");
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const isNarrow = () => matchMedia("(max-width: 640px)").matches;

  async function load(name) {
    const r = await fetch(`data/${name}.json`, { cache: "no-cache" });
    if (!r.ok) throw new Error(`${name}: HTTP ${r.status}`);
    return r.json();
  }

  /* ---------- Tooltip (mouse y touch) ---------- */
  const tip = $("#tip");
  function showTip(html, x, y) {
    tip.innerHTML = html; tip.hidden = false;
    const w = tip.offsetWidth, h = tip.offsetHeight;
    tip.style.left = Math.max(8, Math.min(innerWidth - w - 8, x - w / 2)) + "px";
    tip.style.top = Math.max(8, y - h - 14) + "px";
  }
  const hideTip = () => { tip.hidden = true; };
  addEventListener("scroll", hideTip, { passive: true });

  /* ---------- Tiempo relativo ---------- */
  function relTime(date) {
    const min = Math.round((Date.now() - date) / 6e4);
    if (min < 1) return "recién";
    if (min < 60) return `hace ${min} min`;
    const h = Math.round(min / 60);
    if (h < 48) return `hace ${h} h`;
    return `hace ${Math.round(h / 24)} días`;
  }

  /* ---------- KPIs / header ---------- */
  function animateNumber(el, target) {
    if (reduceMotion || target < 2) { el.textContent = nf.format(target); return; }
    const t0 = performance.now();
    const step = (t) => {
      const p = Math.min(1, (t - t0) / 900);
      el.textContent = nf.format(Math.round(target * (1 - Math.pow(1 - p, 3))));
      if (p < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  function renderKpis(stats) {
    const T = stats.totals || {};
    $$("[data-k]").forEach((el) => animateNumber(el, T[el.dataset.k] ?? 0));
    $$("[data-d]").forEach((el) => {
      const cur = T[el.dataset.d], prev = T[el.dataset.prev];
      if (cur == null || prev == null) { el.textContent = ""; return; }
      const diff = cur - prev;
      if (diff === 0) { el.innerHTML = `= igual ${esc(el.dataset.label)}`; return; }
      const cls = diff > 0 ? "up" : "down";
      el.innerHTML = `<b class="${cls}">${diff > 0 ? "▲ +" : "▼ "}${nf.format(diff)}</b> ${esc(el.dataset.label)}`;
    });
    if (T.victims != null) {
      $("#kpiTotal").textContent = `Histórico: ${nf.format(T.victims)} víctimas reivindicadas por ${nf.format(T.groups ?? 0)} grupos distintos.`;
    }

    const live = $("#live"), upd = $("#updated");
    const d = new Date(stats.generated_at);
    if (!isNaN(d)) {
      const full = d.toLocaleString("es-AR", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
      const paint = () => {
        upd.textContent = relTime(d);
        const stale = (Date.now() - d) / 36e5 > STALE_HOURS;
        live.classList.toggle("stale", stale);
        live.title = (stale ? "Los datos tienen demora. " : "") + "Última actualización: " + full;
      };
      paint();
      setInterval(paint, 60e3);
    }
    if (stats.demo) $("#demoBanner").hidden = false;
  }

  /* ---------- Timeline (barras verticales SVG) ---------- */
  function renderTimeline(rows) {
    const el = $("#timeline");
    if (!rows || !rows.length) { el.innerHTML = `<p class="empty">Sin datos todavía.</p>`; return; }
    const W = el.clientWidth || 900, H = el.clientHeight || 280;
    const m = { t: 22, r: 4, b: 26, l: 30 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const max = Math.max(4, ...rows.map((r) => r.count));
    const nice = Math.ceil(max / 4) * 4;
    const bw = iw / rows.length, gap = Math.max(4, bw * 0.28);
    const y = (v) => m.t + ih - (v / nice) * ih;
    const every = bw < 30 ? 3 : bw < 46 ? 2 : 1; // cuántos meses saltear en el eje
    const lastFull = rows.findLastIndex ? rows.findLastIndex((r) => !r.partial) : rows.length - 1;

    let s = `<svg viewBox="0 0 ${W} ${H}" aria-hidden="true"><defs><pattern id="hatch" width="5" height="5" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="2" height="5" fill="rgba(255,0,0,.6)"/></pattern></defs>`;
    for (let i = 0; i <= 4; i++) {
      const v = (nice / 4) * i, yy = y(v);
      s += `<line class="gridline" x1="${m.l}" x2="${W - m.r}" y1="${yy}" y2="${yy}"/>`;
      s += `<text class="axis" x="${m.l - 8}" y="${yy + 4}" text-anchor="end">${v}</text>`;
    }
    rows.forEach((r, i) => {
      const x = m.l + i * bw + gap / 2, w = bw - gap, h = ih - (y(r.count) - m.t);
      const [yy, mm] = r.month.split("-");
      const top = y(r.count);
      const rad = Math.min(4, w / 2, h);
      const path = h > 0
        ? `M${x},${m.t + ih} V${top + rad} Q${x},${top} ${x + rad},${top} H${x + w - rad} Q${x + w},${top} ${x + w},${top + rad} V${m.t + ih} Z`
        : `M${x},${m.t + ih - 1} H${x + w} V${m.t + ih} H${x} Z`;
      const cls = r.partial ? "partial" : i === lastFull ? "last" : "";
      s += `<path class="bar ${cls}" data-i="${i}" d="${path}"/>`;
      if ((r.partial || i === lastFull) && r.count > 0) s += `<text class="val" x="${x + w / 2}" y="${top - 7}" text-anchor="middle">${r.count}</text>`;
      const fromEnd = rows.length - 1 - i;
      if (fromEnd % every === 0) {
        const lbl = MESES[+mm - 1] + (mm === "01" || i < every ? " " + yy.slice(2) : "");
        s += `<text class="axis" x="${x + w / 2}" y="${H - 6}" text-anchor="middle">${lbl}</text>`;
      }
      s += `<rect class="hit" data-i="${i}" x="${m.l + i * bw}" y="${m.t}" width="${bw}" height="${ih}"/>`;
    });
    el.innerHTML = s + "</svg>";

    const label = (r) => {
      const [yy, mm] = r.month.split("-");
      return `${MESES_L[+mm - 1]} ${yy}${r.partial ? " (en curso)" : ""}<br><b>${nf.format(r.count)}</b> víctima${r.count === 1 ? "" : "s"}`;
    };
    const clear = () => { el.classList.remove("hovering"); $$(".bar.on", el).forEach((b) => b.classList.remove("on")); hideTip(); };
    const activate = (hit, cx) => {
      const i = +hit.dataset.i;
      $$(".bar.on", el).forEach((b) => b.classList.remove("on"));
      $(`.bar[data-i="${i}"]`, el).classList.add("on");
      el.classList.add("hovering");
      const rect = hit.getBoundingClientRect();
      showTip(label(rows[i]), cx ?? rect.left + rect.width / 2, rect.top + 20);
    };
    el.onpointermove = (e) => { if (e.pointerType === "mouse" && e.target.classList.contains("hit")) activate(e.target, e.clientX); };
    el.onpointerleave = (e) => { if (e.pointerType === "mouse") clear(); };
    el.onclick = (e) => { if (e.target.classList.contains("hit")) activate(e.target); };
    document.addEventListener("pointerdown", (e) => { if (!el.contains(e.target)) clear(); }, { passive: true });

    // Tabla accesible para lectores de pantalla
    $("#timelineTable tbody").innerHTML = rows.map((r) => {
      const [yy, mm] = r.month.split("-");
      return `<tr><td>${MESES_L[+mm - 1]} ${yy}${r.partial ? " (en curso)" : ""}</td><td>${r.count}</td></tr>`;
    }).join("");
  }

  /* ---------- Barras horizontales ---------- */
  function renderHbars(sel, rows, upper = false) {
    const el = $(sel);
    if (!rows || !rows.length) { el.innerHTML = `<p class="empty">Sin datos todavía.</p>`; return; }
    const top = rows.slice(0, 8);
    const max = Math.max(...top.map((r) => r.count));
    el.innerHTML = top.map((r) => `
      <div class="hbar" title="${esc(r.name)}: ${r.count}">
        <span class="hbar-l">${esc(upper ? r.name.toUpperCase() : r.name)}</span>
        <span class="hbar-t"><span class="hbar-f" data-w="${((r.count / max) * 100).toFixed(1)}"></span></span>
        <span class="hbar-v">${nf.format(r.count)}</span>
      </div>`).join("");
    // el ancho se setea por CSSOM (compatible con la CSP, sin estilos inline)
    requestAnimationFrame(() => $$(".hbar-f", el).forEach((f) => { f.style.width = f.dataset.w + "%"; }));
  }

  function setupRange(target, rowsByRange, upper) {
    const seg = $(`.seg[data-target="${target}"]`);
    const has12 = rowsByRange["12m"] && rowsByRange["12m"].length;
    if (!has12) { seg.hidden = true; renderHbars("#" + target, rowsByRange.all, upper); return; }
    const set = (range) => {
      $$("button", seg).forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.range === range)));
      renderHbars("#" + target, rowsByRange[range], upper);
    };
    seg.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) set(b.dataset.range); });
    set("12m");
  }

  /* ---------- Tabla genérica con filtros y paginado ---------- */
  function table({ rows, body, pager, count, filters, match, row, unit, cols, section }) {
    let page = 0;
    const current = () => {
      const f = filters.map((x) => x.value.trim().toLowerCase());
      return rows.filter((r) => match(r, f));
    };
    const apply = (scroll = false) => {
      const list = current();
      const pages = Math.max(1, Math.ceil(list.length / PAGE));
      page = Math.max(0, Math.min(page, pages - 1));
      const slice = list.slice(page * PAGE, page * PAGE + PAGE);
      $(body).innerHTML = slice.length ? slice.map(row).join("") :
        `<tr><td colspan="${cols}" class="empty">${rows.length ? "No hay resultados para ese filtro." : "Todavía no hay registros."}</td></tr>`;
      $(count).textContent = `${nf.format(list.length)} ${list.length === 1 ? unit[0] : unit[1]}`;
      const pg = $(pager);
      if (scroll) $(section).scrollIntoView({ behavior: reduceMotion ? "auto" : "smooth", block: "start" });
      if (pages <= 1) { pg.innerHTML = ""; return; }
      const btn = (label, p, dis, cur, aria) => `<button type="button" data-p="${p}" ${dis ? "disabled" : ""} ${cur ? 'aria-current="page"' : ""} aria-label="${aria}">${label}</button>`;
      const span = isNarrow() ? 3 : 5;
      let h = btn("‹", page - 1, page === 0, false, "Página anterior");
      const from = Math.max(0, Math.min(page - Math.floor(span / 2), pages - span));
      for (let p = from; p < Math.min(pages, from + span); p++) h += btn(p + 1, p, false, p === page, `Página ${p + 1}`);
      pg.innerHTML = h + btn("›", page + 1, page >= pages - 1, false, "Página siguiente");
    };
    $(pager).addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b || b.disabled) return;
      page = +b.dataset.p; apply(true);
    });
    let t;
    filters.forEach((x) => x.addEventListener("input", () => { clearTimeout(t); t = setTimeout(() => { page = 0; apply(); }, 120); }));
    apply();
    return current;
  }

  function fillSelect(sel, values, upper) {
    const el = $(sel);
    const counts = new Map();
    values.filter(Boolean).forEach((v) => counts.set(v, (counts.get(v) || 0) + 1));
    [...counts.keys()].sort((a, b) => a.localeCompare(b, "es")).forEach((v) => {
      const o = document.createElement("option");
      o.value = v.toLowerCase();
      o.textContent = `${upper ? v.toUpperCase() : v} (${counts.get(v)})`;
      el.append(o);
    });
  }

  function renderVictims(victims) {
    fillSelect("#vGroup", victims.map((v) => v.group_name), true);
    fillSelect("#vSector", victims.map((v) => v.sector || "Sin datos"));
    table({
      rows: victims, body: "#vBody", pager: "#vPager", count: "#vCount", unit: ["víctima", "víctimas"], cols: 4, section: "#victimas",
      filters: [$("#vSearch"), $("#vGroup"), $("#vSector")],
      match: (v, [q, g, s]) => (!q || [v.name, v.website, v.group_name].join(" ").toLowerCase().includes(q)) &&
        (!g || v.group_name === g) && (!s || (v.sector || "sin datos").toLowerCase() === s),
      row: (v) => {
        const d = vDate(v);
        const isNew = d && daysAgo(d) < 3;
        const site = v.website && v.website.toLowerCase() !== v.name.toLowerCase() ? `<span class="site">${esc(defang(v.website.replace(/^https?:\/\//i, "")))}</span>` : "";
        return `<tr>
        <td class="c-date" data-label="Fecha">${fmtDate(d)}</td>
        <td class="c-org" data-label="Organización">${esc(v.name)}${isNew ? '<span class="new">NUEVO</span>' : ""}${site}</td>
        <td class="c-group" data-label="Grupo"><span class="tag">${esc(v.group_name)}</span></td>
        <td class="c-sector" data-label="Sector">${esc(v.sector || "Sin datos")}</td></tr>`;
      },
    });
  }

  function renderIocs(iocs) {
    const getFiltered = table({
      rows: iocs, body: "#iBody", pager: "#iPager", count: "#iCount", unit: ["indicador", "indicadores"], cols: 5, section: "#iocs",
      filters: [$("#iSearch"), $("#iType")],
      match: (i, [q, t]) => (!t || i.ioc_type === t) &&
        (!q || [i.value, defang(i.value), i.malware, i.as_name, i.asn && "as" + i.asn].join(" ").toLowerCase().includes(q)),
      row: (i) => {
        const ref = safeUrl(i.reference);
        return `<tr>
        <td class="c-date" data-label="Visto">${fmtDate(i.first_seen)}</td>
        <td class="c-ioc" data-label="Indicador"><span class="ioc">${esc(defang(i.value))}</span><button class="copy" type="button" data-v="${esc(i.value)}" aria-label="Copiar indicador original">copiar</button></td>
        <td class="c-mal" data-label="Malware">${esc(i.malware || "—")}</td>
        <td class="c-net" data-label="Red">${i.asn ? `AS${esc(i.asn)}<br><span class="muted">${esc(i.as_name || "")}</span>` : `<span class="muted">${esc(i.reason || "—")}</span>`}</td>
        <td class="c-src" data-label="Fuente">${ref ? `<a href="${esc(ref)}" rel="noopener noreferrer nofollow" target="_blank">${esc(i.source)}</a>` : esc(i.source)}</td></tr>`;
      },
    });
    $("#iBody").addEventListener("click", (e) => {
      const b = e.target.closest(".copy"); if (!b || !navigator.clipboard) return;
      navigator.clipboard.writeText(b.dataset.v).then(() => { b.textContent = "copiado"; setTimeout(() => (b.textContent = "copiar"), 1200); });
    });
    const csvBtn = $("#iCsv");
    csvBtn.disabled = !iocs.length;
    csvBtn.addEventListener("click", () => {
      const cols = ["first_seen", "value", "ioc_type", "threat", "malware", "asn", "as_name", "source", "reference"];
      // Prefijo ' para evitar inyección de fórmulas al abrir el CSV en Excel
      const q = (v) => { let s = String(v ?? ""); if (/^[=+\-@\t\r]/.test(s)) s = "'" + s; return `"${s.replace(/"/g, '""')}"`; };
      const csv = "﻿" + [cols.join(","), ...getFiltered().map((i) => cols.map((c) => q(i[c])).join(","))].join("\r\n");
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      a.download = `observatorio-bitrate-iocs-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.append(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    });
  }

  /* ---------- Navegación: sección activa ---------- */
  function setupNav() {
    const links = $$(".nav a");
    const map = new Map(links.map((a) => [a.getAttribute("href").slice(1), a]));
    if (!("IntersectionObserver" in window)) return;
    const io = new IntersectionObserver((entries) => {
      entries.forEach((en) => {
        if (!en.isIntersecting) return;
        links.forEach((a) => a.removeAttribute("aria-current"));
        const a = map.get(en.target.id);
        if (!a) return;
        a.setAttribute("aria-current", "true");
        // Solo desplaza el menú en horizontal (mobile). Nunca usar scrollIntoView acá:
        // el menú está en un header sticky y eso arrastra la página entera.
        const nav = a.parentElement;
        if (nav.scrollWidth > nav.clientWidth) {
          const target = a.offsetLeft - (nav.clientWidth - a.offsetWidth) / 2;
          nav.scrollTo({ left: Math.max(0, target), behavior: reduceMotion ? "auto" : "smooth" });
        }
      });
    }, { rootMargin: "-45% 0px -50% 0px" });
    map.forEach((_, id) => { const s = document.getElementById(id); if (s) io.observe(s); });
  }

  async function init() {
    setupNav();
    try {
      const [stats, victims, iocs] = await Promise.all([load("stats"), load("victims"), load("iocs")]);
      renderKpis(stats);
      renderTimeline(stats.timeline);
      setupRange("groups", { "12m": stats.top_groups_12m, all: stats.top_groups }, true);
      setupRange("sectors", { "12m": stats.sectors_12m, all: stats.sectors });
      renderHbars("#asns", stats.top_asns);
      renderHbars("#malware", stats.malware);
      renderVictims(victims);
      renderIocs(iocs);
      let t, lastW = innerWidth;
      addEventListener("resize", () => {
        if (innerWidth === lastW) return; // ignora el resize por la barra de direcciones en mobile
        lastW = innerWidth;
        clearTimeout(t); t = setTimeout(() => renderTimeline(stats.timeline), 150);
      });
    } catch (e) {
      $("#updated").textContent = "sin datos";
      $("main").insertAdjacentHTML("afterbegin",
        `<p class="wrap notice" role="alert">No pudimos cargar los datos en este momento. Probá recargar la página en unos minutos. Si el problema sigue, avisanos a <a href="mailto:bitrateinfosec@gmail.com">bitrateinfosec@gmail.com</a>.</p>`);
      $$("#vBody, #iBody").forEach((b) => (b.innerHTML = `<tr><td colspan="5" class="empty">Sin datos.</td></tr>`));
      console.error("[Observatorio]", e);
    }
  }
  init();
})();
