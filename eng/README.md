# IAKIDS English App

This directory is the clean English-only frontend for IAKIDS.

## Isolation rules

- English UI only.
- Do not edit or depend on `/he/` frontend files.
- Do not change the current Hebrew production routes.
- Reuse shared backend/Supabase APIs only where intentional.
- No TTS dependency in the initial English product.
- Homework Help may use chat.
- My Learning System is visual/interactive by default, not chat-first.
- Practice is question/answer UI, not chat-first.
- Test Prep is structured prep with optional AI Coach help.

## Planned structure

```text
eng/
├── index.html
├── assets/
├── css/
├── js/
├── homework/
├── test-prep/
├── learning/
├── practice/
└── progress/
```

Deployment should use the dedicated `english-app` branch so work here cannot affect `main` until intentionally merged.
