/* Observatorio BitRate — frontend estático (sin dependencias). */
(() => {
  "use strict";
  const $ = (s) => document.querySelector(s);
  const PAGE = 20;
  const MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const defang = (s) => String(s).replace(/^http/i, "hxxp").replace(/\./g, "[.]");
  const fmtDate = (d) => (d ? d.slice(0, 10).split("-").reverse().join("/") : "—");
  const vDate = (v) => v.published || v.discovered || v.first_seen || "";
  const daysAgo = (d) => (Date.now() - new Date(d.replace(" ", "T") + (d.endsWith("Z") ? "" : "Z"))) / 864e5;
  const nf = new Intl.NumberFormat("es-AR");

  async function load(name) {
    const r = await fetch(`data/${name}.json`, { cache: "no-cache" });
    if (!r.ok) throw new Error(name);
    return r.json();
  }

  /* ---------- Tooltip ---------- */
  const tip = $("#tip");
  function showTip(html, x, y) {
    tip.innerHTML = html; tip.hidden = false;
    const w = tip.offsetWidth;
    tip.style.left = Math.min(window.innerWidth - w - 8, x + 14) + "px";
    tip.style.top = y - 44 + "px";
  }
  const hideTip = () => (tip.hidden = true);

  /* ---------- KPIs / header ---------- */
  function renderKpis(stats) {
    document.querySelectorAll("[data-k]").forEach((el) => {
      const target = stats.totals[el.dataset.k] ?? 0;
      const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
      if (reduce || target < 2) { el.textContent = nf.format(target); return; }
      const t0 = performance.now();
      const step = (t) => {
        const p = Math.min(1, (t - t0) / 900);
        el.textContent = nf.format(Math.round(target * (1 - Math.pow(1 - p, 3))));
        if (p < 1) requestAnimationFrame(step);
      };
      requestAnimationFrame(step);
    });
    const d = new Date(stats.generated_at);
    $("#updated").textContent = "Actualizado " + d.toLocaleString("es-AR", { day: "2-digit", month: "2-digit", hour: "2-digit", minute: "2-digit" });
    if (stats.demo) $("#demoBanner").hidden = false;
  }

  /* ---------- Timeline (barras verticales SVG) ---------- */
  function renderTimeline(rows) {
    const el = $("#timeline");
    const W = el.clientWidth || 900, H = el.clientHeight || 280;
    const m = { t: 22, r: 4, b: 26, l: 34 };
    const iw = W - m.l - m.r, ih = H - m.t - m.b;
    const max = Math.max(4, ...rows.map((r) => r.count));
    const nice = Math.ceil(max / 4) * 4;
    const bw = iw / rows.length, gap = Math.max(6, bw * 0.28);
    const y = (v) => m.t + ih - (v / nice) * ih;
    let s = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none">`;
    for (let i = 0; i <= 4; i++) {
      const v = (nice / 4) * i, yy = y(v);
      s += `<line class="gridline" x1="${m.l}" x2="${W - m.r}" y1="${yy}" y2="${yy}"/>`;
      s += `<text class="axis" x="${m.l - 8}" y="${yy + 4}" text-anchor="end">${v}</text>`;
    }
    rows.forEach((r, i) => {
      const x = m.l + i * bw + gap / 2, w = bw - gap, h = ih - (y(r.count) - m.t);
      const [yy, mm] = r.month.split("-");
      const last = i === rows.length - 1;
      const rad = Math.min(4, w / 2, h);
      // barra con extremo superior redondeado (4px) anclada a la base
      const top = y(r.count);
      const path = h > 0
        ? `M${x},${m.t + ih} V${top + rad} Q${x},${top} ${x + rad},${top} H${x + w - rad} Q${x + w},${top} ${x + w},${top + rad} V${m.t + ih} Z`
        : "";
      s += `<path class="bar ${last ? "" : "past"}" data-i="${i}" d="${path}"/>`;
      if (last && r.count > 0) s += `<text class="val" x="${x + w / 2}" y="${top - 7}" text-anchor="middle">${r.count}</text>`;
      s += `<text class="axis" x="${x + w / 2}" y="${H - 6}" text-anchor="middle">${MESES[+mm - 1]}${mm === "01" || i === 0 ? " " + yy.slice(2) : ""}</text>`;
      s += `<rect class="hit" data-i="${i}" x="${m.l + i * bw}" y="${m.t}" width="${bw}" height="${ih}"/>`;
    });
    el.innerHTML = s + "</svg>";
    el.querySelectorAll(".hit").forEach((h) => {
      const i = +h.dataset.i, r = rows[i], bar = el.querySelector(`.bar[data-i="${i}"]`);
      const [yy, mm] = r.month.split("-");
      h.addEventListener("mousemove", (e) => { bar.classList.add("on"); showTip(`${MESES[+mm - 1]} ${yy}<br><b>${r.count}</b> víctima${r.count === 1 ? "" : "s"}`, e.clientX, e.clientY); });
      h.addEventListener("mouseleave", () => { bar.classList.remove("on"); hideTip(); });
    });
  }

  /* ---------- Barras horizontales ---------- */
  function renderHbars(sel, rows, upper = false) {
    const el = $(sel);
    if (!rows || !rows.length) { el.innerHTML = `<p class="empty">Sin datos todavía.</p>`; return; }
    const max = Math.max(...rows.map((r) => r.count));
    el.innerHTML = rows.slice(0, 8).map((r) => `
      <div class="hbar" title="${esc(r.name)}: ${r.count}">
        <span class="hbar-l">${esc(upper ? r.name.toUpperCase() : r.name)}</span>
        <span class="hbar-t"><span class="hbar-f" style="width:${(r.count / max) * 100}%"></span></span>
        <span class="hbar-v">${nf.format(r.count)}</span>
      </div>`).join("");
  }

  /* ---------- Tabla genérica con filtros y paginado ---------- */
  function table({ rows, body, pager, count, filters, match, row, unit }) {
    let page = 0;
    const apply = () => {
      const f = filters.map((x) => x.value.trim().toLowerCase());
      const list = rows.filter((r) => match(r, f));
      const pages = Math.max(1, Math.ceil(list.length / PAGE));
      page = Math.min(page, pages - 1);
      const slice = list.slice(page * PAGE, page * PAGE + PAGE);
      $(body).innerHTML = slice.length ? slice.map(row).join("") :
        `<tr><td colspan="6" class="empty">No hay resultados para ese filtro.</td></tr>`;
      $(count).textContent = `${nf.format(list.length)} ${unit}`;
      const pg = $(pager);
      if (pages <= 1) { pg.innerHTML = ""; return list; }
      const btn = (label, p, dis, cur) => `<button type="button" data-p="${p}" ${dis ? "disabled" : ""} ${cur ? 'aria-current="true"' : ""}>${label}</button>`;
      let h = btn("‹", page - 1, page === 0);
      const from = Math.max(0, Math.min(page - 2, pages - 5));
      for (let p = from; p < Math.min(pages, from + 5); p++) h += btn(p + 1, p, false, p === page);
      pg.innerHTML = h + btn("›", page + 1, page >= pages - 1);
      pg.querySelectorAll("button").forEach((b) => b.addEventListener("click", () => { page = +b.dataset.p; apply(); }));
      return list;
    };
    filters.forEach((x) => x.addEventListener("input", () => { page = 0; apply(); }));
    apply();
    return () => rows.filter((r) => match(r, filters.map((x) => x.value.trim().toLowerCase())));
  }

  function fillSelect(sel, values, upper) {
    const el = $(sel);
    [...new Set(values.filter(Boolean))].sort().forEach((v) => {
      const o = document.createElement("option"); o.value = v.toLowerCase(); o.textContent = upper ? v.toUpperCase() : v; el.append(o);
    });
  }

  function renderVictims(victims) {
    fillSelect("#vGroup", victims.map((v) => v.group_name), true);
    fillSelect("#vSector", victims.map((v) => v.sector));
    table({
      rows: victims, body: "#vBody", pager: "#vPager", count: "#vCount", unit: "víctimas",
      filters: [$("#vSearch"), $("#vGroup"), $("#vSector")],
      match: (v, [q, g, s]) => (!q || v.name.toLowerCase().includes(q)) && (!g || v.group_name === g) && (!s || (v.sector || "").toLowerCase() === s),
      row: (v) => `<tr>
        <td>${fmtDate(vDate(v))}</td>
        <td>${esc(v.name)}${daysAgo(vDate(v) || "1970-01-01") < 3 ? '<span class="new">NUEVO</span>' : ""}</td>
        <td><span class="tag">${esc(v.group_name)}</span></td>
        <td>${esc(v.sector || "—")}</td></tr>`,
    });
  }

  function renderIocs(iocs) {
    const getFiltered = table({
      rows: iocs, body: "#iBody", pager: "#iPager", count: "#iCount", unit: "indicadores",
      filters: [$("#iSearch"), $("#iType")],
      match: (i, [q, t]) => (!t || i.ioc_type === t) &&
        (!q || [i.value, i.malware, i.as_name, i.asn && "as" + i.asn].join(" ").toLowerCase().includes(q)),
      row: (i) => `<tr>
        <td>${fmtDate(i.first_seen)}</td>
        <td><span class="ioc">${esc(defang(i.value))}</span><button class="copy" type="button" data-v="${esc(i.value)}" title="Copiar valor original">copiar</button></td>
        <td>${esc(i.malware || "—")}</td>
        <td>${i.asn ? `AS${i.asn}<br><span class="muted">${esc(i.as_name || "")}</span>` : `<span class="muted">${esc(i.reason || "—")}</span>`}</td>
        <td>${i.reference ? `<a href="${esc(i.reference)}" rel="noopener nofollow" target="_blank">${esc(i.source)}</a>` : esc(i.source)}</td></tr>`,
    });
    $("#iBody").addEventListener("click", (e) => {
      const b = e.target.closest(".copy"); if (!b) return;
      navigator.clipboard?.writeText(b.dataset.v).then(() => { b.textContent = "copiado"; setTimeout(() => (b.textContent = "copiar"), 1200); });
    });
    $("#iCsv").addEventListener("click", () => {
      const cols = ["first_seen", "value", "ioc_type", "threat", "malware", "asn", "as_name", "source", "reference"];
      const q = (v) => `"${String(v ?? "").replace(/"/g, '""')}"`;
      const csv = [cols.join(","), ...getFiltered().map((i) => cols.map((c) => q(i[c])).join(","))].join("\n");
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
      a.download = `observatorio-bitrate-iocs-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
    });
  }

  async function init() {
    try {
      const [stats, victims, iocs] = await Promise.all([load("stats"), load("victims"), load("iocs")]);
      renderKpis(stats);
      renderTimeline(stats.timeline);
      renderHbars("#groups", stats.top_groups, true);
      renderHbars("#sectors", stats.sectors);
      renderHbars("#asns", stats.top_asns);
      renderHbars("#malware", stats.malware);
      renderVictims(victims);
      renderIocs(iocs);
      let t; addEventListener("resize", () => { clearTimeout(t); t = setTimeout(() => renderTimeline(stats.timeline), 150); });
    } catch (e) {
      $("#updated").textContent = "Sin datos";
      document.querySelector("main").insertAdjacentHTML("afterbegin",
        `<p class="wrap empty">No se pudieron cargar los datos. Corré <code>python -m collector collect</code> o <code>demo</code>.</p>`);
      console.error(e);
    }
  }
  init();
})();
