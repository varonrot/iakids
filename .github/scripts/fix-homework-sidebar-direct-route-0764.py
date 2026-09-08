from pathlib import Path
import re

INDEX = Path('he/workspace/index.html')
LOADER = Path('he/workspace/lesson-completion.js')

index = INDEX.read_text(encoding='utf-8')
loader = LOADER.read_text(encoding='utf-8')

# Make the sidebar button call the dedicated homework entrypoint directly.
old = '''      onclick="showLearning('homework')"'''
new = '''      onclick="event.preventDefault(); event.stopPropagation(); if (typeof window.showHomeworkLessonWorkspace === 'function') { window.showHomeworkLessonWorkspace(); } else if (typeof window.showLearning === 'function') { window.showLearning('homework'); }"'''
if old in index:
    index = index.replace(old, new, 1)

marker = 'IAKIDS_HOMEWORK_DIRECT_SIDEBAR_ROUTE_0764'
if marker not in index:
    injection = r'''
<script id="IAKIDS_HOMEWORK_DIRECT_SIDEBAR_ROUTE_0764">
(function(){
  function openHomeworkFromSidebar(event){
    const button = event.target.closest('#homeworkSidebarBtn');
    if(!button) return;
    event.preventDefault();
    event.stopImmediatePropagation();

    if(typeof window.showHomeworkLessonWorkspace === 'function'){
      window.showHomeworkLessonWorkspace();
      return;
    }

    // If the homework extension is still finishing its startup, retry briefly.
    let attempts = 0;
    const retry = function(){
      attempts += 1;
      if(typeof window.showHomeworkLessonWorkspace === 'function'){
        window.showHomeworkLessonWorkspace();
        return;
      }
      if(attempts < 30){
        setTimeout(retry, 100);
        return;
      }
      if(typeof window.showLearning === 'function'){
        window.showLearning('homework');
      }else{
        console.error('HOMEWORK SIDEBAR: homework entrypoint is unavailable');
      }
    };
    retry();
  }

  // Capture phase guarantees this runs before older sidebar handlers.
  document.addEventListener('click', openHomeworkFromSidebar, true);
})();
</script>
'''
    index = index.replace('</body>', injection + '\n</body>', 1)

# bump cache/version
index = re.sub(r'IAKIDS\s*•\s*build\s*0\.7\.\d+', 'IAKIDS • build 0.7.64', index, count=1)
index = re.sub(r'window\.IAKIDS_BUILD_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_BUILD_VERSION = "0.7.64";', index, count=1)
index = re.sub(r'lesson-completion\.js\?v=\d+', 'lesson-completion.js?v=0764', index, count=1)
loader = re.sub(r'window\.IAKIDS_HOMEWORK_WORKSPACE_VERSION\s*=\s*"0\.7\.\d+";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.64";', loader, count=1)
loader = re.sub(r'lesson-completion-core\.js\?v=\d+', 'lesson-completion-core.js?v=0764', loader, count=1)

INDEX.write_text(index, encoding='utf-8')
LOADER.write_text(loader, encoding='utf-8')
print('Homework sidebar direct route fixed; build 0.7.64')
