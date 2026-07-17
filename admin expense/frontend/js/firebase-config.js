window.firebaseConfigReady = (async function loadFirebaseConfig() {
  try {
    const res = await fetch("/api/firebase-config");
    if (!res.ok) throw new Error(`Config endpoint returned ${res.status}`);
    const data = await res.json();
    firebase.initializeApp(data.firebaseConfig);
    window.ADMIN_EMAILS = data.adminEmails || [];
    window.BACKEND_CONFIG = data.backendConfig || { BACKEND_URL: "", APP_NAME: "expense_agent" };
  } catch (err) {
    console.error("[firebase-config] Failed to load config from backend:", err);
    document.body.insertAdjacentHTML(
      "afterbegin",
      `<div style="background:#ff4444;color:#fff;padding:12px;text-align:center;font-family:sans-serif;z-index:99999;position:fixed;top:0;left:0;right:0;">
        ⚠️ Could not load Firebase config from backend. Make sure the server is running and .env is configured.
      </div>`
    );
    throw err;
  }
})();
