# IAKIDS Frontend V2

Frontend חדש ונקי ל-IAKIDS, שנבנה בנפרד מהמערכת הישנה כדי לאפשר מעבר הדרגתי בלי לשבור את המוצר הקיים.

## מה כבר נעשה

- נוצרה תיקייה נפרדת: `/frontend-v2/`
- נבנה Dashboard חדש בעיצוב בהיר בגווני טורקיז/כחול
- התאמה מהיום הראשון ל-Desktop, Tablet ו-Mobile
- חיבור ל-Supabase Auth ול-`active_kid_id`
- טעינת הילד הפעיל, נתוני פרופיל, שיעורים, התקדמות, משימות ונושאים אישיים
- נבנה Workspace חדש לשיעורי בית
- Workspace שיעורי הבית מחובר למנוע הקיים:
  - העלאת תמונה / PDF
  - `homework-uploads`
  - `/api/tutor/homework-analyze`
  - `homework_sessions`
  - `/api/tutor/homework-turn`
  - `/api/tutor/homework-coach`
  - TTS קיים
- נוספו מצבי למידה מרכזיים:
  - למד אותי משהו
  - תרגול
  - משחקי למידה
  - שיעורי בית
  - תכנית הלימודים שלי
  - מה שבחרתי ללמוד
- נוסף מספר גרסה למערכת

## קבצים מרכזיים

```text
frontend-v2/
├── index.html
├── styles.css
├── app.js
├── homework.html
├── homework.css
└── homework.js
```

## כתובת

Production:
`https://iakids.app/frontend-v2/`

Homework:
`https://iakids.app/frontend-v2/homework.html`

Render Preview:
`https://iakids-v2.onrender.com/`

## עיקרון עבודה

לא בונים Backend חדש. ה-V2 הוא Frontend חדש שמשתמש ככל האפשר באותם Supabase tables, APIs, AI tutor, homework engine ו-TTS של המערכת הקיימת.
