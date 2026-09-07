#!/usr/bin/env python3
"""Fix touch joystick coords + add exit button on results screen."""
from pathlib import Path

idx = Path('index.html').read_text(encoding='utf-8')
changed = []

# 1) isTouch
old = "const isTouch = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0);  // 超大地图，贪吃蛇式自由游走 + 镜头跟随"
new = "const isTouch = ('ontouchstart' in window) || (navigator.maxTouchPoints > 0) || (window.matchMedia && matchMedia('(pointer: coarse)').matches);"
if old in idx:
    idx = idx.replace(old, new)
    changed.append('isTouch')

# 2) drawTouchUI full replace
import re
m = re.search(r'function drawTouchUI\(\) \{[\s\S]*?\n\}', idx)
if m:
    new_draw = '''function drawTouchUI() {
  // 始终在触屏设备上显示虚拟摇杆（逻辑坐标，与 HUD 一致）
  if (!isTouch && !touchInput.active) return;
  const sw = viewW, sh = viewH;
  const baseX = 90, baseY = sh - 90;
  if (joyMove.active) {
    const r = cv.getBoundingClientRect();
    const lx = (joyMove.cx / Math.max(r.width, 1)) * viewW;
    const ly = (joyMove.cy / Math.max(r.height, 1)) * viewH;
    ctx.globalAlpha = .28;
    ctx.fillStyle = '#000';
    ctx.beginPath(); ctx.arc(lx, ly, 54, 0, 7); ctx.fill();
    ctx.globalAlpha = .55;
    ctx.fillStyle = '#fff';
    const d = Math.min(Math.hypot(joyMove.dx, joyMove.dy), 42);
    const a = Math.atan2(joyMove.dy, joyMove.dx);
    ctx.beginPath(); ctx.arc(lx + Math.cos(a) * d, ly + Math.sin(a) * d, 24, 0, 7); ctx.fill();
    ctx.globalAlpha = 1;
  } else {
    ctx.globalAlpha = .22;
    ctx.fillStyle = '#000';
    ctx.beginPath(); ctx.arc(baseX, baseY, 54, 0, 7); ctx.fill();
    ctx.globalAlpha = .45;
    ctx.fillStyle = '#fff';
    ctx.beginPath(); ctx.arc(baseX, baseY, 24, 0, 7); ctx.fill();
    ctx.globalAlpha = 1;
    ctx.fillStyle = 'rgba(255,255,255,.75)'; ctx.font = 'bold 14px system-ui'; ctx.textAlign = 'center';
    ctx.fillText('移动', baseX, baseY + 48);
  }
  const fb = { x: sw - 90, y: sh - 90, r: 48 };
  ctx.globalAlpha = joyFire.active ? .6 : .32;
  ctx.fillStyle = joyFire.active ? '#ffeb3b' : '#000';
  ctx.beginPath(); ctx.arc(fb.x, fb.y, fb.r, 0, 7); ctx.fill();
  ctx.globalAlpha = 1;
  ctx.fillStyle = '#fff'; ctx.font = 'bold 15px system-ui'; ctx.textAlign = 'center';
  ctx.fillText('射击', fb.x, fb.y + 5);
  const db = { x: sw - 175, y: sh - 70, r: 34 };
  ctx.globalAlpha = .32; ctx.fillStyle = '#81d4fa';
  ctx.beginPath(); ctx.arc(db.x, db.y, db.r, 0, 7); ctx.fill();
  ctx.globalAlpha = 1;
  ctx.fillStyle = '#fff'; ctx.font = 'bold 13px system-ui';
  ctx.fillText('冲刺', db.x, db.y + 5);
}'''
    idx = idx[:m.start()] + new_draw + idx[m.end():]
    changed.append('drawTouchUI')
else:
    print('WARN: drawTouchUI not found')

# 3) render: don't switch to DPR transform for touch UI
old_ui = '''    drawHud();
    // 触屏控件用 CSS 像素，重置变换
    ctx.setTransform(window.devicePixelRatio || 1, 0, 0, window.devicePixelRatio || 1, 0, 0);
    drawTouchUI();'''
new_ui = '''    drawHud();
    // 触屏控件与 HUD 同一逻辑坐标系，保证竖屏/横屏都正确显示
    drawTouchUI();'''
if old_ui in idx:
    idx = idx.replace(old_ui, new_ui)
    changed.append('renderTransform')
else:
    idx2, n = re.subn(
        r'drawHud\(\);\s*//[^\n]*\s*ctx\.setTransform\(window\.devicePixelRatio[\s\S]*?drawTouchUI\(\);',
        'drawHud();\n    // 触屏控件与 HUD 同一逻辑坐标系\n    drawTouchUI();',
        idx,
        count=1,
    )
    if n:
        idx = idx2
        changed.append('renderTransform-re')
    else:
        print('WARN: render UI block not found')

# 4) exit button HTML
if 'id="btnExit"' not in idx:
    old_over = '''      <button id="btnAgain">再来一局</button>
      <div class="tip" id="nextRoundTip"></div>'''
    new_over = '''      <button id="btnAgain">再来一局</button>
      <button id="btnExit" class="secondary-btn" style="margin-top:12px;">返回菜单</button>
      <div class="tip" id="nextRoundTip"></div>'''
    if old_over in idx:
        idx = idx.replace(old_over, new_over)
        changed.append('exitHtml')
    else:
        print('WARN: over HTML not found')

# 5) exit handler
if "getElementById('btnExit')" not in idx:
    old_h = '''document.getElementById('btnAgain').onclick = () => {
  if (mode === 'solo') {
    document.getElementById('over').classList.add('hidden');
    resetGame();
    state = 'playing';
  } else {
    location.reload();
  }
};'''
    new_h = '''document.getElementById('btnAgain').onclick = () => {
  if (mode === 'solo') {
    document.getElementById('over').classList.add('hidden');
    resetGame();
    state = 'playing';
  } else {
    location.reload();
  }
};
document.getElementById('btnExit').onclick = () => {
  document.getElementById('over').classList.add('hidden');
  state = 'menu';
  mode = 'solo';
  document.getElementById('menu').classList.remove('hidden');
  if (typeof ws !== 'undefined' && ws && ws.readyState === 1) {
    try { ws.close(); } catch (e) {}
  }
};'''
    if old_h in idx:
        idx = idx.replace(old_h, new_h)
        changed.append('exitHandler')
    else:
        print('WARN: btnAgain handler not found')

Path('index.html').write_text(idx, encoding='utf-8')
print('CHANGED:', ', '.join(changed) if changed else 'nothing')
print('btnExit present:', 'btnExit' in idx)
print('logical joy present:', 'const sw = viewW, sh = viewH' in idx)
