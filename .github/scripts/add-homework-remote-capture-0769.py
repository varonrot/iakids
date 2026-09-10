from pathlib import Path
p=Path('he/workspace/index.html')
s=p.read_text(encoding='utf-8')
old='<script src="/he/workspace/homework-remote-capture.js?v=0769"></script>'
if old not in s:
    s=s.replace('</body></html>', old+'\n</body></html>')
s=s.replace('build 0.7.68','build 0.7.69').replace('build 0.7.67','build 0.7.69').replace('build 0.7.62','build 0.7.69')
p.write_text(s,encoding='utf-8')
