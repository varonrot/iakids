from pathlib import Path

p = Path('he/workspace/index.html')
text = p.read_text(encoding='utf-8')

old_guard = '''            if(
              row.dataset.locked ===
              "true"
            ){

              return;

            }


'''
if old_guard not in text:
    raise SystemExit('locked click guard not found')
text = text.replace(old_guard, '', 1)

# Force every lesson row to accept pointer input and communicate clickability.
css_marker = '''body.lesson-theme-science
.lesson-sidebar-row{
  position:relative !important;
'''
css_replacement = '''body.lesson-theme-science
.lesson-sidebar-row{
  position:relative !important;

  pointer-events:auto !important;
  cursor:pointer !important;
'''
if css_marker not in text:
    raise SystemExit('sidebar row css marker not found')
text = text.replace(css_marker, css_replacement, 1)

# Remove now-obsolete data-locked rendering entirely.
old_attr = '''
              ${
                isLocked
                  ? 'data-locked="true"'
                  : ""
              }
'''
if old_attr in text:
    text = text.replace(old_attr, '', 1)

# Add keyboard/accessibility semantics to every lesson row.
old_id_attr = '''              data-sidebar-lesson-id="${
                Number(
                  lesson.id
                )
              }"
'''
new_id_attr = '''              data-sidebar-lesson-id="${
                Number(
                  lesson.id
                )
              }"
              role="button"
              tabindex="0"
'''
if old_id_attr not in text:
    raise SystemExit('sidebar data id attr not found')
text = text.replace(old_id_attr, new_id_attr, 1)

# Keyboard Enter/Space should trigger the same click path.
needle = '''        row.addEventListener(
          "click",
          async () => {
'''
if needle not in text:
    raise SystemExit('click handler marker not found')
# Existing click handler remains; add keydown after its listener block by replacing the first local closing pattern.
end_marker = '''        );

      }
    );

}
/* =====================================================
   PERSONAL KID LESSON INTRO VIDEO
'''
keyboard = '''        );

        row.addEventListener(
          "keydown",
          event => {
            if(event.key === "Enter" || event.key === " "){
              event.preventDefault();
              row.click();
            }
          }
        );

      }
    );

}
/* =====================================================
   PERSONAL KID LESSON INTRO VIDEO
'''
if end_marker not in text:
    raise SystemExit('click handler end marker not found')
text = text.replace(end_marker, keyboard, 1)

if 'IAKIDS • build 0.6.1' not in text:
    raise SystemExit('expected build 0.6.1 not found')
text = text.replace('IAKIDS • build 0.6.1', 'IAKIDS • build 0.6.2')
text = text.replace('window.IAKIDS_BUILD_VERSION = "0.6.1";', 'window.IAKIDS_BUILD_VERSION = "0.6.2";')

p.write_text(text, encoding='utf-8')
