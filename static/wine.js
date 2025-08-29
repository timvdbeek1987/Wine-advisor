const $ = id => document.getElementById(id);
const axes = ["ZB","MG","LS","PA","GF"];
function setAxisText(){ axes.forEach(k => $(`v${k}`).innerText = ` ${$(k).value}`); }
axes.forEach(k => $(k).addEventListener("input", setAxisText));

const grapesDiv = $("grapes");
function addGrapeRow(name="", weight=""){
  const row = document.createElement("div");
  row.className = "grape-row";
  const nameInput = document.createElement("input");
  nameInput.placeholder = "Druivenras";
  nameInput.value = name;
  const weightInput = document.createElement("input");
  weightInput.type = "number"; weightInput.step = "0.01"; weightInput.placeholder = "0.5"; weightInput.value = weight;
  const delBtn = document.createElement("button");
  delBtn.textContent = "Verwijder"; delBtn.className = "btn";
  delBtn.addEventListener("click", ()=> row.remove());
  row.appendChild(nameInput); row.appendChild(weightInput); row.appendChild(delBtn);
  grapesDiv.appendChild(row);
}
$("addGrape").addEventListener("click", ()=> addGrapeRow());
$("normalize").addEventListener("click", ()=>{
  const rows = [...document.querySelectorAll(".grape-row")];
  const nums = rows.map(r => parseFloat(r.children[1].value||"0")||0);
  const sum = nums.reduce((a,b)=>a+b,0); if (sum<=0) return;
  rows.forEach((r,i)=> r.children[1].value = (nums[i]/sum).toFixed(2));
});

function readGrapes(){
  return [...document.querySelectorAll(".grape-row")].map(r=>({
    variety: r.children[0].value.trim(),
    weight: parseFloat(r.children[1].value||"0")||0
  })).filter(g => g.variety);
}
function setGrapes(list){
  grapesDiv.innerHTML = "";
  (list && list.length ? list : [{variety:"",weight:""}]).forEach(g=> addGrapeRow(g.variety, g.weight));
}

function setLoading(btn, loading){
  if (!btn) return;
  btn.disabled = loading;
  const orig = btn.getAttribute("data-label") || btn.textContent;
  if (!btn.getAttribute("data-label")) btn.setAttribute("data-label", orig);
  btn.textContent = loading ? "Even geduld…" : orig;
}
function showMsg(text, ok=false){
  const el = $("msg"); if (!el) return;
  el.textContent = text; el.className = ok ? "ok" : "error";
}

async function loadWine(){
  const id = window.__WINE_ID__;
  const res = await fetch(`/api/admin/wine/${id}`);
  if (!res.ok){ alert("Wijn niet gevonden"); return; }
  const w = await res.json();

  $("titleName").textContent = `#${w.id} — ${w.name}`;

  // basis
  $("name").value = w.name || "";
  $("producer").value = w.producer || "";
  $("region").value = w.region || "";
  $("vintage").value = w.vintage || 0;
  $("climate").value = w.climate || "temperate";
  $("soil").value = w.soil || "";
  $("elevage").value = w.elevage || "";
  $("abv").value = w.abv ?? "";
  $("price_eur").value = w.price_eur ?? "";
  $("purchase_price_eur").value = w.purchase_price_eur ?? "";
  $("bottle_size_ml").value = w.bottle_size_ml ?? 750;

  // voorraad
  $("bottles").value = w.bottles ?? 1;
  $("storage_location").value = w.storage_location || "";
  $("drinking_from").value = w.drinking_from ?? "";
  $("drinking_to").value = w.drinking_to ?? "";

  // druiven
  setGrapes(w.grapes || []);

  // profiel
  const p = w.profile || {};
  axes.forEach(k => { $(k).value = Math.max(0, Math.min(100, parseInt(p[k] ?? 50,10))); });
  setAxisText();

  // notes/food/sources
  $("food_pairings").value = w.food_pairings || "";
  $("notes").value = w.notes || "";
  const srcDiv = $("sources");
  srcDiv.innerHTML = (w.sources||[]).map(s=>`<div>• ${s.type||"bron"}: <a href="${s.url||"#"}" target="_blank">${s.term||s.url}</a></div>`).join("");
}

async function saveWine(){
  const id = window.__WINE_ID__;
  const payload = {
    name: $("name").value.trim(),
    producer: $("producer").value.trim() || null,
    region: $("region").value.trim(),
    vintage: parseInt($("vintage").value||"0",10) || 0,
    climate: $("climate").value,
    soil: $("soil").value || null,
    elevage: $("elevage").value || null,
    abv: parseFloat($("abv").value||"") || null,
    price_eur: parseFloat($("price_eur").value||"") || null,
    purchase_price_eur: parseFloat($("purchase_price_eur").value||"") || null,
    bottle_size_ml: parseInt($("bottle_size_ml").value||"750",10) || 750,
    bottles: parseInt($("bottles").value||"0",10) || 0,
    storage_location: $("storage_location").value || null,
    drinking_from: parseInt($("drinking_from").value||"",10) || null,
    drinking_to: parseInt($("drinking_to").value||"",10) || null,
    food_pairings: $("food_pairings").value || null,
    grapes: readGrapes(),
    profile: Object.fromEntries(axes.map(k => [k, parseInt($(k).value,10)])),
    notes: $("notes").value || null,
  };
  const btn = $("btnSave");
  setLoading(btn, true);
  const res = await fetch(`/api/admin/wine/${id}`, {
    method:"PATCH",
    headers: {"Content-Type":"application/json"},
    body: JSON.stringify(payload)
  });
  setLoading(btn, false);
  if (res.ok){
    $("saveMsg").textContent = "Opgeslagen";
    $("saveMsg").className = "ok";
  } else {
    $("saveMsg").textContent = "Opslaan mislukt";
    $("saveMsg").className = "error";
  }
}

// Auto-profiel op basis van de huidige velden
$("btnRule").addEventListener("click", async ()=>{
  try {
    showMsg(""); setLoading($("btnRule"), true);
    const body = {
      grapes: readGrapes(),
      climate: $("climate").value,
      soil: $("soil").value || null,
      oak_months: parseInt($("elevage").value?.match(/\d+/)?.[0] || $("oak_months")?.value || "0", 10) || 0
    };
    const res = await fetch("/api/admin/auto_profile", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body)});
    const data = await res.json();
    if (res.ok){
      const p = data.profile || {};
      axes.forEach(k => { $(k).value = Math.max(0, Math.min(100, parseInt(p[k] ?? 50,10))); });
      setAxisText();
      showMsg("Auto-profiel toegepast.", true);
    } else throw new Error(data.detail || "Fout bij auto-profiel");
  } catch(e){ showMsg(e.message||"Onbekende fout"); }
  finally { setLoading($("btnRule"), false); }
});

// Verrijking
$("btnEnrich").addEventListener("click", async ()=>{
  try {
    showMsg(""); setLoading($("btnEnrich"), true);
    const body = {
      grapes: readGrapes(),
      region: $("region").value,
      vintage: parseInt($("vintage").value||"0",10) || 0
    };
    const res = await fetch("/api/admin/enrich", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(body)});
    const data = await res.json();
    if (res.ok){
      if (data.axes_delta){
        axes.forEach(k => {
          const v = parseInt($(k).value,10) + (data.axes_delta[k]||0);
          $(k).value = Math.max(0, Math.min(100, v));
        });
        setAxisText();
      }
      if (data.notes) $("notes").value = ( $("notes").value ? ($("notes").value+"\n\n") : "" ) + data.notes;
      $("sources").innerHTML = (data.sources||[]).map(s=>`<div>• ${s.type}: <a href="${s.url}" target="_blank" rel="noreferrer">${s.term}</a></div>`).join("");
      showMsg("Verrijking toegepast.", true);
    } else throw new Error(data.detail || "Fout bij verrijking");
  } catch(e){ showMsg(e.message||"Onbekende fout"); }
  finally { setLoading($("btnEnrich"), false); }
});

$("btnSave").addEventListener("click", saveWine);

// init
setAxisText();
loadWine();
