// static/app.js
const packagesEl = document.getElementById('packages');
const queueEl = document.getElementById('queue');
const logEl = document.getElementById('log');
const searchInput = document.getElementById('search');
const searchBtn = document.getElementById('searchBtn');

async function fetchPackages(q) {
  const url = new URL('/packages', location.origin);
  if (q) url.searchParams.set('q', q);
  const res = await fetch(url);
  const data = await res.json();
  return data.items;
}

async function refreshCatalog(q) {
  const items = await fetchPackages(q);
  packagesEl.innerHTML = '';
  for (const p of items) {
    const li = document.createElement('li');
    li.textContent = `${p.name} - ${p.description}`;
    const btn = document.createElement('button');
    btn.textContent = 'Install';
    btn.onclick = async () => {
      const r = await fetch('/enqueue', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({package:p.name})});
      const j = await r.json();
      refreshQueue();
    };
    li.appendChild(btn);
    packagesEl.appendChild(li);
  }
}

async function refreshQueue() {
  const res = await fetch('/queue');
  const data = await res.json();
  queueEl.innerHTML = '';
  for (const job of data) {
    const li = document.createElement('li');
    li.textContent = `${job.job_id} - ${job.package} - ${job.status}`;
    queueEl.appendChild(li);
  }
}

searchBtn.onclick = () => refreshCatalog(searchInput.value);

const ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws');
ws.onopen = () => console.log('ws open');
ws.onmessage = (ev) => {
  const msg = JSON.parse(ev.data);
  if (msg.type === 'stdout' || msg.type === 'progress' || msg.type==='job_started' || msg.type==='job_finished') {
    logEl.textContent += `[${new Date(msg.timestamp*1000).toISOString()}] ${msg.type} ${msg.job_id} ${msg.line || ''} ${msg.percent ? msg.percent + '%' : ''}\n`;
  }
  // update queue periodically (could do more targeted updates)
  refreshQueue();
};

ws.onclose = () => console.log('ws closed');

refreshCatalog();
refreshQueue();
