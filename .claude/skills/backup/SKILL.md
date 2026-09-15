---
name: backup
description: Snapshot main.py (backend/ and backend-ai-tutor-he/) plus every prompt file (root iakids_*_prompt.txt, backend/prompts, backend-ai-tutor-he/prompts) into the next V<N>_BACKUP folder. Use whenever the user asks for a backup (גיבוי / backup) of main or the prompts.
---

# backup — main.py + prompts snapshot

Run from the repo root:

```bash
bash .claude/skills/backup/backup.sh "optional note, e.g. before prompt rewrite"
```

The script:
1. Finds the highest existing `V<N>_BACKUP` and creates `V<N+1>_BACKUP`.
2. Copies (timestamps preserved) `backend/main.py`, `backend-ai-tutor-he/main.py`,
   root `iakids_*_prompt.txt`, `backend/prompts/*.txt`, `backend-ai-tutor-he/prompts/*.txt`.
3. Verifies every copy is byte-identical (`diff`) and fails loudly otherwise.
4. Writes `README.md` inside the folder with date, git HEAD, note and file count.

Then report to the user: folder name, file count, and that it was verified.
Do **not** commit or push — the user decides ([[no-commit-without-approval]]).
If the user asks for "רק פרומפטים" or "רק main", still run the script (it's cheap) and say what it contains.
