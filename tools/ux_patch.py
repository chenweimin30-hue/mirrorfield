#!/usr/bin/env python3
from pathlib import Path

idx = Path('index.html').read_text(encoding='utf-8')
srv = Path('server.js').read_text(encoding='utf-8')

# Fullscreen
idx = idx.replace(
    '#stage{position:relative;width:100%;height:100%;max-width:min(100vw,calc(100vh*1.5));}',
    '#stage{position:relative;width:100%;height:100%;}'
)
idx = idx.replace(
    'canvas{display:block;width:100%;height:100%;border-radius:10px;box-shadow:0 10px 40px rgba(0,0,0,.5);background:#7cb342;touch-action:none;}',
    'canvas{display:block;width:100%;height:100%;background:#7cb342;touch-action:none;}'
)

# Map size menu
if 'name="mapSize"' not in idx:
    menu_insert = (
        '      <div style="display:flex;flex-wrap:wrap;gap:8px;justify-content:center;align-items:center;'
        'margin:0 0 14px;font-size:14px;background:rgba(255,255,255,.08);border:1px solid rgba(255,255,255,.18);'
        'border-radius:22px;padding:8px 16px;max-width:92%;">'
        '<span>地图</span>'
        '<label style="cursor:pointer"><input type="radio" name="mapSize" value="screen" checked> 屏幕大小</label>'
        '<label style="cursor:pointer"><input type="radio" name="mapSize" value="medium"> 中等</label>'
        '<label style="cursor:pointer"><input type="radio" name="mapSize" value="large"> 超大</label>'
        '</div>\n'
    )
    for btn in ('btnSolo', 'btnCampaign', 'btnStart'):
        tag = f'<button id="{btn}">'
        if tag in idx:
            idx = idx.replace(tag, menu_insert + tag)
            break

# Mutable world size + touch detect
for old in (
    'const W = 3840, H = 2560, HEDGE = 18;',
    'const W = 1920, H = 1280, HEDGE = 18;',
):
    if old in idx:
        idx = idx.replace(
            old,
            "let W = 960, H = 640, HEDGE = 18;\n"
            "let mapSizeMode = 'screen';\n"
            "const isTouch = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0);",
            1,
        )
        break

if 'function applyMapSize' not in idx:
    helper = (
        "\nfunction applyMapSize() {\n"
        "  const sel = document.querySelector('input[name=\"mapSize\"]:checked');\n"
        "  mapSizeMode = (sel && sel.value) || 'screen';\n"
        "  if (mapSizeMode === 'screen') { W = Math.round(viewW || 960); H = Math.round(viewH || 640); }\n"
        "  else if (mapSizeMode === 'medium') { W = 1600; H = 1066; }\n"
        "  else { W = 2560; H = 1706; }\n"
        "  if (typeof paintGround === 'function') paintGround();\n"
        "}\n"
    )
    if "window.addEventListener('resize', fit);" in idx:
        idx = idx.replace("window.addEventListener('resize', fit);", helper + "window.addEventListener('resize', fit);")
    elif 'function updateCamera' in idx:
        idx = idx.replace('function updateCamera', helper + 'function updateCamera')

if 'function resetGame' in idx and 'applyMapSize()' not in idx:
    idx = idx.replace('function resetGame() {\n  genMirrors();', "function resetGame() {\n  if (typeof applyMapSize==='function') applyMapSize();\n  genMirrors();")

idx = idx.replace(
    'function drawTouchUI() {\n  if (!touchInput.active) return;',
    'function drawTouchUI() {\n  if (!isTouch && !touchInput.active) return;'
)

if 'function shatterMirror' not in idx:
    shatter = (
        "\nfunction shatterMirror(m, cx, cy) {\n"
        "  m.hp = 0; m.broken = true; m.respawnAt = performance.now() + 2000;\n"
        "  if (typeof spark === 'function') spark(cx, cy, '#cfd8dc', 16, 220);\n"
        "  if (typeof beep === 'function') beep(500, .18, 'sawtooth', .12, 140);\n"
        "}\n"
        "function updateMirrorsLocal() {\n"
        "  const now = performance.now();\n"
        "  for (const m of mirrors) {\n"
        "    if (m.broken && now >= m.respawnAt) {\n"
        "      m.hp = 3; m.broken = false;\n"
        "      if (typeof spark === 'function') spark((m.x1+m.x2)/2, (m.y1+m.y2)/2, '#90caf9', 10, 160);\n"
        "    }\n"
        "  }\n"
        "}\n"
    )
    idx = idx.replace('const MIRROR_HALF = 4;', shatter + 'const MIRROR_HALF = 4;')

if 'if (m.broken) continue;' not in idx:
    idx = idx.replace(
        'function pushOutOfMirrors(o) {\n  for (const m of mirrors) {',
        'function pushOutOfMirrors(o) {\n  for (const m of mirrors) {\n    if (m.broken) continue;'
    )

if 'updateMirrorsLocal' in idx and 'updateMirrorsLocal();' not in idx:
    idx = idx.replace('updatePowerupsLocal();', 'updateMirrorsLocal();\n      updatePowerupsLocal();')

idx = idx.replace("const n = 90 + Math.floor(Math.random() * 30);",
                  "const areaRatio = (W * H) / (960 * 640); const n = Math.max(10, Math.round(16 * areaRatio) + Math.floor(Math.random() * 6));")
idx = idx.replace('spawnT = 3;', 'spawnT = 1.2;')

# Server
for old in ('const W = 3840, H = 2560, HEDGE = 18;', 'const W = 1920, H = 1280, HEDGE = 18;'):
    if old in srv:
        srv = srv.replace(old, 'let W = 1600, H = 1066, HEDGE = 18;', 1)
        break

if 'm.broken' not in srv:
    srv = srv.replace(
        'function pushOutOfMirrors(o, mirrors) {\n  for (const m of mirrors) {',
        'function pushOutOfMirrors(o, mirrors) {\n  for (const m of mirrors) {\n    if (m.broken) continue;'
    )
    srv = srv.replace(
        "room.mirrors.splice(mi, 1); broadcast({ t: 'shatter', i: mi });",
        "m.hp = 0; m.broken = true; m.respawnAt = Date.now() + 2000; broadcast({ t: 'shatter', i: mi });"
    )
    srv = srv.replace(
        "if (m.hp <= 0) { room.mirrors.splice(mi, 1); broadcast({ t: 'shatter', i: mi }); }",
        "if (m.hp <= 0) { m.broken = true; m.respawnAt = Date.now() + 2000; broadcast({ t: 'shatter', i: mi }); }"
    )

srv = srv.replace('room.powerups.length < 3', 'room.powerups.length < 6')
srv = srv.replace('room.puSpawnT = rnd(7, 12);', 'room.puSpawnT = rnd(2.5, 5);')

if 'm.respawnAt' in srv and 'for (const m of room.mirrors)' not in srv:
    inject = (
        "\n  const _now = Date.now();\n"
        "  for (const m of room.mirrors) {\n"
        "    if (m.broken and _now >= m.respawnAt):\n"  # will fix below
    )

# Fix python-style if that accidentally got into JS - use proper JS
if 'm.broken and _now' in srv:
    pass  # skip bad inject
elif 'm.respawnAt' in srv and 'respawnAt' in srv:
    block = (
        "\n  const _nowM = Date.now();\n"
        "  for (const m of room.mirrors) {\n"
        "    if (m.broken && _nowM >= m.respawnAt) { m.broken = false; m.hp = 3; }\n"
        "  }\n"
    )
    if 'function stepPowerups(dt) {' in srv and block.strip() not in srv:
        srv = srv.replace('function stepPowerups(dt) {', 'function stepPowerups(dt) {' + block)

Path('index.html').write_text(idx, encoding='utf-8')
Path('server.js').write_text(srv, encoding='utf-8')
print('patched index', len(idx), 'server', len(srv))
print('mapSize', 'mapSize' in idx)
print('shatterMirror', 'shatterMirror' in idx)
print('isTouch', 'isTouch' in idx)
