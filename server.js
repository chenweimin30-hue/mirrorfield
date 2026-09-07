/* ============================================================
   镜原 Mirrorfield · 联机版服务器
   零依赖 Node.js：静态文件 + WebSocket(RFC6455) + 权威模拟
   最多 10 名真实玩家同房对战（房间制：2~10 人开局）
   运行：node server.js  （默认端口 8080）
============================================================ */
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PORT = process.env.PORT || 8080;
const W = 960, H = 640, HEDGE = 18;
const TICK_HZ = 30;
const SNAPSHOT_MS = 66;
const MAX_PLAYERS = 10;
const LOBBY_WAIT_MS = 8000;
const ROUND_MS = 120000;
const RESPAWN_S = 2;

const MIME = {
  '.html': 'text/html; charset=utf-8', '.js': 'text/javascript',
  '.css': 'text/css', '.json': 'application/json',
  '.png': 'image/png', '.svg': 'image/svg+xml', '.ico': 'image/x-icon',
  '.md': 'text/plain; charset=utf-8'
};
const server = http.createServer((req, res) => {
  let p = (req.url || '/').split('?')[0];
  if (p === '/') p = '/index.html';
  const f = path.join(__dirname, p);
  if (!f.startsWith(__dirname)) { res.writeHead(403); res.end(); return; }
  fs.readFile(f, (err, data) => {
    if (err) { res.writeHead(404); res.end('404'); return; }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(f)] || 'application/octet-stream' });
    res.end(data);
  });
});

const clients = new Map();
let nextId = 1;

server.on('upgrade', (req, socket) => {
  const key = req.headers['sec-websocket-key'];
  if (!key || (req.headers.upgrade || '').toLowerCase() !== 'websocket') { socket.destroy(); return; }
  const accept = crypto.createHash('sha1').update(key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').digest('base64');
  socket.write(
    'HTTP/1.1 101 Switching Protocols\r\n' +
    'Upgrade: websocket\r\nConnection: Upgrade\r\n' +
    `Sec-WebSocket-Accept: ${accept}\r\n\r\n`);
  socket.setNoDelay(true);

  const ws = { socket, id: nextId++, alive: true, send: (obj) => {
    try { socket.write(encodeFrame(JSON.stringify(obj))); } catch (e) {}
  }};
  clients.set(ws, ws);

  socket.on('data', buf => {
    let off = 0;
    while (off < buf.length) {
      const r = decodeFrame(buf, off);
      if (!r) break;
      off = r.next;
      if (r.op === 0x8) { closeWs(ws); return; }
      if (r.op === 0x9) { try { socket.write(encodeFrame('', 0xA)); } catch (e) {} continue; }
      if (r.op === 0x1) {
        let msg; try { msg = JSON.parse(r.data); } catch (e) { continue; }
        onMessage(ws, msg);
      }
    }
  });
  socket.on('error', () => {});
  socket.on('close', () => closeWs(ws));

  ws.send({ t: 'welcome', id: ws.id });
});

function closeWs(ws) {
  if (!clients.has(ws)) return;
  clients.delete(ws);
  roomLeave(ws.id);
}
function encodeFrame(str, op = 0x1) {
  const payload = Buffer.from(str);
  const len = payload.length;
  let header;
  if (len < 126) { header = Buffer.from([0x80 | op, len]); }
  else if (len < 65536) { header = Buffer.alloc(4); header[0] = 0x80 | op; header[1] = 126; header.writeUInt16BE(len, 2); }
  else { header = Buffer.alloc(10); header[0] = 0x80 | op; header[1] = 127; header.writeBigUInt64BE(BigInt(len), 2); }
  return Buffer.concat([header, payload]);
}
function decodeFrame(buf, off) {
  if (off + 2 > buf.length) return null;
  const b1 = buf[off], b2 = buf[off + 1];
  const op = b1 & 0x0f;
  let len = b2 & 0x7f, p = off + 2;
  if (len === 126) { if (p + 2 > buf.length) return null; len = buf.readUInt16BE(p); p += 2; }
  else if (len === 127) { if (p + 8 > buf.length) return null; len = Number(buf.readBigUInt64BE(p)); p += 8; }
  const masked = (b2 & 0x80) !== 0;
  let mask = null;
  if (masked) { if (p + 4 > buf.length) return null; mask = buf.slice(p, p + 4); p += 4; }
  if (p + len > buf.length) return null;
  const data = Buffer.alloc(len);
  for (let i = 0; i < len; i++) data[i] = buf[p + i] ^ (masked ? mask[i % 4] : 0);
  return { op, data: data.toString('utf8'), next: p + len };
}

const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const rnd = (a, b) => a + Math.random() * (b - a);
const dist2 = (ax, ay, bx, by) => { const dx = ax - bx, dy = ay - by; return dx * dx + dy * dy; };
function closestOnSeg(px, py, x1, y1, x2, y2) {
  const dx = x2 - x1, dy = y2 - y1, L2 = dx * dx + dy * dy || 1e-9;
  const t = clamp(((px - x1) * dx + (py - y1) * dy) / L2, 0, 1);
  return { x: x1 + t * dx, y: y1 + t * dy };
}
function raySegment(px, py, dx, dy, x1, y1, x2, y2) {
  const ex = x2 - x1, ey = y2 - y1, fx = x1 - px, fy = y1 - py;
  const den = ex * dy - dx * ey;
  if (Math.abs(den) < 1e-9) return -1;
  const t = (ex * fy - fx * ey) / den, u = (dx * fy - fx * dy) / den;
  return (t > 0.001 && u >= 0 && u <= 1) ? t : -1;
}
function reflect(vx, vy, m) { return m.type === '/' ? { x: -vy, y: -vx } : { x: vy, y: vx }; }
function pushOutOfMirrors(o, mirrors) {
  for (const m of mirrors) {
    const c = closestOnSeg(o.x, o.y, m.x1, m.y1, m.x2, m.y2);
    const d = Math.hypot(o.x - c.x, o.y - c.y), min = o.r + 4;
    if (d < min) {
      if (d < 1e-4) { o.x += min; continue; }
      o.x = c.x + (o.x - c.x) / d * min; o.y = c.y + (o.y - c.y) / d * min;
    }
  }
  o.x = clamp(o.x, HEDGE + o.r, W - HEDGE - o.r);
  o.y = clamp(o.y, HEDGE + o.r, H - HEDGE - o.r);
}

const COLORS = ['#e53935', '#1e88e5', '#43a047', '#fb8c00', '#8e24aa', '#00acc1', '#d81b60', '#5d4037', '#7cb342', '#f4511e'];
const NAMES = ['赤', '蓝', '翠', '橙', '紫', '青', '粉', '棕', '草', '焰'];

let room = {
  phase: 'lobby',
  players: new Map(),
  mirrors: [], bullets: [], powerups: [],
  deadline: 0, countdownEnd: 0, roundEnd: 0,
  puSpawnT: 0,
  mirrorBreakable: true
};

function makeMirror(cx, cy, len, type) {
  const s = len / 2 * Math.SQRT1_2;
  const dx = s, dy = type === '/' ? -s : s;
  return { x1: cx - dx, y1: cy - dy, x2: cx + dx, y2: cy + dy, type, hp: 3 };
}
function genMirrors() {
  const arr = []; const n = 18 + Math.floor(Math.random() * 5);
  let tries = 0;
  while (arr.length < n && tries < 600) {
    tries++;
    const cx = rnd(HEDGE + 70, W - HEDGE - 70), cy = rnd(HEDGE + 70, H - HEDGE - 70);
    let ok = true;
    for (const m of arr) {
      const mx = (m.x1 + m.x2) / 2, my = (m.y1 + m.y2) / 2;
      if (dist2(cx, cy, mx, my) < 105 * 105) { ok = false; break; }
    }
    if (!ok) continue;
    arr.push(makeMirror(cx, cy, rnd(70, 130), Math.random() < .5 ? '/' : '\\'));
  }
  return arr;
}

function newPlayer(id) {
  const idx = room.players.size;
  return {
    id, name: NAMES[idx % 10], color: COLORS[idx % 10],
    x: 0, y: 0, r: 14, aim: 0,
    hp: 100, kills: 0, deaths: 0, score: 0,
    cool: 0, inv: 0, respawnAt: 0, alive: true,
    input: { mx: 0, my: 0, ax: 0, ay: 0, fire: false },
    triT: 0, shieldT: 0, pierceT: 0, healT: 0,
    dash: { cd: 0, t: 0, dx: 0, dy: 0 }
  };
}
function spawnPos(idx, total) {
  const ang = (idx / Math.max(total, 1)) * Math.PI * 2 - Math.PI / 2;
  const rx = W / 2 + Math.cos(ang) * 330, ry = H / 2 + Math.sin(ang) * 200;
  return { x: clamp(rx, HEDGE + 40, W - HEDGE - 40), y: clamp(ry, HEDGE + 40, H - HEDGE - 40) };
}

function roomJoin(ws) {
  if (room.phase === 'playing' || room.phase === 'countdown') {
    if (room.players.size >= MAX_PLAYERS) { ws.send({ t: 'full' }); return; }
  } else if (room.players.size >= MAX_PLAYERS) { ws.send({ t: 'full' }); return; }
  const p = newPlayer(ws.id);
  const sp = spawnPos(room.players.size, room.players.size + 1);
  p.x = sp.x; p.y = sp.y;
  room.players.set(ws.id, p);
  broadcast({ t: 'join', id: ws.id, name: p.name, color: p.color, count: room.players.size });
  ws.send({ t: 'mirrorfield', mirrors: room.mirrors.length ? room.mirrors : (room.mirrors = genMirrors()) });
  if (room.phase === 'lobby' && room.players.size >= 2) {
    if (!room.deadline) room.deadline = Date.now() + LOBBY_WAIT_MS;
  }
}
function roomLeave(id) {
  if (room.players.delete(id)) {
    broadcast({ t: 'leave', id, count: room.players.size });
    if (room.players.size < 2 && room.phase === 'lobby') room.deadline = 0;
    if (room.players.size === 0) { room.phase = 'lobby'; room.deadline = 0; room.mirrors = []; room.bullets = []; }
  }
}

function broadcast(obj) { for (const ws of clients.values()) { ws.send(obj); } }

function stepPlayer(p, dt) {
  const inp = p.input;
  if (p.dash.cd > 0) p.dash.cd -= dt;
  if (p.dash.t > 0) {
    p.dash.t -= dt;
    p.x += p.dash.dx * 9.5 * dt * 60; p.y += p.dash.dy * 9.5 * dt * 60;
  } else {
    const l = Math.hypot(inp.mx, inp.my);
    if (l > 0.01) {
      p.x += inp.mx / Math.max(l, 1) * 3.3 * dt * 60;
      p.y += inp.my / Math.max(l, 1) * 3.3 * dt * 60;
    }
  }
  pushOutOfMirrors(p, room.mirrors);
  p.aim = Math.atan2(inp.ay, inp.ax);
  p.cool -= dt;
  if (inp.fire && p.cool <= 0 && p.alive) {
    const d = Math.hypot(inp.ax, inp.ay) || 1;
    serverFire(p, (inp.ax / d), (inp.ay / d));
    p.cool = p.triT > 0 ? 0.4 : 0.28;
  }
  if (p.inv > 0) p.inv -= dt;
  if (p.triT > 0) p.triT -= dt;
  if (p.shieldT > 0) p.shieldT -= dt;
  if (p.pierceT > 0) p.pierceT -= dt;
}
function serverFire(p, dx, dy) {
  const mk = (ang) => {
    const c = Math.cos(ang), s = Math.sin(ang);
    room.bullets.push({
      x: p.x + c * (p.r + 16), y: p.y + s * (p.r + 16),
      vx: c * 9.5, vy: s * 9.5, owner: p.id, color: p.color,
      r: 3.5, bounces: 0, life: 600, pierce: p.pierceT > 0
    });
  };
  const base = Math.atan2(dy, dx);
  if (p.triT > 0) { mk(base - 0.09); mk(base); mk(base + 0.09); }
  else mk(base);
}

function stepBullets(dt) {
  const steps = 3;
  for (let i = room.bullets.length - 1; i >= 0; i--) {
    const b = room.bullets[i];
    b.life -= dt * 60;
    for (let s = 0; s < steps; s++) {
      b.x += b.vx / steps * dt * 60; b.y += b.vy / steps * dt * 60;
      for (let mi = room.mirrors.length - 1; mi >= 0; mi--) {
        const m = room.mirrors[mi];
        const c = closestOnSeg(b.x, b.y, m.x1, m.y1, m.x2, m.y2);
        const d = Math.hypot(b.x - c.x, b.y - c.y), min = 4 + b.r;
        if (d < min) {
          if (b.pierce) {
            if (!room.mirrorBreakable) continue;
            room.mirrors.splice(mi, 1); broadcast({ t: 'shatter', i: mi }); continue;
          }
          const r = reflect(b.vx, b.vy, m);
          b.vx = r.x; b.vy = r.y;
          if (d < 1e-4) b.x += min;
          else { b.x = c.x + (b.x - c.x) / d * (min + .5); b.y = c.y + (b.y - c.y) / d * (min + .5); }
          b.bounces++;
          if (room.mirrorBreakable) {
            m.hp--;
            if (m.hp <= 0) { room.mirrors.splice(mi, 1); broadcast({ t: 'shatter', i: mi }); }
          }
          break;
        }
      }
    }
    let dead = b.life <= 0 || b.x < 4 || b.x > W - 4 || b.y < 4 || b.y > H - 4;
    if (!dead) {
      for (const p of room.players.values()) {
        if (!p.alive || p.id === b.owner) continue;
        const dd = dist2(b.x, b.y, p.x, p.y);
        if (dd < (p.r + b.r) ** 2) {
          if (p.shieldT > 0) { dead = true; break; }
          if (p.inv > 0) break;
          p.hp -= 12; p.inv = 0.5;
          const killer = room.players.get(b.owner);
          if (killer) killer.score += 10;
          dead = true;
          if (p.hp <= 0) {
            p.alive = false; p.deaths++; p.respawnAt = Date.now() + RESPAWN_S * 1000;
            if (killer) { killer.kills++; killer.score += 100 + (b.bounces > 0 ? 50 * b.bounces : 0); }
            broadcast({ t: 'kill', victim: p.id, killer: b.owner, bounces: b.bounces });
          }
          break;
        }
      }
    }
    if (dead) room.bullets.splice(i, 1);
  }
}

const PU_TYPES = ['heal', 'triple', 'shield', 'pierce'];
function stepPowerups(dt) {
  room.puSpawnT -= dt;
  if (room.puSpawnT <= 0 && room.powerups.length < 3) {
    const x = rnd(HEDGE + 60, W - HEDGE - 60), y = rnd(HEDGE + 60, H - HEDGE - 60);
    room.powerups.push({ x, y, r: 11, type: PU_TYPES[Math.floor(Math.random() * 4)], life: 700 });
    room.puSpawnT = rnd(7, 12);
  }
  for (let i = room.powerups.length - 1; i >= 0; i--) {
    const pu = room.powerups[i];
    pu.life -= dt * 60;
    if (pu.life <= 0) { room.powerups.splice(i, 1); continue; }
    for (const p of room.players.values()) {
      if (p.alive && dist2(pu.x, pu.y, p.x, p.y) < (pu.r + p.r) ** 2) {
        if (pu.type === 'heal') p.hp = Math.min(100, p.hp + 40);
        else if (pu.type === 'triple') p.triT = 10;
        else if (pu.type === 'shield') p.shieldT = 8;
        else if (pu.type === 'pierce') p.pierceT = 6;
        room.powerups.splice(i, 1);
        broadcast({ t: 'pickup', i, by: p.id, kind: pu.type });
        break;
      }
    }
  }
}

function tick() {
  const now = Date.now();
  const dt = 1 / TICK_HZ;

  if (room.phase === 'lobby') {
    if (room.players.size >= 2 && room.deadline && now >= room.deadline) {
      room.phase = 'countdown';
      room.countdownEnd = now + 3000;
      room.mirrors = genMirrors();
      room.bullets = []; room.powerups = []; room.puSpawnT = 3;
      let i = 0;
      for (const p of room.players.values()) {
        const sp = spawnPos(i, room.players.size);
        p.x = sp.x; p.y = sp.y; p.hp = 100; p.alive = true;
        p.kills = 0; p.deaths = 0; p.score = 0;
        p.triT = 0; p.shieldT = 0; p.pierceT = 0; p.cool = 0; p.inv = 2;
        i++;
      }
      broadcast({ t: 'countdown', mirrors: room.mirrors, startAt: room.countdownEnd,
                  mirrorBreakable: room.mirrorBreakable });
    }
  } else if (room.phase === 'countdown') {
    if (now >= room.countdownEnd) {
      room.phase = 'playing';
      room.roundEnd = now + ROUND_MS;
      broadcast({ t: 'start' });
    }
  } else if (room.phase === 'playing') {
    for (const p of room.players.values()) {
      if (!p.alive) {
        if (now >= p.respawnAt) {
          let bx = W / 2, by = H / 2, best = -1;
          for (let t = 0; t < 20; t++) {
            const cx = rnd(HEDGE + 60, W - HEDGE - 60), cy = rnd(HEDGE + 60, H - HEDGE - 60);
            let dmin = 1e9;
            for (const q of room.players.values()) if (q.alive && q.id !== p.id) dmin = Math.min(dmin, dist2(cx, cy, q.x, q.y));
            if (dmin > best) { best = dmin; bx = cx; by = cy; }
          }
          p.x = bx; p.y = by; p.hp = 100; p.alive = true; p.inv = 1.5;
          broadcast({ t: 'respawn', id: p.id, x: bx, y: by });
        }
        continue;
      }
      stepPlayer(p, dt);
    }
    const arr = [...room.players.values()].filter(p => p.alive);
    for (let i = 0; i < arr.length; i++) {
      for (let j = i + 1; j < arr.length; j++) {
        const a = arr[i], b2 = arr[j];
        const dx = b2.x - a.x, dy = b2.y - a.y;
        const d = Math.hypot(dx, dy), min = 36;
        if (d > 0 && d < min) {
          const push = (min - d) / 2;
          const nx = dx / d, ny = dy / d;
          a.x -= nx * push; a.y -= ny * push;
          b2.x += nx * push; b2.y += ny * push;
        } else if (d === 0) { b2.x += min / 2; }
      }
    }
    // 软碰撞后再次钳制到场地内，避免被挤出屏幕
    for (const p of arr) {
      p.x = clamp(p.x, HEDGE + p.r, W - HEDGE - p.r);
      p.y = clamp(p.y, HEDGE + p.r, H - HEDGE - p.r);
    }
    stepBullets(dt);
    stepPowerups(dt);
    if (now >= room.roundEnd || room.players.size === 0) endRound();
  } else if (room.phase === 'results') {
    if (now >= room.roundEnd) {
      room.phase = 'lobby'; room.deadline = room.players.size >= 2 ? now + LOBBY_WAIT_MS : 0;
      room.mirrors = genMirrors(); room.bullets = []; room.powerups = [];
      broadcast({ t: 'lobby' });
    }
  }
}
function endRound() {
  room.phase = 'results';
  room.roundEnd = Date.now() + 10000;
  const board = [...room.players.values()]
    .map(p => ({ id: p.id, name: p.name, color: p.color, kills: p.kills, deaths: p.deaths, score: p.score }))
    .sort((a, b) => b.score - a.score);
  broadcast({ t: 'results', board });
}

function onMessage(ws, msg) {
  const p = room.players.get(ws.id);
  if (!p) { if (msg.t === 'join') roomJoin(ws); return; }
  switch (msg.t) {
    case 'settings': {
      if (room.phase === 'lobby' && typeof msg.mirrorBreakable === 'boolean') {
        room.mirrorBreakable = msg.mirrorBreakable;
        broadcast({ t: 'mirror-setting', mirrorBreakable: room.mirrorBreakable });
      }
      break;
    }
    case 'input': {
      if (typeof msg.mx === 'number') p.input.mx = clamp(msg.mx, -1, 1);
      if (typeof msg.my === 'number') p.input.my = clamp(msg.my, -1, 1);
      if (typeof msg.ax === 'number') p.input.ax = msg.ax;
      if (typeof msg.ay === 'number') p.input.ay = msg.ay;
      p.input.fire = !!msg.fire;
      if (msg.dash && p.dash.cd <= 0 && p.alive) {
        const l = Math.hypot(p.input.mx, p.input.my);
        if (l > 0.01) {
          p.dash.t = 0.1; p.dash.cd = 1.5;
          p.dash.dx = p.input.mx / l; p.dash.dy = p.input.my / l;
          p.inv = Math.max(p.inv, 0.17);
        }
      }
      break;
    }
    case 'ping': ws.send({ t: 'pong', ts: msg.ts }); break;
  }
}

function snapshot() {
  if (room.phase === 'playing' || room.phase === 'countdown' || room.phase === 'results') {
    const ps = [];
    for (const p of room.players.values()) {
      ps.push({ id: p.id, x: Math.round(p.x * 10) / 10, y: Math.round(p.y * 10) / 10,
                a: Math.round(p.aim * 100) / 100, hp: p.hp, al: p.alive ? 1 : 0,
                sh: p.shieldT > 0 ? 1 : 0, tr: p.triT > 0 ? 1 : 0, pi: p.pierceT > 0 ? 1 : 0,
                k: p.kills, s: p.score, n: p.name, c: p.color });
    }
    const bs = room.bullets.map(b => ({
      x: Math.round(b.x), y: Math.round(b.y),
      vx: Math.round(b.vx * 10) / 10, vy: Math.round(b.vy * 10) / 10,
      o: b.owner === 'local' ? 0 : b.owner, b: b.bounces
    }));
    broadcast({ t: 'snap', ps, bs, mus: room.mirrors.length, phase: room.phase,
                end: room.phase === 'playing' ? Math.max(0, room.roundEnd - Date.now()) : 0 });
  } else {
    const lobby = [...room.players.values()].map(p => ({ id: p.id, name: p.name, color: p.color }));
    broadcast({ t: 'lobbysnap', players: lobby, wait: room.deadline ? Math.max(0, room.deadline - Date.now()) : -1 });
  }
}

setInterval(tick, 1000 / TICK_HZ);
setInterval(snapshot, SNAPSHOT_MS);

server.listen(PORT, '0.0.0.0', () => {
  console.log('镜原联机服务器已启动');
  console.log('  本机访问   http://localhost:' + PORT);
  console.log('  手机访问   http://<本机局域网IP>:' + PORT + ' （需同一 WiFi）');
});
