/* One fetch helper for the whole frontend.
 * Every /api/v1/* response is {ok:true,data} or {ok:false,error} — unwrapping
 * and error handling live here so new endpoints need no new plumbing. */
(function () {
  "use strict";

  class ApiError extends Error {
    constructor(code, message, status) {
      super(message || "Xatolik yuz berdi.");
      this.code = code || "unknown_error";
      this.status = status;
    }
  }

  async function request(path, options) {
    const opts = options || {};
    let response;
    try {
      response = await fetch(path, {
        method: opts.method || "GET",
        headers: opts.body ? { "Content-Type": "application/json" } : {},
        body: opts.body ? JSON.stringify(opts.body) : undefined,
      });
    } catch (networkError) {
      throw new ApiError("network_error", "Aloqa yo'q. Internetni tekshiring.", 0);
    }

    let payload = null;
    try {
      payload = await response.json();
    } catch (parseError) {
      throw new ApiError("bad_response", "Server javobi tushunarsiz.", response.status);
    }

    if (!payload || payload.ok !== true) {
      const error = (payload && payload.error) || {};
      throw new ApiError(error.code, error.message, response.status);
    }
    return payload.data;
  }

  window.api = {
    ApiError: ApiError,
    get: (path) => request(path, { method: "GET" }),
    post: (path, body) => request(path, { method: "POST", body: body || {} }),
  };
})();
