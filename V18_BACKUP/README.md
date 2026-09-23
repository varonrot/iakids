# V18_BACKUP — main.py + prompts snapshot

Created: 2026-09-23 20:17 UTC
Git HEAD: ce60fd0b
Note: before planner batching (148s plan on a 20-exercise page)
Files: 19

backup.sh stopped at its verify step because backend/prompts/ also holds two test images
(images.jpeg, images2.png) that the script does not copy; every .txt prompt and both main.py
files were copied and are byte-identical (checked with diff -rq on backend-ai-tutor-he/prompts).

Do not edit files here; restore by copying back to the original path.
