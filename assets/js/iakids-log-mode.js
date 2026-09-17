/* =====================================================
   IAKIDS LOG MODE — 17/09/2026

   שתי תצורות:
     test  — כל ההדפסות נכתבות ל-console (פיתוח ובדיקות)
     prod  — שום הדפסה לא נכתבת, חוץ מ-console.error

   למה מתג אחד ולא שני סקריפטים:
   הדפים הם קבצים סטטיים ש-nginx (וב-iakids.app גם GitHub Pages)
   מגיש כמו שהם. הבקאנד לא מייצר אותם ולכן אי אפשר להסיר את
   ההדפסות בצד השרת. שתי גרסאות של אותו קובץ היו מתפצלות תוך
   שבוע, ובניית build step נוגדת את מבנה הפרויקט. לכן מוחלפות
   פונקציות ה-console פעם אחת, לפני כל שאר הסקריפטים.

   איך בוחרים תצורה:
     1. window.IAKIDS_LOG_MODE = "test" לפני טעינת הקובץ (גובר על הכל)
     2. ?log=1 או ?log=0 בכתובת, נשמר לשארית הטאב
     3. localStorage.IAKIDS_LOG = "1" / "0" (נשאר בין ביקורים)
     4. ברירת מחדל: localhost ורשתות פנימיות = test, כל השאר = prod

   לדיבוג על פרוד: להוסיף ?log=1 לכתובת ולרענן,
   או להריץ בקונסולה iakidsLogMode("test") ואז לרענן.

   חשוב: console.error אף פעם לא מושתק, ושגיאות שלא נתפסו
   ממשיכות להופיע כרגיל. המתג לא מסתיר תקלות, רק רעש.
===================================================== */
(function () {

  var W = window;

  if (W.__iakidsLogModeReady) {
    return;
  }

  W.__iakidsLogModeReady = true;

  if (!W.console) {
    W.console = {};
  }

  var C = W.console;

  /* ההדפסות שמושתקות בפרוד. console.error נשאר תמיד. */
  var QUIET = [
    "log", "debug", "info", "warn", "table", "dir", "dirxml",
    "group", "groupCollapsed", "groupEnd",
    "time", "timeEnd", "timeLog", "count", "countReset",
    "trace", "assert", "profile", "profileEnd"
  ];

  /* עותק של הפונקציות המקוריות, כדי שאפשר יהיה להחזיר אותן בזמן ריצה */
  var ORIGINAL = {};

  QUIET.forEach(function (name) {
    ORIGINAL[name] =
      typeof C[name] === "function"
        ? C[name].bind(C)
        : function () {};
  });

  W.__iakidsConsole = ORIGINAL;

  function noop() {}

  function readStore(store, key) {
    try {
      return store ? store.getItem(key) : null;
    } catch (e) {
      /* מצב פרטי או חסימת אחסון: מתעלמים */
      return null;
    }
  }

  function writeStore(store, key, value) {
    try {
      if (store) { store.setItem(key, value); }
    } catch (e) {
      /* אין אחסון, המצב יחזיק רק לעמוד הנוכחי */
    }
  }

  function hostIsLocal() {
    var host = String(W.location && W.location.hostname || "");
    return (
      host === ""
      || host === "localhost"
      || host === "127.0.0.1"
      || host === "::1"
      || /\.local$/.test(host)
      || /^192\.168\./.test(host)
      || /^10\./.test(host)
      || /^172\.(1[6-9]|2[0-9]|3[01])\./.test(host)
    );
  }

  function forcedFromUrl() {
    var search = String(W.location && W.location.search || "");
    var match = /[?&]log=([01])(?:&|$)/.exec(search);
    return match ? match[1] : null;
  }

  function resolveMode() {

    if (W.IAKIDS_LOG_MODE === "test" || W.IAKIDS_LOG_MODE === "prod") {
      return W.IAKIDS_LOG_MODE;
    }

    var forced = forcedFromUrl();

    if (forced) {
      writeStore(W.sessionStorage, "IAKIDS_LOG", forced);
      return forced === "1" ? "test" : "prod";
    }

    var stored =
      readStore(W.sessionStorage, "IAKIDS_LOG")
      || readStore(W.localStorage, "IAKIDS_LOG");

    if (stored === "1") { return "test"; }
    if (stored === "0") { return "prod"; }

    return hostIsLocal() ? "test" : "prod";
  }

  function apply(mode) {

    QUIET.forEach(function (name) {
      C[name] = mode === "test" ? ORIGINAL[name] : noop;
    });

    W.IAKIDS_LOG_MODE = mode;
  }

  /* החלפה בזמן ריצה, בלי לרענן: iakidsLogMode("test") */
  W.iakidsLogMode = function (next) {

    if (next !== "test" && next !== "prod") {
      return W.IAKIDS_LOG_MODE;
    }

    writeStore(W.sessionStorage, "IAKIDS_LOG", next === "test" ? "1" : "0");
    apply(next);

    ORIGINAL.log("IAKIDS LOG MODE:", next);

    return next;
  };

  apply(resolveMode());

  if (W.IAKIDS_LOG_MODE === "test") {
    ORIGINAL.log(
      "IAKIDS LOG MODE: test (prod is silent; use ?log=1 or iakidsLogMode(\"test\"))"
    );
  }

})();
