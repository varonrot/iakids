from pathlib import Path

path = Path('he/workspace/index.html')
text = path.read_text(encoding='utf-8')
text = text.replace('IAKIDS • build 0.7.69', 'IAKIDS • build 0.7.71')
text = text.replace('window.IAKIDS_BUILD_VERSION = "0.7.62";', 'window.IAKIDS_BUILD_VERSION = "0.7.71";')
text = text.replace('/he/workspace/homework-remote-capture.js?v=0769', '/he/workspace/homework-remote-capture.js?v=0771')
text = text.replace('/he/workspace/homework-remote-capture.js?v=0770', '/he/workspace/homework-remote-capture.js?v=0771')
path.write_text(text, encoding='utf-8')

js = Path('he/workspace/homework-remote-capture.js')
if js.exists():
    t = js.read_text(encoding='utf-8')
    t = t.replace('0.7.70', '0.7.71').replace('__IAKIDS_REMOTE_HOMEWORK_0770', '__IAKIDS_REMOTE_HOMEWORK_0771')
    js.write_text(t, encoding='utf-8')
