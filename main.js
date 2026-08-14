/* CaribTech Labs - main frontend behavior (vanilla JS, no dependencies) */

document.addEventListener("DOMContentLoaded", function () {
  initMobileMenu();
  initFileDropLabel();
  initChatbot();
  initDealClicks();
});

/* ---------------------------------------------------------------------- */
/* Mobile nav                                                              */
/* ---------------------------------------------------------------------- */
function initMobileMenu() {
  const toggle = document.querySelector(".navbar__toggle");
  const menu = document.querySelector(".mobile-menu");
  if (!toggle || !menu) return;

  toggle.addEventListener("click", function () {
    const isOpen = menu.classList.toggle("is-open");
    toggle.setAttribute("aria-expanded", isOpen ? "true" : "false");
  });
}

/* ---------------------------------------------------------------------- */
/* File input UX for the project request form                             */
/* ---------------------------------------------------------------------- */
function initFileDropLabel() {
  const input = document.getElementById("attachments");
  const label = document.getElementById("file-drop-label");
  if (!input || !label) return;

  const defaultText = label.textContent;
  input.addEventListener("change", function () {
    if (input.files.length === 0) {
      label.textContent = defaultText;
    } else if (input.files.length === 1) {
      label.textContent = input.files[0].name;
    } else {
      label.textContent = input.files.length + " files selected";
    }
  });
}

/* ---------------------------------------------------------------------- */
/* Deal click tracking (internal analytics, non-invasive)                  */
/* ---------------------------------------------------------------------- */
function initDealClicks() {
  document.querySelectorAll("[data-deal-id]").forEach(function (el) {
    el.addEventListener("click", function () {
      const dealId = el.getAttribute("data-deal-id");
      fetch("/deals/" + dealId + "/click", { method: "POST" }).catch(function () {});
    });
  });
}

/* ---------------------------------------------------------------------- */
/* Chatbot widget                                                          */
/* ---------------------------------------------------------------------- */
function initChatbot() {
  const launcher = document.getElementById("chatbot-launcher");
  const win = document.getElementById("chatbot-window");
  if (!launcher || !win) return;

  const closeBtn = document.getElementById("chatbot-close");
  const body = document.getElementById("chatbot-body");
  const form = document.getElementById("chatbot-form");
  const input = document.getElementById("chatbot-input");

  let initialized = false;

  launcher.addEventListener("click", function () {
    win.classList.toggle("is-open");
    if (win.classList.contains("is-open") && !initialized) {
      initialized = true;
      loadChatbotInit();
    }
  });

  if (closeBtn) {
    closeBtn.addEventListener("click", function () {
      win.classList.remove("is-open");
    });
  }

  function loadChatbotInit() {
    fetch("/api/chatbot/init")
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (!data.enabled) {
          appendBotMessage("Chat is currently unavailable. Please use our Contact page instead.");
          return;
        }
        appendBotMessage(data.welcome_message);
        if (data.suggested_questions && data.suggested_questions.length) {
          appendSuggestions(data.suggested_questions);
        }
      })
      .catch(function () {
        appendBotMessage("Sorry, something went wrong loading the chat.");
      });
  }

  function appendBotMessage(text, showCta) {
    const msg = document.createElement("div");
    msg.className = "chat-msg chat-msg--bot";
    msg.textContent = text;
    if (showCta) {
      const ctaWrap = document.createElement("div");
      ctaWrap.className = "chat-msg__cta";
      const cta = document.createElement("a");
      cta.href = "/request";
      cta.className = "btn btn--primary btn--sm";
      cta.textContent = "Start a Project";
      ctaWrap.appendChild(cta);
      msg.appendChild(ctaWrap);
    }
    body.appendChild(msg);
    body.scrollTop = body.scrollHeight;
  }

  function appendUserMessage(text) {
    const msg = document.createElement("div");
    msg.className = "chat-msg chat-msg--user";
    msg.textContent = text;
    body.appendChild(msg);
    body.scrollTop = body.scrollHeight;
  }

  function appendSuggestions(questions) {
    const wrap = document.createElement("div");
    wrap.className = "chat-suggestions";
    questions.forEach(function (q) {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "chat-suggestion-btn";
      btn.textContent = q;
      btn.addEventListener("click", function () {
        sendMessage(q);
      });
      wrap.appendChild(btn);
    });
    body.appendChild(wrap);
    body.scrollTop = body.scrollHeight;
  }

  function sendMessage(text) {
    appendUserMessage(text);
    fetch("/api/chatbot/message", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    })
      .then(function (res) { return res.json(); })
      .then(function (data) {
        if (data.error) {
          appendBotMessage(data.error);
          return;
        }
        appendBotMessage(data.answer, data.show_cta);
      })
      .catch(function () {
        appendBotMessage("Sorry, I couldn't process that. Please try again.");
      });
  }

  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      const text = input.value.trim();
      if (!text) return;
      sendMessage(text);
      input.value = "";
    });
  }
}
