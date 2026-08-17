/* Patient chat: incremental polling for new messages + sending answers. */
(function () {
  "use strict";

  const root = document.getElementById("chat-root");
  if (!root) return;

  const patientId = root.dataset.patientId;
  const listEl = document.getElementById("messages");
  const emptyHint = document.getElementById("empty-hint");
  const formEl = document.getElementById("chat-form");
  const inputEl = document.getElementById("chat-input");
  const sendEl = document.getElementById("chat-send");
  const errorEl = document.getElementById("chat-error");
  const subtitleEl = document.getElementById("chat-subtitle");
  const connectionEl = document.getElementById("chat-connection");

  let lastId = 0;

  const BUBBLE = {
    patient: "ml-auto bg-teal-600 text-white",
    doctor: "mr-auto bg-amber-100 text-amber-900 border border-amber-200",
    system: "mr-auto bg-slate-100 text-slate-800",
  };

  const SENDER_LABEL = {
    doctor: "Shifokor",
    system: "Hamroh",
    patient: "Siz",
  };

  function showError(message) {
    errorEl.textContent = message;
    errorEl.classList.remove("hidden");
  }

  function clearError() {
    errorEl.classList.add("hidden");
  }

  function renderMessage(message) {
    if (emptyHint) emptyHint.remove();

    const wrapper = document.createElement("div");
    wrapper.className = "flex";

    const bubble = document.createElement("div");
    bubble.className =
      "max-w-[80%] rounded-2xl px-4 py-2 text-sm whitespace-pre-wrap " +
      (BUBBLE[message.sender] || BUBBLE.system);

    const label = document.createElement("div");
    label.className = "text-[11px] opacity-70 mb-0.5";
    label.textContent = SENDER_LABEL[message.sender] || message.sender;

    const text = document.createElement("div");
    text.textContent = message.text;

    bubble.appendChild(label);
    bubble.appendChild(text);
    wrapper.appendChild(bubble);
    if (message.sender === "patient") wrapper.classList.add("justify-end");
    listEl.appendChild(wrapper);

    lastId = Math.max(lastId, message.id);
  }

  function scrollToEnd() {
    listEl.scrollTop = listEl.scrollHeight;
  }

  async function refreshStatus() {
    const status = await api.get("/api/v1/patients/" + patientId + "/status");
    if (status.pending_question) {
      subtitleEl.textContent =
        status.current_day + "-kun · javob kutilmoqda";
      inputEl.placeholder =
        (status.pending_question.config &&
          status.pending_question.config.placeholder) ||
        "Javobingizni yozing…";
    } else {
      subtitleEl.textContent =
        status.current_day + "-kun · yangi savol yo'q";
      inputEl.placeholder = "Xabar yozing…";
    }
  }

  async function fetchNewMessages() {
    const data = await api.get(
      "/api/v1/patients/" + patientId + "/messages?after_id=" + lastId
    );
    if (data.messages.length) {
      data.messages.forEach(renderMessage);
      scrollToEnd();
      await refreshStatus();
    }
  }

  const poller = startPolling(fetchNewMessages, {
    intervalMs: 3000,
    onOk: () => {
      connectionEl.textContent = "•";
      connectionEl.className = "text-xs text-teal-500";
      clearError();
    },
    onError: (err) => {
      connectionEl.textContent = "•";
      connectionEl.className = "text-xs text-red-500";
      showError(err.message);
    },
  });

  formEl.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = inputEl.value.trim();
    if (!text) return;

    sendEl.disabled = true;
    try {
      await api.post("/api/v1/patients/" + patientId + "/messages", { text: text });
      inputEl.value = "";
      clearError();
      await fetchNewMessages();
    } catch (err) {
      showError(err.message);
    } finally {
      sendEl.disabled = false;
      inputEl.focus();
    }
  });

  refreshStatus().catch((err) => showError(err.message));
  poller.now();
})();
