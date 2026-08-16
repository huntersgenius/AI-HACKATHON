/* Patient detail: merged timeline + sending a message to the patient. */
(function () {
  "use strict";

  const root = document.getElementById("detail-root");
  if (!root) return;

  const patientId = root.dataset.patientId;
  const doctorId = root.dataset.doctorId;
  const timelineEl = document.getElementById("timeline");
  const formEl = document.getElementById("reply-form");
  const inputEl = document.getElementById("reply-input");
  const sendEl = document.getElementById("reply-send");
  const errorEl = document.getElementById("detail-error");

  const RISK = {
    red: { badge: "bg-red-100 text-red-700", label: "Shoshilinch", card: "border-red-300 bg-red-50" },
    yellow: { badge: "bg-amber-100 text-amber-700", label: "Eʼtibor kerak", card: "border-amber-300 bg-amber-50" },
    green: { badge: "bg-teal-100 text-teal-700", label: "Barqaror", card: "border-teal-200 bg-teal-50" },
  };

  const SENDER = {
    system: { label: "Hamroh savoli", css: "border-slate-200 bg-white" },
    patient: { label: "Bemor javobi", css: "border-slate-200 bg-slate-50" },
    doctor: { label: "Shifokor xabari", css: "border-teal-200 bg-teal-50" },
  };

  const SOURCE = { llm: "AI tahlili", rules: "Qoidalar", merged: "AI + qoidalar" };

  function showError(message) {
    errorEl.textContent = message;
    errorEl.classList.remove("hidden");
  }

  function riskStyle(level) {
    return RISK[level] || RISK.green;
  }

  function block(css) {
    const el = document.createElement("div");
    el.className = "rounded-lg border p-3 " + css;
    return el;
  }

  function label(text, css) {
    const el = document.createElement("div");
    el.className = "text-[11px] uppercase tracking-wide " + (css || "text-slate-400");
    el.textContent = text;
    return el;
  }

  function renderMessage(item) {
    const meta = SENDER[item.sender] || SENDER.system;
    const el = block(meta.css);
    el.appendChild(label(meta.label + " · " + item.created_at));
    const body = document.createElement("div");
    body.className = "text-sm mt-1 whitespace-pre-wrap";
    body.textContent = item.text;
    el.appendChild(body);
    return el;
  }

  function renderAssessment(item) {
    const style = riskStyle(item.risk_level);
    const el = block(style.card);
    el.appendChild(
      label(style.label + " · " + (SOURCE[item.source] || item.source) +
            " · " + item.risk_score + "/100")
    );
    if (item.reasoning) {
      const why = document.createElement("div");
      why.className = "text-sm mt-1";
      why.textContent = item.reasoning;
      el.appendChild(why);
    }
    if (item.danger_signals && item.danger_signals.length) {
      const sig = document.createElement("div");
      sig.className = "text-xs text-slate-500 mt-1";
      sig.textContent = "Belgilar: " + item.danger_signals.join(", ");
      el.appendChild(sig);
    }
    if (item.recommended_action) {
      const act = document.createElement("div");
      act.className = "text-xs font-medium mt-1";
      act.textContent = item.recommended_action;
      el.appendChild(act);
    }
    return el;
  }

  function renderHeader(detail) {
    const badge = document.getElementById("risk-badge");
    const style = riskStyle(detail.patient.risk_level);
    badge.className =
      "inline-block rounded-full px-3 py-1 text-xs font-medium " + style.badge;
    badge.textContent = style.label;

    document.getElementById("day-label").textContent =
      detail.patient.current_day + "-kun";

    const reasoning = document.getElementById("latest-reasoning");
    const action = document.getElementById("latest-action");
    const latest = detail.latest_assessment;
    if (latest && latest.reasoning) {
      reasoning.textContent = latest.reasoning;
      reasoning.classList.remove("hidden");
    } else {
      reasoning.classList.add("hidden");
    }
    if (latest && latest.recommended_action) {
      action.textContent = latest.recommended_action;
      action.classList.remove("hidden");
    } else {
      action.classList.add("hidden");
    }
  }

  async function refresh() {
    const [detail, timeline] = await Promise.all([
      api.get("/api/v1/patients/" + patientId + "/detail"),
      api.get("/api/v1/patients/" + patientId + "/timeline"),
    ]);

    renderHeader(detail);

    timelineEl.innerHTML = "";
    if (!timeline.items.length) {
      const empty = document.createElement("p");
      empty.className = "text-sm text-slate-400";
      empty.textContent = "Hozircha yozuv yoʻq.";
      timelineEl.appendChild(empty);
      return;
    }
    timeline.items.forEach((item) => {
      timelineEl.appendChild(
        item.kind === "assessment" ? renderAssessment(item) : renderMessage(item)
      );
    });
    timelineEl.scrollTop = timelineEl.scrollHeight;
  }

  startPolling(refresh, {
    intervalMs: 3000,
    onOk: () => errorEl.classList.add("hidden"),
    onError: (err) => showError(err.message),
  });

  formEl.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = inputEl.value.trim();
    if (!text) return;

    sendEl.disabled = true;
    try {
      await api.post("/api/v1/patients/" + patientId + "/doctor-message", {
        text: text,
        doctor_id: Number(doctorId),
      });
      inputEl.value = "";
      errorEl.classList.add("hidden");
      await refresh();
    } catch (err) {
      showError(err.message);
    } finally {
      sendEl.disabled = false;
      inputEl.focus();
    }
  });
})();
