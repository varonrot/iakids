from pathlib import Path

p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
s=s.replace('IAKIDS • build 0.7.70','IAKIDS • build 0.7.71')
s=s.replace('/he/workspace/homework-remote-capture.js?v=0769','/he/workspace/homework-remote-capture.js?v=0771')
s=s.replace('/he/workspace/homework-remote-capture.js?v=0770','/he/workspace/homework-remote-capture.js?v=0771')
p.write_text(s,encoding='utf-8')
