(function () {
  const db = firebase.firestore();
  const auth = firebase.auth();
  let adminUser = null;

  function toast(msg, kind) {
    const el = document.createElement("div");
    el.className = "toast" + (kind ? ` toast--${kind}` : "");
    el.textContent = msg;
    document.getElementById("toastStack").appendChild(el);
    setTimeout(() => el.remove(), 4500);
  }

  let resolvePendingConfirm = null;
  function confirm(title, body, actionLabel, actionCls) {
    if (resolvePendingConfirm) resolvePendingConfirm(false);

    return new Promise((resolve) => {
      resolvePendingConfirm = resolve;
      const modal = document.getElementById("confirmModal");
      const btnConf = document.getElementById("modalConfirm");
      const btnCanc = document.getElementById("modalCancel");
      document.getElementById("modalTitle").textContent = title;
      document.getElementById("modalBody").textContent = body;
      btnConf.textContent = actionLabel;
      btnConf.className = `btn ${actionCls || "btn--primary"}`;
      modal.hidden = false;
      const done = (val) => {
        modal.hidden = true;
        resolvePendingConfirm = null;
        resolve(val);
      };
      btnConf.onclick = () => done(true);
      btnCanc.onclick = () => done(false);
    });
  }

  let stats = { pending: 0, approved: 0, rejected: 0 };
  function updateStats() {
    document.getElementById("statPending").textContent = stats.pending;
    document.getElementById("statApproved").textContent = stats.approved;
    document.getElementById("statRejected").textContent = stats.rejected;
  }

  async function resumeAgentSession(
    submitterUserId,
    submitterSessionId,
    decision,
  ) {
    const ensureRes = await fetch(
      `${BACKEND_CONFIG.BACKEND_URL}/apps/${BACKEND_CONFIG.APP_NAME}/users/${submitterUserId}/sessions/${submitterSessionId}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: "{}",
      },
    );

    if (!ensureRes.ok && ensureRes.status !== 400 && ensureRes.status !== 409) {
      throw new Error(
        `Couldn't reach submitter's session (HTTP ${ensureRes.status})`,
      );
    }

    const payload = {
      appName: BACKEND_CONFIG.APP_NAME,
      userId: submitterUserId,
      sessionId: submitterSessionId,
      newMessage: { role: "user", parts: [{ text: decision }] },
      streaming: false,
    };
    const res = await fetch(`${BACKEND_CONFIG.BACKEND_URL}/run_sse`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`Backend responded ${res.status}`);

    if (res.body) {
      const reader = res.body.getReader();
      while (true) {
        const { done } = await reader.read();
        if (done) break;
      }
    }
  }

  async function decide(docId, doc, decision) {
    const card = document.querySelector(`[data-doc-id="${docId}"]`);
    if (card)
      card.querySelectorAll("button").forEach((b) => (b.disabled = true));

    const label = decision === "approve" ? "approved" : "rejected";
    const ok = await confirm(
      `${decision === "approve" ? "Approve" : "Reject"} expense`,
      `"${doc.description}" — ${doc.amountLabel} from ${doc.submitterName}. This will ${label} the expense and notify the submitter.`,
      decision === "approve" ? "Approve" : "Reject",
      decision === "approve" ? "btn--approve" : "btn--reject",
    );
    if (!ok) {
      if (card)
        card.querySelectorAll("button").forEach((b) => (b.disabled = false));
      return;
    }

    try {
      await resumeAgentSession(doc.userId, doc.sessionId, decision);

      await db.collection("pending_expenses").doc(docId).update({
        status: label,
        decidedAt: firebase.firestore.FieldValue.serverTimestamp(),
        decidedBy: adminUser.email,
      });

      toast(
        `Expense ${label} and submitter notified.`,
        decision === "approve" ? "success" : "error",
      );
    } catch (err) {
      console.error("[Admin] Decision failed:", err);
      toast(`Failed: ${err.message}. Backend may not be reachable.`, "error");
      if (card)
        card.querySelectorAll("button").forEach((b) => (b.disabled = false));
    }
  }

  function renderCard(docId, doc, resolved) {
    const el = document.createElement("div");
    el.className = "expense-card" + (resolved ? " expense-card--resolved" : "");
    el.dataset.docId = docId;

    const ts = doc.submittedAt
      ? new Date(doc.submittedAt.seconds * 1000).toLocaleString()
      : "—";
    const decidedTs = doc.decidedAt
      ? new Date(doc.decidedAt.seconds * 1000).toLocaleString()
      : null;

    const chipMap = {
      approved: ["chip--auto", "Approved"],
      rejected: ["chip--flagged", "Rejected"],
      auto_approved: ["chip--auto", "Auto-approved"],
    };
    const [chipCls, chipLabel] = chipMap[doc.status] || [
      "chip--flagged",
      "Rejected",
    ];
    const statusChip = resolved
      ? `<span class="chip ${chipCls}">${chipLabel}</span>`
      : `<span class="chip chip--review">Needs review</span>`;

    const actions = resolved
      ? `
      <div class="card-resolved-by">
        Decision by <strong>${doc.decidedBy || "—"}</strong> at ${decidedTs || "—"}
      </div>`
      : `
      <div class="card-actions">
        <button class="btn btn--approve" data-action="approve" data-doc="${docId}">Approve</button>
        <button class="btn btn--reject"  data-action="reject"  data-doc="${docId}">Reject</button>
      </div>`;

    el.innerHTML = `
      <div class="card-header">
        <div class="card-submitter">
          <span class="card-avatar">${(doc.submitterName || "?").charAt(0).toUpperCase()}</span>
          <div>
            <div class="card-name">${doc.submitterName || "—"}</div>
            <div class="card-email">${doc.submitterEmail || "—"}</div>
          </div>
        </div>
        <div class="card-meta-right">
          ${statusChip}
          <span class="card-amount">${doc.amountLabel || "—"}</span>
        </div>
      </div>
      <div class="card-description">${doc.description || "—"}</div>
      <div class="card-tags">
        <span class="tag">${doc.category || "Other"}</span>
        <span class="tag">${doc.currency || "—"}</span>
        <span class="tag">${doc.date || "—"}</span>
      </div>
      <div class="card-agent-reply">${doc.agentReply ? `Agent: "${doc.agentReply.slice(0, 140)}${doc.agentReply.length > 140 ? "…" : ""}"` : ""}</div>
      <div class="card-footer">
        <span class="card-ts">Submitted ${ts}</span>
        ${actions}
      </div>`;

    el.querySelectorAll("[data-action]").forEach((btn) => {
      btn.addEventListener("click", () =>
        decide(btn.dataset.doc, doc, btn.dataset.action),
      );
    });

    return el;
  }

  let unsubscribeQueue = null;

  function listenToQueue() {
    if (unsubscribeQueue) return;

    const pendingQueue = document.getElementById("pendingQueue");
    const pendingEmpty = document.getElementById("pendingEmpty");
    const resolvedQueue = document.getElementById("resolvedQueue");
    const resolvedEmpty = document.getElementById("resolvedEmpty");
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    unsubscribeQueue = db
      .collection("pending_expenses")
      .orderBy("submittedAt", "desc")
      .onSnapshot(
        (snap) => {
          pendingQueue.innerHTML = "";
          resolvedQueue.innerHTML = "";
          let pending = 0,
            approved = 0,
            rejected = 0;

          snap.forEach((docSnap) => {
            const doc = docSnap.data();
            if (doc.status === "pending_review") {
              pendingQueue.appendChild(renderCard(docSnap.id, doc, false));
              pending++;
            } else {
              resolvedQueue.appendChild(renderCard(docSnap.id, doc, true));
              const decidedDate = doc.decidedAt
                ? new Date(doc.decidedAt.seconds * 1000)
                : null;
              if (decidedDate && decidedDate >= today) {
                if (doc.status === "approved") approved++;
                if (doc.status === "rejected") rejected++;
              }
            }
          });

          pendingEmpty.style.display = pending === 0 ? "flex" : "none";
          resolvedEmpty.style.display =
            snap.size - pending === 0 ? "block" : "none";
          stats = { pending, approved, rejected };
          updateStats();
        },
        (err) => {
          if (!adminUser) return;
          console.error("[Admin] Firestore error:", err);
          toast(
            "Couldn't load queue — check Firestore rules and connection.",
            "error",
          );
        },
      );
  }

  function stopListeningToQueue() {
    if (unsubscribeQueue) {
      unsubscribeQueue();
      unsubscribeQueue = null;
    }
  }

  window.addEventListener("ledgerline:user", (e) => {
    const user = e.detail;
    const adminShell = document.getElementById("adminShell");
    const gate = document.getElementById("adminAuthGate");
    const gateMsg = document.getElementById("adminGateMsg");

    if (!ADMIN_EMAILS.includes(user.email)) {
      gate.hidden = false;
      gateMsg.textContent = `${user.email} is not authorized as a reviewer. Redirecting…`;
      setTimeout(() => {
        window.location.href = "index.html";
      }, 2200);
      return;
    }

    adminUser = user;
    adminShell.hidden = false;
    document.getElementById("adminAvatar").textContent = user.email
      .charAt(0)
      .toUpperCase();
    document.getElementById("adminName").textContent =
      user.displayName || user.email.split("@")[0];
    document.getElementById("adminEmail").textContent = user.email;

    if (!document.getElementById("adminSignOutBtn").dataset.bound) {
      document
        .getElementById("adminSignOutBtn")
        .addEventListener("click", () => {
          stopListeningToQueue();
          auth.signOut();
        });
      document.getElementById("adminSignOutBtn").dataset.bound = "1";
    }
    listenToQueue();
  });

  firebase.auth().onAuthStateChanged((user) => {
    if (!user) {
      adminUser = null;
      stopListeningToQueue();
      document.getElementById("adminAuthGate").hidden = false;
      document.getElementById("adminGateMsg").textContent =
        "Sign in via the employee page first.";
      document.querySelector("#adminAuthGate .link-btn") &&
        (document.querySelector("#adminAuthGate .link-btn").style.display =
          "block");
    }
  });
})();
