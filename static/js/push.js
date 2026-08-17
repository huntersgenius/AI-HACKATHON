/* Web Push opt-in: registers the service worker, subscribes the browser,
 * and sends the subscription to /api/v1/push/subscribe. One button per page
 * calls HamrohPush.init(type, id, buttonId) — type is 'patient' or 'doctor'. */
(function () {
  "use strict";

  function urlBase64ToUint8Array(base64) {
    const padding = "=".repeat((4 - (base64.length % 4)) % 4);
    const base64Safe = (base64 + padding).replace(/-/g, "+").replace(/_/g, "/");
    const raw = atob(base64Safe);
    const output = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; ++i) output[i] = raw.charCodeAt(i);
    return output;
  }

  function setButtonState(btn, enabled) {
    btn.textContent = enabled
      ? "🔔 Bildirishnomalar yoqilgan"
      : "🔕 Bildirishnomalarni yoqish";
    btn.classList.toggle("bg-teal-600", enabled);
    btn.classList.toggle("text-white", enabled);
    btn.classList.toggle("bg-white", !enabled);
    btn.disabled = false;
  }

  async function init(subscriberType, subscriberId, buttonId) {
    const btn = document.getElementById(buttonId);
    if (!btn) return;

    if (!("serviceWorker" in navigator) || !("PushManager" in window)) {
      btn.remove();
      return;
    }

    let registration;
    try {
      registration = await navigator.serviceWorker.register("/sw.js");
    } catch (err) {
      btn.remove();
      return;
    }

    const existing = await registration.pushManager.getSubscription();
    setButtonState(btn, !!existing);

    btn.addEventListener("click", async () => {
      btn.disabled = true;
      try {
        const already = await registration.pushManager.getSubscription();
        if (already) {
          await already.unsubscribe();
          await api.post("/api/v1/push/unsubscribe", { endpoint: already.endpoint });
          setButtonState(btn, false);
          return;
        }

        const permission = await Notification.requestPermission();
        if (permission !== "granted") {
          setButtonState(btn, false);
          return;
        }

        const { key } = await api.get("/api/v1/push/vapid-public-key");
        if (!key) {
          btn.remove();
          return;
        }

        const subscription = await registration.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: urlBase64ToUint8Array(key),
        });

        await api.post("/api/v1/push/subscribe", {
          subscriber_type: subscriberType,
          subscriber_id: subscriberId,
          subscription: subscription.toJSON(),
        });
        setButtonState(btn, true);
      } catch (err) {
        setButtonState(btn, false);
      }
    });
  }

  window.HamrohPush = { init: init };
})();
