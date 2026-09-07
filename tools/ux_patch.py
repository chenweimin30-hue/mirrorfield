#!/usr/bin/env python3
from pathlib import Path

idx = Path('index.html').read_text(encoding='utf-8')

# Ensure applyMapSize is called when starting campaign/solo
if 'function resetGame' in idx and 'applyMapSize()' not in idx.split('function resetGame')[1][:120]:
    idx = idx.replace(
        'function resetGame() {\n  genMirrors();',
        "function resetGame() {\n  if (typeof applyMapSize==='function') applyMapSize();\n  genMirrors();"
    )

# Also call before start when buttons clicked if patterns exist
for sig in (
    "mode = 'solo';\n  state = 'playing';",
    "mode = 'campaign';\n  resetGame();",
):
    if sig in idx and 'applyMapSize' not in sig:
        pass

if "document.getElementById('btnSolo')" in idx and 'applyMapSize()' not in idx:
    # inject into resetGame is enough if solo uses resetGame
    pass

# Force inject into resetGame more aggressively
if 'function resetGame() {\n  genMirrors();' in idx:
    idx = idx.replace(
        'function resetGame() {\n  genMirrors();',
        "function resetGame() {\n  if (typeof applyMapSize==='function') applyMapSize();\n  genMirrors();"
    )
elif 'function resetGame(){\n  genMirrors();' in idx:
    idx = idx.replace(
        'function resetGame(){\n  genMirrors();',
        "function resetGame(){\n  if (typeof applyMapSize==='function') applyMapSize();\n  genMirrors();"
    )
else:
    # last resort: prepend call after function open
    import re
    idx2, n = re.subn(
        r'(function resetGame\(\)\s*\{)',
        r"\1\n  if (typeof applyMapSize==='function') applyMapSize();",
        idx,
        count=1,
    )
    if n:
        idx = idx2

Path('index.html').write_text(idx, encoding='utf-8')
print('resetGame fixed', 'applyMapSize()' in idx.split('function resetGame')[1][:200])
