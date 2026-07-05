const WS_URL = `ws://${location.hostname || "localhost"}:8765`;
const TOAST_DURATION_MS = 6000;

const stripEl = document.getElementById("strip");
const toastsEl = document.getElementById("toasts");
const lastIncByCar = new Map();

function connect() {
  const ws = new WebSocket(WS_URL);
  ws.onmessage = (event) => render(JSON.parse(event.data));
  ws.onclose = () => setTimeout(connect, 1500);
  ws.onerror = () => ws.close();
}

function trendArrow(carIdx, inc) {
  const prev = lastIncByCar.get(carIdx);
  lastIncByCar.set(carIdx, inc);
  if (prev !== undefined && inc > prev) {
    return `<span class="trend">▲</span>`;
  }
  return "";
}

function carRow(car, extraClass) {
  const gapText = car.gap === null || car.gap === undefined ? "--" : `${car.gap > 0 ? "+" : ""}${car.gap.toFixed(1)}s`;
  return `
    <div class="row ${extraClass} state-${car.state || "CLEAN"}">
      <div class="pos">${car.pos ?? ""}</div>
      <div class="name">${car.name ?? ""}</div>
      <div class="lic">${car.lic ?? ""}</div>
      <div class="inc">${car.inc ?? 0}x ${trendArrow(car.car_idx, car.inc ?? 0)}</div>
      <div class="gap">${gapText}</div>
    </div>`;
}

function playerRow(player) {
  if (!player) return "";
  return `
    <div class="row player">
      <div class="pos">${player.pos ?? ""}</div>
      <div class="name">${player.name ?? "YOU"}</div>
      <div class="lic">${player.lic ?? ""}</div>
      <div class="inc">${player.inc ?? 0}x</div>
      <div class="gap">--</div>
    </div>`;
}

function render(payload) {
  const cars = payload.cars || [];
  const ahead = cars
    .filter((c) => c.gap > 0)
    .sort((a, b) => a.gap - b.gap)
    .slice(0, 3)
    .reverse();
  const behind = cars
    .filter((c) => c.gap < 0)
    .sort((a, b) => b.gap - a.gap)
    .slice(0, 3);

  stripEl.innerHTML = [
    ...ahead.map((c) => carRow(c, "")),
    playerRow(payload.player),
    ...behind.map((c) => carRow(c, "")),
  ].join("");

  for (const alert of payload.alerts || []) {
    showToast(alert.message);
  }
}

function showToast(message) {
  const el = document.createElement("div");
  el.className = "toast";
  el.textContent = message;
  toastsEl.appendChild(el);
  setTimeout(() => el.remove(), TOAST_DURATION_MS);
}

connect();
