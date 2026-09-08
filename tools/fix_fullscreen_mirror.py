#!/usr/bin/env python3
"""Fix: true fullscreen layout + mirror auto-respawn after break (~2s)."""
from pathlib import Path
import re

idx = Path('index.html').read_text(encoding='utf-8')
changed = []

# --- 1) CSS: force edge-to-edge, no letterbox feel ---
old_css = '''  html,body{margin:0;padding:0;height:100%;background:#2e3b2a;font-family:system-ui,"Segoe UI","Microsoft YaHei",sans-serif;
            overflow:hidden;touch-action:none;-webkit-user-select:none;user-select:none;}
  #wrap{position:relative;width:100%;height:100%;display:flex;align-items:center;justify-content:center;}
  #stage{position:relative;width:100%;height:100%;}
  canvas{display:block;width:100%;height:100%;background:#7cb342;touch-action:none;}'''

new_css = '''  html,body{margin:0;padding:0;width:100%;height:100%;height:100dvh;background:#2e3b2a;font-family:system-ui,"Segoe UI","Microsoft YaHei",sans-serif;
            overflow:hidden;touch-action:none;-webkit-user-select:none;user-select:none;
            position:fixed;inset:0;}
  #wrap{position:fixed;inset:0;width:100%;height:100%;display:block;}
  #stage{position:absolute;inset:0;width:100%;height:100%;}
  canvas{display:block;position:absolute;inset:0;width:100% !important;height:100% !important;background:#7cb342;touch-action:none;}'''

if old_css in idx:
    idx = idx.replace(old_css, new_css)
    changed.append('css-fullscreen')
else:
    print('WARN: css block not exact match')

# --- 2) fit(): use full stage ---
old_fit = '''function fit() {
  const r = stage.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  cv.width = r.width * dpr; cv.height = r.height * dpr;
  cv.style.width = r.width + 'px'; cv.style.height = r.height + 'px';
  // 可视区域高度固定 640 逻辑像素，宽度按屏幕比例延伸（贪吃蛇式镜头）
  viewH = 640;
  viewW = Math.max(480, viewH * (r.width / Math.max(r.height, 1)));
  window.__sx = (r.width * dpr) / viewW;
  window.__sy = (r.height * dpr) / viewH;
  window.__scale = r.height / viewH;
  window.__offX = 0; window.__offY = 0;
  applyCameraTransform();
}'''

new_fit = '''function fit() {
  const r = stage.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const cssW = Math.max(1, r.width);
  const cssH = Math.max(1, r.height);
  cv.width = Math.round(cssW * dpr);
  cv.height = Math.round(cssH * dpr);
  cv.style.width = cssW + 'px';
  cv.style.height = cssH + 'px';
  // 逻辑高度固定 640，宽度按真实屏幕比例，保证横竖屏都铺满
  viewH = 640;
  viewW = Math.max(480, Math.round(viewH * (cssW / cssH)));
  window.__sx = cv.width / viewW;
  window.__sy = cv.height / viewH;
  window.__scale = cssH / viewH;
  window.__offX = 0; window.__offY = 0;
  applyCameraTransform();
}'''

if old_fit in idx:
    idx = idx.replace(old_fit, new_fit)
    changed.append('fit')
else:
    print('WARN: fit() not exact')

# --- 3) Bullet hit: shatter instead of remove ---
old_bullet = '''        if (mirrorBreakable && m.hp > 0) {
          m.hp--;
          if (m.hp <= 0) {
            mirrors = mirrors.filter(mm => mm !== m);
            spark(c.x, c.y, '#90a4ae', 18, 40);
            beep(200, .15, 'triangle', .1);
          }
        }'''

new_bullet = '''        if (mirrorBreakable && !m.broken && m.hp > 0) {
          m.hp--;
          if (m.hp <= 0) {
            shatterMirror(m, c.x, c.y);
          }
        }'''

if old_bullet in idx:
    idx = idx.replace(old_bullet, new_bullet)
    changed.append('bullet-shatter')
else:
    idx2, n = re.subn(
        r"if \(mirrorBreakable && m\.hp > 0\) \{\s*m\.hp--;\s*if \(m\.hp <= 0\) \{\s*mirrors = mirrors\.filter\(mm => mm !== m\);\s*spark\([^)]+\);\s*beep\([^)]+\);\s*\}\s*\}",
        "if (mirrorBreakable && !m.broken && m.hp > 0) {\n          m.hp--;\n          if (m.hp <= 0) {\n            shatterMirror(m, c.x, c.y);\n          }\n        }",
        idx,
        count=1,
    )
    if n:
        idx = idx2
        changed.append('bullet-shatter-re')
    else:
        print('WARN: bullet shatter block not found')

# --- 4) Skip broken mirrors in bullet reflection ---
old_mirror_loop = '''    for (const m of mirrors) {
      const c = closestOnSeg(b.x, b.y, m.x1, m.y1, m.x2, m.y2);
      if (Math.hypot(b.x - c.x, b.y - c.y) < b.r + 3) {'''

new_mirror_loop = '''    for (const m of mirrors) {
      if (m.broken) continue;
      const c = closestOnSeg(b.x, b.y, m.x1, m.y1, m.x2, m.y2);
      if (Math.hypot(b.x - c.x, b.y - c.y) < b.r + 3) {'''

if old_mirror_loop in idx:
    idx = idx.replace(old_mirror_loop, new_mirror_loop)
    changed.append('skip-broken-reflect')
else:
    print('WARN: mirror loop in bullets not found')

# --- 5) drawMirror: don't draw broken ---
old_draw = '''function drawMirror(m) {
  ctx.strokeStyle = m.hp < 3 ? `rgba(144,164,174,${0.4 + m.hp * 0.2})` : '#90a4ae';
  ctx.lineWidth = 7;
  ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(m.x1, m.y1); ctx.lineTo(m.x2, m.y2); ctx.stroke();
  ctx.strokeStyle = 'rgba(255,255,255,.35)'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(m.x1, m.y1); ctx.lineTo(m.x2, m.y2); ctx.stroke();
}'''

new_draw = '''function drawMirror(m) {
  if (m.broken) return;
  ctx.strokeStyle = m.hp < 3 ? `rgba(144,164,174,${0.4 + m.hp * 0.2})` : '#90a4ae';
  ctx.lineWidth = 7;
  ctx.lineCap = 'round';
  ctx.beginPath(); ctx.moveTo(m.x1, m.y1); ctx.lineTo(m.x2, m.y2); ctx.stroke();
  ctx.strokeStyle = 'rgba(255,255,255,.35)'; ctx.lineWidth = 2;
  ctx.beginPath(); ctx.moveTo(m.x1, m.y1); ctx.lineTo(m.x2, m.y2); ctx.stroke();
}'''

if old_draw in idx:
    idx = idx.replace(old_draw, new_draw)
    changed.append('draw-skip-broken')
else:
    print('WARN: drawMirror not exact')

# --- 6) Call updateMirrorsLocal in solo playing loop ---
old_loop = '''      updateBullets();
      updatePowerups();'''
new_loop = '''      updateBullets();
      updateMirrorsLocal();
      updatePowerups();'''

if old_loop in idx and 'updateMirrorsLocal();' not in idx.split('updateBullets();')[1][:80]:
    idx = idx.replace(old_loop, new_loop, 1)
    changed.append('call-updateMirrors')
elif 'updateMirrorsLocal();' in idx:
    changed.append('call-updateMirrors-already')
else:
    print('WARN: loop inject point not found')

old_make = '''  return { x1: cx - dx, y1: cy - dy, x2: cx + dx, y2: cy + dy, type, hp: 3 };'''
new_make = '''  return { x1: cx - dx, y1: cy - dy, x2: cx + dx, y2: cy + dy, type, hp: 3, broken: false, respawnAt: 0 };'''
if old_make in idx:
    idx = idx.replace(old_make, new_make)
    changed.append('makeMirror-flags')

Path('index.html').write_text(idx, encoding='utf-8')
print('CHANGED:', ', '.join(changed) if changed else 'nothing')
print('has shatter in bullets:', 'shatterMirror(m, c.x, c.y)' in idx)
print('has updateMirrorsLocal call:', idx.count('updateMirrorsLocal') >= 2)
print('has broken skip draw:', 'if (m.broken) return;' in idx)
