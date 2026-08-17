/* Doctor dashboard: patient list + active alerts, polled every 3 seconds. */
(function () {
  "use strict";

  const root = document.getElementById("dashboard-root");
  if (!root) return;

  const doctorId = root.dataset.doctorId;
  const patientsEl = document.getElementById("patients");
  const alertsEl = document.getElementById("alerts");
  const errorEl = document.getElementById("dash-error");
  const connectionEl = document.getElementById("dash-connection");

  // Colour coding is data-driven: the risk level names the style.
  const RISK = {
    red: {
      row: "border-red-300 bg-red-50",
      dot: "bg-red-500",
      label: "Shoshilinch",
      text: "text-red-700",
    },
    yellow: {
      row: "border-amber-300 bg-amber-50",
      dot: "bg-amber-500",
      label: "Eʼtibor kerak",
      text: "text-amber-700",
    },
    green: {
      row: "border-slate-200 bg-white",
      dot: "bg-teal-500",
      label: "Barqaror",
      text: "text-teal-700",
    },
  };

  function riskStyle(level) {
    return RISK[level] || RISK.green;
  }

  function setText(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
  }

  function showError(message) {
    errorEl.textContent = message;
    errorEl.classList.remove("hidden");
  }

  function renderPatient(patient) {
    const style = riskStyle(patient.risk_level);
    const card = document.createElement("a");
    card.href = "/doctor/patient/" + patient.id;
    card.className =
      "block rounded-xl border p-4 transition hover:shadow-sm " + style.row;

    const head = document.createElement("div");
    head.className = "flex items-center justify-between gap-3";

    const left = document.createElement("div");
    left.className = "flex items-center gap-2";
    const dot = document.createElement("span");
    dot.className = "inline-block w-2.5 h-2.5 rounded-full " + style.dot;
    const name = document.createElement("span");
    name.className = "font-medium";
    name.textContent = patient.full_name;
    left.appendChild(dot);
    left.appendChild(name);

    const badge = document.createElement("span");
    badge.className = "text-xs font-medium " + style.text;
    badge.textContent = style.label;

    head.appendChild(left);
    head.appendChild(badge);
    card.appendChild(head);

    const meta = document.createElement("div");
    meta.className = "text-xs text-slate-500 mt-1";
    meta.textContent =
      patient.current_day + "-kun · " + (patient.diagnosis || "");
    card.appendChild(meta);

    if (patient.latest_assessment && patient.latest_assessment.reasoning) {
      const why = document.createElement("div");
      why.className = "text-sm text-slate-700 mt-2";
      why.textContent = patient.latest_assessment.reasoning;
      card.appendChild(why);
    }

    if (patient.open_alerts > 0) {
      const alerts = document.createElement("div");
      alerts.className = "text-xs mt-2 " + style.text;
      alerts.textContent = patient.open_alerts + " ta ochiq signal";
      card.appendChild(alerts);
    }

    return card;
  }

  function renderAlert(alert) {
    const style = riskStyle(alert.severity);
    const row = document.createElement("div");
    row.className = "rounded-lg border p-3 flex items-start gap-2 " + style.row;

    const dot = document.createElement("span");
    dot.className = "inline-block w-2 h-2 rounded-full mt-1.5 " + style.dot;

    const body = document.createElement("div");
    const title = document.createElement("div");
    title.className = "text-sm font-medium";
    title.textContent = alert.title;
    const when = document.createElement("div");
    when.className = "text-xs text-slate-500";
    when.textContent = alert.created_at;
    body.appendChild(title);
    body.appendChild(when);

    const resolve = document.createElement("button");
    resolve.className =
      "ml-auto text-xs rounded-lg border border-slate-300 bg-white px-3 py-2 hover:bg-slate-100";
    resolve.textContent = "Yopish";
    resolve.addEventListener("click", async () => {
      resolve.disabled = true;
      try {
        await api.post("/api/v1/alerts/" + alert.id + "/resolve", {});
        await refresh();
      } catch (err) {
        showError(err.message);
        resolve.disabled = false;
      }
    });

    row.appendChild(dot);
    row.appendChild(body);
    row.appendChild(resolve);
    return row;
  }

  const EVENT_LABEL = {
    "checkin.sent": "Savol yuborildi",
    "checkin.answered": "Bemor javob berdi",
    "assessment.created": "Tahlil tugadi",
    "alert.raised": "Signal yaratildi",
    "alert.resolved": "Signal yopildi",
    "doctor.replied": "Shifokor xabar yubordi",
  };

  function renderEvent(event) {
    const row = document.createElement("div");
    row.className = "px-3 py-2 flex items-baseline gap-2 text-sm";

    const name = document.createElement("span");
    name.className = "font-medium";
    name.textContent = EVENT_LABEL[event.event_name] || event.event_name;

    const code = document.createElement("code");
    code.className = "text-[11px] text-slate-400";
    code.textContent = event.event_name;

    const payload = document.createElement("span");
    payload.className = "text-xs text-slate-500 ml-auto";
    payload.textContent = JSON.stringify(event.payload);

    row.appendChild(name);
    row.appendChild(code);
    row.appendChild(payload);
    return row;
  }

  function replaceChildren(el, nodes, emptyMessage) {
    el.innerHTML = "";
    if (!nodes.length) {
      const empty = document.createElement("p");
      empty.className = "text-sm text-slate-400";
      empty.textContent = emptyMessage;
      el.appendChild(empty);
      return;
    }
    nodes.forEach((n) => el.appendChild(n));
  }

  async function refresh() {
    const [dashboard, alerts, events] = await Promise.all([
      api.get("/api/v1/doctors/" + doctorId + "/dashboard"),
      api.get("/api/v1/doctors/" + doctorId + "/alerts?status=new"),
      api.get("/api/v1/demo/events?limit=20"),
    ]);

    setText("count-total", dashboard.counts.total);
    setText("count-red", dashboard.counts.red);
    setText("count-yellow", dashboard.counts.yellow);
    setText("count-alerts", dashboard.counts.new_alerts);

    replaceChildren(
      patientsEl,
      dashboard.patients.map(renderPatient),
      "Bemorlar topilmadi."
    );
    replaceChildren(
      alertsEl,
      alerts.alerts.map(renderAlert),
      "Faol signal yoʻq."
    );
    replaceChildren(
      document.getElementById("events"),
      events.events.map(renderEvent),
      "Voqealar yoʻq."
    );
  }

  const resetBtn = document.getElementById("demo-reset");
  if (resetBtn) {
    resetBtn.addEventListener("click", async () => {
      resetBtn.disabled = true;
      try {
        await api.post("/api/v1/demo/reset", {});
        await refresh();
      } catch (err) {
        showError(err.message);
      } finally {
        resetBtn.disabled = false;
      }
    });
  }

  startPolling(refresh, {
    intervalMs: 3000,
    onOk: () => {
      connectionEl.textContent = "yangilandi";
      connectionEl.className = "text-xs text-teal-600";
      errorEl.classList.add("hidden");
    },
    onError: (err) => {
      connectionEl.textContent = "aloqa yoʻq";
      connectionEl.className = "text-xs text-red-500";
      showError(err.message);
    },
  });
})();
