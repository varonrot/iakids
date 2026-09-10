from pathlib import Path
p=Path('he/workspace/index.html')
s=p.read_text()
s=s.replace('IAKIDS • build 0.7.69','IAKIDS • build 0.7.70')
s=s.replace('/he/workspace/homework-remote-capture.js?v=0769','/he/workspace/homework-remote-capture.js?v=0770')
p.write_text(s)
