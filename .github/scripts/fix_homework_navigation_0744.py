from pathlib import Path
import re

ROOT = Path('.')
loader = ROOT / 'he' / 'workspace' / 'lesson-completion.js'
index = ROOT / 'he' / 'workspace' / 'index.html'

text = loader.read_text(encoding='utf-8')

# Bump version/cache.
text = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.44";', text, count=1)
text = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0744', text, count=1)

# Add a prominent, always-visible Home button style below the homework sidebar title.
style_anchor = '''      .homework-sidebar-title strong{\n        font:900 15px "Heebo",Arial,sans-serif;\n      }\n'''
style_block = style_anchor + '''\n      .homework-sidebar-home{\n        width:100%;\n        min-height:46px;\n        margin:0 0 12px;\n        padding:0 12px;\n        display:flex;\n        align-items:center;\n        justify-content:center;\n        gap:9px;\n        border:1px solid rgba(92,179,255,.55);\n        border-radius:12px;\n        background:linear-gradient(135deg,rgba(21,93,171,.88),rgba(79,48,183,.86));\n        color:#fff;\n        box-shadow:0 8px 20px rgba(0,8,28,.24),0 0 16px rgba(63,156,255,.12);\n        font:850 12px "Heebo",Arial,sans-serif;\n        cursor:pointer;\n      }\n\n      .homework-sidebar-home:hover{\n        transform:translateY(-1px);\n        border-color:#78ddff;\n      }\n'''
if '.homework-sidebar-home{' not in text:
    if style_anchor not in text:
        raise RuntimeError('sidebar style anchor not found')
    text = text.replace(style_anchor, style_block, 1)

# Add the actual Home button before the homework steps.
html_anchor = '''      <div class="homework-sidebar-title">\n        <i class="fa-solid fa-camera"></i>\n        <strong>עזרה בשיעורי בית</strong>\n      </div>\n'''
html_block = html_anchor + '''      <button type="button" class="homework-sidebar-home" data-homework-home>\n        <i class="fa-solid fa-house"></i>\n        <span>דף הבית</span>\n      </button>\n'''
if 'data-homework-home' not in text:
    if html_anchor not in text:
        raise RuntimeError('sidebar html anchor not found')
    text = text.replace(html_anchor, html_block, 1)

# Wire the button immediately after appendChild so it cannot get lost behind overlay state.
wire_anchor = '''    sidebar.appendChild(overlay);\n  }\n'''
wire_block = '''    sidebar.appendChild(overlay);\n\n    overlay.querySelector("[data-homework-home]")?.addEventListener("click", function(){\n      window.location.href = "/he/workspace/";\n    });\n  }\n'''
if 'window.location.href = "/he/workspace/";' not in text:
    if wire_anchor not in text:
        raise RuntimeError('sidebar wire anchor not found')
    text = text.replace(wire_anchor, wire_block, 1)

loader.write_text(text, encoding='utf-8')

# Visible build bump in main page.
i = index.read_text(encoding='utf-8')
i = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.44', i)
i = re.sub(r'build\s*0\.7\.\d+', 'build 0.7.44', i)
index.write_text(i, encoding='utf-8')

print('Homework navigation fixed; version 0.7.44')
