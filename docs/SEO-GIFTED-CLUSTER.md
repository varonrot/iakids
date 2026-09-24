# Hebrew gifted-tests cluster — 2026-09-24

Public hub: https://iakids.app/he/blog/gifted-tests/

12 pages: hub, grade-2 (existing, integrated), grade-3, stage-a, stage-b,
preparation, free-practice, verbal-questions, quantitative-questions,
shape-patterns, dates-registration, results-appeals.

Intent: parent information plus original low-pressure familiarisation questions.
23 original questions total, hints and worked explanations; no scores, diagnostic
claims, official-question reproductions, or prediction of admission.
The dates page explicitly does not claim a verified 2026–27 primary exam date.
Official source links appear beside procedural content; detailed eligibility and
dates are left to current Ministry notices. Review dates page when new notices arrive.

Design: existing grade-2 prototype, self-hosted Heebo font, blue/green palette,
responsive article/sidebar, hero images, RTL, accessible native details, explicit
LTR mathematical/visual sequences, keyboard focus styles, print-only questions.

SEO: distinct titles/descriptions, canonical URLs, Article/CollectionPage and
breadcrumb JSON-LD for new pages, image social metadata, hub and sibling links,
entry points from /he/blog/. Existing sitemap workflow discovers index.html files.

GA4: G-DKPPTPCDW8 once per page. Automatic page_view plus cluster_view,
cluster_link_click, cluster_cta_click, practice_start, practice_hint_open,
practice_solution_open, practice_print. Events include content_group=gifted_tests_he,
article_slug, content_language, and action-specific placement/link_path/question_id.
No names, answers, scores or form inputs are collected by the custom events.
In GA4, register article_slug/placement/question_id as event-scoped custom dimensions
if needed for standard reports. No Analytics property settings were changed.
Event code verified with local handler checks; delivery into GA reports must be
confirmed separately (browser blocking/consent/settings can affect measurement).

Images: built-in image generation, optimised to 1200x800 WebP with Pillow.
Existing grade-2/hero.webp retained. New assets:
- he/blog/gifted-tests/assets/reading.webp
- he/blog/gifted-tests/assets/puzzle.webp

Generation prompts:

Reading: Use case photorealistic-natural. Create landscape editorial photograph
1536x1024 for Hebrew parenting educational website IAKIDS. A 8 year old girl with
dark wavy hair and her father reading an illustrated book together at a bright
kitchen table in contemporary Israeli apartment, warm candid curiosity, both
looking down at book, natural real faces and hands, gentle daylight, neutral cream
background with pale blue and sage green accents, pencil and notebook on table,
intimate relaxed learning not studying under pressure. Medium wide composition,
premium editorial photography. Book seen at angle with small indistinct illustration,
no readable text, no letters, no logos, no watermarks. Subject fits central 80 percent.
Single image.

Puzzle: Use case photorealistic-natural. Landscape 1536x1024 editorial education
photograph. Overhead flat lay on warm cream desk: beautiful wooden geometric tangram
pieces, a few blue and sage green wooden counting cubes grouped neatly, simple
unmarked notebook and pencil, small child's hand reaching to move a wooden triangle.
Tactile natural wood, sunlight and gentle shadows, refined contemporary educational
brand palette light blue sage green pale yellow, airy composition. Realistic
photography, not render. No numbers, no readable text, no letters, no logos, no screens.
A calm invitation to explore patterns and quantities for a primary school parenting
article. Not a test diagram, no claims about mathematical sequence. Single image.

Validation: all 12 pages checked for unique titles, one H1, unique element IDs,
valid JSON-LD, resolvable local images/cluster links/anchors, one GA config,
and JavaScript syntax. Verified hint/solution/print/CTA event handlers. Questions
and arithmetic reviewed manually. No backend, prompt or workspace changes.
