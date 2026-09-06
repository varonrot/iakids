from pathlib import Path

CORE = Path('he/workspace/lesson-completion-core.js')
EXT = Path('he/workspace/lesson-completion.js')
INDEX = Path('he/workspace/index.html')

core = CORE.read_text(encoding='utf-8')
ext = EXT.read_text(encoding='utf-8')
index = INDEX.read_text(encoding='utf-8')

old = '''  async function getHomeworkAccessToken(){
    try{
      const sessionResult = await window.sb?.auth?.getSession?.();
      return sessionResult?.data?.session?.access_token || "";
    }
    catch(error){
      console.warn("HOMEWORK ACCESS TOKEN WARNING:", error);
      return "";
    }
  }
'''

new = '''  async function getHomeworkAccessToken(){
    try{
      // The workspace Supabase client is declared as top-level `sb` in index.html.
      // It is not guaranteed to exist as window.sb, so prefer the real client first.
      let client = null;

      if(typeof sb !== "undefined" && sb?.auth?.getSession){
        client = sb;
      }
      else if(window.sb?.auth?.getSession){
        client = window.sb;
      }
      else if(window.supabaseClient?.auth?.getSession){
        client = window.supabaseClient;
      }

      if(!client){
        console.warn("HOMEWORK ACCESS TOKEN: Supabase client not found");
        return "";
      }

      const sessionResult = await client.auth.getSession();
      const token = sessionResult?.data?.session?.access_token || "";

      console.log("HOMEWORK ACCESS TOKEN:", token ? "session available" : "no session");
      return token;
    }
    catch(error){
      console.warn("HOMEWORK ACCESS TOKEN WARNING:", error);
      return "";
    }
  }
'''

count = core.count(old)
if count < 1:
    raise SystemExit('getHomeworkAccessToken block not found')
core = core.replace(old, new)

index = index.replace('IAKIDS • build 0.7.26', 'IAKIDS • build 0.7.27')
index = index.replace('window.IAKIDS_BUILD_VERSION = "0.7.26";', 'window.IAKIDS_BUILD_VERSION = "0.7.27";')
index = index.replace('/he/workspace/lesson-completion.js?v=0726', '/he/workspace/lesson-completion.js?v=0727')

ext = ext.replace('window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.26";', 'window.IAKIDS_HOMEWORK_WORKSPACE_VERSION = "0.7.27";')
ext = ext.replace('/he/workspace/lesson-completion-core.js?v=0726', '/he/workspace/lesson-completion-core.js?v=0727')

CORE.write_text(core, encoding='utf-8')
EXT.write_text(ext, encoding='utf-8')
INDEX.write_text(index, encoding='utf-8')
print(f'Fixed homework auth client in {count} block(s); build 0.7.27')

# trigger workflow
