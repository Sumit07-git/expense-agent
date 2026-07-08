import json
import logging
import os
from pathlib import Path

from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from google.adk.cli.fast_api import get_fast_api_app

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("expense_agent.fast_api_app")

CURRENCY_INJECTION_SCRIPT = """
<script>
(function() {
  const CURRENCIES = [
    {code:"USD",symbol:"$",flag:"🇺🇸",name:"US Dollar"},
    {code:"EUR",symbol:"€",flag:"🇪🇺",name:"Euro"},
    {code:"GBP",symbol:"£",flag:"🇬🇧",name:"British Pound"},
    {code:"INR",symbol:"₹",flag:"🇮🇳",name:"Indian Rupee"},
    {code:"JPY",symbol:"¥",flag:"🇯🇵",name:"Japanese Yen"},
    {code:"CAD",symbol:"CA$",flag:"🇨🇦",name:"Canadian Dollar"},
    {code:"AUD",symbol:"A$",flag:"🇦🇺",name:"Australian Dollar"},
    {code:"CHF",symbol:"Fr",flag:"🇨🇭",name:"Swiss Franc"},
    {code:"CNY",symbol:"¥",flag:"🇨🇳",name:"Chinese Yuan"},
    {code:"KRW",symbol:"₩",flag:"🇰🇷",name:"South Korean Won"},
    {code:"BRL",symbol:"R$",flag:"🇧🇷",name:"Brazilian Real"},
    {code:"MXN",symbol:"MX$",flag:"🇲🇽",name:"Mexican Peso"},
    {code:"SGD",symbol:"S$",flag:"🇸🇬",name:"Singapore Dollar"},
    {code:"HKD",symbol:"HK$",flag:"🇭🇰",name:"Hong Kong Dollar"},
    {code:"SEK",symbol:"kr",flag:"🇸🇪",name:"Swedish Krona"},
    {code:"NOK",symbol:"kr",flag:"🇳🇴",name:"Norwegian Krone"},
    {code:"DKK",symbol:"kr",flag:"🇩🇰",name:"Danish Krone"},
    {code:"PLN",symbol:"zł",flag:"🇵🇱",name:"Polish Zloty"},
    {code:"TRY",symbol:"₺",flag:"🇹🇷",name:"Turkish Lira"},
    {code:"RUB",symbol:"₽",flag:"🇷🇺",name:"Russian Ruble"},
    {code:"ZAR",symbol:"R",flag:"🇿🇦",name:"South African Rand"},
    {code:"THB",symbol:"฿",flag:"🇹🇭",name:"Thai Baht"},
    {code:"MYR",symbol:"RM",flag:"🇲🇾",name:"Malaysian Ringgit"},
    {code:"PHP",symbol:"₱",flag:"🇵🇭",name:"Philippine Peso"},
    {code:"IDR",symbol:"Rp",flag:"🇮🇩",name:"Indonesian Rupiah"},
    {code:"AED",symbol:"AED",flag:"🇦🇪",name:"UAE Dirham"},
    {code:"SAR",symbol:"SAR",flag:"🇸🇦",name:"Saudi Riyal"},
    {code:"NGN",symbol:"₦",flag:"🇳🇬",name:"Nigerian Naira"},
    {code:"EGP",symbol:"E£",flag:"🇪🇬",name:"Egyptian Pound"},
    {code:"PKR",symbol:"₨",flag:"🇵🇰",name:"Pakistani Rupee"},
    {code:"BDT",symbol:"৳",flag:"🇧🇩",name:"Bangladeshi Taka"},
    {code:"VND",symbol:"₫",flag:"🇻🇳",name:"Vietnamese Dong"},
    {code:"COP",symbol:"COL$",flag:"🇨🇴",name:"Colombian Peso"},
    {code:"ARS",symbol:"AR$",flag:"🇦🇷",name:"Argentine Peso"},
    {code:"PEN",symbol:"S/.",flag:"🇵🇪",name:"Peruvian Sol"},
    {code:"LKR",symbol:"Rs",flag:"🇱🇰",name:"Sri Lankan Rupee"},
    {code:"NPR",symbol:"Rs",flag:"🇳🇵",name:"Nepalese Rupee"},
    {code:"ILS",symbol:"₪",flag:"🇮🇱",name:"Israeli Shekel"},
    {code:"CZK",symbol:"Kč",flag:"🇨🇿",name:"Czech Koruna"},
    {code:"HUF",symbol:"Ft",flag:"🇭🇺",name:"Hungarian Forint"},
    {code:"RON",symbol:"lei",flag:"🇷🇴",name:"Romanian Leu"},
    {code:"UAH",symbol:"₴",flag:"🇺🇦",name:"Ukrainian Hryvnia"},
    {code:"GHS",symbol:"₵",flag:"🇬🇭",name:"Ghanaian Cedi"},
    {code:"TWD",symbol:"NT$",flag:"🇹🇼",name:"Taiwan Dollar"},
    {code:"NZD",symbol:"NZ$",flag:"🇳🇿",name:"New Zealand Dollar"},
    {code:"KES",symbol:"KSh",flag:"🇰🇪",name:"Kenyan Shilling"},
  ];

  /* Persist the selected currency across page reloads */
  let selectedCurrency = localStorage.getItem("expense_currency") || "USD";

  const style = document.createElement("style");
  style.textContent = `
    /* ---- Hide the app-type selector (only one agent) ---- */
    .app-selector-container,
    mat-form-field:has(mat-select[aria-label*="app"]),
    mat-form-field:has(mat-select[aria-label*="App"]),
    mat-form-field:has(mat-select[aria-label*="agent"]),
    mat-form-field:has(mat-select[aria-label*="Agent"]) {
      display: none !important;
    }

    /* ---- Currency picker styles ---- */
    .currency-picker-wrapper {
      display: inline-flex;
      align-items: center;
      margin-right: 8px;
      position: relative;
      flex-shrink: 0;
    }
    .currency-picker-btn {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: linear-gradient(135deg, rgba(124,196,255,0.12), rgba(99,102,241,0.12));
      border: 1px solid rgba(124,196,255,0.30);
      border-radius: 10px;
      padding: 8px 12px 8px 10px;
      color: #7cc4ff;
      font-family: 'Google Sans', Roboto, sans-serif;
      font-size: 13.5px;
      font-weight: 500;
      cursor: pointer;
      transition: all 0.25s ease;
      white-space: nowrap;
      line-height: 1;
      box-shadow: 0 1px 4px rgba(0,0,0,0.15);
    }
    .currency-picker-btn:hover {
      background: linear-gradient(135deg, rgba(124,196,255,0.22), rgba(99,102,241,0.22));
      border-color: rgba(124,196,255,0.50);
      box-shadow: 0 2px 8px rgba(124,196,255,0.15);
      transform: translateY(-1px);
    }
    .currency-picker-btn .cpb-flag { font-size: 16px; }
    .currency-picker-btn .cpb-code { font-weight: 600; letter-spacing: 0.4px; }
    .currency-picker-btn .cpb-symbol { opacity: 0.65; font-size: 12px; }
    .currency-picker-btn .cpb-arrow {
      font-size: 9px;
      opacity: 0.5;
      margin-left: 2px;
      transition: transform 0.2s ease;
    }
    .currency-picker-btn.open .cpb-arrow { transform: rotate(180deg); }

    .currency-dropdown-panel {
      display: none;
      position: absolute;
      bottom: calc(100% + 8px);
      left: 0;
      background: #1a1a2e;
      border: 1px solid rgba(124,196,255,0.15);
      border-radius: 14px;
      box-shadow: 0 12px 40px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.04);
      width: 280px;
      max-height: 360px;
      overflow: hidden;
      z-index: 9999;
      flex-direction: column;
      backdrop-filter: blur(12px);
      animation: currencyDropIn 0.2s ease-out;
    }
    @keyframes currencyDropIn {
      from { opacity: 0; transform: translateY(8px); }
      to { opacity: 1; transform: translateY(0); }
    }
    .currency-dropdown-panel.open { display: flex; }

    .currency-dropdown-header {
      padding: 12px 14px 8px;
      font-size: 11px;
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.8px;
      color: rgba(124,196,255,0.6);
      font-family: 'Google Sans', Roboto, sans-serif;
    }

    .currency-search {
      padding: 0 12px 10px;
      border-bottom: 1px solid rgba(255,255,255,0.06);
      flex-shrink: 0;
    }
    .currency-search input {
      width: 100%;
      background: rgba(255,255,255,0.05);
      border: 1px solid rgba(255,255,255,0.08);
      border-radius: 8px;
      padding: 8px 10px 8px 32px;
      color: #e0e0e0;
      font-family: 'Google Sans', Roboto, sans-serif;
      font-size: 13px;
      outline: none;
      transition: border-color 0.2s;
      box-sizing: border-box;
    }
    .currency-search input:focus {
      border-color: rgba(124,196,255,0.4);
      background: rgba(255,255,255,0.07);
    }
    .currency-search input::placeholder { color: rgba(255,255,255,0.25); }
    .currency-search-wrap {
      position: relative;
    }
    .currency-search-wrap::before {
      content: "🔍";
      position: absolute;
      left: 9px;
      top: 50%;
      transform: translateY(-50%);
      font-size: 12px;
      pointer-events: none;
      opacity: 0.5;
    }

    .currency-list {
      overflow-y: auto;
      flex: 1;
      padding: 4px 0;
    }
    .currency-list::-webkit-scrollbar { width: 5px; }
    .currency-list::-webkit-scrollbar-track { background: transparent; }
    .currency-list::-webkit-scrollbar-thumb { background: rgba(124,196,255,0.15); border-radius: 4px; }
    .currency-list::-webkit-scrollbar-thumb:hover { background: rgba(124,196,255,0.25); }

    .currency-item {
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 9px 14px;
      cursor: pointer;
      transition: all 0.15s ease;
      font-size: 13px;
      color: #bbb;
      border-left: 3px solid transparent;
    }
    .currency-item:hover {
      background: rgba(124,196,255,0.07);
      color: #ddd;
      border-left-color: rgba(124,196,255,0.3);
    }
    .currency-item.active {
      background: rgba(124,196,255,0.12);
      color: #7cc4ff;
      border-left-color: #7cc4ff;
    }
    .currency-item .ci-flag { font-size: 17px; flex-shrink: 0; }
    .currency-item .ci-code { font-weight: 600; min-width: 38px; letter-spacing: 0.3px; }
    .currency-item .ci-symbol { opacity: 0.5; font-size: 12px; min-width: 24px; text-align: center; }
    .currency-item .ci-name { opacity: 0.5; font-size: 12px; margin-left: auto; }

    .currency-no-results {
      padding: 20px 14px;
      text-align: center;
      color: rgba(255,255,255,0.3);
      font-size: 13px;
    }
  `;
  document.head.appendChild(style);

  /* Helper to update the textarea placeholder to hint about selected currency */
  function updatePlaceholder() {
    var ta = document.querySelector("textarea[matinput], textarea[mat-input], mat-form-field textarea, .chat-input textarea, .mat-mdc-input-element, textarea");
    if (ta) {
      var cur = CURRENCIES.find(function(c) { return c.code === selectedCurrency; }) || CURRENCIES[0];
      ta.setAttribute("placeholder", "e.g. I spent 45 on flight (" + cur.code + " " + cur.symbol + ")");
    }
  }

  function createPicker(container) {
    const wrapper = document.createElement("div");
    wrapper.className = "currency-picker-wrapper";

    const cur = CURRENCIES.find(c => c.code === selectedCurrency) || CURRENCIES[0];

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "currency-picker-btn";
    btn.innerHTML = '<span class="cpb-flag">' + cur.flag + '</span><span class="cpb-code">' + cur.code + '</span><span class="cpb-symbol">(' + cur.symbol + ')</span><span class="cpb-arrow">\u25b2</span>';

    const panel = document.createElement("div");
    panel.className = "currency-dropdown-panel";

    const header = document.createElement("div");
    header.className = "currency-dropdown-header";
    header.textContent = "Select Currency";
    panel.appendChild(header);

    const searchBox = document.createElement("div");
    searchBox.className = "currency-search";
    const searchWrap = document.createElement("div");
    searchWrap.className = "currency-search-wrap";
    searchWrap.innerHTML = '<input type="text" placeholder="Search by name or code...">';
    searchBox.appendChild(searchWrap);
    panel.appendChild(searchBox);

    const list = document.createElement("div");
    list.className = "currency-list";
    panel.appendChild(list);

    function renderList(filter) {
      list.innerHTML = "";
      const q = (filter || "").toLowerCase();
      let count = 0;
      CURRENCIES.forEach(function(c) {
        if (q && !c.code.toLowerCase().includes(q) && !c.name.toLowerCase().includes(q) && !c.symbol.toLowerCase().includes(q)) return;
        count++;
        const item = document.createElement("div");
        item.className = "currency-item" + (c.code === selectedCurrency ? " active" : "");
        item.innerHTML = '<span class="ci-flag">' + c.flag + '</span><span class="ci-code">' + c.code + '</span><span class="ci-symbol">' + c.symbol + '</span><span class="ci-name">' + c.name + '</span>';
        item.addEventListener("click", function(e) {
          e.stopPropagation();
          selectedCurrency = c.code;
          localStorage.setItem("expense_currency", c.code);
          btn.innerHTML = '<span class="cpb-flag">' + c.flag + '</span><span class="cpb-code">' + c.code + '</span><span class="cpb-symbol">(' + c.symbol + ')</span><span class="cpb-arrow">\u25b2</span>';
          btn.classList.remove("open");
          panel.classList.remove("open");
          renderList("");
          searchBox.querySelector("input").value = "";
          updatePlaceholder();
        });
        list.appendChild(item);
      });
      if (count === 0) {
        const noRes = document.createElement("div");
        noRes.className = "currency-no-results";
        noRes.textContent = 'No currency found for "' + (filter || "") + '"';
        list.appendChild(noRes);
      }
    }
    renderList("");

    searchBox.querySelector("input").addEventListener("input", function(e) {
      renderList(e.target.value);
    });
    searchBox.querySelector("input").addEventListener("click", function(e) { e.stopPropagation(); });

    btn.addEventListener("click", function(e) {
      e.stopPropagation();
      e.preventDefault();
      const isOpen = panel.classList.contains("open");
      panel.classList.toggle("open");
      btn.classList.toggle("open");
      if (!isOpen) {
        searchBox.querySelector("input").value = "";
        renderList("");
        setTimeout(function() { searchBox.querySelector("input").focus(); }, 50);
      }
    });

    document.addEventListener("click", function() {
      panel.classList.remove("open");
      btn.classList.remove("open");
    });

    wrapper.appendChild(panel);
    wrapper.appendChild(btn);
    return wrapper;
  }

  /* ---- Auto-select expense_agent & hide app selector ---- */
  function autoSelectAgent() {
    /* Strategy 1: Try clicking mat-select options */
    const matSelects = document.querySelectorAll("mat-select, mat-form-field mat-select");
    matSelects.forEach(function(sel) {
      const label = (sel.getAttribute("aria-label") || "").toLowerCase();
      const placeholder = (sel.getAttribute("placeholder") || "").toLowerCase();
      const parentLabel = sel.closest("mat-form-field");
      const labelText = parentLabel ? (parentLabel.textContent || "").toLowerCase() : "";
      if (label.includes("app") || label.includes("agent") || placeholder.includes("app") || placeholder.includes("agent") || labelText.includes("app") || labelText.includes("agent")) {
        sel.click();
        setTimeout(function() {
          const options = document.querySelectorAll("mat-option, .mat-mdc-option");
          options.forEach(function(opt) {
            const text = (opt.textContent || "").trim().toLowerCase();
            if (text.includes("expense")) {
              opt.click();
            }
          });
          /* Close any open overlay */
          const backdrop = document.querySelector(".cdk-overlay-backdrop");
          if (backdrop) backdrop.click();
        }, 200);
      }
    });

    /* Strategy 2: Hide any select/dropdown that looks like an app selector via broad CSS */
    const allFormFields = document.querySelectorAll("mat-form-field");
    allFormFields.forEach(function(ff) {
      const text = (ff.textContent || "").toLowerCase();
      const label = ff.querySelector("mat-label");
      const labelText = label ? (label.textContent || "").toLowerCase() : "";
      if (labelText.includes("app") || labelText.includes("agent") || text.includes("select an app") || text.includes("select app")) {
        ff.style.display = "none";
      }
    });

    /* Strategy 3: Look for regular select elements */
    const regularSelects = document.querySelectorAll("select");
    regularSelects.forEach(function(sel) {
      const options = sel.querySelectorAll("option");
      let hasExpense = false;
      options.forEach(function(opt) {
        if ((opt.textContent || "").toLowerCase().includes("expense")) {
          opt.selected = true;
          hasExpense = true;
          sel.dispatchEvent(new Event("change", { bubbles: true }));
        }
      });
      /* If this is a single-option select for app type, hide it */
      if (options.length <= 2 && hasExpense) {
        const parent = sel.closest("mat-form-field") || sel.closest(".form-field") || sel.parentElement;
        if (parent) parent.style.display = "none";
      }
    });
  }

  /* ---- Inject currency picker beside message input ---- */
  let pickerInjected = false;
  let agentSelected = false;
  let agentSelectAttempts = 0;

  function tryInjectPicker() {
    if (pickerInjected) return;

    /* Broad selector: find the chat input textarea/input in any ADK dev UI variant */
    var textarea = document.querySelector(
      "textarea[matinput], textarea[mat-input], mat-form-field textarea, " +
      ".chat-input textarea, .mat-mdc-input-element, " +
      "textarea[placeholder*='message'], textarea[placeholder*='Message'], " +
      "input[placeholder*='message'], input[placeholder*='Message'], " +
      ".mdc-text-field textarea, textarea"
    );
    if (!textarea) return;

    /* Walk up to find the row containing the input + send button */
    var inputRow = textarea.closest("mat-form-field")
      || textarea.closest(".mat-mdc-form-field")
      || textarea.closest(".mat-mdc-text-field-wrapper")
      || textarea.parentElement;
    if (!inputRow) return;

    var actionRow = inputRow.parentElement;
    if (!actionRow) return;

    /* Ensure flex layout so the picker sits to the left */
    if (getComputedStyle(actionRow).display !== "flex") {
      actionRow.style.display = "flex";
      actionRow.style.alignItems = "flex-end";
      actionRow.style.gap = "8px";
    }

    var picker = createPicker(actionRow);
    actionRow.insertBefore(picker, actionRow.firstChild);
    pickerInjected = true;

    /* Update the placeholder to reflect selected currency */
    updatePlaceholder();
  }

  const observer = new MutationObserver(function() {
    /* Auto-select the expense agent and hide the app selector */
    if (!agentSelected && agentSelectAttempts < 15) {
      agentSelectAttempts++;
      autoSelectAgent();
      /* Check if we successfully hid something */
      const hiddenFields = document.querySelectorAll("mat-form-field[style*='display: none']");
      if (hiddenFields.length > 0 || agentSelectAttempts >= 10) {
        agentSelected = true;
      }
    }

    tryInjectPicker();

    if (pickerInjected && agentSelected) observer.disconnect();
  });

  observer.observe(document.body, { childList: true, subtree: true });

  /* Also try immediately and after short delays for SPAs */
  setTimeout(autoSelectAgent, 500);
  setTimeout(autoSelectAgent, 1500);
  setTimeout(autoSelectAgent, 3000);
  /* Extra retry for late-rendering Angular apps */
  [500, 1000, 2000, 3000, 5000].forEach(function(delay) {
    setTimeout(tryInjectPicker, delay);
  });

  /* ---- Intercept fetch to prepend currency to messages ---- */
  const origFetch = window.fetch;
  window.fetch = function(url, opts) {
    if (
      typeof url === "string" &&
      (url.includes("/run_sse") || url.includes("/run") || url.includes("/chat")) &&
      opts && opts.method && opts.method.toUpperCase() === "POST" &&
      opts.body
    ) {
      try {
        const body = JSON.parse(opts.body);
        /* Standard ADK dev UI message format */
        if (body.newMessage && body.newMessage.parts && body.newMessage.parts.length > 0) {
          const firstPart = body.newMessage.parts[0];
          if (firstPart.text && !firstPart.text.startsWith("[Currency:") && !firstPart.text.startsWith("{")) {
            firstPart.text = "[Currency: " + selectedCurrency + "] " + firstPart.text;
            opts = Object.assign({}, opts, { body: JSON.stringify(body) });
          }
        }
        /* Alternative message formats */
        if (body.message && typeof body.message === "string" && !body.message.startsWith("[Currency:") && !body.message.startsWith("{")) {
          body.message = "[Currency: " + selectedCurrency + "] " + body.message;
          opts = Object.assign({}, opts, { body: JSON.stringify(body) });
        }
        if (body.input && typeof body.input === "string" && !body.input.startsWith("[Currency:") && !body.input.startsWith("{")) {
          body.input = "[Currency: " + selectedCurrency + "] " + body.input;
          opts = Object.assign({}, opts, { body: JSON.stringify(body) });
        }
      } catch(e) {}
    }
    return origFetch.call(this, url, opts);
  };

  /* ---- Also intercept XMLHttpRequest for frameworks that use it ---- */
  const origXHROpen = XMLHttpRequest.prototype.open;
  const origXHRSend = XMLHttpRequest.prototype.send;
  XMLHttpRequest.prototype.open = function(method, url) {
    this._expenseUrl = url;
    this._expenseMethod = method;
    return origXHROpen.apply(this, arguments);
  };
  XMLHttpRequest.prototype.send = function(data) {
    if (
      this._expenseMethod && this._expenseMethod.toUpperCase() === "POST" &&
      typeof this._expenseUrl === "string" &&
      (this._expenseUrl.includes("/run_sse") || this._expenseUrl.includes("/run") || this._expenseUrl.includes("/chat")) &&
      typeof data === "string"
    ) {
      try {
        var body = JSON.parse(data);
        var modified = false;
        if (body.newMessage && body.newMessage.parts && body.newMessage.parts.length > 0) {
          var fp = body.newMessage.parts[0];
          if (fp.text && !fp.text.startsWith("[Currency:") && !fp.text.startsWith("{")) {
            fp.text = "[Currency: " + selectedCurrency + "] " + fp.text;
            modified = true;
          }
        }
        if (body.message && typeof body.message === "string" && !body.message.startsWith("[Currency:")) {
          body.message = "[Currency: " + selectedCurrency + "] " + body.message;
          modified = true;
        }
        if (body.input && typeof body.input === "string" && !body.input.startsWith("[Currency:")) {
          body.input = "[Currency: " + selectedCurrency + "] " + body.input;
          modified = true;
        }
        if (modified) data = JSON.stringify(body);
      } catch(e) {}
    }
    return origXHRSend.call(this, data);
  };

  setTimeout(function() {
    try {
      var details = {
        url: window.location.href,
        textarea_exists: !!document.querySelector('textarea'),
        input_exists: !!document.querySelector('input'),
        picker_wrapper_exists: !!document.querySelector('.currency-picker-wrapper'),
        elements: Array.from(document.querySelectorAll('input,textarea,button,div')).map(function(el) {
          if (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || (el.tagName === 'BUTTON' && el.textContent.trim()) || el.className.includes('input') || el.className.includes('chat')) {
            return {
              tag: el.tagName,
              id: el.id,
              className: el.className,
              placeholder: el.placeholder || '',
              text: el.textContent ? el.textContent.trim().substring(0, 50) : '',
              parent: el.parentElement ? el.parentElement.tagName + '.' + el.parentElement.className : ''
            };
          }
          return null;
        }).filter(Boolean),
        body_html: document.body.innerHTML.substring(0, 100000)
      };
      fetch('/api/diagnose_dom', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(details)
      });
    } catch(e) {}
  }, 3000);

})();
</script>
"""


class PubSubSubscriptionNormalizerMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if (
            scope["type"] == "http"
            and scope["path"].endswith("/trigger/pubsub")
            and scope["method"] == "POST"
        ):
            body = b""
            more_body = True
            while more_body:
                message = await receive()
                body += message.get("body", b"")
                more_body = message.get("more_body", False)

            try:
                if body:
                    data = json.loads(body)
                    if "subscription" in data and isinstance(data["subscription"], str):
                        orig_sub = data["subscription"]
                        short_sub = orig_sub.split("/")[-1]
                        data["subscription"] = short_sub
                        logger.info(
                            f"Subscription path normalized: '{orig_sub}' -> '{short_sub}'"
                        )
                    body = json.dumps(data).encode("utf-8")
            except Exception as e:
                logger.error(
                    f"Error normalising Pub/Sub subscription in middleware: {e}"
                )

            async def new_receive():
                return {"type": "http.request", "body": body, "more_body": False}

            await self.app(scope, new_receive, send)
            return

        await self.app(scope, receive, send)


class DevUIScriptInjectionMiddleware:
    """Injects the currency picker script into any HTML page served by the app."""

    _UI_PATHS = {"/dev-ui", "/dev-ui/", "/", "/index.html"}

    def __init__(self, app):
        self.app = app
        self.script_bytes = CURRENCY_INJECTION_SCRIPT.encode("utf-8")

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")

        if (
            path.startswith("/apps/")
            or path.startswith("/run")
            or path.startswith("/api")
        ):
            await self.app(scope, receive, send)
            return

        if path not in self._UI_PATHS and not path.startswith("/dev-ui"):
            await self.app(scope, receive, send)
            return

        response_body = bytearray()
        original_headers = []
        status_code = 200

        async def capture_send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 200)
                original_headers.clear()
                for h in message.get("headers", []):
                    if h[0].lower() != b"content-length":
                        original_headers.append(h)
            elif message["type"] == "http.response.body":
                response_body.extend(message.get("body", b""))

        await self.app(scope, receive, capture_send)

        html = response_body.decode("utf-8", errors="replace")

        if "</body>" in html:
            html = html.replace("</body>", CURRENCY_INJECTION_SCRIPT + "</body>")

        modified_body = html.encode("utf-8")

        content_length_header = (b"content-length", str(len(modified_body)).encode())
        final_headers = original_headers + [content_length_header]

        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": final_headers,
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": modified_body,
            }
        )


app = get_fast_api_app(
    agents_dir="expense_agent",
    web=True,
    otel_to_cloud=False,
    trigger_sources=["pubsub"],
    session_service_uri=os.environ.get(
        "SESSION_DB_URL", "sqlite+aiosqlite:///./sessions.db"
    ),
)

app.add_middleware(PubSubSubscriptionNormalizerMiddleware)


_frontend_origins = os.environ.get("FRONTEND_ORIGINS", "*")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if _frontend_origins == "*" else _frontend_origins.split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
if _frontend_dir.is_dir():
    app.mount("/ui", StaticFiles(directory=str(_frontend_dir), html=True), name="ui")
    logger.info(f"Serving frontend from {_frontend_dir} at /ui")


async def diagnose_dom(request: Request):
    data = await request.json()
    with open("dom_diagnose.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting local web service on port 8080...")
    uvicorn.run(app, host="127.0.0.1", port=8080)
