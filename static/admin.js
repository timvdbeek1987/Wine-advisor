// --- Meta-data (landen → regio’s) & druivenlijsten ---
const COUNTRIES = {
  "France": ["Bordeaux","Burgundy","Champagne","Loire","Rhône","Alsace","Languedoc","Provence","Overig…"],
  "Italy": ["Toscana","Piemonte","Veneto","Sicilia","Puglia","Abruzzo","Friuli","Overig…"],
  "Spain": ["Rioja","Ribera del Duero","Rías Baixas","Priorat","Cava","Overig…"],
  "Germany": ["Mosel","Rheingau","Pfalz","Nahe","Baden","Franken","Overig…"],
  "Austria": ["Wachau","Kamptal","Kremstal","Burgenland","Steiermark","Overig…"],
  "Portugal": ["Douro","Dão","Vinho Verde","Alentejo","Bairrada","Overig…"],
  "USA": ["Napa Valley","Sonoma","Willamette Valley","Walla Walla","Finger Lakes","Overig…"],
  "Argentina": ["Mendoza","Salta","Patagonia","Overig…"],
  "Chile": ["Maipo","Colchagua","Casablanca","Aconcagua","Overig…"],
  "South Africa": ["Stellenbosch","Swartland","Paarl","Walker Bay","Hemel-en-Aarde","Overig…"],
  "Australia": ["Barossa","McLaren Vale","Yarra Valley","Margaret River","Hunter Valley","Overig…"],
  "New Zealand": ["Marlborough","Central Otago","Hawke's Bay","Martinborough","Overig…"]
};

const COMMON_GRAPES_WHITE = [
  "Chardonnay","Sauvignon Blanc","Riesling","Chenin Blanc","Pinot Grigio",
  "Gewürztraminer","Grüner Veltliner","Albariño","Viognier"
];
const COMMON_GRAPES_RED = [
  "Pinot Noir","Merlot","Cabernet Sauvignon","Syrah","Grenache",
  "Tempranillo","Sangiovese","Malbec"
];

// DOM helpers
const $ = id => document.getElementById(id);
const axes = ["ZB","MG","LS","PA","GF"];
function setAxisText() { axes.forEach(k => $(`v${k}`).innerText = ` ${$(k).value}`); }
axes.forEach(k => $(k).addEventListener("input", setAxisText));

// Tabs
document.querySelectorAll(".tab").forEach(btn=>{
  btn.addEventListener("click", ()=>{
    document.querySelectorAll(".tab").forEach(t=>t.classList.remove("active"));
    btn.classList.add("active");
    const id = btn.getAttribute("data-tab");
    document.querySelectorAll(".panel").forEach(p=>p.style.display="none");
    $(id).style.display = "";
  });
});

// --- Land / Regio ---
function populateCountries() {
  const cSel = $("country"); if (!cSel) return;
  cSel.innerHTML = "";
  Object.keys(COUNTRIES).forEach(c => {
    const opt = document.createElement("option"); opt.value = c; opt.textContent = c; cSel.appendChild(opt);
  });
  cSel.value = "France"; // default
  populateRegions();
}
function populateRegions() {
  const cSel = $("country"); if (!cSel) return;
  const c = cSel.value;
  const regions = COUNTRIES[c] || ["Overig…"];
  const rSel = $("region"); rSel.innerHTML = "";
  regions.forEach(r => {
    const opt = document.createElement("option"); opt.value = r; opt.textContent = r; rSel.appendChild(opt);
  });
  toggleRegionOther();
}
function toggleRegionOther() {
  const rSel = $("region");
  const other = $("regionOther");
  if (!rSel || !other) return;
  const isOther = rSel.value && rSel.value.toLowerCase().startsWith("overig");
  other.disabled = !isOther;
  other.placeholder = isOther ? "Schrijf hier de regio" : "(niet nodig)";
}
$("country")?.addEventListener("change", populateRegions);
$("region")?.addEventListener("change", toggleRegionOther);

// --- Druiven UI ---
const grapesDiv = $("grapes");
function addGrapeRow(name = "", weight = "") {
  if (!grapesDiv) return;
  const row = document.createElement("div");
  row.className = "grape-row";
  const nameInput = document.createElement("input");
  nameInput.placeholder = "Druivenras (typ of kies hieronder)";
  nameInput.value = name;
  const weightInput = document.createElement("input");
  weightInput.type = "number"; weightInput.step = "0.01"; weightInput.placeholder = "0.5"; weightInput.value = weight;
  const delBtn = document.createElement("button");
  delBtn.textContent = "Verwijder"; delBtn.className = "btn ghost";
  delBtn.addEventListener("click", () => row.remove());
  row.appendChild(nameInput);
  row.appendChild(weightInput);
  row.appendChild(delBtn);
  grapesDiv.appendChild(row);

  // autocomplete via datalist
  const dlId = `dl-${Math.random().toString(36).slice(2)}`;
  const dl = document.createElement("datalist"); dl.id = dlId;
  [...COMMON_GRAPES_WHITE, ...COMMON_GRAPES_RED].forEach(g => {
    const o = document.createElement("option"); o.value = g; dl.appendChild(o);
  });
  document.body.appendChild(dl);
  nameInput.setAttribute("list", dlId);
}
$("addGrape")?.addEventListener("click", () => addGrapeRow());
$("normalize")?.addEventListener("click", () => {
  const rows = [...document.querySelectorAll(".grape-row")];
  const nums = rows.map(r => parseFloat(r.children[1].value || "0") || 0);
  const sum = nums.reduce((a,b)=>a+b,0);
  if (sum <= 0) return;
  rows.forEach((r, i) => r.children[1].value = (nums[i]/sum).toFixed(2));
});
// Prefill
if (grapesDiv) { addGrapeRow(""); addGrapeRow(""); }

// --- Sliders helpers ---
function setSliders(p) { axes.forEach(k => { const el=$(k); if(el) el.value=Math.max(0,Math.min(100,Math.round(p[k]??50))); }); setAxisText(); }
function setLoading(btn, loading) {
  if (!btn) return; btn.disabled = loading;
  const orig = btn.getAttribute("data-label") || btn.textContent;
  if (!btn.getAttribute("data-label")) btn.setAttribute("data-label", orig);
  btn.textContent = loading ? "Even geduld…" : orig;
}
function showMsg(text, ok=false) { const m=$("msg"); if (!m) return; m.textContent=text; m.className = ok ? "ok" : "error"; }

// --- Form lezen ---
function readGrapes() {
  const rows = [...document.querySelectorAll(".grape-row")];
  return rows.map(r => ({
    variety: r.children[0].value.trim(),
    weight: parseFloat(r.children[1].value || "0") || 0
  })).filter(g => g.variety);
}
function resolveRegion() {
  const r = $("region")?.value;
  const other = $("regionOther")?.value?.trim() || "";
  return (r && r.toLowerCase().startsWith("overig")) ? (other || "Overig") : r;
}
function readForm() {
  const grapes = readGrapes();
  return {
    name: $("name")?.value?.trim(),
    producer: $("producer")?.value?.trim() || null,
    color: $("color")?.value || null,        // NIEUW
    sweetness: $("sweetness")?.value || "dry",// NIEUW
    country: $("country")?.value,
    region: resolveRegion(),
    climate: $("climate")?.value,
    grapes,
    vintage: parseInt($("vintage")?.value || "0", 10),
    soil: $("soil")?.value || null,
    oak_months: parseInt($("oak")?.value || "0", 10),
    elevage: $("elevage")?.value?.trim() || null,
    abv: parseFloat($("abv")?.value || "0"),
    purchase_price_eur: parseFloat($("purchase_price")?.value || "0"),
    bottle_size_ml: parseInt($("bottle_size")?.value || "750", 10),
    storage_location: $("storage")?.value || null,
    bottles: parseInt($("bottles")?.value || "1", 10) || 1,
    drinking_from: parseInt($("drink_from")?.value || "0", 10) || null,
    drinking_to: parseInt($("drink_to")?.value || "0", 10) || null,
  };
}

// --- Suggestie drinkvenster ---
// 1) Probeert /api/admin/enrich (als die window meegeeft)
// 2) Valt terug op heuristiek obv kleur/druif/klimaat/jaargang
$("btnSuggestWindow")?.addEventListener("click", async ()=>{
  const msg = $("winMsg");
  try {
    msg.textContent = "Bezig met suggestie…";
    const b = readForm();

    // probeer enrichment
    const res = await fetch("/api/admin/enrich", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({ region: b.region, country: b.country, grape_terms: b.grapes?.map(g=>g.variety)||[], vintage: b.vintage })
    });
    const data = await res.json().catch(()=> ({}));

    let from = null, to = null;
    if (res.ok && data && (data.drinking_window || (data.window_from && data.window_to))) {
      from = data.window_from || (data.drinking_window?.from ?? null);
      to   = data.window_to   || (data.drinking_window?.to   ?? null);
    }

    // heuristische fallback
    const y = b.vintage || new Date().getFullYear();
    if (!from || !to) {
      const color = (b.color||"").toLowerCase();
      const mainGrape = (b.grapes && b.grapes[0]?.variety || "").toLowerCase();
      const climate = (b.climate||"temperate").toLowerCase();

      function yrs(min, max){ return [y+min, y+max]; }

      if (color.includes("mousser") || mainGrape.includes("champagne")) {
        [from, to] = yrs(1, 5);
      } else if (color.includes("wit")) {
        if (["riesling","chenin"].some(g=>mainGrape.includes(g))) [from,to]=yrs(2,10);
        else if (mainGrape.includes("chardonnay")) [from,to]=yrs(1,8);
        else [from,to]=yrs(0,4);
      } else if (color.includes("rosé")) {
        [from,to]=yrs(0,2);
      } else { // rood
        if (["nebbiolo","cabernet","syrah","tempranillo"].some(g=>mainGrape.includes(g))) [from,to]=yrs(3,15);
        else if (["pinot noir","sangiovese","grenache","merlot"].some(g=>mainGrape.includes(g))) [from,to]=yrs(2,10);
        else [from,to]=yrs(1,6);
      }
      // klimaat kleine verschuiving
      if (climate === "cool") { from = Math.max(from-1, y); }
      if (climate === "warm") { to = to - 1; }
    }

    $("drink_from").value = from || "";
    $("drink_to").value = to || "";
    msg.textContent = (from && to) ? `Suggestie: ${from}–${to}` : "Geen duidelijke suggestie gevonden.";
  } catch(e) {
    msg.textContent = "Fout bij suggestie.";
  }
});

// --- Acties: auto-profiel & verrijking ---
$("btnRule")?.addEventListener("click", async ()=>{
  try {
    setLoading($("btnRule"), true); showMsg("");
    const body = readForm();
    if (!body.grapes?.length) { showMsg("Voeg minstens 1 druivenras toe."); return; }
    const res = await fetch("/api/admin/auto_profile", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (res.ok) {
      setSliders(data.profile);
      const v = $("verify"); if (v) { v.textContent = "Profiel uit regels toegepast"; v.className="pill"; }
      showMsg("Auto-profiel toegepast.", true);
    } else throw new Error(data.detail || "Fout bij auto-profiel");
  } catch(e) { showMsg(e.message || "Onbekende fout"); }
  finally { setLoading($("btnRule"), false); }
});

$("btnEnrich")?.addEventListener("click", async ()=>{
  try {
    setLoading($("btnEnrich"), true); showMsg("");
    const body = readForm();
    const res = await fetch("/api/admin/enrich", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (res.ok) {
      if (data.axes_delta) {
        axes.forEach(k => {
          const el=$(k); if (!el) return;
          const v = parseInt(el.value,10) + (data.axes_delta[k]||0);
          el.value = Math.max(0, Math.min(100, v));
        });
        setAxisText();
      }
      if (data.notes) { const n=$("notes"); if (n) n.value = ( n.value ? (n.value+"\n\n") : "" ) + data.notes; }
      const s = $("sources");
      if (s) s.innerHTML = (data.sources||[])
        .map(src=>`<div>• ${src.type}: <a href="${src.url}" target="_blank" rel="noreferrer">${src.term}</a></div>`)
        .join("");
      const v = $("verify"); if (v) { v.textContent = "Verrijking toegepast"; v.className="pill"; }
      showMsg("Verrijking toegepast.", true);
    } else throw new Error(data.detail || "Fout bij verrijking");
  } catch(e) { showMsg(e.message || "Onbekende fout"); }
  finally { setLoading($("btnEnrich"), false); }
});

// --- Opslaan nieuwe wijn ---
$("btnSave")?.addEventListener("click", async ()=>{
  try {
    setLoading($("btnSave"), true); showMsg(""); const saveMsg = $("saveMsg"); if (saveMsg) saveMsg.textContent="";
    const b = readForm();
    if (!b.name) { showMsg("Naam is verplicht"); return; }
    if (!b.vintage) { showMsg("Jaargang is verplicht"); return; }
    if (!b.grapes?.length) { showMsg("Voeg minstens 1 druivenras toe."); return; }

    const profile = Object.fromEntries(axes.map(k => [k, parseInt($(k).value,10)]));
    const payload = {
      ...b,
      region: resolveRegion(),
      profile,
      notes: $("notes")?.value || null,
      // Tip: 'color' en 'sweetness' worden meegestuurd; voeg kolommen toe in db/app om ze op te slaan
    };
    const res = await fetch("/api/admin/wine", {
      method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (res.ok) {
      const sm = $("saveMsg"); if (sm) { sm.textContent = `Opgeslagen (#${data.id})`; sm.className = "ok"; }
      // naar Voorraad-tab springen
      document.querySelector('[data-tab="tab-stock"]').click();
      fetchList();
    } else throw new Error(data.detail || "Opslaan mislukt");
  } catch(e) {
    const sm = $("saveMsg"); if (sm) { sm.textContent = e.message || "Onbekende fout"; sm.className="error"; }
  } finally { setLoading($("btnSave"), false); }
});

// ===========================
//  Voorraad & beheer (lijst)
// ===========================
let page = 0;
const limit = 20;
let total = 0;

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[m]));
}

async function fetchList() {
  const qRaw = ($("searchQ")?.value || "").trim().toLowerCase();
  const url = `/api/admin/wines?q=${encodeURIComponent(qRaw)}&limit=${limit}&offset=${page*limit}`;
  try {
    const res = await fetch(url);
    const data = await res.json();
    total = data.total || 0;
    // client-side uitbreiding: ook filter op druivennaam als back-end dat (nog) niet doet
    const items = (data.items || []).filter(it => {
      if (!qRaw) return true;
      if (it.name?.toLowerCase().includes(qRaw)) return true;
      if (it.region?.toLowerCase().includes(qRaw)) return true;
      if ((it.grapes_join || "").toLowerCase().includes(qRaw)) return true;
      return true; // server filterde al op name/region
    });
    renderTable(items);
    const from = total ? page*limit + 1 : 0;
    const to = Math.min((page+1)*limit, total);
    if ($("pagInfo")) $("pagInfo").textContent = total ? `${from}–${to} van ${total}` : "Geen resultaten";
  } catch (e) {
    if ($("pagInfo")) $("pagInfo").textContent = "Fout bij laden lijst";
  }
}

function renderTable(items) {
  const tbody = $("tblBody");
  if (!tbody) return;
  tbody.innerHTML = "";
  items.forEach(row => {
    const grapesTxt = (row.grapes && Array.isArray(row.grapes))
      ? row.grapes.map(g=>g.variety).filter(Boolean).join(", ")
      : (row.grapes_join || "—");

    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td>${row.id}</td>
      <td><a href="/admin/wine/${row.id}" style="text-decoration:none; color:#121B39;">${escapeHtml(row.name||'')}</a></td>
      <td>${escapeHtml(row.region||'')}</td>
      <td>${row.vintage ?? ''}</td>
      <td>${escapeHtml(grapesTxt)}</td>
      <td>${row.bottles ?? 0}</td>
      <td><button class="btn" data-act="del">Verwijder</button></td>
    `;

    // Verwijderen
    tr.querySelector('[data-act="del"]').addEventListener("click", async ()=>{
      if (!confirm(`Verwijder #${row.id} - ${row.name}?`)) return;
      const btn = tr.querySelector('[data-act="del"]');
      setLoading(btn, true);
      const res = await fetch(`/api/admin/wine/${row.id}`, { method:"DELETE" });
      setLoading(btn, false);
      if (res.ok) { tr.remove(); fetchList(); } else { alert("Verwijderen mislukt"); }
    });

    tbody.appendChild(tr);
  });
}

// Events voor zoeken/pagineren
$("btnSearch")?.addEventListener("click", ()=> { page = 0; fetchList(); });
$("searchQ")?.addEventListener("keydown", (e)=> { if (e.key === "Enter") { page = 0; fetchList(); }});
$("prevPage")?.addEventListener("click", ()=> { if (page>0) { page--; fetchList(); }});
$("nextPage")?.addEventListener("click", ()=> { if ((page+1)*limit < total) { page++; fetchList(); }});

// init
populateCountries();
setAxisText();
fetchList();
