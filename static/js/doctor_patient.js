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


  const trendEl = document.getElementById("trend-chart");

  const RISK_COLOUR = { red: "#dc2626", yellow: "#d97706", green: "#0d9488" };

  function renderTrend(trend) {
    if (!trendEl) return; // trend_chart feature is off
    const points = trend.points || [];
    if (points.length < 2) {
      trendEl.textContent =
        "Grafik uchun kamida ikkita baholash kerak (hozir " + points.length + ").";
      return;
    }

    const W = 520, H = 120, PAD = 14;
    const stepX = (W - PAD * 2) / (points.length - 1);
    const y = (score) => H - PAD - (Math.max(0, Math.min(100, score)) / 100) * (H - PAD * 2);
    const coords = points.map((p, i) => [PAD + i * stepX, y(p.risk_score)]);

    const svgNS = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(svgNS, "svg");
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);
    svg.setAttribute("class", "w-full h-32");

    // Yellow and red thresholds as guide lines.
    [[34, "#fcd34d"], [67, "#fca5a5"]].forEach(([score, colour]) => {
      const line = document.createElementNS(svgNS, "line");
      line.setAttribute("x1", PAD); line.setAttribute("x2", W - PAD);
      line.setAttribute("y1", y(score)); line.setAttribute("y2", y(score));
      line.setAttribute("stroke", colour);
      line.setAttribute("stroke-dasharray", "4 4");
      svg.appendChild(line);
    });

    const path = document.createElementNS(svgNS, "polyline");
    path.setAttribute("fill", "none");
    path.setAttribute("stroke", "#0f766e");
    path.setAttribute("stroke-width", "2");
    path.setAttribute("points", coords.map((c) => c.join(",")).join(" "));
    svg.appendChild(path);

    points.forEach((p, i) => {
      const dot = document.createElementNS(svgNS, "circle");
      dot.setAttribute("cx", coords[i][0]);
      dot.setAttribute("cy", coords[i][1]);
      dot.setAttribute("r", "4");
      dot.setAttribute("fill", RISK_COLOUR[p.risk_level] || RISK_COLOUR.green);
      const title = document.createElementNS(svgNS, "title");
      title.textContent = p.risk_score + "/100 · " + p.created_at;
      dot.appendChild(title);
      svg.appendChild(dot);
    });

    trendEl.innerHTML = "";
    trendEl.appendChild(svg);
    const caption = document.createElement("div");
    caption.className = "text-xs text-slate-500 mt-1";
    caption.textContent =
      points.length + " ta baholash · hozirgi ball: " + trend.current + "/100";
    trendEl.appendChild(caption);
  }

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
    const requests = [
      api.get("/api/v1/patients/" + patientId + "/detail"),
      api.get("/api/v1/patients/" + patientId + "/timeline"),
    ];
    if (trendEl) requests.push(api.get("/api/v1/patients/" + patientId + "/trend"));
    const [detail, timeline, trend] = await Promise.all(requests);

    renderHeader(detail);
    if (trend) renderTrend(trend);

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
