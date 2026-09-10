from pathlib import Path

EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

# 1) Make intro line a positioning context and add visible writing hand.
old_css = '''      .homework-notebook-intro-line{\n        min-height:34px;\n        margin:0 0 6px;\n        color:#24408a;\n        font-family:"Gveret Levin","Segoe Print","Comic Sans MS",cursive;\n        font-weight:500;\n        line-height:1.75;\n        text-align:right;\n        white-space:pre-wrap;\n        letter-spacing:.1px;\n      }\n'''
new_css = '''      .homework-notebook-intro-line{\n        position:relative;\n        min-height:42px;\n        margin:0 0 8px;\n        padding-left:42px;\n        color:#24408a;\n        font-family:"Gveret Levin","Segoe Print","Comic Sans MS",cursive;\n        font-weight:500;\n        line-height:1.75;\n        text-align:right;\n        white-space:pre-wrap;\n        letter-spacing:.1px;\n      }\n\n      .homework-writing-hand{\n        position:absolute;\n        top:-6px;\n        left:0;\n        z-index:4;\n        font-size:31px;\n        line-height:1;\n        pointer-events:none;\n        filter:drop-shadow(0 2px 2px rgba(20,40,90,.18));\n        transform:rotate(-12deg);\n        transition:left .08s linear, top .08s linear;\n        animation:homeworkWritingHandBob .45s ease-in-out infinite alternate;\n      }\n\n      @keyframes homeworkWritingHandBob{\n        from{transform:translateY(0) rotate(-12deg)}\n        to{transform:translateY(2px) rotate(-8deg)}\n      }\n'''
if old_css in ext:
    ext = ext.replace(old_css, new_css, 1)
elif '.homework-writing-hand{' not in ext:
    raise SystemExit('intro CSS anchor not found')

# 2) Slow the handwriting and move the hand along the live writing edge.
old_writer = '''    const row = document.createElement("div");\n    row.className = `homework-notebook-intro-line ${className || ""} writing`;\n    const span = document.createElement("span");\n    row.appendChild(span);\n    host.appendChild(row);\n\n    const delay = value.length > 55 ? 15 : 23;\n    for(let i=0;i<value.length;i+=1){\n      span.textContent += value[i];\n      if(i % 4 === 0) await homeworkNotebookSleep(delay);\n    }\n    row.classList.remove("writing");\n'''
new_writer = '''    const row = document.createElement("div");\n    row.className = `homework-notebook-intro-line ${className || ""} writing`;\n    const span = document.createElement("span");\n    const hand = document.createElement("span");\n    hand.className = "homework-writing-hand";\n    hand.textContent = "✍️";\n    hand.setAttribute("aria-hidden", "true");\n    row.appendChild(span);\n    row.appendChild(hand);\n    host.appendChild(row);\n\n    // Deliberately visible handwriting pace: roughly 2-4 seconds per line.\n    const delay = value.length > 55 ? 55 : value.length > 32 ? 68 : 82;\n    for(let i=0;i<value.length;i+=1){\n      span.textContent += value[i];\n\n      // Hebrew grows from right to left. The left edge of the written span is\n      // therefore approximately where the pen tip currently is.\n      const rowRect = row.getBoundingClientRect();\n      const spanRect = span.getBoundingClientRect();\n      const x = Math.max(0, Math.min(row.clientWidth - 34, spanRect.left - rowRect.left - 18));\n      hand.style.left = `${x}px`;\n\n      await homeworkNotebookSleep(delay);\n    }\n\n    await homeworkNotebookSleep(260);\n    hand.remove();\n    row.classList.remove("writing");\n'''
if old_writer in ext:
    ext = ext.replace(old_writer, new_writer, 1)
elif 'hand.className = "homework-writing-hand"' not in ext:
    raise SystemExit('intro writer anchor not found')

# Version bump.
ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.74";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.76";')
for oldv in ('0.7.74','0.7.75'):
    index = index.replace(f'IAKIDS • build {oldv}', 'IAKIDS • build 0.7.76')
    index = index.replace(f'window.IAKIDS_BUILD_VERSION = "{oldv}";', 'window.IAKIDS_BUILD_VERSION = "0.7.76";')
index = index.replace('/he/workspace/lesson-completion.js?v=0774', '/he/workspace/lesson-completion.js?v=0776')
index = index.replace('/he/workspace/lesson-completion.js?v=0775', '/he/workspace/lesson-completion.js?v=0776')

EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print('Slowed notebook handwriting and added animated writing hand; build 0.7.76')
