/* =====================================================
   IAKIDS API — 17/09/2026

   הדלת היחידה של הדפדפן אל הנתונים.

   ההחלטה: ה-UI פונה לבקאנד וכל העבודה שם. אין שאילתה ישירה
   למסד משום דף, סקריפט או משחק. הסיבה היא לא שאפשר להסתיר
   את הקוד, כי אי אפשר. כל עוד דף קורא
   sb.from("kids_profiles"), שם הטבלה, רשימת העמודות והקשרים
   יושבים בכתובת הבקשה ובתשובה, וכל אחד רואה אותם בלשונית
   הרשת. מה שכן אפשר להסתיר זה שכבת הנתונים עצמה, וזה קורה
   ברגע שהדפדפן מפסיק לדבר עם המסד.

   השלב הזה מכסה את kids_profiles: שם הילד, הגיל, המגדר
   והתחומים. המפה המלאה ושאר השלבים ב-MIGRATION_TO_BACKEND.md.

   הרשאה נקבעת בשרת בלבד. מזהה ילד בבקשה לא מוכיח כלום:
   השרת מצליב אותו מול בעל החשבון שבטוקן.
===================================================== */
(function () {

  var W = window;

  if (W.iakidsApi) {
    return;
  }

  function apiBase() {

    if (typeof W.IAKIDS_API_BASE === "string" && W.IAKIDS_API_BASE) {
      return W.IAKIDS_API_BASE;
    }

    /* באותו שרת: nginx מעביר /tutor-api לבקאנד */
    if (String(W.location.hostname || "").endsWith("smarts-brains.online")) {
      return W.location.origin + "/tutor-api";
    }

    return "https://iakids-ai-tutor-he.onrender.com";
  }

  /*
    הטוקן מגיע מהסשן של Supabase Auth. זיהוי הוא לא מסד נתונים,
    וזאת עדיין ספריית האימות של האתר. אם יום אחד גם האימות יעבור
    לבקאנד, רק הפונקציה הזאת תשתנה.
  */
  async function accessToken() {

    var client =
      W.sb
      || W.supabaseClient
      || (W.IAKidsActivity && W.IAKidsActivity._client)
      || null;

    if (!client && W.IAKidsActivity && W.IAKidsActivity._getClient) {
      try {
        client = await W.IAKidsActivity._getClient();
      } catch (e) {
        client = null;
      }
    }

    if (!client || !client.auth) {
      return null;
    }

    try {
      var res = await client.auth.getSession();
      return (res && res.data && res.data.session)
        ? res.data.session.access_token
        : null;
    } catch (e) {
      return null;
    }
  }

  async function request(path, method, body) {

    var token = await accessToken();

    if (!token) {
      throw new Error("not signed in");
    }

    var res = await fetch(apiBase() + path, {
      method: method || "GET",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + token
      },
      body: body ? JSON.stringify(body) : null
    });

    var payload = null;

    try {
      payload = await res.json();
    } catch (e) {
      payload = null;
    }

    if (!res.ok) {
      var err = new Error(
        (payload && (payload.detail || payload.message)) || ("HTTP " + res.status)
      );
      err.status = res.status;
      throw err;
    }

    return payload;
  }

  W.iakidsApi = {

    /* כל הילדים של החשבון המחובר, לפי סדר יצירה */
    async listKids() {
      var j = await request("/api/kid/list");
      return (j && j.kids) || [];
    },

    /* ילד אחד. 404 אם הוא לא של החשבון הזה. */
    async getKid(kidId) {
      if (!kidId) { return null; }
      var j = await request("/api/kid/" + encodeURIComponent(kidId));
      return (j && j.kid) || null;
    },

    /* עדכון חלקי: שדה שלא נשלח לא נוגעים בו */
    async updateKid(kidId, fields) {
      var body = Object.assign({ kid_id: kidId }, fields || {});
      var j = await request("/api/kid/update", "POST", body);
      return (j && j.kid) || null;
    },

    async createKid(fields) {
      var j = await request("/api/kid/create", "POST", fields || {});
      return (j && j.kid) || null;
    },

    /*
      הילד הפעיל: מה שנשמר ב-localStorage, ואם אין, הראשון של החשבון.
      מחזיר null בלי לזרוק, כי חלק מהדפים נטענים גם בלי ילד.
    */
    async activeKid() {
      try {

        var stored = null;
        try { stored = localStorage.getItem("active_kid_id"); } catch (e) { stored = null; }

        if (stored) {
          try {
            var kid = await this.getKid(stored);
            if (kid) { return kid; }
          } catch (e) {
            /* מזהה ישן או ילד שנמחק: ממשיכים לרשימה */
          }
        }

        var kids = await this.listKids();

        if (!kids.length) { return null; }

        try { localStorage.setItem("active_kid_id", kids[0].id); } catch (e) {}

        return kids[0];

      } catch (e) {
        console.warn("IAKIDS API activeKid failed:", e);
        return null;
      }
    }

  };

})();
