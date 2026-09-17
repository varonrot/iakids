from pathlib import Path

index_path = Path('he/workspace/index.html')
js_path = Path('he/workspace/openai-clean-chat.js')

text = index_path.read_text(encoding='utf-8')

# Remove the unrelated dashboard layout overrides that landed together with build 0.7.120.
text = text.replace('''    body:not(.lesson-theme-science):not(.science-hierarchy-mode) .app:has(#dashboardView:not([style*="display: none"]):not([style*="display:none"])) #dashboardView{\n      position:relative!important;\n    }\n\n''', '')
text = text.replace('''      width:auto!important;\n      max-width:none!important;\n''', '')
text = text.replace('''      transform:none!important;\n''', '')

text = text.replace('IAKIDS • build 0.7.120', 'IAKIDS • build 0.7.121')
text = text.replace('window.IAKIDS_BUILD_VERSION = "0.7.120";', 'window.IAKIDS_BUILD_VERSION = "0.7.121";')
text = text.replace('openai-clean-chat.js?v=07120', 'openai-clean-chat.js?v=07121')
index_path.write_text(text, encoding='utf-8')

if js_path.exists():
    js = js_path.read_text(encoding='utf-8')
    js = js.replace("window.IAKIDS_BUILD_VERSION||'0.7.120'", "window.IAKIDS_BUILD_VERSION||'0.7.121'")
    js_path.write_text(js, encoding='utf-8')
