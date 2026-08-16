/* Reusable polling utility: run `tick` every `intervalMs` (default 3s).
 * A failing tick is reported and the loop keeps going — a dropped request
 * must never stop the demo. Polling pauses while the tab is hidden. */
(function () {
  "use strict";

  function startPolling(tick, options) {
    const opts = options || {};
    const intervalMs = opts.intervalMs || 3000;
    let timer = null;
    let running = false;
    let stopped = false;

    async function run() {
      if (running || stopped) return;
      if (document.hidden) return;
      running = true;
      try {
        await tick();
        if (opts.onOk) opts.onOk();
      } catch (err) {
        if (opts.onError) opts.onError(err);
      } finally {
        running = false;
      }
    }

    run();
    timer = setInterval(run, intervalMs);
    document.addEventListener("visibilitychange", () => {
      if (!document.hidden) run();
    });

    return {
      now: run,
      stop: () => {
        stopped = true;
        clearInterval(timer);
      },
    };
  }

  window.startPolling = startPolling;
})();
