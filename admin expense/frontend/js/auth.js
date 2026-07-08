(function () {
  const auth = firebase.auth();
  const googleProvider = new firebase.auth.GoogleAuthProvider();

  const authGate = document.getElementById("authGate");
  const appShell = document.getElementById("appShell");

  const views = {
    signin: document.getElementById("view-signin"),
    signup: document.getElementById("view-signup"),
    reset: document.getElementById("view-reset"),
  };

  function showView(name) {
    Object.values(views).forEach((v) => (v.hidden = true));
    views[name].hidden = false;
  }

  if (authGate) {
    document
      .getElementById("goToSignUp")
      .addEventListener("click", () => showView("signup"));
    document
      .getElementById("goToSignIn")
      .addEventListener("click", () => showView("signin"));
    document
      .getElementById("forgotPasswordBtn")
      .addEventListener("click", () => showView("reset"));
    document
      .getElementById("backToSignIn")
      .addEventListener("click", () => showView("signin"));
  }

  function setBusy(form, busy) {
    const btn = form.querySelector("button[type=submit]");
    const label = btn.querySelector(".btn-label");
    const spinner = btn.querySelector(".btn-spinner");
    btn.disabled = busy;
    spinner.hidden = !busy;
    label.style.opacity = busy ? "0.6" : "1";
  }

  function showError(elId, message) {
    const el = document.getElementById(elId);
    el.textContent = message;
    el.hidden = false;
  }
  function hideError(elId) {
    document.getElementById(elId).hidden = true;
  }

  function friendlyAuthError(error) {
    const map = {
      "auth/invalid-email": "That email address doesn't look right.",
      "auth/user-not-found": "No account found with that email.",
      "auth/wrong-password": "Incorrect password. Try again.",
      "auth/invalid-credential": "Email or password is incorrect.",
      "auth/email-already-in-use": "An account already exists for that email.",
      "auth/weak-password": "Use at least 8 characters for your password.",
      "auth/popup-closed-by-user":
        "Google sign-in was closed before finishing.",
      "auth/network-request-failed":
        "Network error — check your connection and try again.",
      "auth/configuration-not-found":
        "Firebase Authentication isn't configured yet for this project.",
    };
    return (
      map[error.code] ||
      error.message ||
      "Something went wrong. Please try again."
    );
  }

  if (document.getElementById("signInForm"))
    document
      .getElementById("signInForm")
      .addEventListener("submit", async (e) => {
        e.preventDefault();
        hideError("signInError");
        const form = e.target;
        const email = form.email.value.trim();
        const password = form.password.value;
        const persistence = form.remember.checked
          ? firebase.auth.Auth.Persistence.LOCAL
          : firebase.auth.Auth.Persistence.SESSION;

        setBusy(form, true);
        try {
          await auth.setPersistence(persistence);
          await auth.signInWithEmailAndPassword(email, password);
        } catch (err) {
          showError("signInError", friendlyAuthError(err));
        } finally {
          setBusy(form, false);
        }
      });

  if (document.getElementById("signUpForm"))
    document
      .getElementById("signUpForm")
      .addEventListener("submit", async (e) => {
        e.preventDefault();
        hideError("signUpError");
        const form = e.target;
        const name = form.name.value.trim();
        const email = form.email.value.trim();
        const password = form.password.value;

        setBusy(form, true);
        try {
          const cred = await auth.createUserWithEmailAndPassword(
            email,
            password,
          );
          if (name) await cred.user.updateProfile({ displayName: name });
        } catch (err) {
          showError("signUpError", friendlyAuthError(err));
        } finally {
          setBusy(form, false);
        }
      });

  if (document.getElementById("resetForm"))
    document
      .getElementById("resetForm")
      .addEventListener("submit", async (e) => {
        e.preventDefault();
        hideError("resetError");
        document.getElementById("resetSuccess").hidden = true;
        const form = e.target;
        const email = form.email.value.trim();

        setBusy(form, true);
        try {
          await auth.sendPasswordResetEmail(email);
          const successEl = document.getElementById("resetSuccess");
          successEl.textContent = "Reset link sent — check your inbox.";
          successEl.hidden = false;
        } catch (err) {
          showError("resetError", friendlyAuthError(err));
        } finally {
          setBusy(form, false);
        }
      });

  if (document.getElementById("googleSignInBtn"))
    document
      .getElementById("googleSignInBtn")
      .addEventListener("click", async () => {
        hideError("signInError");
        try {
          await auth.signInWithPopup(googleProvider);
        } catch (err) {
          showError("signInError", friendlyAuthError(err));
        }
      });

  if (document.getElementById("signOutBtn"))
    document
      .getElementById("signOutBtn")
      .addEventListener("click", () => auth.signOut());

  auth.onAuthStateChanged((user) => {
    if (user) {
      if (authGate) authGate.style.display = "none";
      if (appShell) appShell.hidden = false;
      window.dispatchEvent(
        new CustomEvent("ledgerline:user", { detail: user }),
      );
    } else {
      if (authGate) authGate.style.display = "grid";
      if (appShell) appShell.hidden = true;
      if (authGate) showView("signin");
    }
  });

  (function animateAuthPipeline() {
    const fill = document.getElementById("authPipelineFill");
    if (!fill) return;
    const nodes = document.querySelectorAll("#authPipeline .pipeline-node");
    const widths = [6, 27, 50, 73, 94];
    let i = 0;
    setInterval(() => {
      nodes.forEach((n, idx) => {
        n.classList.toggle("is-done", idx < i);
        n.classList.toggle("is-active", idx === i);
      });
      fill.style.width = widths[i] + "%";
      i = (i + 1) % nodes.length;
    }, 1800);
  })();
})();
