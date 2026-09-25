# BUGFIXES — what each commit fixed

Rule (2026-09-16): every `commit` + `push` adds an entry here that says exactly what was fixed, how it showed up, and how it was verified. Newest first. Build numbers refer to the workspace stamp (`IAKIDS • build 0.7.N`).

## 2026-09-25 — Fit the English dashboard into a desktop viewport (eng-dashboard-7)

- Symptom: the bottom dashboard row was cut off on a 1915×987 browser screenshot, requiring vertical scrolling to see the full page.
- Cause: the page used independent minimum row heights plus fixed hero, feature media, and feature body heights; their sum exceeded the viewport once all progress rows returned.
- Fix: for desktop viewports 900–1140 CSS pixels tall, allocate the hero, feature cards, and dashboard panels from the available height and compact feature text without removing content. Refresh the CSS cache key.
- Verification: checked the computed height of each row, desktop page scroll height after deployment, and the final full-page rendering.
- Build: eng-dashboard-7, English dashboard only.

## 2026-09-25 — Restore the English Recent Progress reference (eng-dashboard-6)

- Symptom: the Recent Progress card showed an empty state rather than the four activity rows and encouragement strip in the approved reference image.
- Fix: restore the four illustrative activity rows, right-aligned View all link, mint encouragement strip, and mobile visibility; refresh the dashboard stylesheet cache key.
- Verification: markup and responsive style checks, plus live page inspection after deployment.
- Build: eng-dashboard-6, English dashboard only. Activity values are illustrative and are not read from a child's learning record.


## 2026-09-25 — Restore complete English dashboard CSS and bugfix history (eng-dashboard-5)

- Symptom: dashboard feature images were placeholders and the Recent Progress book icon filled its panel after the logo size fix.
- Cause: a previous file upload captured truncated command output, inserting truncation warnings into the CSS and this changelog and omitting large sections.
- Fix: reconstruct both files from the last complete versions, preserve later changes, and refresh the dashboard CSS cache key.
- Verification: original CSS rules and later additions are present, no truncation markers remain, and uploaded Git blobs match local blob hashes exactly. Check the desktop and tablet dashboard layout after deployment.
- Build: eng-dashboard-5, English dashboard and changelog only.


## 2026-09-25 — Constrain the English dashboard logo at every viewport (eng-dashboard-4)

- Symptom: at tablet widths, the brand mark rendered at its 1280px source size, covering dashboard content and causing horizontal overflow.
- Cause: logo dimensions were only set inside the mobile and wide desktop media queries.
- Fix: define a 38px default logo size with contained scaling; existing breakpoint-specific sizes remain in effect. Bump the dashboard stylesheet cache key.
- Verification: confirmed the base sizing rule applies across the missing 721–1100px range and narrower/wider breakpoint rules override it as intended; `git diff --check`.
- Build: eng-dashboard-4, English dashboard only.


## 2026-09-24 — Claude Code project settings were invalid JSON; gate hooks never ran (build 0.7.148)

- Symptom: Claude Code reported "Settings (.claude/settings.json): Expected object, but received undefined", and the PreToolUse/PostToolUse prompt-gate hooks (pre-edit backup, post-edit gate, the Bash guard on bare `systemctl restart`) were silently skipped.
- Cause: the three hook `command` strings contained unescaped double quotes around `${CLAUDE_PROJECT_DIR:-/opt/iakids}/tools/prompt_gate.py`, so the file stopped parsing at line 9 (since e320959d).
- Fix: escaped the inner quotes (`\"`). The commands are unchanged once parsed.
- Verification: `json.load` parses the file and prints the three commands as intended; `prompt_gate --all` passes.
- Build: 0.7.148.

## 2026-09-24 — Complete Recent Progress empty state (eng-dashboard-3)

- Symptom: the Recent Progress panel showed two brief placeholder rows and a large unused gap.
- Fix: replace them with a centered first-use state, a learning-book illustration, a short explanation, and a Test Prep action. No activity is implied.
- Verification: HTML structure and CTA target checked; responsive empty-state styles added; JavaScript and auth flow remain unchanged.
- Build: eng-dashboard-3, English dashboard only.


## 2026-09-24 — Restore English dashboard sections (eng-dashboard-2)

- Symptom: summary cards, Continue Learning, Recent Progress and the mobile goal disappeared after the authentication release.
- Cause: parent-auth.js explicitly hid all four sections to remove demo data.
- Fix: preserve the dashboard layout, replace fabricated scores/activity/lesson progress with honest unavailable and starter states, and route the starter CTA through the existing Test Prep sign-in flow.
- Verification: syntax and DOM checks for section visibility, removal of fabricated metrics, and Test Prep CTA destination.
- Workflow: per user instruction, CLAUDE.md now treats requested fixes as authorization to commit, push and deploy after verification, without a separate shipping confirmation.
- Build: eng-dashboard-2, English frontend only; Hebrew workspace build unchanged.


## 2026-09-24 — Hebrew reading comprehension SEO cluster

- Need: dedicated reading comprehension coverage beyond the existing test-preparation article.
- Change: eight linked pages, 24 original exercises with hints/solutions, original reading passages, generated hero, Heebo and printable worksheets. Added blog discovery cards and contextual link from Hebrew test preparation.
- SEO/analytics: unique metadata, canonical and structured data, GA4 G-DKPPTPCDW8 with reading_comprehension_he event grouping. Existing sitemap workflow picks up eight new index pages.
- Verification: HTML, internal links, IDs, metadata, JSON-LD and inline JS syntax checked. Event harness verifies view, CTA placements, link, hint, solution, practice and print paths. Live rendering and sitemap checked after deployment; Analytics report ingestion not asserted.
- Build: blog content only; workspace build unchanged. Image prompt and implementation details in docs/SEO-READING-COMPREHENSION.md.

## 2026-09-24 — English Google parent sign-in (eng-auth-1)

- Need: Start prep should open parent Google sign-in before selecting or uploading study material.
- Change: responsive parent dialog with Google only, isolated PKCE session, pending-action restoration, existing authenticated kid-list/create APIs, profile selection and first-time name/grade form. The current tutor API uses its legacy age field for grade 1–6. No browser database queries or backend/schema changes.
- UI: parent profile button, real child names rendered as text, sample Emma/statistics/activity hidden. Auth errors and cancellation do not open Test Prep; close restores focus and scrolling.
- Verification: node syntax and diff checks; DOM harness passed unauthenticated gating, OAuth configuration, existing child, cross-account selection isolation, new profile, name escaping, API error, direct-link entry, callback resume/cancellation and scroll restoration. Google provider is enabled and authorize returns 302 to accounts.google.com; kid-list without bearer returns 401. Full Google callback with a real account still requires live user verification.
- Build: English eng-auth-1; shared Hebrew/Spanish screens unchanged. Supabase browser SDK vendored at 2.57.4 from official jsDelivr package distribution.

## 2026-09-24 — Hebrew school test preparation SEO cluster

- Need: expand Hebrew SEO coverage from gifted testing to ordinary elementary school test preparation.
- Change: nine new pages and integration of the existing overview (10-page cluster), 21 original exercises with hints/explanations, planning and review tables, two generated WebP heroes, Heebo, internal links and blog discovery cards. Existing overview canonical preserved; one stale learning-gap link repaired.
- SEO/measurement: unique metadata and structured data; GA4 G-DKPPTPCDW8 and cluster interaction events. Existing sitemap workflow discovers the new index pages.
- Verification: parsed all 11 changed HTML files and structured data, checked inline JavaScript syntax, IDs, canonical URLs and images. Event harness passed view, all three CTA placements, cluster link, practice start, hint, solution and print. Live delivery and sitemap checked after deployment; GA reporting ingestion is not asserted.
- Build: content-only blog addition; workspace build unchanged. Details and image prompts: docs/SEO-TEST-PREPARATION.md.

## 2026-09-24 — English Test Prep mobile layout (prep-mobile-20260924)

- Symptom: the mobile banner shrank into a corner, cards felt compact, and Cancel sat beside the footer note with excess empty space below.
- Cause: the mobile image used contain/auto height and the desktop footer stayed horizontal.
- Fix: use a full-height cover image with a left readability gradient, larger stacked cards, a flexible full-screen content area, centered footer note, and a full-width Cancel button. Narrow-phone and safe-area spacing remain responsive. Only English modal CSS and its cache version changed.
- Verification: CSS parser passed, both English entry points reference the new stylesheet version; desktop declarations preserved. Phone visual verification remains required; no mobile viewport control is exposed in the connected browser.
- Build: English CSS cache version prep-mobile-20260924; Hebrew workspace unchanged.

## 2026-09-24

### 2026-09-24 — exam prep and gifted in the main menu; menu grows on hover; "חדש" badges (build 0.7.147)
- **Exam prep and gifted** (user: move them to the main menu, not under בדיקות ומעקב):
  - They now have their own buttons in the workspace menu, "הכנה למבחן" and "מבחן המחוננים". Each opens its page in the same center view as the hub (`openDiagnosticsView(path, btnId)`, limited to `/he/diagnostics/…`) and highlights its own button.
  - The hub no longer has the "תרגול לקראת…" section.
  - On those two pages, "סיימתי להיום" closes the view (`C.leave`), and the back link to the hub is gone.
- **"הכנה למבחן" opened a "coming soon" page, and then בדיקות ומעקב stopped working** (user report):
  - *Cause 1*: an old script (`IAKIDS_EXAM_PREP_COMING_SOON_0751`) catches, in the capture phase, every click on anything whose text contains "הכנה למבחן" and opens a "coming soon" screen. It swallowed the new button's click.
  - *Cause 2*: that screen sits above the checks view (z-index 248 against 246) and nothing closed it, so after seeing it once, בדיקות ומעקב opened behind it and the menu seemed dead.
  - *Fix*: the old catcher now opens the real exam prep (the "coming soon" screen stays only as a fallback), and opening the checks view hides the old screen.
  - *Gate*: both are pinned and negative-tested.
  - *Verified* on the real workspace with all old scripts loaded: each of the three buttons opens its page, and with the old screen forced open, clicking בדיקות ומעקב puts the checks on top.
- **Hub layout** (user: all 4 in one row, or 2 rows of 2): the four check cards sit in one row when the frame is wider than 1000px, 2×2 in the workspace center, and one column on a phone. Measured by card positions at 1200, 860 and 400px.
- **Menu text too small** (user): on hover or keyboard focus, a menu item's title grows ×1.18 and its icon ×1.12, anchored on the right (`IAKIDS_MENU_HOVER_ZOOM`, declared after every other `.side-item` rule; respects reduced motion).
- **Badges** (user: a "new" or "premium" tag):
  - `<span class="side-badge new">חדש</span>`, a cyan-to-green pill with a soft pulse, now on בדיקות ומעקב, הכנה למבחן and מבחן המחוננים.
  - `<span class="side-badge premium">פרימיום</span>`, a gold pill with ★, is ready but not placed on any item yet.
  - Both are labels only; nothing is locked.
- **Gate**:
  - The hub must not link to exam prep or gifted, and the menu must keep both buttons with their paths.
  - The hover block must exist and come after the last `.side-item{` rule.
  - The earlier rule that required exam prep to be inside the hub now only forbids the old coming-soon placeholder.
  - Each rule was negative-tested.
- **Verified**:
  - The real menu markup and view script were tested in headless Chromium: each button opens its page, highlights itself, and any other menu item closes the view.
  - On the real workspace the computed hover transform is `matrix(1.18…)`.
  - The badges were rendered and checked on screen.
  - `prompt_gate --all` passes.

### 2026-09-24 — English Test Prep entry popup
- **Symptom**: Start prep, its arrow, and navigation/mobile Test Prep links led to a missing page.
- **Cause**: the English Test Prep entry flow had not been implemented.
- **Fix**: shared native dialog with a dedicated optimized photographic banner, three accessible action cards, responsive full-screen mobile layout, Escape/backdrop/Cancel dismissal, focus return and background scroll lock. Connected dashboard and Homework header; added a direct-route fallback. File selection supports local image preview and 20 MB/type validation; topic text is retained only for the current page. AI analysis, suggested topics and plan generation remain explicitly unavailable; no uploads or invented results.
- **Verification**: JavaScript syntax check; checked scoped styles, imports, safe text rendering and object-URL cleanup. Live browser smoke check follows deployment.
- **Build**: English prep-modal-20260924; no Hebrew/Spanish changes.

### 2026-09-24 — Complete Hebrew gifted-tests content cluster
- **Need**: one sample post lacked a complete linked topic cluster.
- **Change**: add 11 pages (hub plus 10 supporting articles), integrate the existing grade-2 article, add the cluster to the Hebrew blog, add two optimised hero assets, and GA4 interaction events on all 12 cluster pages.
- **Verification**: original questions/solutions reviewed; all page titles, H1s, IDs, JSON-LD, local images, cluster links, anchors, single GA config and JS syntax checked; analytics event handlers exercised locally. Live verification follows publication.
- **Build**: SEO gifted-cluster-20260924; Hebrew workspace build unchanged (content addition only).

### 2026-09-24 — Tablet lower panels left an empty column
- **Symptom**: at 1180px, Continue Learning and My Subjects used only two-thirds of the row, with cramped text and a blank third column.
- **Cause**: desktop three-column override combined with the <=1280 full-row Recent Progress placement.
- **Fix**: explicitly use two flexible columns at 1101–1280px; keep Recent Progress across the full next row with a two-column activity list and natural height.
- **Verification**: checked the conflicting media rules and final override; cache key updated on both English pages.
- **Build**: English tablet-panels-20260924; Hebrew workspace unchanged.

### 2026-09-24 — checks: a real teacher and real photos instead of icons; a "working" sign while questions load (build 0.7.146)
- **User request**: a realistic teacher, not an icon ("המורה מכינה שאלות על שברים…" showed 👩‍🏫), and free photos wherever the checks used icons. Before that: "nothing happens, no sign anything is running".
- **Teacher**: every check screen shows our own lesson teacher (`assets/diagnostics/teacher.webp`, a round crop of `assets/lesson/lesson-teacher.webp`, 11 KB) through `C.teacher()`. The child meets the same teacher as in the lessons.
- **Waiting**: `C.busy()` shows the teacher, what she is doing ("זה לוקח כחצי דקה" for exam prep) and moving dots. It is used in comprehension, dictation, exam prep and gifted while the server prepares questions, and respects reduced motion.
- **Photos**: the six hub cards and the end screen use Pexels photos (Pexels License: free for commercial use, no attribution needed): 640×400 WebP, 12–26 KB each. The source, photographer and license for each are in `assets/diagnostics/CREDITS.md`.
- **Kept as symbols**: 🔊 on the play buttons, ✓ on the keypad and ⚙️ inside the "machine" figure are controls or part of the question.
- **Gate**: the teacher image must exist and be the one the shell uses; no page may put an emoji in `.ck-teacher`; every `/assets/diagnostics/…` image a page shows must exist. Negative-tested: an emoji teacher fails, and the missing photos failed before they were copied in.
- **Verified**: headless Chromium, with the hub photos and the exam-prep loading screen (teacher plus dots) screenshotted and checked. There were zero console errors, and `prompt_gate --all` passes.

### 2026-09-24 — Small-laptop dashboard card stretching
- **Symptom**: at 1280px, feature artwork became very tall and summary labels wrapped excessively.
- **Cause**: equal fractional page grid rows inherited the height of a multi-row lower dashboard; feature media flex-grow consumed the excess. Summary icons and bars left too little text space.
- **Fix**: content-sized page flow at 1101–1400px, bounded 150–168px feature media, and compact summary icons without decorative bars at that breakpoint.
- **Verification**: inspected responsive cascade and measured live card layout; post-deploy browser check follows.
- **Build**: English laptop-layout-20260924; Hebrew workspace unchanged.

### 2026-09-24 — English leaf favicon
- **Symptom**: English pages did not declare the requested leaf browser-tab icon.
- **Fix**: declare the existing transparent IA KIDS leaf PNG as the favicon on the dashboard and Homework Help, with relative paths compatible with /eng/.
- **Verification**: visually inspected the existing brand asset and checked both relative paths; no artwork regeneration.
- **Build**: English favicon leaf-20260924; Hebrew workspace unchanged.

### 2026-09-24 — Publish IA KIDS ENG at /eng/
- **Symptom**: the English dashboard was available only on iakids-eng.onrender.com; iakids.app/eng/ returned 404.
- **Cause**: main held only a few English images, without the English pages and styles.
- **Fix**: publish only eng/ from english-app commit 378e6b0083017f671926026bd57a8e8a86abf842. Preserve all other application directories and deployment configuration. Relative asset and Homework Help links support /eng/.
- **Verification**: checked source paths and exact English subtree; production HTTP checks follow deployment. Remaining menu destinations are existing unfinished screens, not part of this migration.
- **Build**: English release 378e6b0; Hebrew workspace build unchanged (English-only publication).

### 2026-09-24 — every check said "צריך להיכנס מתוך סביבת הלמידה" inside the workspace (build 0.7.145)
- **Symptom** (user report): opening any check from "בדיקות ומעקב" in the workspace showed "צריך להיכנס מתוך סביבת הלמידה" instead of starting. The hub's tracking strip also stayed empty.
- **Cause**: the check pages run in a frame and looked for `parent.CURRENT_KID` and `parent.sb`. In the workspace, both are declared as top-level `let` and `const`, which never become `window` properties, so the frame saw no child and no session.
  - A second bug sat behind the first: the profile stores the grade as a number (1–6), while the checks expect a letter, so every child would have started at grade ב.
- **Fix**:
  - The workspace exposes `window.IAKIDS_CHECK_BRIDGE` with `kid()` and `session()`, next to the diagnostics view.
  - `check-shell.js` reads the child and the token through the bridge first, and maps grade 1–6 to א–ו with `gradeLetter()`.
- **Same build, second report** (user: "picked grade ב, the comprehension check doesn't advance"; "exam prep, fractions: nothing happens, no sign anything is running"): nginx caches JS for 4 hours, and the check pages loaded `check-shell.js` without a version. Browsers kept the 0.7.143 shell, which has no `api()` or `signedOut()`, so the start button threw an error and nothing happened. Every check page now loads `check-shell.js?v=07N` and `.css?v=07N` with the build number.
- **Gate**: the workspace must keep the bridge, and a node test checks that the shell finds the child through the bridge and turns grade 3 into ג. Every page that loads the shell must carry `?v=` of the current build. All three were negative-tested.
- **Verified**: headless Chromium with a parent page that declares `let CURRENT_KID` and `const sb`, the way the workspace does:
  - without the bridge, the old "sign in" screen and grade ב;
  - with the bridge, the child is found, grade ה is selected and the question set is requested.

### 2026-09-24 — "בדיקות ומעקב" complete: math, comprehension, dictation, exam practice, gifted familiarisation (build 0.7.144)
- **Why**: the user asked for every check and practice in the hub to be ready, including the gifted familiarisation. All six hub cards are now active.
- **Mental math** (`he/diagnostics/math/`), grades א–ו, adaptive, no bank needed (generators). Built from Israeli sources:
  - the strands use the Ministry's terms, with a percent level for ה–ו (50%, 25%, 10%);
  - missing-number formats appear from grade א, as in the Yesodot check;
  - numbers are read aloud only in א–ב, per the ראמ"ה rule;
  - the report adds "what the school expects now", "when the school checks" and a speed state on basic facts ("נכון, עדיין מחשב"). The speed thresholds (4 s in ב–ג, 3 s from ד; none in א) are labelled research-based, not an official norm.
- **Comprehension** (`comprehension/`): listening in א–ב, reading in ג–ו, 12 original texts (2 forms per grade), 6 questions each across the Ministry's four dimensions. The report is organised by dimension, with a tip for each.
- **Dictation** (`dictation/`): letter tiles in א–ב, typing in ג–ו, 12 forms and 136 words, each word said inside a sentence. The server scores and accepts listed alternative spellings. The report is by spelling feature.
- **Exam practice** (`exam/`, `POST /api/tutor/exam-practice/start|answer`): 8 multiple-choice questions for the child's grade from the subject module; answers stay on the server for 3 hours; the child gets feedback after each answer; nothing reaches a report. New prompt: `prompts/homework/iakids_exam_practice_prompt.txt`.
- **Gifted familiarisation** (`gifted/`): 60 original items in 5 types: word pairs, missing words, word problems, numbers in shapes (pyramid, circles, machine, arrows, tree) and next shape (series and 3×3). The figures are drawn as SVG. Each section opens with a worked example; the child sees the explanation after each answer; there is no score; the next session picks unseen items.
- **Fluency**: forms A, B and C per grade, rotating, so a re-check does not repeat the same text.
- **Server banks** (`backend-ai-tutor-he/data/checks/`): `GET /api/tutor/checks/{bank}/set` sends items without answers or explanations; `POST /api/tutor/checks/score` scores without writing to the DB. Ownership of the kid is checked, and request sizes are limited, now including dict fields.
- **Leaks found and closed while testing**:
  - Grade א comprehension asked "which title fits?" while the story's title was on screen. The server now drops the title when a question asks for it.
  - The gifted figures carried their rule and formula, which is the answer, in the payload. The server strips them.
- **Content checks**:
  - A separate agent solved every gifted and comprehension item without the key. The results were 36/36 and 72/72 matching, and no item was ambiguous.
  - Three "moral" questions had wrong options that were too easy to rule out; they were rewritten.
  - A story where a child uses the oven alone and tastes from every jar was changed: an adult turns on the oven, and "if unsure, ask".
  - Sneaking into a neighbour's home without the parents' knowledge was removed.
- **Gate**, each rule negative-tested:
  - `check_bank_checks`: every bank is valid; 4 different options; `why_wrong` covers exactly the wrong options; tiles can spell the word; comprehension dimensions are the Ministry's four; א–ב comprehension is listening.
  - Code rules for the title strip, the figure strip and the answer-free payloads.
  - The math node test parses the new missing-number and percent formats.
- **Verified**:
  - Headless Chromium walked through math (א, ה), comprehension (ב, ה), dictation (ב, ה), exam practice, the gifted page (all 60 items and 5 intros) and the hub. There were zero console errors, and the screenshots were reviewed.
  - A live exam-practice run for grade ב times tables gave 8 correct questions and no answers in the payload.
  - `prompt_gate --all` passes.
- **Still to do before families use it**: a Hebrew teacher proofreads the nikud (fluency, dictation, comprehension, gifted); 5–10 parents read a report; the privacy review before results move to the server.

### 2026-09-24 — "בדיקות ומעקב": check shell and reading fluency v2 (build 0.7.143)
- **Why**: research on assessing young children, the Ministry's own checks (the literacy profile, the grade-ב fluency check, the grade-ג fluency tool, the תשפ"ז evaluation calendar) and children's assessment products. It came back with 41 sources and recommendations.
- **Renamed** "מבחנים ואבחונים" to "בדיקות ומעקב": to Israeli parents "אבחון" means a formal learning-disability evaluation, and "מבחן" means an exam. The hub order is now a parent strip (only after a first check), then short checks, then "תרגול לקראת…" (exam prep and gifted familiarisation, never in a report), then "איך זה עובד". Every card shows grades, minutes, "עם הורה" and the microphone.
- **Shared check shell** (`he/diagnostics/check-shell.js` and `.css`):
  - a parent screen (what is checked, how long, what it is not);
  - a spoken child intro;
  - a progress path that counts items;
  - a stopping rule (3 misses in a row, or 4 of the last 5);
  - an effort-only end screen with one "בואו נתרגל";
  - a parent report: strengths first, what to strengthen, practice, a re-check date, numbers folded away, a trend only after 3 runs and a change within the day-to-day spread shown as "יציב", the not-a-diagnosis line, and delete.
  - Results stay on the device until the privacy review of storing children's results on the server.
- **Reading fluency v2** (`he/diagnostics/fluency/`), grades ב–ג, in the Ministry's format:
  - a vowelled 80-word graded list read for 45 seconds, then a one-minute passage, with the easier passage when the list is low (ג: below 26, the Ministry's risk band; ב: our own threshold of 20);
  - the parent marks misread words with a small dot, taps the last word read at the chime, and rates prosody;
  - the child sees no clock, score or right/wrong.
  - The report uses דיוק, קצב, הנגנה. The Ministry's grade-ג bands appear only as a labelled rough reference, with the Ministry's own caveat that the norms were not checked. It suggests talking to the class teacher only after two low checks at least 4 weeks apart.
- **Gate**, for these pages and any check added later: no clinical words (דיסלקציה, לקות למידה, ADHD, הפרעת קשב, אבחנה, "חשד ל"), no network calls, every check on the shell, the report keeps the not-a-diagnosis line, the hub keeps checks before practice, and the shell's stop, trend and delete logic runs under node. Each was negative-tested. The negative tests also exposed a gate crash on files outside the repo, now fixed.
- **To do before families use it**: proofread the nikud of the two 80-word lists and the passages; write alternate forms for re-checks; show the parent report to 5–10 parents so nobody reads it as a diagnosis; and a lawyer's review of Amendment 13 before results move to the server.

### 2026-09-24 — the user menu opened behind panels; uploaded files missing from הקבצים שלי (build 0.7.142)
- **User menu behind panels** (user report, homework tab, then also the learning world and other screens): the name menu in the top bar opened behind the homework panel and the center views.
  - *Cause*: the top bar was at z-index 20 inside `.app`, while the center views sit at 240–247 (dashboard, my lessons, my files, achievements, diagnostics) and the worlds at 40–100.
  - *Fix*: an `IAKIDS_TOPBAR_STACKING` block on both workspaces. The top bar is at 400 (still below the modals at 9999+), the menu at 1000, and on mobile the hamburger is at 410 so the bar does not cover it.
  - *Gate*: `topbar_stacking_checks` scans every page with the user menu and fails if any view, world, panel or sidebar declares a z-index at or above the top bar's, including views added later. It was negative-tested.
- **Uploaded files missing from הקבצים שלי** (user report).
  - *Cause*: the files were in storage (checked read-only: 3 of 3). But the page listed `homework_sessions`, whose file name and link are never filled, so it showed "none". Its fallback then listed the storage folder from the browser, which storage rules do not allow, and got nothing. The separate page `he/files/` had the same bug through `/api/kid/files`.
  - *Fix*: `/api/kid/files` now reads `homework_uploads` for this parent and child, signs each file for an hour, and takes status and question counts from the session that started right after the upload. It keeps the fields `he/files/` uses. The workspace view calls this route instead of the database, and the browser storage fallback is off. That removes two browser database and storage calls, per the architecture rule.
  - *Verified*: read-only against production, 3 files returned with working links, subject and topic; another parent's id gets 404.
  - *Gate*: code rules on the route's table and signing, and screen rules that the view uses the API and the fallback stays off. Both negative-tested.

### 2026-09-24 — chat security review, server and browser (build 0.7.142)
- **Asked**: check whether text typed into the chat can make a model leak data from the database or anything else, whether any model is connected to the database or can act, and limit the size of chat text. Server and browser.
- **Found, and good already**:
  - None of the 27 model calls has tools or function calling, so no model can reach the database or act.
  - The child is loaded with a `user_id` filter, and memory and history only for that child, so the most an injection could leak is the attacker's own child's data, the prompt, and the homework plan's correct answer.
  - The browser shows replies as text (`textContent`, or markdown that escapes HTML first), so injected HTML cannot run.
- **Found, and fixed**:
  - No request had a length limit.
  - The chat history came from the browser unchecked: any size, and "system" turns accepted.
  - No prompt had explicit security rules.
  - Only the homework reply was checked for leaks.
- **Fix**:
  - `LimitedRequest` is now the base of all 19 request bodies. It rejects oversize strings and lists before the route runs: 1,500 characters for a message or answer, 20,000 for source text, 6,000 for TTS text, 300 for ids and short fields, and 50 items per list.
  - `clip_chat_history()` keeps 12 user/assistant turns of at most 2,000 characters each and drops other roles.
  - `PROMPT_SECURITY_RULES` is added to every prompt that takes a child's or parent's text: the chat, the lesson dialogue, the lesson closing, the homework coach, turn and v2, the clean chat and the curriculum builder. It says the conversation is content, never instructions; never reveal the instructions, plan or answer; there is no database or tools and no pretend queries; and redirect kindly.
  - `reply_leaks_internal()` and `guard_reply_payload()` replace any reply, or any string of a structured reply, that holds internal markers, table names or key-like tokens. This is on all 7 reply routes.
  - `maxlength="1500"` is set on the chat inputs of the workspace, the games workspace, the homework page and add-subject.
- **Red team** (extraction only, dev, dummy DB key): 12 attacks on the homework coach with a plan whose answer is 80 — ignore rules, reveal the prompt in Hebrew and English, the CORRECT ANSWER field, the whole plan, "debug mode" tables and keys, a read-only SQL query, other children, a role change, forged history including a "system" turn, HTML injection, and the answer as words or gematria. None got the answer, the prompt, internal text or system details. A 5,000-character message was rejected.
- **Gate, including future code**:
  - it fails on any model call with tools;
  - on any route body that is a plain `BaseModel`;
  - on any function that sends a user's text to a model without `PROMPT_SECURITY_RULES` or without a reply leak check (found by scanning, not by list);
  - on a missing chat-input `maxlength`;
  - on a `REQUIRED` prompt entry that pins nothing. This caught `iakids_lesson_transition_prompt.txt`, now pinned with 5 sections.
  - unit tests for history trimming, leak detection and the 1,501-character rejection.
  - Each was negative-tested, including against a new, not-yet-written route.
- **CLAUDE.md**: the security rule and a checklist for every new prompt or model route.

### 2026-09-24 — homework help: the typed text stayed in the box after Enter or Send (build 0.7.141)
- **Symptom** (user report): while writing in homework help, pressing Enter or Send did not clear the text.
- **Cause**: a regression from 0.7.137. `runStructuredHomeworkTurn()` sends the coach path straight to `runHomeworkProductionCoach()`, which returns before the lines that show the child's message and clear the box; only the old path had those lines. 0.7.137 routed every homework message to the coach, so the bug reached everyone. The child's own message was also missing from the chat, and a second Enter could send twice.
- **Fix**: before asking the teacher, the coach path shows the child's message, clears the box and disables Send. Send is re-enabled with focus returned, and on a failure the child sees "לא הצלחתי לענות כרגע…" instead of silence.
- **Gate**: `homework_checks` fails if the coach path in `runStructuredHomeworkTurn` asks the teacher before showing the message, clearing the box and disabling Send. It was negative-tested.
- **Verified**: `node --check` passes, and the function itself ran under node with a stub box and button: the box clears, the message shows, Send is disabled while waiting and re-enabled after, an empty message is not sent, and a failure shows the message without leaving Send disabled.

### 2026-09-24 — "מבחנים ואבחונים" hub and the reading-fluency check (build 0.7.141)
- **Why**: stage 0 of the reading-fluency plan. Before building a practice tool, we need to measure whether the browser's speech recognition hears children reading Hebrew well enough. A tool that tells a child who read correctly that he made a mistake does more harm than good.
- **New**: `he/diagnostics/` is a hub of checks with a card per check. Reading fluency is live; comprehension, dictation, mental math and gifted-test prep are marked "בקרוב". `he/diagnostics/reading-fluency/` is the check itself, for a parent to run with a child: grade א–ג passages (grade ג has one vocalised, one with partial nikud and one without), the browser's recognition (`he-IL`, continuous), the parent marking the words the child really misread, and a comparison. It reports false alarms (the machine said wrong, the parent heard right), misses, and words correct per minute by parent and by machine. Results can be copied as text and stay on the device.
- **No server, no database, no model, no recording.** In Chrome the recognition itself runs at Google; the page says so.
- **The comparison**: word-level alignment that ignores nikud, punctuation, and ו/י after the first letter. The passages are כתיב חסר (שֻׁלְחָן) and recognition returns כתיב מלא (שולחן), so a naive comparison would mark correct reading as wrong. Words after the point where the child stopped are not errors.
- **Menu**: a "מבחנים ואבחונים" item in the workspace sidebar. It opens in the center of the workspace like the dashboard and "הקבצים שלי": a view with a "חזרה" button that loads `/he/diagnostics/` in a frame allowed to use the microphone, so there is no second copy of the page. The first version navigated away, and the user said it opened "as if it does not belong to the system". Inside the frame the pages drop their own background and back link, any other menu button closes the view, and closing it stops the microphone. "הכנה למבחן" moved from the sidebar into the hub as a card, still "בקרוב".
- **Gate**: both pages load the log switch first; the check page may not contain fetch, XMLHttpRequest, supabase, .from(, sendBeacon or WebSocket; the menu item must exist; and the comparison runs under node on known cases (כתיב מלא against חסר, substitution, omission, stopping midway, an extra word). Each was negative-tested.
- **Verified**: the comparison tests pass under node, the page script passes `node --check`, and `prompt_gate.py --all` passes. Not yet run with a real child: that is the check itself.
- **To proofread**: the passages and their nikud were written for this check and need one human read before children use them.

## 2026-09-23

### 2026-09-23 — grades 1–2: a correct short answer is enough (build 0.7.140)
- **Symptom** (live test with the subject modules): a grade-1 child answered "ג'וני" to "איך קוראים לתלמיד החדש?". The teacher said it was correct, then asked for the answer again as a full sentence. The question stayed open.
- **Cause**: the Hebrew module's answer rule (standalone and not 3–4 words) comes from the grade-4 national test scoring guide, and it applied to every grade.
- **Fix**: the rule now applies from grade ג. The grade א and ב sections say that a correct answer of one word or a few words is enough unless the page asks for a full sentence, and that a correct answer is not sent back to be rewritten.
- **Gate**: two REQUIRED sections in the Hebrew module, plus unit tests that a grade-1 child gets the rule and a grade-4 child does not. Both were negative-tested.
- **Verified live** on the same grade-1 page: the plan's criteria say "מילה אחת מספיקה", and "ג'וני" gets "נָכוֹן, לַתַּלְמִיד הֶחָדָשׁ קוֹרְאִים ג'וֹנִי." with the question complete.

### 2026-09-23 — homework help knows the school curriculum per subject and grade (build 0.7.139)
- **Why**: the teacher prompt was general. It had no way to know that a grade-2 child has learned only the ×2/4/5/10 tables, that fractions start in ד, that grade ג reads with vowel marks until about mid-year, or that רש"י is not taught in the ממלכתי stream.
- **Research**: the official Ministry of Education documents: ארגון הלמידה ביסודי תשפ"ז (weekly hours; which subject exists in which grade), the math programs (the new program for א–ג, the 2006 program for ד–ו, both in force this year), חינוך לשוני עברית (2003 and 2026), English Curriculum 2020 and its grammar and lexis bands, תנ"ך ממלכתי, מדע וטכנולוגיה (the תשפ"ז content specs), היסטוריה (new from תשפ"ז) and מולדת/גאוגרפיה. Cells no official source confirmed are phrased as "ask the child whether this was taught".
- **Modules**: `prompts/homework/subjects/{math,hebrew,english,tanakh,science,history,geography}.txt`. Each has a general part (terms, methods, what is never taught in elementary school) and one section per grade (what was learned, what is taught this year, what is not taught yet). לשון, קריאה, הבנת הנקרא, ספרות and הבעה are one subject in the curriculum, so they share the Hebrew module.
- **How it is used**: the subject comes from the stored page reading (`homework_subject_key`). The teacher (`homework-coach`, `homework-turn`) and the planner get the general part plus the child's grade section only, about 1,650 characters (a whole module is about 4,800). With an unknown grade, they get every grade. Every module opens with "כללי הליבה גוברים תמיד".
- **Gate**: REQUIRED sections for every module (core line, source, every grade, "לא נלמד"); a scan that fails if a module loosens the core ("מותר לתת את התשובה"); the slash-form scan now covers the subfolder; code rules for the wiring to teacher, turn and planner; unit tests for subject detection (13 cases), grade normalisation (11 cases) and grade slicing. Each was negative-tested.
- **Menu**: the test buttons "OpenAI נקי" and "עזרה בשיעורי בית V2" are now deleted from the sidebar of `he/workspace/index.html`; in 0.7.137 they were only hidden. "עזרה בשיעורי בית" is the only homework link. The server routes are unchanged. The gate fails if either button id comes back, even hidden.
- **Verified offline** (no model calls; credit is low): on the 41 saved worksheet pages, subject detection matched 38. The three misses: "טבע ומולדת" (fixed by adding טבע), a page the reader labelled "מולדת" (geography, acceptable), and "מורשת" (no module yet, an open question).

### 2026-09-23 — every model is an env var with a default (build 0.7.138)
- **Symptom**: changing a model meant editing `main.py` and deploying. The homework coach, the clean chat, the planner, direct Gemini TTS, lesson images and the transition video all had the model name written into the call (`model="gpt-5.6-sol"` appeared 7 times).
- **Fix**: each one reads an env var, with the current model as its default. Nothing changes when the variable is missing from `.env` or the service unit. New variables: `CHAT_MODEL`, `LESSON_MODEL`, `HOMEWORK_COACH_MODEL`, `HOMEWORK_PLANNER_MODEL`, `CLEAN_CHAT_MODEL`, `GEMINI_TTS_MODEL`, `LESSON_IMAGE_MODEL`, `LESSON_TRANSITION_VIDEO_MODEL`. `HOMEWORK_VISION_MODEL`, `OPENROUTER_TTS_MODEL`, `NIKUD_MODEL`, `STT_MODEL` and `IMAGE_TEXT_CHECK_MODEL` already worked this way. The `[config]` startup line prints the resolved models. The session row records the real chat and TTS models instead of fixed strings.
- **Gate**: `model_config_checks` fails on a versioned model name written into a call and on a missing env read. A unit test checks the defaults when nothing is set. Both were negative-tested.
- **Verified**: `prompt_gate.py --all` passes. With `HOMEWORK_COACH_MODEL=test-model` set, the coach model resolves to `openai/test-model` and the others keep their defaults.
- **Also in this build: the grade-1 picture page was unclear.** Live report: the topic showed as "Addition and Subtraction with Visual Aids" and the teacher said only a blank and an equals sign were visible. *Cause 1*: the server was not yet deployed, so the old reader (gpt-4o-mini, no Hebrew or picture rules) was still running. *Cause 2*, which remains in the new reader: it put the picture description in `refers_to` and left the text as `____ - ____ = ____`, and it paraphrased the printed instruction. *Fix*: `normalize_homework_exercises()` puts the description into a text that has only blanks and signs ("קבוצה גדולה של המבורגרים - קבוצה קטנה של המבורגרים: ____ - ____ = ____"), and the prompt says instructions are copied word for word, with nikud. *Gate*: a code rule, three unit tests and two REQUIRED sections, each negative-tested.

### 2026-09-23 — homework help: one route, a page read like a teacher reads it, a private plan per question (build 0.7.137)
- **An addition page was taught with multiplication.** Live test: after the page was read, the child's messages went to `/api/tutor/chat`, the general chat, which knows nothing about the page. The teacher drifted to "הכפלות של 80" and "8 פעמים 10". *Cause*: only a help button turned on homework routing, and four of the five buttons (understand, explain, hint, check) built their prompt **in the browser** and sent it to the general chat. *Fix*: every button, and anything typed after the page is read, now goes to `/api/tutor/homework-coach` with `help_mode`, using the server-side mode prompts that already existed (`HOMEWORK_HELP_MODE_PROMPTS`).
- **A page with no numbering became one question: the instruction line.** "35+40 = ___" has no "1." and no "?", so the screen's regex took "פתרו את התרגילים הבאים:" as the only question. *Fix*: both screens (`lesson-completion-core.js`, `frontend-v2/homework.js`) use the reader's `exercises[]`; the regex is only the fallback.
- **The topic showed as "addition" on a Hebrew page.** *Fix*: the reader writes subject and topic in the page's language (English pages: "זמן עתיד (future tense)"), with a code fallback to the page title and a subject map (Math → חשבון).
- **Reading the page (stage 1).** The prompt now reads the title and headings, gives each exercise its heading and punctuation word for word, copies tables in full, and marks picture-counting exercises. Model: `HOMEWORK_VISION_MODEL`, default `google/gemini-3.1-flash-lite` on OpenRouter. Measured on two real pages, 2 interleaved runs each: gpt-4o-mini read **10 of 20** exercises both times and none of the pictures; flash-lite read 20/20 and every sign in 3–5 s; gpt-5.6-sol read them too but took 25–92 s. A reply that is not valid JSON is read once more instead of showing the child an empty page.
- **Nobody counts drawn objects reliably.** Checked against the answer key of the grade-1 page (20−4, 12+5, …): 0–1 of 10 exact for every model. Picture exercises now carry no numbers, and the teacher never says a count: the child counts, and the teacher checks the arithmetic on the child's own counts.
- **The teaching plan (stage 2).** After the page is read, `gpt-5.6-sol` plans every question in the background (what is asked, where the information is, 2–5 steps, typical mistakes, answer criteria, correct answer). The plan lives in `homework_uploads.analysis_json`, and only the server adds it to the teacher's prompt, so the browser never sees it. Question 1 is planned alone, then the rest in parallel batches of 4, and each batch is stored as it lands. Result: 148 s for a 20-exercise page became 37 s, with question 1 ready in about 12 s. The teacher waits up to 15 s for it.
- **Teacher rules added**: teach in curriculum order (never the simple with the advanced); a correct answer is never rejected mid-steps (the child said "80" and was told it "does not fit the step"); an example never reuses an item of the answer, and for a message or lesson question it teaches a different message (the teacher's "different" example for כבשת הרש had the same moral); no slash forms. In code, a reply that contains an answer item is rewritten once.
- **Prompts**: the homework coach prompt moved to `prompts/homework/`, and the pedagogy prompt used by `homework-turn` moved too and was rewritten without הילד/ה and אומר/ת. The `חפש/י בטקסט` line appended in code became neutral. The voice now gets `kid_id` from the homework page.
- **Hidden from children**: the test buttons "OpenAI נקי" and "עזרה בשיעורי בית V2" (hidden, not removed).
- **Cache**: `lesson-completion.js` and `lesson-completion-core.js` were still `?v=07131`, so browsers would have kept the old homework code. Both now follow the build.
- **Gate**: new REQUIRED sections for all four homework prompts, a slash-form scan of `prompts/homework/`, code rules (planner started, plan reaches coach and turn, help mode used, batching, reply check, vision retry, vision model knob), screen rules (routing, `upload_id`, exercises first, test buttons hidden, cache-busters), and unit tests (question matching, answer-leak check, Hebrew topic, JSON parsing, reply check). Each one was broken in a scratch copy and the gate failed.
- **Verified**: `prompt_gate.py --all` passes. End to end on 41 real worksheet pages (5 per subject: math, reading, English, Tanakh, science, history, game topics) in dev, running the real `homework_coach` route with a stubbed login. Addressing matched the child's gender on every page; no answer leaked into a reply; no multiplication on an addition page. The pages that failed were fixed and re-run.
- **Not changed, noted**: homework that spans two pages (a text on page 1, questions on page 2). One image is uploaded, and the teacher asks for the missing page. `homework-coach-v2` and `openai-clean-chat` remain in `main.py` behind the hidden buttons.
- **Cost note**: `.env.dev` and `.env.prod` share one OpenRouter key; the test run spent production credit. Balance after testing: $2.90 of $10. One test call got 402 (in-flight credit reservation).

## 2026-09-17

### 2026-09-17 — evening sweep: payments, Render, the closing summary
- **The lesson closing has never run in production yet** — no lesson has been completed since it was deployed — so the store path was exercised directly: an insert with `session_id = null` succeeds and the cache lookup finds it. Not a bug; simply untested by a real child so far.
- **Render is on today's code.** Every route added today answers there, admin and kid routes included.
- **The payment webhook is healthy in production.** A request with a bogus signature gets 403, which proves the secret is set on Render. The empty `LEMON_*` keys in the local `backend/.env` are a local artefact, and the note about them in `docs/SECURITY.md` is stale on that point.
- **The plan label is chosen by the browser.** `index.html` builds the checkout URL with `checkout[custom][plan]=…`, and the webhook records whatever arrives in `custom_data.plan`. A user can open the monthly variant with `plan=annual`. **Not exploitable today**: nothing treats annual differently from monthly — both are just "paid" — and `expires_at` comes from LemonSqueezy's real `renews_at`. It becomes exploitable the day annual grants anything extra. The plan should derive from `variant_id` on the server. *Recommended, not changed*: the core backend deploys through Render and cannot be verified from here.
- **A replayed webhook refills the month.** `subscription_created` upserts `messages_used: 0` with no check that the `lemon_subscription_id` was already seen, so a re-delivered event resets the quota. Small, code-only, in the core backend. *Recommended, not changed*, same reason.
- **Two read-then-act checks added today** — the child limit and the monthly lesson quota — could be beaten by two simultaneous requests. At two accounts generating lessons this is theoretical; the chat quota was moved into a locked SQL function for exactly this, and these can follow it if volume ever warrants.

### 2026-09-17 — the coach session hole is closed, and the rest of the schema was audited
- **Closed and verified from the server, both directions**: a stranger's account now reads **0** coach sessions where it read 10, and an account with a child reads **exactly 1** — its own. A policy that also locks out the owner is not a fix, so both halves were tested.
- **My sweep query was wrong and I corrected it.** For an INSERT policy the condition lives in `with_check`, not `qual`, so the first version flagged every INSERT policy in the schema for nothing and sent a long list of false positives to be read. Sorry for the noise.
- **Six tables are readable by any signed-in account, and all six are meant to be**: exam pages, exam questions, the games catalogue, the nikud dictionary, the lesson catalogue and lesson content. Shared content, decided in the 2026-09-10 audit. The dangerous columns of `lesson_units_content` were closed separately this morning with column grants. So the `debug_` policy was the only unintended open read.
- **Every write policy checks ownership — tested live, not read.** An anonymous client and a signed-in account writing under another account's id were both refused on `kids_profiles`, `homework_sessions`, `homework_uploads`, `support_tickets`, `kids_memory` and `subscriptions`. That last one includes an account trying to **give itself a paid plan**, which was the 2026-09-10 finding: it is genuinely closed.
- **The `public` role on several policies looks alarming and is not**: the check is `auth.uid() = user_id`, and for an anonymous caller `auth.uid()` is null, so the comparison is never true.
- **Found a way to close `app_admins` after all.** It had to stay open this morning because a policy on `support_tickets` reads it. The sweep shows that policy calls `is_admin(auth.uid())`, so the function exists and runs as the caller. Making it `SECURITY DEFINER` lets the table close while the support pages keep working. Written into `RUN_NOW.sql` as optional, commented out, with the order to run it in.
- **Housekeeping, no rush**: `learning_lessons` carries two identical read policies and `kids_profiles` four overlapping INSERT policies. Harmless in themselves, but four policies on one action is exactly how the `debug_` one stayed invisible.

### 2026-09-17 — a policy left over from debugging was keeping the table open
- **The correct policy was added and changed nothing.** A fresh account still read every coach session. `pg_policies` showed why:

| policy | permissive | roles | cmd | condition |
|---|---|---|---|---|
| `debug_select_learning_coach_sessions` | PERMISSIVE | authenticated | SELECT | `true` |
| `lcs_select_own` | PERMISSIVE | authenticated | SELECT | `kid_id in (...)` |

- **Postgres combines permissive policies with OR.** One policy saying "any signed-in account, all rows" makes every restrictive policy beside it pointless. The new one was never going to help while that one existed — it has to be dropped.
- **My mistake in the first attempt**: I wrote a policy without listing what was already on the table. Adding a rule to a table is not the same as knowing what the table allows.
- **Worth more than this one table**: a `debug_` policy sat in production, invisible until someone looked. `RUN_NOW.sql` now ends with a sweep that lists every permissive SELECT policy in the schema whose condition is just `true` — every table any signed-in account can read in full. There is no reason to assume this was the only one.

### 2026-09-17 — `supabase/migrations/RUN_NOW.sql`: what is actually left to run
- Every migration in the folder was checked against the live project by looking for the object it creates. **Sixteen are applied. One is not**: the policy that stops every signed-in account reading other children's coach sessions.
- The file holds that one block between paste markers, the reason it matters, what keeps working after it, and how to verify — plus the two things still open that are not database changes: `APP_ENV=prod` on Render, which is why 37 routes and 21 schemas are public there while the box answers 404, and the six security headers on iakids.app that the mirror already sends.
- Not reachable from the web: the whole `supabase/` folder is blocked, as is every `.sql`.

### 2026-09-17 — three things in the question mechanism that worked against the child
Reviewed end to end and checked against a real transcript. ארבל answered "המורה, ארנב, תלמידה" — the complete correct answer — and was told **"איבדת את המילה שהכי חשובה במשפט"**. She repeated the same answer. She was told she had missed an animal. She repeated it a third time. She was told a word "with a trace of an animal" was missing. The round limit then ended the dialogue at 60 and the lesson moved on **without ever telling her she had been right**. The root cause, a coach with no answer key, was fixed this morning; the transcript exposed three more.

**1. The score the child sees was arithmetically unfair.** `calculate_lesson_coach_mastery` divided by the *total* number of parts and counted a part not yet reached as zero. The gauge is refreshed after every coach turn and is labelled "הבנה כללית", so:

| parts | score on part 1 | what the child saw |
|---|---|---|
| 2 | 90 | 45% |
| 3 | 90 | 30% |
| 4 | 100 | 25% |

A child doing well was shown a number that reads as failure. The average is now over the parts actually attempted. Verified on real data: a child with 40 on part 1 sees 40, and a finished lesson still reports 76 exactly as before, because at the end every part has a score.

**2. Nobody noticed a child repeating themselves.** An identical answer is the clearest signal a child can send that the hint is not working. `repeated_answer` is now computed from the dialogue and forces the closing behaviour: no fourth hint, say the answer, explain it in a sentence, confirm what the child did get right, move on. A fourth hint to a stuck child is not teaching, it is attrition.

**3. The wording opened with what was missing.** The prompt banned judgemental phrasing only in the final round. It now bans it everywhere and requires the first sentence to be what the child *did* say, with the verbs of loss and failure — איבדת, פספסת, טעית, שכחת, לא ענית — forbidden outright. "מצאת שניים. יש עוד אחד שמחכה" instead of "לא ענית על כל שמות העצם".

**Gates**: the mastery divisor, the repeat detection and all three new prompt sections are pinned. Backup taken in `V14_BACKUP` before the prompt changed.

**Deliberately left alone**: the mastery threshold of 90 does not block a child from continuing, the round limit gives a struggling child *more* turns rather than fewer, and the no-response timer is off during the dialogue. Those three are sound.

### build 0.7.136 — a line that threw on every kid load, on both workspaces
- **`document.getElementById("heroAvatar").src = avatarUrl;`** — that element is not in the page. `getElementById` returned null, the assignment threw, and **everything after it in the function stopped**, including `window.ACTIVE_KID_ID = kid.id`, which other code reads. The same block was written out twice, so the second copy never ran either. Both the Hebrew workspace and the games workspace carried it, identically.
- **Why it hid**: the dashboard fields a few lines above are all null-checked, so the page looked fine. Only the tail of the function was missing, silently.
- **Fix**: the four writes go through a helper that checks the element first, so a missing one is skipped instead of stopping the function. **New gate rule**: writing to an element that is not in the page fails the build, verified by restoring the exact line.

### 2026-09-17 — a child's understanding scores were readable by any signed-in account
- **How it was found**: signing in as a brand new account with no data of its own and reading every table the browser still touches. Twenty-two came back empty, correctly isolated. `learning_coach_sessions` came back with other accounts' rows.
- **What was exposed**: `kid_id`, the lesson, the understanding score the teacher gave at the start and the end, how many rounds the dialogue took, and the timestamps — another child's performance, lesson by lesson. Their actual words were not exposed; `kid_lesson_history` is properly isolated.
- **Cause**: the table had row level security enabled with no policy restricting rows, which in practice means every signed-in account.
- **Migration written, not yet applied**: a policy matching `kid_unit_lesson_progress` — a row is visible when the child belongs to the caller. The two screens that read it already filter by `kid_id`, so the policy should be invisible to them.
- **Checked and sound in the same sweep**: the games question bank is not directly readable while the RPC still serves questions, media jobs have no stuck or failed rows, and no table has an orphan row pointing at a deleted child or lesson.

### 2026-09-17 — nothing was capped; now two things are
- **There was no limit on the number of children.** Not in the browser, not in the server, nowhere. One account already holds nine. The endpoint written this morning had no check either.
- **The Hebrew tutor had no quota of any kind.** The only quota in the whole product is the monthly chat message count, and it is enforced in the *core* backend, the Spanish chat. Lesson generation, images and voice — the expensive half, about $0.87 a lesson — were open to any signed-in account. 178 of 180 accounts are on the free plan.
- **Two limits now exist, both server-side.** Children per account, checked when one is created. New lessons per month, checked **before** the first model call of a fresh generation, so a child is told before anything starts rather than half way through a lesson. A lesson served from cache costs nothing and is never counted.
- **The numbers are deliberately far above real use**: three children free and ten paid, thirty new lessons a month free and two hundred paid. Measured the same day: only two accounts have ever generated a lesson, ten and six in a month. These are a ceiling against a runaway loop or an abusive account, not a paywall — that is a product decision, and all four are environment variables (`FREE_MAX_KIDS`, `PAID_MAX_KIDS`, `FREE_MONTHLY_LESSONS`, `PAID_MONTHLY_LESSONS`). `LESSON_QUOTA_ENFORCE=0` measures without blocking.
- **A subscription lookup that fails never blocks a child**: it falls back to treating the account as free rather than refusing.
- **Verified end to end** on a real account: three children created, the fourth refused with 403 and a Hebrew explanation. The paid account resolves as paid, the free one as free, and the lesson counts match what the cost table shows.
- **The parent sees the reason**: the API module was turning a structured error into "[object Object]". It now surfaces the server's own message.

### 2026-09-17 — "הישגים" and "הקבצים שלי" exist now, and the sidebar is whole
- Two more buttons that had pointed at nothing since the workspace was written.
- **`GET /api/kid/achievements`** counts what the child actually did: lessons opened and finished, the best and average understanding score, the subjects, games played and finished, and the number of distinct days they studied. **A number that cannot be computed is left out rather than shown as a zero**, because a zero reads as failure to a child. Six badges, earned or locked, drawn from those same numbers.
- **`GET /api/kid/files`** lists the homework pages the child photographed, with how many questions were answered. An account with nothing uploaded gets a sentence and a button to the workspace, not an empty screen.
- Both pages share the design of `/he/my-lessons/` and neither touches the database.
- **Verified against real data**: nine lessons opened and one finished, best understanding 76%, two subjects, ten games with one finished, three active days.

### 2026-09-17 — the queries asking for columns that do not exist are fixed, and gated
- **`/games/progress/` is repaired.** It asked `kids_profiles` for `avatar_url` and `grade`, which are `avatar_key` and `age`, and embedded `games_catalog` with `icon_path` and `game_url`, which are `icon` and `route_path`. PostgREST answered 42703 to both and the call sites swallowed it, so the page drew an empty report and looked merely unused. The avatar now goes through the same known-avatar helper as the rest of the site.
- **All 65 distinct browser queries now run clean** against the real schema.
- **New gate rule** with the column list recorded in `tools/browser_query_columns.json`: a query asking for a column the table does not have fails the build. It compares shapes and never touches the database, so the gate stays offline. Verified by restoring the exact bug that was live.

- The same class as the `parent_lesson` bug. Every distinct database query in the browser, 65 of them, was run against the real schema. Two fail, both on `/games/progress/`: `kids_profiles` is asked for `avatar_url` and `grade` (the columns are `avatar_key` and `age`), and `kid_game_sessions` embeds `games_catalog` with column names it does not have. Both sit behind `if(!error)`, so the page silently shows nothing. **Found, not yet fixed.**
- The pattern that hides them is everywhere: eight sites assign query results only `if(!r.error)`, and 33 empty `catch` blocks in the workspace alone. Most disappear with the move to the backend; the rest need to say something when they fail.

### 2026-09-17 — "השיעורים שלי" exists now
- **The page behind the sidebar button was never built.** It has been there since the workspace was written, and every child who pressed it got a server error. The data was always there: the progress row joined to the lesson and its subject.
- **`GET /api/kid/lessons`** returns every lesson the child has opened, newest activity first, with the subject, the unit, the progress, the understanding score and the dates. The kid is resolved against the caller's account first, so one parent cannot read another's child. It is registered before `/api/kid/{kid_id}` so "lessons" is not swallowed as an id.
- **The page reads nothing from the database**, in keeping with the rule taken today. It groups by subject, because a child thinks in subjects and not in dates, shows a progress bar per lesson, filters by in-progress or completed, and opens a lesson back in the workspace. An account with no child, and a child with no lessons, each get a sentence rather than an empty screen.
- **Verified against the real data**: ארבל has nine lessons opened across two subjects with one completed, and every row resolves to its subject, unit and lesson name.

### 2026-09-17 — internal documents were readable on the web; every menu link audited
- **The documents are now closed.** The site root is the repo, so every `.md` in it was public. `SECURITY.md` — "what was found, what was fixed, what is still open" — was the worst of them: a list of open security findings, served to anyone. `BUGFIXES.md`, `MIGRATION_TO_BACKEND.md`, `PERFORMANCE.md`, `HANDOFF.md`, `TODO.md` and the deploy script were all readable too. They now live in `docs/`, which nginx refuses, and a rule blocks `.md`, `.sql`, `.sh` and similar anywhere on the site, so the game specs are covered in place. Verified: the documents answer 404 and the site, its assets and the games still answer 200.
- **Every internal link on the site was checked**, 38 of them across all pages. Seven were broken. Three were simply pointing at the wrong path and are fixed:
  - `/chat/` — **the Spanish onboarding sent every new account there when it finished**, and the page does not exist. It goes to `/workspace/` now. This one was breaking sign-up.
  - `/pt/support/` — the Portuguese workspace's support button; support is one page for all languages.
  - `/workspace/u1` — a placeholder path left in a marketing page, in two places, with a comment saying to change it.
- **Four pages in the Hebrew sidebar were never built**: "השיעורים שלי", "הכנה למבחן", "הישגים", "הקבצים שלי". Until they exist the buttons say so instead of dropping the child on a server error.

### 2026-09-17 — bug sweep from the real logs
- **Every documentation file in the repo is readable on the web.** The site root is the repo itself, and nginx blocks `.git`, the backend folders, `supabase` and `CLAUDE.md` — but not markdown. `/BUGFIXES.md`, `/MIGRATION_TO_BACKEND.md`, `/PERFORMANCE.md`, `/handoff_perfromance.md` and `/tools/deploy_tutor.sh` all answer 200 right now. This file alone describes every bug and every security hole we have closed, with table names, column names and route names, and the migration document is a table-by-table map of the database. Three of those files were written today, so the exposure was made worse by the work itself. **A tested nginx fix is ready and waiting for approval**; it is a production config change.
- **The missing video poster**: `/assets/backgrounds/video-poster.webp`, asked for on every load of the Hebrew landing page, 58 times in the log and never there. The hero video showed nothing until it buffered. A real frame was pulled from the demo video itself and saved at 1280px, 57 KB.
- **The avatar bug was in three more screens**, untouched: the Spanish workspace, the Portuguese workspace and the games workspace all built the image path straight from `avatar_key`. Fixed with the same known-avatar helper, eight call sites in all.
- **The gate was only scanning part of the site.** That is why the avatar bug survived in those three. It now covers every folder that serves a page, and the first thing that showed is that the count of direct database calls in the browser is **230**, not the 178 first measured. The ratchet holds the true figure.
- **Not a bug: the "144 empty lessons".** Of 206 lesson rows, 15 have been generated and the rest are `empty` because lessons are generated when a child opens them. The row's own `status` column is not read by any live screen.
- **The backend itself is clean**: one transient metrics timeout in the last three hours, nothing else. The errors filling the earlier log were the corrupted key and the missing images, both fixed today.

### 2026-09-17 — the longest call in the lesson pipeline was taking the slow way round
- **Where the child's wait goes**: the Visual Director is one call of 2000 to 3300 output tokens, measured between 14 and 46 seconds, while the whole rest of the lesson text takes 6 to 22 seconds a part. The child waits through all of it before a single word appears.
- **Measured properly, not guessed**: the same prompt sent three times to each provider, interleaved, same SDK (openai 3.10.0) and same server. Direct won every single run.

| run | direct | openrouter |
|---|---|---|
| 1 | 17.9 s | 28.0 s |
| 2 | 22.5 s | 31.3 s |
| 3 | 15.5 s | 27.7 s |

- **Fix**: this one call goes straight to OpenAI. Everything else stays on OpenRouter, because the reason the service runs through it is the voice quota, which this call never touches. `VISUAL_DIRECTOR_PROVIDER=openrouter` puts it back without a deploy.
- **Caveat worth keeping**: this is true for this model, this request shape and this server. Another project measured the opposite, which is entirely possible — for models OpenRouter routes to a faster provider, or from a different region, the extra hop can pay for itself. The knob exists so the answer can be re-measured rather than argued.
- **Bug caught while testing**: `DEFAULT_OPENAI_MODEL` is rebound to the prefixed `openai/gpt-4o-mini` at import time when the service runs on OpenRouter, so the first version of this change handed a prefixed id to the direct API, which does not know it. The selector strips the prefix.

### 2026-09-17 — cost reporting: a missing price and a view that counted almost nothing
- **The missing price**: `gemini-3.1-flash-lite` was not in `MODEL_PRICING_USD`, and it is the model behind the image text checks and the nikud pass. Of the last thousand recorded calls, 134 had no price at all and landed in the reports as "unknown". Added at the published rate. Verified that all five pricing paths now resolve: text for both providers, images per image, and voice by audio seconds.
- **Applied and verified**: media and text now add up to the total exactly (lesson 12: 2.8977 + 0.166 = 3.0637), and the picture it finally shows is that **media is about 95% of what a lesson costs**. The first attempt was rejected with `42P16: cannot change name of view column`, because `create or replace view` may only append columns — putting the new one in the middle reads as renaming `cost_usd`. The new column sits last.
- **The view**: `ai_costs_per_lesson.media_cost_usd` counted `purpose in ('tts','image','video','lesson')`, but the worker — which generates every image, every voice line and every intro video — tags its calls `media`. In the last five thousand calls that is 634 rows, the largest group, and none of them counted. `tts_live` and `intro` were missed too, while `lesson`, which is text, was counted as media. The per-lesson media figure has been wrong since the view was written, and wrong in the direction that matters: it under-reported the expensive half. Migration written, **not yet applied**, adding `text_cost_usd` alongside so the two halves add up to the total and any gap is visible.
- **Closed on its own**: the OpenRouter voice rows that were stuck at `cost_source='pending'` are all resolved — zero pending rows remain, so the generation-id lookup is working.
- **Cannot be fixed by a price table**: a few `gpt-5.6-sol` rows carry no token counts at all, because the response reported no usage. They stay unpriced and visible as "unknown", which is the honest outcome.

### 2026-09-17 — the parent's picture was a 404 on five pages
- **Symptom**: `/assets/default-parent.png` was requested on every load of the workspace (Hebrew, Spanish, Portuguese and games) and the add-subject page, and the file did not exist. A parent whose account has no picture from Google got a broken image in the top bar, and the site log filled with 404s.
- **Fix**: the file now exists — a deliberately generic illustrated figure, not a recognisable person, in the calm palette the app uses, 256 pixels and under 50 KB because it loads on every page. No code changed: the five references were already correct.

### 2026-09-17 — the games leaderboard was writing to tables that do not exist
- **Symptom in the code**: every completed game called `IAKidsCloud.recordWin()`, which inserted into `game_wins`. That table is not in the database, and neither is `game_achievements`. Each write failed inside its own try/catch, so nothing ever surfaced and nothing was ever recorded. The SQL file the comment pointed at, `games/games-tables.sql`, does not exist either.
- **Nothing read them**: `recordAchievement` and `topWins` have no callers anywhere on the site, and no leaderboard is drawn from them.
- **Not fixed by creating the tables**, for two reasons. The design keyed rows on an email the browser supplied, and its own comment admitted that could not be verified — anyone could post a score under any name. And the UI no longer talks to the database at all. A leaderboard, if it is wanted, is a backend endpoint scoring against the signed-in account.
- **Fix**: the object is an honest no-op stub with the whole story written above it, so existing call sites keep working and nobody believes scores are being saved. Four more direct database calls gone from the browser.

### build 0.7.135 — a gender chosen by mistake could not be corrected from the workspace
- **Symptom**: the parent panel could always change a child's gender, and its field even preloads the current value. The workspace could not. Gender was set once by the popup that appears on entry, and after that, right or wrong, it was locked.
- **Why it matters here**: the teacher addresses the child by that value in writing *and* in speech, so a wrong choice is heard in every sentence.
- **Fix**: the child-details dialog has a "בן או בת" field right after the name, in the same style as the grade picker. It marks what is set now, so the parent can see it and change it with one click; leaving it alone keeps what is stored.
- **Note**: audio already generated stays in the old wording. The voice cache key includes gender, so every new line is correct, but a line generated earlier sounds as it was generated.

### 2026-09-17 — he/parent-panel is off the database
- The three direct `kids_profiles` calls — list, update and create — became `iakidsApi` calls. This is the first screen that exercises all three operations.

### 2026-09-17 — the two converted screens were broken, twice, for two different reasons
- **Symptom**: on `/he/add-subject/` typing in the chat did nothing at all. No error, no message, nothing.
- **Cause one, mine**: the pages create their client as `const sb = supabase.createClient(...)`, and **a `const` at the top level of a classic script never becomes a property of `window`**. The API module looked for `window.sb`, found nothing, and `activeKid()` returned null quietly. The chat's first line is `if (!text || !CURRENT_KID) return;`, so it simply returned. The same applied to the key, also a `const`.
- **Fix**: the module now walks a chain — a client the page registered with `useClient()`, a global one if there is one, the games SDK's client, and failing all of those it creates its own. The session lives in `localStorage` and is shared, so it is the same session either way. It also warns out loud instead of failing silently. Verified in a real JS engine for four cases including "page uses const for both the client and the key".
- **Cause two, the browser**: after the fix the page still did not work. The site's own log showed the browser had loaded the module at 5128 bytes, and the fixed file is 7435; on the next visit the page came back 304 and the module was never re-requested. The browser was running the broken copy from cache. **Every shared JS file gets a version in its script tag from the first day** — the project already does this for the dictation and completion scripts. Without it a fix reaches the server and never reaches the user, and both sides think it shipped.
- **Verified end to end from the production log**: `GET /api/kid/...` answered 200 for the real parent, three `curriculum/chat` calls answered 200, `CUSTOM CURRICULUM APPROVED` followed, and the subject "משחק טאקי" is in the database, active, with its curriculum. Zero errors in the whole window.
- **Noticed, not fixed**: `/assets/default-parent.png` is requested on the add-subject page and does not exist, 404 on every load. It is the parent picture shown when the account has none from Google.

### 2026-09-17 — he/add-subject is off the database
- Two direct `kids_profiles` queries became one `iakidsApi.activeKid()` call. The page no longer knows the table exists.
- Second screen of stage 1. The gate's ceiling on direct database calls drops with each screen that ships, so the number can only go down.

### 2026-09-17 — stage 1 of moving the UI off the database: the kid profile API
- **Four routes** cover everything the browser did with `kids_profiles`: list my kids, read one, update one partially, create one. About thirty direct call sites across the site collapse into these five operations.
- **Authorisation is server-side only.** A kid id in the request proves nothing: every route resolves the owner from the token and filters on `user_id`. Verified against production with two real test accounts — a parent reading or updating another parent's child gets 404 and the child is unchanged, no token gets 401, an invalid gender or an empty update gets 400, and the response carries only the fields a screen draws, never `user_id`.
- **`assets/js/iakids-api.js`** is the single door: it resolves the API base, takes the token from the existing auth session, and exposes `listKids`, `getKid`, `updateKid`, `createKid` and `activeKid`.
- **Found and fixed on the way**: `get_child_by_id` used `.single()`, which *raises* when nothing matches, so a parent asking for a child that is not theirs got a 500 after the retry wrapper had tried three times, instead of a plain 404.
- **Learned the hard way**: the site container mounts `/opt/iakids` straight as the web root, so every frontend file edit is live the moment it is saved, with no commit and no deploy. A converted page was live for a few minutes while its backend routes were not yet deployed, and was restored immediately. Frontend and backend of the same change now ship together, backend first.

### 2026-09-17 — the tasks page showed a default avatar for every child
- **Symptom**: the child's picture never appeared on `/he/tasks/`.
- **Cause**: the page asked for `avatar_key + ".webp"` (`dog.webp`) while the files are named `dog_blue.png`. Every request answered 404 and an `onerror` handler quietly swapped in the generic default, so nothing ever looked broken and no child ever saw the avatar they chose. Same class as the missing dog avatar fixed earlier today, in a page that had not been touched then.
- **Fix**: the page uses the shared naming convention and the known-avatar list, so an unknown key falls back to a real image instead of a broken one.
- **Also**: `/he/tasks/` is now the first screen that no longer queries the database at all. Its task list is empty because `kid_tasks` holds no rows for any child, not because of the change.

### 2026-09-17 — decision: the UI talks to the backend, never to the database
- **Question asked**: can the code be hidden so a user of the system cannot see it. **Answer: no.** The browser must receive and run it. Minifying or obfuscating buys an attacker hours, not safety, and here it would cost a build step the project deliberately avoids, break the log switch and blind the gates that read those files.
- **What can be hidden is the data layer.** As long as a page calls `sb.from("kids_profiles")`, the table name, the column list and the relationships sit in the request URL and the JSON response, visible in the network tab whatever the JavaScript looks like. The only way to hide them is to stop the browser talking to the database — which is the decision that was taken.
- **Measured**: 178 direct database calls in 53 browser files. `kids_profiles` appears in about 30 of them, most through one shared helper in `games/game-sdk.js`. Full inventory, per-table counts and the staged order are in `MIGRATION_TO_BACKEND.md`.
- **Gate**: the number of direct database calls in browser files may only go down. A new `.from(...)` call in any page fails the build and says to add an endpoint. Verified by adding one on purpose.
- **Checked while mapping**: no real secret is in any page. The Firebase and Supabase publishable keys are public by design and documented as such in `games/game-sdk.js`. The gate now also fails on a secret-looking key or any mention of `service_role` in a page.

### 2026-09-17 — the admin email list was published in two pages
- **Symptom**: `he/admin/lessons-review/` and `he/iakids-admin-dashboard-he/` each carried the admin email addresses in plain source, five in one and two in the other.
- **What it protected**: nothing. Every admin route already checks `ADMIN_EMAILS` server-side and answers 403, which was verified when those routes were built. What the list did do was hand anyone the accounts worth phishing.
- **Fix**: a new `GET /api/admin/whoami` answers 200 for an admin and 403 for anyone else. Both pages ask it instead of holding a list. A gate rule fails the build if an allowlist ever comes back.

### 2026-09-17 — browser grants revoked on every table the browser never touches
- **Applied and verified** with a real signed-in session: all 27 revoked tables answer `permission denied`, all 23 tables live pages use still work, the backend (service_role) still reads everything, and the services are clean.
- **One table had to come back out of the list: `app_admins`.** Revoking it broke reading `support_tickets`, and the error named a table nobody asked for: `permission denied for table app_admins`. A row level policy on support_tickets asks whether the user is in app_admins, and a policy runs with the caller's own rights, so the moment the caller cannot read that table the whole policy fails — for an ordinary user looking at their own tickets. `app_admins` is empty and holds only admin user ids. The proper fix is a `SECURITY DEFINER is_app_admin()` helper and a policy that calls it; until then the table stays granted, and the migration says why.
- **Why**: Supabase grants `anon` and `authenticated` every privilege on every table in `public` by default, and row level security is the only thing in front of them. That is one policy mistake away from an open table, and it already happened: the 2026-09-10 audit found anonymous reads of exam answer keys, exam questions and the whole lesson catalogue, plus an anonymous INSERT into subscriptions that only a NOT NULL constraint stopped.
- **Method**: every `.html` and `.js` file the site serves was scanned for `.from("table")`, excluding backup copies. 28 tables are never read or written from a browser; 23 are. Only the 28 are revoked, so nothing that works today stops working.
- **Functions were checked one by one**, because a `SECURITY INVOKER` function needs the caller's own rights: `record_user_location`, `game_record_answer`, `game_record_answers` and `game_question_mark` are `SECURITY DEFINER`; `game_next_questions` is invoker but reads only `game_questions` and `kid_question_answers`, both of which stay granted.
- **Still open by design**: the 23 tables live pages read directly. Closing those means moving their reads behind the backend first, which is a separate job.
- **Found on the way**: `games/game-sdk.js` calls two tables that do not exist in the database at all, `game_achievements` and `game_wins`, so those calls have always failed.

### 2026-09-17 — every migration now has a rollback file
- **Rule**: `<name>.sql` must ship with `<name>_rollback.sql` in the same commit; the gate fails otherwise, and a rollback with only comments counts as missing.
- **Written for all 17 migrations**, 14 of which had none. Statements that would destroy data are written out but left commented with `-- DATA LOSS:` — a `drop table` or `drop column` is never left ready to run.
- **Honest about what a rollback cannot do**: `create or replace function` cannot be undone by dropping the function, because that removes it entirely. Those files say so and name the earlier migration to re-run instead. The rollback of the 2026-09-10 security audit opens with a capitalised warning that running it reopens the holes it closed.

### build 0.7.135 — a browser query had been asking for a column that does not exist
- **Found while checking that the answer-key migration breaks nothing.** One query in the workspace asked `lesson_units_content` for `parent_lesson`, which is not a column of that table. PostgREST answers `42703 undefined column`, and the call site is `if(!r.error) unitMeta = r.data` — so the error was swallowed and the unit names were silently missing from that view. Confirmed against prod: the old query fails today, the corrected one returns rows.
- **Fix**: it now asks for `learning_lesson_id`, the column it actually needed.
- **Also verified**: every live browser query on that table selects only columns the new grant keeps, so the migration cannot break the product.

### build 0.7.134 — the answer key was on its way to the browser
- **Found while answering "how do I stop someone reading the JS and turning the logs back on"**. The honest answer is that you cannot: anything the page holds can be shown. So the question becomes what the page is allowed to hold — and today's own change had just made that worse.
- **The leak**: `question.answer` was added this morning so the Learning Coach stops inventing the answer it grades the child against. The unit-lesson route returns `structured_lesson` verbatim, so the answer to every question was about to travel to the browser, where any child with the network tab open could read it before answering.
- **Fixed in the response**: `public_structured_lesson()` strips `answer` from every question on the way out, at both return paths (fresh and cached). The coach reads the answer from the database, never from the client, so nothing else changes. The original object is not mutated.
- **Still open, needs approval**: `lesson_units_content` is readable by **any signed-in account** (`for select to authenticated using (true)`, from the 2026-09-10 RLS work), so a child with a session can query the table from the console and read `generated_lesson_json` directly, route or no route. Row level security cannot fix this — the row must stay readable, it is one column that must not be. `supabase/migrations/20260917_hide_lesson_answer_key.sql` revokes column-level select on `generated_lesson_json` and `lesson_audio_json` from `authenticated` and `anon`. **Not applied.** Checked first that no browser code reads either column.
- **`he/lesson/index.html`** was doing `select("*")` on that table, which pulled the whole generated JSON into the page. It now selects the seven columns it actually uses.
- **Three gate rules**: the strip helper must exist and be used on every path that returns a structured lesson, no browser file may read `generated_lesson_json`, and no browser file may `select("*")` from `lesson_units_content`. All verified by breaking them.

### build 0.7.133 — test and production log modes
- **Ask**: a test configuration where the logs are written to the console, and a production one where they are not.
- **Why one switch and not two scripts**: the pages are static files that nginx (and GitHub Pages on iakids.app) serves as they are. The backend never generates them, so the prints cannot be stripped on the way out, and a second copy of a page would diverge within a week. A build step is against the project's structure. So `assets/js/iakids-log-mode.js` replaces the console methods once, before anything else runs.
- **Behaviour**: test prints everything; production prints nothing except `console.error`, which is never silenced, and uncaught exceptions are untouched. The switch hides noise, never failures.
- **Choosing the mode**: `window.IAKIDS_LOG_MODE` before the shim, then `?log=1` / `?log=0` in the URL (kept for the tab), then `localStorage.IAKIDS_LOG`, otherwise localhost and private ranges are test and everything else is production. On production, open with `?log=1` or run `iakidsLogMode("test")` and reload.
- **Covers**: log, debug, info, warn, table, dir, group, time, count, trace and assert, on all six pages that print — the workspace alone had 154 log calls, 70 warns and a table, all of which were reaching every child's console together with kid ids and signed media URLs.
- **Verified** in a real JS engine for six cases: production host, localhost, production with `?log=1` (and that it persists), localhost with `?log=0`, blocked storage in private mode, and switching at runtime in both directions. Loading the file twice does not re-wrap. Four gate rules, each verified by breaking it.

### build 0.7.132 — a lesson now ends with a summary, not with a video and three numbers
- **What it was**: the closing was the coach's one-sentence wrap-up of the **last question only**, then `lesson-closing.mp4` — one file, identical for every lesson and every child, twenty seconds — then a card with three numbers and a grid of eight equal lesson cards. Nothing ever told the child what they had learned. The progress rail even had a "סיכום" step with a checkered flag that rendered nothing.
- **New**: `POST /api/tutor/unit-lesson/closing` returns a personal wrap-up built from the lesson's own explanations, the child's real answers and the per-part scores: a spoken summary of about thirty seconds, three short lines (למדנו / הצלחת / נחזק) shown on the card, and one sentence for the parent. Generated once per child per lesson and cached in the history table, so re-entering a finished lesson costs nothing and needs no migration.
- **Verified on lesson 152 with ארבל's real answers**: "ארבל, היום למדנו איך לזהות שמות עצם שמציינים אנשים ובעלי חיים… הצלחת לזהות כמעט את כל השמות במשפטים… כדאי לחזק את זיהוי השמות במשפטים מורכבים יותר." Correct feminine forms throughout, grounded in what she actually wrote, no numbers and no question.
- **The video** is cut to a four-second sting and plays while the summary is fetched.
- **The lesson is finally marked as finished**: `status="completed"`, `completed_at`, `progress_percent=100`, `xp_earned` and `stars_earned` are written when the last part ends. Those are exactly the columns the child's and the parent's dashboards read, which is why every unit lesson had been showing zero.
- **One next step** instead of a grid of equals: the next lesson was already computed in the code and never shown. It is now a single primary button, with the unit grid kept below it.
- **The score on the card** came from scraping the on-screen gauge, which is refreshed by a call nobody awaits, so it could show the previous part's score. It now comes from the progress row the backend just wrote.
- **The parent** sees the teacher's sentence instead of percentages, with the numbers moved to a small second line.
- **Five gate rules** cover all of it (route, response model, cache, completion write, the fetch/render/sting in the screen, the single next button, the score source), each verified by breaking it on purpose.

### build 0.7.131 — "save" in the child-details dialog left it open (again)
- **Symptom**: editing the child's details and pressing save kept the dialog on screen. The profile was in fact saved.
- **Cause**: after the save, the function refreshes the screen. Four of those updates wrote to elements that do not exist on every screen (`heroGreeting`, `heroAvatar`, `rightbarAvatar`, `rightbarName`) with no check, so the first missing one threw and `closeSettings()` was never reached. The earlier fix in 0.7.122 had only wrapped the subject list.
- **Fix**: once the save has succeeded, the whole screen refresh runs inside `try`, every element is checked before it is written, and `closeSettings()` runs in a `finally`. A failed refresh can never hold the dialog open again. Gate rule added and verified by removing the `finally` on purpose.

### build 0.7.131 — 22 children had a broken avatar
- **Symptom**: `GET /assets/avatars/dog_blue.png 404`.
- **Cause**: the avatar URL was built straight from `avatar_key` with no check that the file exists. Of 137 children, 22 had chosen `dog` and there was no dog image; 2 have no key at all.
- **Fix**: `dog_blue.png` was generated in the same style as the other six avatars (the cat was used as the style reference) and added. A shared `iakidsAvatarUrl()` helper falls back to the cat for any unknown key, in the workspace and in the parent panel. The gate fails if an avatar URL is ever built straight from the key again.

### build 0.7.130 — a server restart ended a child's lesson, in Spanish
- **Symptom**: ארבל sent her answer at the exact moment of a deploy and got "⚠️ Algo salió mal. Intenta más tarde." — a Spanish sentence on a Hebrew page — and the lesson stopped.
- **Cause**: a restart takes about 16 seconds and nginx answers 502 during it. The chat treated that as a fatal error, and the error text had never been translated.
- **Fix**: 502, 503 and 504 are retried twice with a growing pause before anything is shown; the messages are Hebrew and say the server is waking up. Two gate rules pin both, and the gate now fails on any non-Hebrew error string in the workspace.

### build 0.7.130 — the 15 existing lessons got their correct answer without being regenerated
- **Why**: the coach fix only helps lessons generated from today on. Regenerating a lesson to add one field would throw away its text, images and audio.
- **`tools/backfill_lesson_answers.py`**: one cheap text call per part writes `question.answer` into a lesson that has none, and touches nothing else. Run on all 15 ready lessons (30 questions, about 70 seconds). Lesson 152 part 1 now carries "המילים המורה, ארנב, תלמידה", which is exactly what the child had answered.
- **Also**: the lesson quality report now warns when a question has no stored answer and names the tool that fixes it.

### build 0.7.129 — the teacher judged the child against an answer it had invented
- **Symptom, three lessons in a row**: ארבל answered "המורה, ארנב, תלמידה" — the complete correct answer — and the teacher scored 40 and asked her to find "the word that means an animal", which she had just said. On the next lesson she answered "ספריה זה מקום, שולחן זה חפץ, וילדים זה שם עצם" and the teacher sent her back to ילדים instead of naming the one word she actually missed, מחברת.
- **Cause**: the Learning Coach was never given the correct answer. `RUNTIME_DATA.lesson.correct_answer` was the literal sentence "Derive from the lesson explanation and lesson goal", so the model derived an answer itself and graded the child against it.
- **Fix**: the teacher now writes the answer together with the question (`UniversalLessonResponse.answer`), it is stored next to the question in the structured lesson and handed to the coach. The child never sees it and it is never spoken. Lessons cached before today fall back to the old behaviour instead of failing. The coach prompt now requires an explicit item-by-item comparison against that answer and forbids asking for more once every item has been said.

### build 0.7.129 — "after N attempts give the answer and move on" never actually happened
- **Symptom**: a child who could not answer was moved to the next lesson part still holding an open question, with no answer.
- **Cause**: the loop guard existed and worked — the round limit is 1 to 4 by score, with a hard ceiling of 5 — but the model was always told `maximum_rounds: 5`. Its "last round" therefore never arrived before the server cut the session off, so the prompt rule "on the last round explain the correct answer and stop asking" could never fire. The end-of-session decision was also taken after the teacher's text was already written, so the last message usually still ended with a question that was then shipped with `wait_for_answer: false`.
- **Fix**: `learning_coach_round_plan()` is the one source of truth. It derives the limit from the score the session already has, before the model runs, and that same number is what the model is told, what the session status uses and what the flow decision enforces. `coach_state.is_final_round` tells the model outright, and the prompt now requires it to state the full answer, explain it in a sentence, ask nothing, and close with encouragement.

### build 0.7.129 — every case we fell into is now a gate rule, and the installer runs them
- **New rule in CLAUDE.md**: a bug reported in the chat, a prompt or the lesson mechanism is not fixed until `tools/prompt_gate.py` would catch it again, in the same commit, with a negative test proving the rule fails when the code is broken.
- **New checks**: `workspace_checks` (the lesson layout must apply to every subject, the visual wait must have a budget and a give-up flag, the build stamp must match `IAKIDS_BUILD_VERSION`), `media_failure_checks` (a part whose images all failed must log FAILED, `require_api_key` must exist), `learning_coach_checks` (the stored answer, the round plan, `is_final_round`), and `learning_coach_round_tests` (the limit never reaches zero, is monotonic in the score, and the last allowed round reports itself as final).
- **Coverage widened**: the commit gate now also fires on `he/workspace/index.html` and on the gate file itself, and a change to code alone runs the code rules instead of returning early.
- **`bash tools/install_hooks.sh`** installs the hook **and runs the whole suite**, so a fresh clone is verified at install time. All six new rules were verified by breaking them on purpose.
- **Live check corrected**: the 3-provider check failed a deploy on a hero image whose only text was "CO2, H2O, O2" — stricter than the product, which allows universally readable scientific notation. It now applies the same `is_allowed_scientific_text` rule as production, and still fails on words in any language.

### build 0.7.128 — the corrupted Gemini key, found and repaired; lesson 152 has its pictures
- **Where the key broke**: `.env.prod` alone. An append to a file whose last line had no closing newline glued `OPENROUTER_API_KEY=…` onto the end of `GEMINI_API_KEY`, turning a 53-character key into 146 characters with a Hebrew letter in the middle. `.env` and `.env.dev` were never touched and are clean. The broken file is kept as `.env.prod.bak2`.
- **Repaired**: the `GEMINI_API_KEY` line was replaced from `.env`, the file now ends with a newline, and `tools/deploy_tutor.sh` restarted both services with the gate green (the new env-file check passes).
- **Lesson 152**: a `unit_lesson_visuals` job was queued for it — media only, no new text and no extra text cost. All 16 images were generated in 42 s and the visuals route no longer reports a missing file.
- **Fixed in the same pass**: the `images_ok` counter added earlier today counted every image of the lesson instead of the current part, so part 2 reported 16 of 8.

### build 0.7.127 — a lesson was generated with no pictures at all, and the screen waited for them
- **Symptom**: lesson 152 ("שמות של אנשים וחיות", Hebrew) played its text and voice but showed no image; the hero request answered 500 and the visuals poll answered "not ready" for all 16 images.
- **Cause**: not the lesson and not the pipeline. `.env.prod` was appended to without a trailing newline, so the next variable was glued onto the end of `GEMINI_API_KEY` (53 characters became 146, including a Hebrew letter). The server started normally and everything that goes through OpenRouter — text, voice — worked, while **every** image call died deep inside the SDK with `UnicodeEncodeError: 'ascii' codec can't encode character '\u05d1'`. The media job then reported `done` although zero images were produced.
- **Fix, three layers**:
  1. `require_api_key()` at startup: a key must be present, clean ASCII, and must not carry a second `VAR=` inside it. A corrupted env file now refuses to start and names the variable, instead of silently producing lessons with no pictures.
  2. `env_file_checks()` in the prompt gate, on the **deploy** path only (`--all`): the same three rules read straight from the env file, so a broken key is caught before the restart. It is deliberately not part of the commit gate — a commit must not depend on a secrets file that is not in git. The render smoke now runs with dummy keys, so it tests prompts, not secrets.
  3. A part whose images all failed logs `LESSON PART VISUAL GENERATION FAILED (no image produced)` and the DONE line carries `images_ok` / `images_planned`.

### build 0.7.127 — images no longer hold up the lesson
- **Symptom**: with the images failing, the child sat in front of a stuck screen. `waitForLessonVisual` polls up to 40 times with a 2.5–8 s backoff (~300 s), and the opening buffer waits for three images one after another, so a failure could freeze the lesson for many minutes.
- **Fix**: one wait budget of 45 s (`window.LESSON_VISUAL_WAIT_BUDGET_MS`); when it runs out the lesson gives up on images for the rest of the session (`LESSON_VISUALS_GIVE_UP`), every later wait returns immediately, the "generating" box is hidden, and the text and voice continue normally. The flag resets when a lesson opens.

### build 0.7.126 — the lesson screen worked only for מדעים; images were not shown in the middle
- **Symptom**: in a Hebrew lesson ("מהו שם עצם?", lesson 151) the lesson pictures were not displayed in the centre of the screen and the chat sat on the right, while the very same flow in a science lesson looked right. It looked like the generated lesson was broken.
- **Cause**: the lesson was fine — the backend served all 14 visuals plus the hero, all valid images. The whole lesson-screen layout (picture stage in the middle, chat column, heights, dark topbar) lives in 467 CSS rules scoped to `body.lesson-theme-science`, but `setLessonBackgroundForSubject()` added that class **only when the subject was exactly "מדעים"**. Any other subject opened the lesson with no layout at all.
- **Fix**: the class now marks "a lesson screen is open" and is added for every subject; the science-only part, the dusk background image, moved to a new class `lesson-subject-science` that is toggled by subject. Leaving the lesson removes both.
- **Verified**: every inline script passes `node --check`; the background layer stays invisible for non-science subjects (base rule is `opacity:0`), so nothing changes for lessons that already looked right.

### build 0.7.126 — restored two migration files that had been emptied
- `supabase/migrations/20260914_media_jobs.sql` and `..._priority.sql` were sitting in the working tree with 0 lines (one held a single stray `g`), i.e. a stray shell redirect had overwritten them. Restored from `HEAD` before the commit so the queue migrations are not lost.

### build 0.7.125 — the teacher's example gave away the whole answer
- **Symptom**: the question was "find the nouns in: דני שיחק עם כדור בחצר". The child answered partially and the teacher replied with an "example" that named דני, כדור and חצר with their reasons — the complete answer — and then asked "what else?".
- **Fix**: a new rule block in the two prompts that answer a child mid-question (`learning_coach_system_prompt.txt`, `iakids_structured_lesson_prompt.txt`): feedback confirms only what the child actually said; a hint says **how many** items are missing, never which; an example must use different words from the active question; and a final self-check — "if the child copied my reply, would it answer the question? then rewrite it". The gate requires both sections to stay in the files.

### build 0.7.123 — the child's name was mispronounced ("ארבל")
- **Symptom**: the voice said the name wrong; a name is the first word a child hears.
- **Fix**: `vocalize_name()` — a curated nikud table for the names in the product (אַרְבֵּל, אֵיתָן, אֲבִישַׁג, אַלּוֹנָה, רוֹתֶם …), a single small model call for a name that is not in it, and the result is stored in Storage (`tts-cache/v1/name_nikud.json`) so every process and every restart reuses it. Names in Latin letters are left alone (the voice prompt already reads them as English). The name is substituted into the spoken text before the gender nikud, in the live route and in the intro cache warm-up so both produce the same cache key. Override with `TTS_NAME_NIKUD_JSON`.
- **Verified**: "היי ארבל! ... אני כאן בשבילך. כל הכבוד, הצלחת." now speaks as "היי אַרְבֵּל! ... בִּשְׁבִילֵךְ ... הִצְלַחְתְּ" through the real route (audio sent to the user).

### build 0.7.122 — the teacher spoke to a girl in masculine (ארבל)
- **Symptom**: ארבל (gender=female in her profile) wrote to the teacher and the reply was read aloud in masculine: "אני כאן בשבילְךָ" instead of "בשבילֵךְ".
- **Cause**: not the text. "בשבילך", "שלך", "הצלחת", "ראית" are spelled **identically** for a boy and a girl and only the vowels differ, so the written answer was correct and the TTS defaulted to masculine. The prompt did carry `gender: female`.
- **Fix**: `second_person_nikud()` — a deterministic table (no model) for ~35 second-person forms (־ך suffixes and past tense) in both genders; `vocalize_for_tts(text, gender)` applies it; the live TTS route resolves the child from `kid_id` (else the tutor session) and the workspace sends `kid_id`; the TTS cache key now includes gender so a girl never gets the boy's recording.
- **Also found while fixing**: `openai_clean_chat` and `homework_coach_v2` (added on another branch) talked to the child with no gender rule at all, and `iakids_universal_unit_lesson_prompt.txt` was loaded but **never used** — the shared-lesson neutrality rule added on 2026-09-16 sat in a dead file. Both routes now start with `hebrew_child_prompt_block(child)`, the rules moved into the file that is really used (`iakids_lesson_initial_prompt.txt`), and the dead file was deleted.
- **New Hebrew correctness block** (`HEBREW_WRITING_RULES`, one source of truth) in every child-facing prompt: gender agreement on every verb/adjective/suffix, Hebrew numerals agreeing with the noun, no slash forms, no gershayim abbreviations, no emoji in spoken text, English only when it is what is taught.
- **New gates**: `child_prompt_gender_checks` (any route building a Hebrew prompt for the child without a gender rule fails), `prompt_usage_checks` (a loaded prompt whose template is never used fails — this is what caught the dead file), plus unit tests for the nikud tables and a rule that the TTS cache key must include gender.
- **Verified**: live TTS with and without `kid_id` returns different audio; gate + live 3-provider check pass.

### build 0.7.122 — "save" in the child-details screen did not close it
- **Cause**: two of my own changes. In the parent panel the new gender select was **required**, so editing a child that had no gender was blocked. In the workspace, `saveSettings` refreshed the subject list after saving and any error there skipped `closeSettings()`.
- **Fix**: on edit the gender field is optional (empty = leave what is stored); `loadSubjects` is wrapped so the modal always closes; the workspace profile modal can set gender too; the one-time "boy or girl?" prompt got an "אחר כך" dismiss so it can never trap the screen.


### housekeeping — removed backups taken for work that never touched a prompt
- `V3_BACKUP`, `V6_BACKUP`, `V10_BACKUP` deleted: their prompt files were byte-identical to `V4`, `V7` and the current tree, because the work they preceded (TTS nikud in code, the live TTS cache, dictation) changed no prompt file. Kept: V1 (first snapshot), V2, V4, V5, V7, V8, V9 — each holds a distinct pre-change prompt state. The gate still passes.

### build 0.7.121 — dictation: speak instead of typing, in every chat box
- **Ask**: wherever there is a speaker and a chat, let the child speak and have the words appear in the box.
- **How**: `assets/js/iakids-dictation.js` uses the browser's built-in Web Speech API — no model, no cost, and the text appears live while the child speaks. It auto-attaches to the workspace mic button (which was decorative until now), the games workspace, the add-subject chat and the Homework V2 composer (a mic button is injected where none exists). Lesson audio is paused before listening so the teacher's voice is not recorded; 2.5 s of silence ends the recording; permission and no-speech errors show a short Hebrew hint.
- **Fallback (off by default)**: browsers without the API (Firefox, old WebViews) hide the mic. Setting `window.IAKIDS_STT_SERVER_FALLBACK = true` records and posts to the new `POST /api/tutor/stt` (OpenAI transcription, Gemini as an alternative, `STT_PROVIDER`). Verified round-trip: our own Hebrew TTS clip came back transcribed word for word in 1.3 s.

## 2026-09-16

### build 0.7.114 — dynamic image count: no image for a segment that adds nothing new
- **Symptom**: images like visual 1, 2, 4, 5, 10 of a part showed the same idea; every segment got its own picture (one image per sentence, ~70% of lesson cost).
- **Fix**: one plan entry per segment stays (player contract segment N → entry N), but only some entries get a NEW image; the others point at the previous image (`reuse_of`) and the visuals route serves that file. The director's `reuse_previous` flag proved unreliable (0% in one run, 90% in the next), so a deterministic **image budget** decides: `ceil(segments × VISUAL_NEW_RATIO)` new images per part (default 0.5, min `VISUAL_MIN_NEW`=3), given to the segments whose prompts differ most from the previous one. Math notation (sin, cos, π, √, x²) joins the allowed in-image notation.
- **Verified**: offline on lesson 12's plan (26 entries → 15 new images incl. the 2 question images, 11 reused: 16 images with hero instead of 27, ~$0.37 saved per lesson); first regeneration with the flag alone produced 26 images (that is why the budget exists).

### build 0.7.114 — CO2 in an image was treated like a caption
- **Decision**: universally readable scientific notation (chemical formulas, plain numbers, units) is language-neutral and allowed in a shared image; words and labels in any language are not.
- **Fix**: vision check classifies `kind=formula`; `is_allowed_scientific_text()` (formula must contain a digit or be allowlisted, so "Growth Thinking" never passes); generation-time check no longer retries on such images; the three image prompts state the exception explicitly.

### build 0.7.114 — admin page did not explain why an image was flagged
- **Symptom**: the review screen showed a flagged image with a sentence like "The boy is holding a small tablet…" (the vision model's description) instead of the text it read.
- **Fix**: the vision check now returns the text verbatim plus kind and confidence; a description or low confidence is a warning, not a failure. The report stores a verdict per image; the modal explains the rule, shows the quoted text and confidence next to each image, and offers per-image actions: approve (human override) or regenerate that single image (`/api/admin/lessons/{id}/images/approve|regenerate`).

### build 0.7.114 — intro too long for a lesson that already exists
- **Symptom**: opening an existing (cached) lesson still played the full opening video and the whole intro sequence, although the intro only exists to cover generation time.
- **Fix**: the workspace probes the lesson request for 1.5 s; if it comes back from cache, the opening video is cut at 4 s (`LESSON_INTRO_MAX_MS`) and the intro is trimmed to one spoken line. New lessons are unchanged.
- **Verified**: script passes `node --check`; served at build 0.7.114 on smarts-brains.online.

### build 0.7.114 — paid quality checks off by default
- `LESSON_QUALITY_GATE` and `IMAGE_TEXT_CHECK` now default to `0` (each costs model calls per lesson). Everything stays wired; set `=1` in the service environment to turn them on. The admin page's re-check button still runs the gate on demand.

### build 0.7.114 — admin screen: lesson review (admins only)
- New page `/he/admin/lessons-review/` (Google sign-in; allowlist rotem/yossi) backed by `/api/admin/lessons/*` routes that enforce `ADMIN_EMAILS` server-side (a non-admin parent gets 403, verified). Shows every lesson with its quality-gate verdict, the flagged images with the text found, the lesson text, and actions: human approval (with note), re-check, regenerate (wipe + `content_version` bump).


### build 0.7.113 — re-entering a lesson showed only the last question
- **Symptom**: a child who reached "explanation 1 → question" and came back saw only the question in the chat; the explanation and their own answers were gone.
- **Cause**: `/api/tutor/active-lesson-state` returned only `last_assistant_message`; the workspace rendered just that.
- **Fix**: the endpoint now returns `chat_history` (every `kid_lesson_history` row of that unit lesson, teacher and child) and `resume_context` (explanation segments + question of the part the child is on); the workspace renders them, without audio, before playing the last teacher message.
- **Verified**: state endpoint for an active session returns the rows; workspace script passes `node --check`.

### build 0.7.113 — quality-gate failures no longer withhold a lesson
- **Symptom**: after the gate flagged lesson 6 (text on the hero image) the child got "השיעור בבדיקת איכות".
- **Decision**: a failed gate only flags the lesson (`generated_lesson_json.quality.ok=false`) for the admin review screen; lessons are always served. Only an explicit `generation_status="needs_review"` set by a human withholds one.

### commit 702b63c1 — Render build would fail
- `python-multipart` (required by the OpenAI clean chat route) was missing from `backend-ai-tutor-he/requirements.txt`. Found because the same import error took the box's service down for 4 minutes on 2026-09-15.

### commit e320959d — quality gates end to end (build 0.7.112)
- Lesson quality gate after every media job (text rules, visuals vs segments, audio vs segments, storage consistency, no readable text in images) with report in `generated_lesson_json.quality`; `tools/lesson_gate.py`.
- Curriculum-builder prompt placeholders (`{child_name}`, `{gender}`, …) were never filled — the model saw the literal text. Found by the new prompt gate.
- Visual director asked for "labeled diagram / captions" despite the rules → `sanitize_generation_prompt`; hero prompt rendered the lesson title as text → strict no-text block + retry.
- Prompt gate: required placeholders/sections per prompt, orphan prompts, inline-code rules, unit tests, render smoke; git pre-commit + Claude Code hooks; `deploy_tutor.sh` runs the live 3-provider check when prompts changed.
- Route decorator landed on a helper (prod down 4 min on 2026-09-15) → import smoke in the gate, restart only via `deploy_tutor.sh`.
- TTS: normalisation (emoji, arrows, ×÷=%°, fractions, gershayim), long-segment split, live TTS cache in Storage + memory (greeting/shared lines 3.7 s → 0.2 s), nikud on homographs (מִדְבָּר vs מְדַבֵּר).
- Gender: `hebrew_gender_rule` in every child-facing prompt; onboarding / parent panel / workspace collect gender (131 of 133 kids had none).
- Shared lessons stay neutral (rule in generation prompts + log check); RTL / child-safety / shared-audience rules in image prompts; `content_version` bump on regeneration and delete; style chain across parts; signed URLs 4 h.

## 2026-09-15

### build 0.7.104 — parallel director + parallel TTS; nikud
- Part-1 director ran serially before part-2 teacher (77 s → 71 s); TTS segments serial (147 s → 58 s); "מדבר" read as medaber → nikud for ambiguous words.

### build 0.7.102 — Part 1 of every lesson was the question chopped into sentences
- **Cause**: on 2026-09-01 `lesson_director_prompt.txt` lost `{lesson_text}` and the part-1 director received only the question. 14 of 15 lessons affected.
- **Fix**: `direct_lesson_part()` (explanation in prompt + user message, validation, retry, fallback); placeholder restored. Affected lessons wiped and regenerated.
