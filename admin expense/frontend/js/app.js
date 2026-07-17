(async function () {
  await window.firebaseConfigReady;
  const CURRENCIES = [
    { code: "USD", symbol: "$", flag: "🇺🇸" },
    { code: "EUR", symbol: "€", flag: "🇪🇺" },
    { code: "GBP", symbol: "£", flag: "🇬🇧" },
    { code: "INR", symbol: "₹", flag: "🇮🇳" },
    { code: "JPY", symbol: "¥", flag: "🇯🇵" },
    { code: "CAD", symbol: "CA$", flag: "🇨🇦" },
    { code: "AUD", symbol: "A$", flag: "🇦🇺" },
    { code: "CHF", symbol: "Fr", flag: "🇨🇭" },
    { code: "CNY", symbol: "¥", flag: "🇨🇳" },
    { code: "SGD", symbol: "S$", flag: "🇸🇬" },
    { code: "AED", symbol: "AED", flag: "🇦🇪" },
    { code: "BRL", symbol: "R$", flag: "🇧🇷" },
  ];
  let selectedCurrency = localStorage.getItem("ll_currency") || "USD";
  let currentUser = null;
  let sessionId = null;
  let sessionReady = false;
  let ledger = [];

  const db = firebase.firestore();

  function toast(msg, kind) {
    const el = document.createElement("div");
    el.className = "toast" + (kind ? ` toast--${kind}` : "");
    el.textContent = msg;
    document.getElementById("toastStack").appendChild(el);
    setTimeout(() => el.remove(), 4500);
  }

  const currencyTrigger = document.getElementById("currencyTrigger");
  const currencyMenu = document.getElementById("currencyMenu");

  function renderCurrencyMenu() {
    currencyMenu.innerHTML = "";
    CURRENCIES.forEach((c) => {
      const opt = document.createElement("div");
      opt.className =
        "currency-option" + (c.code === selectedCurrency ? " is-selected" : "");
      opt.innerHTML = `<span>${c.flag}</span><span class="cc">${c.code}</span><span>${c.symbol}</span>`;
      opt.addEventListener("click", () => {
        selectedCurrency = c.code;
        localStorage.setItem("ll_currency", c.code);
        syncCurrency();
        currencyMenu.hidden = true;
      });
      currencyMenu.appendChild(opt);
    });
  }
  function syncCurrency() {
    const c =
      CURRENCIES.find((x) => x.code === selectedCurrency) || CURRENCIES[0];
    document.getElementById("currencyFlag").textContent = c.flag;
    document.getElementById("currencyCode").textContent = c.code;
    document.getElementById("composerCurrencyHint").textContent = c.code;
    renderCurrencyMenu();
  }
  currencyTrigger.addEventListener("click", (e) => {
    e.stopPropagation();
    currencyMenu.hidden = !currencyMenu.hidden;
  });
  document.addEventListener("click", () => {
    currencyMenu.hidden = true;
  });
  syncCurrency();

  const STEP_WIDTHS = [6, 27, 50, 73, 94];
  function setPipeline(step, opts) {
    opts = opts || {};
    document.querySelectorAll("#appPipeline .pipeline-node").forEach((n, i) => {
      n.classList.toggle("is-done", i < step);
      n.classList.toggle("is-active", i === step && !opts.complete);
      n.classList.toggle("is-flag", opts.flagStep === i);
    });
    document.getElementById("appPipelineFill").style.width =
      (opts.complete ? 100 : STEP_WIDTHS[step] || 6) + "%";
  }
  function resetPipeline() {
    setPipeline(0);
  }

  async function animatePipeline(promise) {
    let step = 0;
    setPipeline(0);
    const tick = setInterval(() => {
      step = Math.min(step + 1, 3);
      setPipeline(step);
    }, 650);
    try {
      const r = await promise;
      clearInterval(tick);
      setPipeline(4, { complete: true });
      return r;
    } catch (e) {
      clearInterval(tick);
      throw e;
    }
  }

  function chipFor(status) {
    const map = {
      pending: ["chip--pending", "Pending"],
      auto: ["chip--auto", "Approved"],
      review: ["chip--review", "Awaiting review"],
      flagged: ["chip--flagged", "Rejected"],
    };
    const [cls, label] = map[status] || map.pending;
    return `<span class="chip ${cls}">${label}</span>`;
  }
  function addLedgerEntry(entry) {
    ledger.unshift(entry);
    document.getElementById("ledgerEmpty").hidden = true;
    document.getElementById("ledgerCount").textContent = ledger.length;
    renderLedger();
  }
  function updateLedgerEntry(id, patch) {
    const item = ledger.find((e) => e.id === id);
    if (item) Object.assign(item, patch);
    renderLedger();
  }
  function renderLedger() {
    document.querySelectorAll(".ledger-item").forEach((n) => n.remove());
    ledger.forEach((entry) => {
      const el = document.createElement("div");
      el.className = "ledger-item";
      el.innerHTML = `
        <div class="ledger-item-top">
          <span class="ledger-amount">${entry.amountLabel || "—"}</span>
          ${chipFor(entry.status)}
        </div>
        <div class="ledger-item-desc">${esc(entry.text)}</div>`;
      document.getElementById("ledgerList").appendChild(el);
    });
  }

  async function writePendingExpense(data) {
    try {
      const isAutoApproved = data.status === "auto_approved";
      const ref = await db.collection("pending_expenses").add({
        userId: currentUser.uid,
        sessionId: sessionId,
        submitterName:
          currentUser.displayName || currentUser.email.split("@")[0],
        submitterEmail: currentUser.email,
        description: data.text,
        amountLabel: data.amountLabel || "—",
        category: data.category || "Other",
        date: data.date,
        currency: selectedCurrency,
        status: data.status || "pending_review",
        submittedAt: firebase.firestore.FieldValue.serverTimestamp(),
        agentReply: data.agentReply || "",
        frontendDocId: null,

        ...(isAutoApproved && {
          decidedBy: "Agent (auto-approved)",
          decidedAt: firebase.firestore.FieldValue.serverTimestamp(),
        }),
      });
      return ref.id;
    } catch (err) {
      console.warn("[Ledgerline] Firestore write failed:", err.message);

      return null;
    }
  }

  function statusForDoc(d) {
    if (d.status === "approved" || d.status === "auto_approved") return "auto";
    if (d.status === "rejected") return "flagged";
    return "review";
  }

  function listenForDecisions() {
    db.collection("pending_expenses")
      .where("userId", "==", currentUser.uid)

      .onSnapshot(
        (snap) => {
          snap.docChanges().forEach((change) => {
            const d = change.doc.data();
            const docId = change.doc.id;

            if (change.type === "added") {
              if (ledger.some((e) => e.id === docId)) return;
              ledger.push({
                id: docId,
                text: d.description,
                amountLabel: d.amountLabel,
                status: statusForDoc(d),
                submittedAtMs: d.submittedAt
                  ? d.submittedAt.toMillis()
                  : Date.now(),
              });
            } else if (change.type === "modified") {
              const item = ledger.find((e) => e.id === docId);
              if (item) item.status = statusForDoc(d);
              if (d.status === "approved") {
                toast("✓ Your expense was approved by a reviewer.", "success");
              } else if (d.status === "rejected") {
                toast("✗ Your expense was rejected by a reviewer.", "error");
              }
            } else if (change.type === "removed") {
              ledger = ledger.filter((e) => e.id !== docId);
            }
          });

          ledger.sort(
            (a, b) => (b.submittedAtMs || 0) - (a.submittedAtMs || 0),
          );
          document.getElementById("ledgerEmpty").hidden = ledger.length > 0;
          document.getElementById("ledgerCount").textContent = ledger.length;
          renderLedger();
        },
        (err) => {
          console.warn(
            "[Ledgerline] Couldn't load submission history:",
            err.message,
          );
          toast("Couldn't load submission history — see console.", "error");
        },
      );
  }

  const conversation = document.getElementById("conversation");

  function esc(s) {
    const d = document.createElement("div");
    d.textContent = s;
    return d.innerHTML;
  }

  function addUserMessage(text) {
    document.getElementById("conversationEmpty").style.display = "none";
    const msg = document.createElement("div");
    msg.className = "msg msg--user";
    msg.innerHTML = `<span class="msg-avatar">${initials()}</span><span class="msg-bubble">${esc(text)}</span>`;
    conversation.appendChild(msg);
    conversation.scrollTop = conversation.scrollHeight;
  }

  function addAgentTyping() {
    const msg = document.createElement("div");
    msg.className = "msg msg--agent";
    msg.id = "agentTyping";
    msg.innerHTML = `<span class="msg-avatar">AI</span><span class="msg-bubble"><span class="typing"><span></span><span></span><span></span></span></span>`;
    conversation.appendChild(msg);
    conversation.scrollTop = conversation.scrollHeight;
  }
  function removeAgentTyping() {
    const el = document.getElementById("agentTyping");
    if (el) el.remove();
  }

  function needsReview(text) {
    return /(needs review|escalat|pending approval|review required|above.*threshold|sent.*reviewer|high risk|manual review|flagged.*risk|needs? human|further review|requires.*review)/i.test(
      text,
    );
  }
  function statusFromText(text) {
    if (/(inject|pii)/i.test(text)) return "flagged";
    if (/(reject|declin)/i.test(text)) return "flagged";
    if (/auto[- ]?approv/i.test(text)) return "auto";
    return "review";
  }

  function addAgentMessage(text, parsed) {
    removeAgentTyping();
    const status = statusFromText(text);
    const msg = document.createElement("div");
    msg.className = "msg msg--agent";

    const reviewNotice =
      status === "review"
        ? `<div class="review-notice">
           <span class="review-notice-icon">⏳</span>
           Sent to a reviewer — you'll be notified here when a decision is made.
         </div>`
        : "";

    let card = parsed
      ? `
      <div class="decision-card">
        <div class="decision-card-head">
          <span class="decision-amount">${parsed.amountLabel || "—"}</span>
          ${chipFor(status)}
        </div>
        <div class="decision-grid">
          <div class="decision-cell"><div class="decision-cell-label">Category</div><div class="decision-cell-value">${parsed.category || "—"}</div></div>
          <div class="decision-cell"><div class="decision-cell-label">Date</div><div class="decision-cell-value">${parsed.date || "—"}</div></div>
        </div>
        <div class="decision-note">${esc(parsed.note || "Routed through the approval workflow.")}</div>
        ${reviewNotice}
      </div>`
      : "";

    msg.innerHTML = `<span class="msg-avatar">AI</span><span class="msg-bubble">${esc(text)}${card}</span>`;
    conversation.appendChild(msg);
    conversation.scrollTop = conversation.scrollHeight;
    return { status, needsReview: status === "review" };
  }

  function quickParse(input) {
    const m = input.match(/(\d+(\.\d{1,2})?)/);
    const amount = m ? m[1] : null;
    const c =
      CURRENCIES.find((x) => x.code === selectedCurrency) || CURRENCIES[0];
    return {
      amountLabel: amount ? `${c.symbol}${amount}` : null,
      category: guessCategory(input),
      date: new Date().toISOString().slice(0, 10),
    };
  }

  function guessCategory(input) {
    const t = input.toLowerCase();
    if (
      /flight|hotel|airbnb|uber|ola|taxi|cab|train|railway|bus|travel|trip|boarding|airport|visa fee/.test(
        t,
      )
    )
      return "travel";
    if (
      /lunch|dinner|breakfast|meal|coffee|tea|food|restaurant|cafe|swiggy|zomato|domino|pizza|biryani|snack/.test(
        t,
      )
    )
      return "meals";
    if (
      /software|saas|subscription|license|domain|hosting|aws|gcp|azure|github|figma|notion|jira/.test(
        t,
      )
    )
      return "software";
    if (
      /movie|movies|cinema|theatre|concert|show|netflix|hotstar|spotify|game|games|gaming|entertainment|ticket/.test(
        t,
      )
    )
      return "entertainment";
    if (
      /office|supplies|stationery|equipment|furniture|printer|monitor|keyboard|mouse|desk/.test(
        t,
      )
    )
      return "office supplies";
    if (/medicine|hospital|doctor|clinic|pharmacy|health|medical/.test(t))
      return "healthcare";
    if (
      /book|course|training|workshop|seminar|conference|udemy|coursera|learning/.test(
        t,
      )
    )
      return "education";
    return "other";
  }

  function extractFromReply(replyText, fallback) {
    const catMatch = replyText.match(
      /\*{0,2}Category\*{0,2}\s*[:\-]\s*([^\n*]+)/i,
    );
    const category = catMatch
      ? catMatch[1].trim().toLowerCase()
      : fallback.category;

    const amtMatch =
      replyText.match(
        /\*{0,2}Amount\*{0,2}\s*[:\-]\s*([\d,]+(?:\.\d{1,2})?)\s*([A-Z]{3})?/i,
      ) ||
      replyText.match(
        /([\d,]+(?:\.\d{1,2})?)\s*(USD|EUR|GBP|INR|JPY|CAD|AUD|CHF|CNY|SGD|AED|BRL)/i,
      );
    let amountLabel = fallback.amountLabel;
    if (amtMatch) {
      const num = amtMatch[1].replace(/,/g, "");
      const codeFromReply = amtMatch[2]
        ? amtMatch[2].toUpperCase()
        : selectedCurrency;
      const cur =
        CURRENCIES.find((x) => x.code === codeFromReply) ||
        CURRENCIES.find((x) => x.code === selectedCurrency) ||
        CURRENCIES[0];
      amountLabel = `${cur.symbol}${parseFloat(num).toFixed(2)}`;
    }

    const dateMatch = replyText.match(/\b(\d{4}-\d{2}-\d{2})\b/);
    const date = dateMatch ? dateMatch[1] : fallback.date;

    return { category, amountLabel, date };
  }

  function getOrCreateSessionId() {
    const key = `ll_session_${currentUser.uid}`;
    let sid = localStorage.getItem(key);
    if (!sid) {
      sid = "sess_" + Math.random().toString(36).slice(2, 12);
      localStorage.setItem(key, sid);
    }
    return sid;
  }

  async function ensureSession() {
    if (sessionReady) return true;
    sessionId = getOrCreateSessionId();
    try {
      const res = await fetch(
        `${BACKEND_CONFIG.BACKEND_URL}/apps/${BACKEND_CONFIG.APP_NAME}/users/${currentUser.uid}/sessions/${sessionId}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        },
      );

      if (!res.ok && res.status !== 400 && res.status !== 409)
        throw new Error(`HTTP ${res.status}`);
      sessionReady = true;
      setConn(true);
      return true;
    } catch (err) {
      console.error("[Ledgerline] Backend unreachable:", err);
      setConn(false);
      toast(
        `Backend unreachable: ${err.message}. Check BACKEND_URL and server.`,
        "error",
      );
      return false;
    }
  }

  function setConn(ok) {
    const pill = document.getElementById("connStatus");
    pill.classList.toggle("is-off", !ok);
    pill.lastChild.textContent = ok ? "Live" : "Offline demo";
  }

  async function callAgent(text) {
    const ok = await ensureSession();
    if (!ok) return offlineResponse(text);
    const payload = {
      appName: BACKEND_CONFIG.APP_NAME,
      userId: currentUser.uid,
      sessionId,
      newMessage: {
        role: "user",
        parts: [
          {
            text: `[Email: ${currentUser.email}] [Currency: ${selectedCurrency}] ${text}`,
          },
        ],
      },
      streaming: false,
    };
    const res = await fetch(`${BACKEND_CONFIG.BACKEND_URL}/run_sse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok || !res.body) throw new Error(`Backend ${res.status}`);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "",
      collected = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      for (const line of lines) {
        if (!line.startsWith("data:")) continue;
        const raw = line.slice(5).trim();
        if (!raw || raw === "[DONE]") continue;
        try {
          const evt = JSON.parse(raw);
          (evt?.content?.parts || []).forEach((p) => {
            if (!p.text) return;

            const cleaned = stripJsonNoise(p.text);
            if (cleaned) collected += cleaned;
          });
        } catch (_) {}
      }
    }
    return collected.trim() || "Processed — no summary returned.";
  }

  function stripJsonNoise(text) {
    let t = text;

    t = t.replace(/```(?:json)?\s*([\s\S]*?)```/gi, (match, inner) => {
      try {
        JSON.parse(inner.trim());
        return "";
      } catch (_) {
        return match;
      }
    });

    const trimmed = t.trim();
    if (!trimmed) return "";

    if (
      (trimmed.startsWith("{") && trimmed.endsWith("}")) ||
      (trimmed.startsWith("[") && trimmed.endsWith("]"))
    ) {
      try {
        JSON.parse(trimmed);
        return "";
      } catch (_) {}
    }

    return t;
  }

  function offlineResponse(text) {
    const parsed = quickParse(text);
    const amount = parsed.amountLabel
      ? parseFloat(parsed.amountLabel.replace(/[^0-9.]/g, ""))
      : 0;
    return new Promise((resolve) =>
      setTimeout(
        () =>
          resolve(
            amount >= 100
              ? `This expense (${parsed.amountLabel}) is above the auto-approval threshold and needs review. It has been sent to a reviewer — you'll be notified when a decision is made.`
              : `Auto-approved. ${parsed.amountLabel} for ${parsed.category.toLowerCase()} is under the threshold and has been cleared.`,
          ),
        1400,
      ),
    );
  }

  const composerForm = document.getElementById("composerForm");
  const composerInput = document.getElementById("composerInput");
  const composerSend = document.getElementById("composerSend");

  composerInput.addEventListener("input", () => {
    composerInput.style.height = "auto";
    composerInput.style.height =
      Math.min(composerInput.scrollHeight, 140) + "px";
  });

  composerForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = composerInput.value.trim();
    if (!text) return;
    composerInput.value = "";
    composerInput.style.height = "auto";
    addUserMessage(text);
    const parsed = quickParse(text);
    const entryId = "e_" + Date.now();
    addLedgerEntry({
      id: entryId,
      text,
      status: "pending",
      amountLabel: parsed.amountLabel,
    });
    composerSend.disabled = true;
    addAgentTyping();
    try {
      const replyText = await animatePipeline(callAgent(text));

      const clientParsed = quickParse(text);
      const agentParsed = extractFromReply(replyText, clientParsed);
      const { status, needsReview: nr } = addAgentMessage(replyText, {
        amountLabel: agentParsed.amountLabel,
        category: agentParsed.category,
        date: agentParsed.date,
        note: replyText.slice(0, 160) + (replyText.length > 160 ? "…" : ""),
      });
      updateLedgerEntry(entryId, {
        status,
        amountLabel: agentParsed.amountLabel,
      });

      const newDocId = await writePendingExpense({
        text,
        ...agentParsed,
        agentReply: replyText,
        status: nr ? "pending_review" : "auto_approved",
      });

      if (newDocId) {
        const item = ledger.find((entryItem) => entryItem.id === entryId);
        if (item) item.id = newDocId;
      }
    } catch (err) {
      removeAgentTyping();
      toast("Agent error — check console.", "error");
      updateLedgerEntry(entryId, { status: "flagged" });
      resetPipeline();
    } finally {
      composerSend.disabled = false;
    }
  });

  document
    .getElementById("newExpenseBtn")
    .addEventListener("click", () => composerInput.focus());

  function initials() {
    if (!currentUser) return "U";
    return (currentUser.displayName || currentUser.email || "U")
      .trim()
      .charAt(0)
      .toUpperCase();
  }

  function applyUser(user) {
    currentUser = user;
    sessionReady = false;
    const name = user.displayName || user.email.split("@")[0];
    document.getElementById("userName").textContent = name;
    document.getElementById("userEmail").textContent = user.email || "";
    document.getElementById("userAvatar").textContent = initials();

    if (ADMIN_EMAILS.includes(user.email)) {
      window.location.href = "admin.html";
      return;
    }
    resetPipeline();
    ensureSession();
    listenForDecisions();
  }

  window.addEventListener("ledgerline:user", (e) => applyUser(e.detail));
})();
