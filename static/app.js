const $ = id => document.getElementById(id);
const STALE_AFTER = Number(document.body.dataset.stale) * 1000;
let paused = false, timer = null, selected = null, zone = "";

const post = (url, body) => fetch(url, {
  method: "POST",
  headers: {"Content-Type": "application/json"},
  body: JSON.stringify(body || {})
});
const clock = ts => new Date(ts).toLocaleTimeString();

function render(data) {
  $("total").textContent = data.total;
  $("free").textContent = data.available;
  $("occ").textContent = data.occupied;
  $("util").textContent = data.utilisation + "%";
  $("meterFill").style.width = data.utilisation + "%";

  $("lot").innerHTML = data.bays.map(b => {
    const cls = ["bay", b.occupied ? "busy" : "free",
      zone && !b.bay_id.startsWith(zone) ? "dim" : "",
      b.bay_id === selected ? "selected" : ""].join(" ");
    return `<div class="${cls}" role="button" tabindex="0" data-id="${b.bay_id}"
      data-occ="${b.occupied}" aria-label="Bay ${b.bay_id} ${b.occupied ? "occupied" : "available"}">
      ${b.bay_id}<small>${b.occupied ? "Occupied" : "Free"}</small></div>`;
  }).join("");

  const age = new Date(data.server_time) - new Date(data.last_update);
  const stale = age > STALE_AFTER;
  $("banner").hidden = !stale;
  $("banner").textContent = "No sensor has reported for " + Math.round(age / 1000) +
    " s. Start the simulator with: python simulator.py";
  $("status").className = "status" + (stale ? " stale" : "");
  $("status").textContent = (stale ? "Data may be out of date. " : "Live. ") +
    "Last checked " + new Date().toLocaleTimeString();
}

function renderEvents(events) {
  $("log").innerHTML = events.length ? events.map(v =>
    `<li>${clock(v.ts)}  ${v.bay_id} -> ${v.occupied ? "OCCUPIED" : "FREE"}` +
    `${v.distance_cm != null ? " (" + v.distance_cm + " cm)" : ""} [${v.source}]</li>`
  ).join("") : "<li>Waiting for sensor events...</li>";
}

function renderChart(rows) {
  const max = Math.max(1, ...rows.map(r => r.arrivals));
  $("chart").innerHTML = rows.map(r =>
    `<div style="height:${Math.round(100 * r.arrivals / max)}%"
      title="${r.hour}:00 - ${r.arrivals} arrivals">` +
    `${Number(r.hour) % 3 === 0 ? "<span>" + r.hour + "</span>" : ""}</div>`
  ).join("");
}

async function showDetail(id) {
  const res = await fetch("/api/bays/" + encodeURIComponent(id));
  if (!res.ok) return;
  const d = await res.json();
  const rows = d.history.map(h =>
    `<li>${clock(h.ts)} ${h.occupied ? "occupied" : "available"} [${h.source}]</li>`
  ).join("");
  $("detail").hidden = false;
  $("detail").innerHTML = `<h3>Bay ${id}: ${d.bay.occupied ? "occupied" : "available"}</h3>
    Last reading: ${d.bay.distance_cm != null ? d.bay.distance_cm + " cm" : "manual override"}
    at ${clock(d.bay.updated_at)}
    <ul>${rows || "<li>No state changes recorded yet.</li>"}</ul>`;
}

async function refresh() {
  if (paused) return;
  try {
    const [b, e, h] = await Promise.all([
      fetch("/api/bays"), fetch("/api/events"), fetch("/api/history")
    ]);
    if (!b.ok || !e.ok || !h.ok) throw new Error("API request failed");
    render(await b.json());
    renderEvents(await e.json());
    renderChart(await h.json());
    if (selected) showDetail(selected);
  } catch (_error) {
    $("status").className = "status stale";
    $("status").textContent = "Could not load dashboard data. Please refresh the page.";
  }
}

function schedule() {
  clearInterval(timer);
  timer = setInterval(refresh, Number($("interval").value));
}

async function pick(el) {
  selected = el.dataset.id;
  await post("/api/telemetry", {
    bay_id: selected,
    occupied: el.dataset.occ !== "1",
    source: "manual"
  });
  refresh();
}

$("lot").addEventListener("click", e => {
  const bay = e.target.closest(".bay");
  if (bay) pick(bay);
});
$("lot").addEventListener("keydown", e => {
  const bay = e.target.closest(".bay");
  if (bay && (e.key === "Enter" || e.key === " ")) {
    e.preventDefault();
    pick(bay);
  }
});
$("pause").onclick = () => {
  paused = !paused;
  $("pause").textContent = paused ? "Resume updates" : "Pause updates";
  if (!paused) refresh();
};
$("reset").onclick = async () => {
  await post("/api/reset");
  selected = null;
  $("detail").hidden = true;
  refresh();
};
$("interval").onchange = schedule;
$("zone").onchange = e => {
  zone = e.target.value;
  refresh();
};

refresh();
schedule();
