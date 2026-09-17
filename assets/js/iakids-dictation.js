/* =====================================================
   IAKIDS DICTATION (2026-09-17)

   מיקרופון בכל תיבת צ'אט: הילד מדבר והמילים מופיעות בתיבה במקום להקליד.

   ברירת המחדל היא זיהוי הדיבור המובנה בדפדפן (Web Speech API):
   בלי מודל, בלי עלות, עם טקסט שמופיע תוך כדי הדיבור.
   רק אם הדפדפן לא תומך (Firefox, WebView ישן) וגם הופעל
   window.IAKIDS_STT_SERVER_FALLBACK = true, נשלחת הקלטה ל-/api/tutor/stt.

   שימוש:
     <script src="/assets/js/iakids-dictation.js"></script>
     IAKidsDictation.autoAttach();                       // מזהה את תיבות הצ'אט המוכרות
     IAKidsDictation.attach({ input, button, onFinal }); // חיבור ידני

   הרכיב עוצר אודיו שמתנגן (המורה) לפני ההקלטה, כדי לא להקליט את הרמקול.
   ===================================================== */
(function () {
  "use strict";
  if (window.IAKidsDictation) { return; }

  var SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  var SILENCE_MS = 2500;      /* שקט אחרי דיבור -> סיום אוטומטי */
  var MAX_MS = 60000;         /* תקרה קשיחה */
  var STYLE_ID = "iakids-dictation-style";

  function injectStyle() {
    if (document.getElementById(STYLE_ID)) { return; }
    var css = document.createElement("style");
    css.id = STYLE_ID;
    css.textContent =
      ".iakids-mic-listening{position:relative;color:#fff !important;background:#e5484d !important;border-color:#e5484d !important}" +
      ".iakids-mic-listening::after{content:'';position:absolute;inset:-6px;border-radius:inherit;border:2px solid rgba(229,72,77,.55);animation:iakidsMicPulse 1.1s ease-out infinite;pointer-events:none}" +
      "@keyframes iakidsMicPulse{0%{transform:scale(.92);opacity:.9}100%{transform:scale(1.25);opacity:0}}" +
      ".iakids-mic-busy{opacity:.6;cursor:progress}" +
      ".iakids-dictation-hint{position:absolute;bottom:100%;inset-inline-start:0;margin-bottom:6px;background:rgba(17,22,30,.92);color:#fff;font:12px/1.4 system-ui,Arial,sans-serif;padding:6px 10px;border-radius:8px;max-width:min(320px,80vw);z-index:99999;pointer-events:none;direction:rtl}" +
      ".iakids-mic-unsupported{display:none !important}";
    document.head.appendChild(css);
  }

  function hint(anchor, text, ms) {
    try {
      var host = anchor && anchor.parentElement;
      if (!host) { return; }
      if (getComputedStyle(host).position === "static") { host.style.position = "relative"; }
      var old = host.querySelector(".iakids-dictation-hint");
      if (old) { old.remove(); }
      var el = document.createElement("div");
      el.className = "iakids-dictation-hint";
      el.textContent = text;
      host.appendChild(el);
      setTimeout(function () { if (el.parentNode) { el.remove(); } }, ms || 3200);
    } catch (e) { /* הודעה היא נחמדות, לא תנאי */ }
  }

  function pausePlayingAudio() {
    /* לא מקליטים את המורה: עוצרים כל אודיו/וידאו שמתנגן */
    var stopped = [];
    try {
      document.querySelectorAll("audio, video").forEach(function (el) {
        if (!el.paused && !el.muted) { el.pause(); stopped.push(el); }
      });
    } catch (e) { /* ignore */ }
    return stopped;
  }

  function setValue(input, text) {
    if (!input) { return; }
    if (input.isContentEditable) { input.textContent = text; }
    else { input.value = text; }
    try { input.dispatchEvent(new Event("input", { bubbles: true })); } catch (e) { /* ignore */ }
  }

  function getValue(input) {
    if (!input) { return ""; }
    return input.isContentEditable ? (input.textContent || "") : (input.value || "");
  }

  /* ---------------- fallback: הקלטה ושליחה לשרת (כבוי כברירת מחדל) ------------- */
  function serverFallbackEnabled() {
    return window.IAKIDS_STT_SERVER_FALLBACK === true;
  }

  async function recordAndTranscribe(state) {
    var base = window.TUTOR_API_BASE ||
      (location.hostname.endsWith("smarts-brains.online") ? location.origin + "/tutor-api"
        : "https://iakids-ai-tutor-he.onrender.com");
    var stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    var rec = new MediaRecorder(stream);
    var chunks = [];
    rec.ondataavailable = function (e) { if (e.data && e.data.size) { chunks.push(e.data); } };
    var done = new Promise(function (resolve) { rec.onstop = resolve; });
    state.stopServer = function () { try { rec.stop(); } catch (e) { /* ignore */ } };
    rec.start();
    setTimeout(function () { if (rec.state === "recording") { rec.stop(); } }, MAX_MS);
    await done;
    stream.getTracks().forEach(function (t) { t.stop(); });
    var blob = new Blob(chunks, { type: rec.mimeType || "audio/webm" });
    var b64 = await new Promise(function (resolve) {
      var fr = new FileReader();
      fr.onloadend = function () { resolve(String(fr.result).split(",")[1] || ""); };
      fr.readAsDataURL(blob);
    });
    var session = null;
    try { session = (await window.sb.auth.getSession()).data.session; } catch (e) { /* ignore */ }
    if (!session) { throw new Error("no session"); }
    var r = await fetch(base + "/api/tutor/stt", {
      method: "POST",
      headers: { "Content-Type": "application/json", "Authorization": "Bearer " + session.access_token },
      body: JSON.stringify({ audio_base64: b64, mime_type: blob.type || "audio/webm" })
    });
    var j = await r.json();
    if (!r.ok) { throw new Error(j.detail || ("HTTP " + r.status)); }
    return String(j.text || "");
  }

  /* ---------------------------------- attach ---------------------------------- */
  function attach(options) {
    var opts = options || {};
    var input = typeof opts.input === "string" ? document.querySelector(opts.input) : opts.input;
    var button = typeof opts.button === "string" ? document.querySelector(opts.button) : opts.button;
    if (!input || !button || button.dataset.iakidsDictation === "1") { return null; }
    injectStyle();
    button.dataset.iakidsDictation = "1";
    button.type = button.type || "button";

    if (!SR && !serverFallbackEnabled()) {
      button.classList.add("iakids-mic-unsupported");     /* אין תמיכה: מסתירים במקום להטעות */
      console.log("IAKIDS DICTATION: browser has no speech recognition, mic hidden");
      return null;
    }

    var state = { listening: false, rec: null, silenceTimer: null, hardTimer: null, base: "", stopServer: null };
    var lang = opts.lang || "he-IL";

    function ui(on, busy) {
      button.classList.toggle("iakids-mic-listening", Boolean(on));
      button.classList.toggle("iakids-mic-busy", Boolean(busy));
      button.setAttribute("aria-pressed", on ? "true" : "false");
      button.title = on ? "מקליט… לחצו לסיום" : (busy ? "מתמלל…" : (opts.title || "דברו במקום להקליד"));
    }

    function stop() {
      clearTimeout(state.silenceTimer); clearTimeout(state.hardTimer);
      state.silenceTimer = state.hardTimer = null;
      if (state.rec) { try { state.rec.stop(); } catch (e) { /* ignore */ } }
      if (state.stopServer) { state.stopServer(); state.stopServer = null; }
      state.listening = false;
      ui(false, false);
    }

    function finish(text) {
      var value = String(text || "").trim();
      setValue(input, value);
      try { input.focus(); } catch (e) { /* ignore */ }
      if (value && typeof opts.onFinal === "function") { opts.onFinal(value); }
      console.log("IAKIDS DICTATION RESULT:", { chars: value.length });
    }

    async function start() {
      pausePlayingAudio();
      state.base = getValue(input).trim();
      state.listening = true;
      ui(true, false);

      if (!SR) {                                   /* מסלול שרת, רק אם הופעל במפורש */
        ui(false, true);
        try {
          var text = await recordAndTranscribe(state);
          finish((state.base ? state.base + " " : "") + text);
        } catch (e) {
          console.warn("IAKIDS DICTATION SERVER FALLBACK FAILED:", e);
          hint(button, "לא הצלחנו לשמוע. אפשר לכתוב בינתיים.");
        }
        state.listening = false; ui(false, false);
        return;
      }

      var rec = new SR();
      state.rec = rec;
      rec.lang = lang;
      rec.continuous = true;                      /* לילד מותר לעצור באמצע משפט */
      rec.interimResults = true;
      rec.maxAlternatives = 1;

      var finalText = "";
      rec.onresult = function (event) {
        var interim = "";
        for (var i = event.resultIndex; i < event.results.length; i++) {
          var res = event.results[i];
          if (res.isFinal) { finalText += res[0].transcript; }
          else { interim += res[0].transcript; }
        }
        var shown = (state.base ? state.base + " " : "") + (finalText + interim).trim();
        setValue(input, shown);                   /* הכיתוב מופיע תוך כדי הדיבור */
        clearTimeout(state.silenceTimer);
        state.silenceTimer = setTimeout(stop, SILENCE_MS);
      };
      rec.onerror = function (event) {
        console.warn("IAKIDS DICTATION ERROR:", event.error);
        if (event.error === "not-allowed" || event.error === "service-not-allowed") {
          hint(button, "צריך לאשר לדפדפן להשתמש במיקרופון כדי לדבר.", 5000);
        } else if (event.error === "no-speech") {
          hint(button, "לא שמעתי כלום. לוחצים על המיקרופון ומדברים.");
        } else if (event.error !== "aborted") {
          hint(button, "לא הצלחנו לשמוע. אפשר לכתוב בינתיים.");
        }
      };
      rec.onend = function () {
        clearTimeout(state.silenceTimer); clearTimeout(state.hardTimer);
        state.listening = false; state.rec = null;
        ui(false, false);
        finish((state.base ? state.base + " " : "") + finalText.trim());
      };

      try { rec.start(); } catch (e) {
        console.warn("IAKIDS DICTATION START FAILED:", e);
        state.listening = false; ui(false, false); return;
      }
      state.hardTimer = setTimeout(stop, MAX_MS);
      console.log("IAKIDS DICTATION: listening", { lang: lang });
    }

    button.addEventListener("click", function (e) {
      e.preventDefault();
      if (state.listening) { stop(); } else { start(); }
    });

    return { start: start, stop: stop, isListening: function () { return state.listening; } };
  }

  /* ------------------------------- auto attach -------------------------------- */
  function injectMic(afterEl, title) {
    var b = document.createElement("button");
    b.type = "button";
    b.className = "iakids-mic-btn";
    b.title = title || "דברו במקום להקליד";
    b.setAttribute("aria-label", b.title);
    b.innerHTML = '<i class="fa-solid fa-microphone"></i>';
    if (!b.querySelector("i")) { b.textContent = "🎤"; }
    b.style.cssText = "border:1px solid rgba(120,140,180,.35);background:transparent;color:inherit;border-radius:10px;" +
      "min-width:38px;height:38px;cursor:pointer;font-size:16px;display:inline-flex;align-items:center;justify-content:center";
    afterEl.insertAdjacentElement("afterend", b);
    return b;
  }

  function autoAttach() {
    var pairs = [];
    /* 1. זוגות מסומנים בדף: <button data-dictation-for="#chatInput"> */
    document.querySelectorAll("[data-dictation-for]").forEach(function (btn) {
      var input = document.querySelector(btn.getAttribute("data-dictation-for"));
      if (input) { pairs.push({ input: input, button: btn }); }
    });
    /* 2. ה-workspace: כפתור הדיבור שכבר קיים במסך */
    document.querySelectorAll(".composer-wrap .talk-btn, .talk-btn").forEach(function (btn) {
      var wrap = btn.closest(".composer-wrap") || btn.closest(".input") || document;
      var input = wrap.querySelector(".input input, input[type='text'], input:not([type])");
      if (input) { pairs.push({ input: input, button: btn }); }
    });
    /* 3. טפסי צ'אט אחרים: מזריקים מיקרופון ליד תיבת הטקסט */
    document.querySelectorAll("#chatForm #chatInput, form.composer #chatInput, #chatInput").forEach(function (input) {
      if (input.closest("form") && input.closest("form").querySelector(".iakids-mic-btn, .talk-btn, [data-dictation-for]")) { return; }
      pairs.push({ input: input, button: injectMic(input) });
    });
    var n = 0;
    pairs.forEach(function (p) { if (attach(p)) { n++; } });
    console.log("IAKIDS DICTATION: attached to", n, "chat box(es)", SR ? "(browser speech recognition)" : "(server fallback)");
    return n;
  }

  window.IAKidsDictation = {
    supported: Boolean(SR),
    attach: attach,
    autoAttach: autoAttach,
    version: 1
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () { autoAttach(); });
  } else {
    autoAttach();
  }
})();
