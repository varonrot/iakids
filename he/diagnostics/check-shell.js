/*
  בדיקות ומעקב: the shared shell every check plugs into (2026-09-24).

  Built from the research in the diagnostics plan: a parent screen first, a spoken intro for the
  child, no clock / score / right-wrong shown to the child, a progress path that counts items, a
  stopping rule, an end screen that praises effort only, and a parent report that is not a diagnosis.

  Storage: results stay on this device (localStorage) until the privacy review of storing children's
  results on the server is done. The parent can delete them from the report.
*/
(function(){
  "use strict";

  var NOT_DIAGNOSIS = "זו בדיקה קצרה בבית, לא אבחון. היא עוזרת לבחור מה לתרגל. " +
    "לשאלות על התקדמות בקריאה או בלמידה כדאי לפנות למחנכת.";
  var STORE_KEY = "iakids_checks_v1";

  function esc(v){
    return String(v == null ? "" : v).replace(/[&<>"']/g, function(c){
      return {"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c];
    });
  }

  // The profile stores the grade as 1–6; the checks work in letters.
  function gradeLetter(g){
    var n = parseInt(g, 10);
    if (n >= 1 && n <= 6) return "אבגדהו".charAt(n - 1);
    return String(g || "").replace(/[^אבגדהו]/g, "").charAt(0);
  }

  // The child's id when the page runs inside the workspace frame; otherwise a local label.
  function currentKid(){
    try {
      var p = window.parent && window.parent !== window ? window.parent : null;
      var b = p && p.IAKIDS_CHECK_BRIDGE;   // the workspace's CURRENT_KID is a let: only the bridge can reach it
      var k = p && ((b && b.kid && b.kid()) || p.CURRENT_KID || p.SELECTED_KID || p.currentKid);
      if (k && k.id) return {id: String(k.id), name: String(k.child_name || k.name || ""), grade: gradeLetter(k.grade)};
    } catch (e) {}
    return {id: "local", name: "", grade: ""};
  }

  // Our API (never the database). Inside the workspace frame the parent page holds the signed-in
  // session; the child must be the parent's own (the server checks it). Only the check routes.
  var API_PATHS = ["/api/tutor/checks/", "/api/tutor/exam-practice"];
  function apiBase(){
    return location.hostname.endsWith("smarts-brains.online") ? location.origin + "/tutor-api" : "https://iakids-ai-tutor-he.onrender.com";
  }
  function authToken(){
    try {
      var p = window.parent && window.parent !== window ? window.parent : window;
      if (p.IAKIDS_CHECK_BRIDGE && p.IAKIDS_CHECK_BRIDGE.session){
        return p.IAKIDS_CHECK_BRIDGE.session().then(function(r){ return (r && r.data && r.data.session && r.data.session.access_token) || null; });
      }
      var client = p.sb || p.supabaseClient;
      if (!client || !client.auth) return Promise.resolve(null);
      return client.auth.getSession().then(function(r){ return (r && r.data && r.data.session && r.data.session.access_token) || null; });
    } catch (e) { return Promise.resolve(null); }
  }
  function api(path, body){
    if (!API_PATHS.some(function(p){ return path.indexOf(p) === 0; })) return Promise.reject(new Error("not a check route"));
    return authToken().then(function(token){
      if (!token) throw new Error("signed-out");
      var opts = {headers: {Authorization: "Bearer " + token}};
      if (body){ opts.method = "POST"; opts.headers["Content-Type"] = "application/json"; opts.body = JSON.stringify(body); }
      return fetch(apiBase() + path, opts).then(function(r){ if (!r.ok) throw new Error("api " + r.status); return r.json(); });
    });
  }
  function signedOut(root){
    root.innerHTML = "<section class='ck-card ck-parent'><h1>צריך להיכנס מתוך סביבת הלמידה</h1>" +
      "<p class='ck-note'>הבדיקה הזו פועלת כשפותחים אותה מהתפריט \"בדיקות ומעקב\" בתוך סביבת הלמידה, עם הילד שנבחר.</p></section>";
  }

  function readAll(){ try { return JSON.parse(localStorage.getItem(STORE_KEY) || "{}"); } catch (e) { return {}; } }
  function writeAll(all){ try { localStorage.setItem(STORE_KEY, JSON.stringify(all)); return true; } catch (e) { return false; } }

  var store = {
    save: function(kidId, checkId, result){
      var all = readAll(); all[kidId] = all[kidId] || {}; all[kidId][checkId] = all[kidId][checkId] || [];
      all[kidId][checkId].push(result); writeAll(all);
    },
    list: function(kidId, checkId){ var all = readAll(); return ((all[kidId] || {})[checkId] || []).slice(); },
    removeAll: function(kidId){ var all = readAll(); delete all[kidId]; writeAll(all); },
    kids: function(){ return Object.keys(readAll()); }
  };

  // Spoken instructions in the browser's Hebrew voice when there is one; the text is always on screen too.
  function speak(text){
    try {
      if (!window.speechSynthesis) return;
      window.speechSynthesis.cancel();
      var u = new SpeechSynthesisUtterance(String(text || ""));
      u.lang = "he-IL"; u.rate = 0.95;
      window.speechSynthesis.speak(u);
    } catch (e) {}
  }

  // A soft sound that tells the PARENT the time is up; nothing about time is shown to the child.
  function chime(){
    try {
      var C = window.AudioContext || window.webkitAudioContext; if (!C) return;
      var ctx = new C(), o = ctx.createOscillator(), g = ctx.createGain();
      o.frequency.value = 660; g.gain.value = 0.08; o.connect(g); g.connect(ctx.destination);
      o.start(); o.stop(ctx.currentTime + 0.35);
    } catch (e) {}
  }

  // Stop a strand after 3 misses in a row, or 4 of the last 5 (research: basal/ceiling practice).
  function shouldStop(outcomes){
    var n = outcomes.length;
    if (n >= 3 && !outcomes[n - 1] && !outcomes[n - 2] && !outcomes[n - 3]) return true;
    if (n >= 5){ var misses = outcomes.slice(-5).filter(function(x){ return !x; }).length; if (misses >= 4) return true; }
    return false;
  }

  // Trend only after 3 complete runs: the median of the last 3 against the median of the 3 before,
  // and a change smaller than `stableBand` is "יציב", never a drop.
  function trend(values, stableBand){
    var v = values.filter(function(x){ return typeof x === "number" && isFinite(x); });
    if (v.length < 3) return {state: "start", label: "נקודת פתיחה", n: v.length};
    function med(a){ var s = a.slice().sort(function(x, y){ return x - y; }); return s[Math.floor(s.length / 2)]; }
    var last = med(v.slice(-3));
    if (v.length < 6) return {state: "baseline", label: "יש כבר תמונה ראשונה", value: last, n: v.length};
    var prev = med(v.slice(-6, -3)), d = last - prev;
    if (Math.abs(d) < (stableBand || 0)) return {state: "stable", label: "יציב", value: last, n: v.length};
    return {state: d > 0 ? "up" : "down", label: d > 0 ? "בשיפור" : "כדאי לחזק", value: last, delta: d, n: v.length};
  }

  function addWeeks(date, weeks){ var d = new Date(date); d.setDate(d.getDate() + weeks * 7); return d; }
  function heDate(d){ try { return new Date(d).toLocaleDateString("he-IL"); } catch (e) { return ""; } }

  function progressPath(el, total, done){
    var html = "";
    for (var i = 0; i < total; i++) html += "<i class='ck-dot" + (i < done ? " on" : "") + "'></i>";
    el.innerHTML = html;
  }

  // Screens -----------------------------------------------------------------------------------

  function parentGate(root, opts){
    root.innerHTML =
      "<section class='ck-card ck-parent'>" +
        "<div class='ck-tag'>להורה</div>" +
        "<h1>" + esc(opts.title) + "</h1>" +
        "<ul class='ck-facts'>" +
          "<li><b>מה בודקים:</b> " + esc(opts.what) + "</li>" +
          "<li><b>כמה זמן:</b> " + esc(opts.minutes) + "</li>" +
          "<li><b>מה תקבלו:</b> " + esc(opts.get) + "</li>" +
          "<li><b>מה זה לא:</b> " + esc(NOT_DIAGNOSIS) + "</li>" +
          (opts.needsMic ? "<li><b>מיקרופון:</b> נדרש.</li>" : "<li><b>מיקרופון:</b> לא נדרש. אתם מקשיבים ומסמנים.</li>") +
        "</ul>" +
        (opts.extraHtml || "") +
        "<p class='ck-note'>כדאי לשבת יחד בחדר שקט. אפשר לעצור בכל רגע.</p>" +
        "<button class='ck-btn ck-primary' type='button' data-go>מתחילים</button>" +
      "</section>";
    root.querySelector("[data-go]").addEventListener("click", function(){ opts.onStart && opts.onStart(root); });
  }

  // The same teacher the child meets in the lessons (a photo-real image we own), never an icon.
  function teacher(){ return "<img class='ck-teacher' src='/assets/diagnostics/teacher.webp' alt='המורה' width='112' height='112'>"; }
  // Waiting on the server: the teacher, what she is doing, and moving dots so the child sees it is working.
  function busy(root, text){
    root.innerHTML = "<section class='ck-card ck-child ck-busy'>" + teacher() + "<p class='ck-say'>" + esc(text) +
      "</p><div class='ck-dots' aria-label='טוען'><span></span><span></span><span></span></div></section>";
  }

  function childIntro(root, text, onNext){
    root.innerHTML =
      "<section class='ck-card ck-child'>" +
        teacher() +
        "<p class='ck-say'>" + esc(text) + "</p>" +
        "<div class='ck-row'><button class='ck-btn' type='button' data-replay>🔊 שוב</button>" +
        "<button class='ck-btn ck-primary' type='button' data-next>מוכנים</button></div>" +
      "</section>";
    speak(text);
    root.querySelector("[data-replay]").addEventListener("click", function(){ speak(text); });
    root.querySelector("[data-next]").addEventListener("click", function(){ try { speechSynthesis.cancel(); } catch (e) {} onNext(); });
  }

  // Effort only: no score, no percent, no time, no comparison. The same for every child who finishes.
  function childEnd(root, opts){
    var line = opts.effortLine || "עבדת יפה עד הסוף!";
    root.innerHTML =
      "<section class='ck-card ck-child ck-end'>" +
        "<img class='ck-star' src='/assets/diagnostics/done.webp' alt='' width='640' height='400'>" +
        "<h1>" + esc(line) + "</h1>" +
        (opts.strategyLine ? "<p class='ck-say'>" + esc(opts.strategyLine) + "</p>" : "") +
        "<div class='ck-row'>" +
          (opts.practiceHref ? "<a class='ck-btn ck-primary' href='" + esc(opts.practiceHref) + "' target='_top'>בואו נתרגל</a>" : "") +
          "<button class='ck-btn' type='button' data-done>סיימתי להיום</button>" +
        "</div>" +
        "<button class='ck-link' type='button' data-report>לדוח להורה</button>" +
      "</section>";
    speak(line);
    root.querySelector("[data-done]").addEventListener("click", function(){ opts.onDone && opts.onDone(); });
    root.querySelector("[data-report]").addEventListener("click", function(){ opts.onReport && opts.onReport(); });
  }

  // The parent report: what & when, strengths, what to strengthen, practice, next date, details
  // (folded), trend (3+ runs), the not-a-diagnosis line, and delete.
  function parentReport(root, r){
    var trendHtml = r.trend && r.trend.state !== "start"
      ? "<p><b>מעקב:</b> " + esc(r.trend.label) + (r.trend.n ? " (" + r.trend.n + " בדיקות)" : "") + "</p>"
      : "<p><b>מעקב:</b> נקודת פתיחה. מגמה מוצגת רק אחרי 3 בדיקות.</p>";
    root.innerHTML =
      "<section class='ck-card ck-parent ck-report'>" +
        "<div class='ck-tag'>דוח להורה</div>" +
        "<h1>" + esc(r.title) + "</h1>" +
        "<p class='ck-note'>" + esc(r.when) + "</p>" +
        (r.partial ? "<p class='ck-warn'>הבדיקה לא הושלמה, ולכן היא לא נכנסת למעקב.</p>" : "") +
        "<h2>מה הולך טוב</h2><ul>" + (r.strengths || []).map(function(x){ return "<li>" + esc(x) + "</li>"; }).join("") + "</ul>" +
        "<h2>מה כדאי לחזק</h2><ul>" + (r.toStrengthen || []).map(function(x){ return "<li>" + esc(x) + "</li>"; }).join("") + "</ul>" +
        "<h2>איך מתרגלים</h2><div class='ck-row'>" + (r.practice || []).map(function(p){
          return "<a class='ck-btn' href='" + esc(p.href) + "' target='_top'>" + esc(p.label) + "</a>"; }).join("") + "</div>" +
        "<p><b>בדיקה חוזרת מומלצת:</b> " + esc(r.nextCheck) + "</p>" +
        trendHtml +
        (r.escalate ? "<p class='ck-warn'>" + esc(r.escalate) + "</p>" : "") +
        "<details><summary>פרטים ומספרים</summary>" + (r.detailsHtml || "") + "</details>" +
        "<p class='ck-not-dx'>" + esc(NOT_DIAGNOSIS) + "</p>" +
        "<div class='ck-row'>" +
          "<button class='ck-btn' type='button' data-again>בדיקה נוספת</button>" +
          "<button class='ck-link' type='button' data-delete>מחיקת כל התוצאות של הילד מהמכשיר</button>" +
        "</div>" +
        "<p class='ck-note'>התוצאות נשמרות רק במכשיר הזה. לא נשמרת הקלטה.</p>" +
      "</section>";
    root.querySelector("[data-again]").addEventListener("click", function(){ r.onAgain && r.onAgain(); });
    root.querySelector("[data-delete]").addEventListener("click", function(){
      if (confirm("למחוק את כל תוצאות הבדיקות של הילד מהמכשיר הזה?")){ store.removeAll(r.kidId); r.onDeleted && r.onDeleted(); }
    });
  }

  window.IAKidsCheck = {
    teacher: teacher, busy: busy,
    gradeLetter: gradeLetter,
    api: api, signedOut: signedOut,
    NOT_DIAGNOSIS: NOT_DIAGNOSIS, esc: esc, currentKid: currentKid, store: store, speak: speak, chime: chime,
    shouldStop: shouldStop, trend: trend, addWeeks: addWeeks, heDate: heDate, progressPath: progressPath,
    parentGate: parentGate, childIntro: childIntro, childEnd: childEnd, parentReport: parentReport
  };
})();
