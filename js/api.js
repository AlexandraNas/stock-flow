// Thin fetch wrapper for the StockFlow API. Every call sends/receives
// JSON and includes the session cookie so Flask's login-gated routes work.

const api = {
  async _request(method, path, body) {
    const opts = {
      method,
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
    };
    if (body !== undefined) opts.body = JSON.stringify(body);

    const res = await fetch(path, opts);
    let data = null;
    try {
      data = await res.json();
    } catch (e) {
      data = null;
    }
    if (!res.ok) {
      const message = (data && data.error) || `Request failed (${res.status})`;
      throw new Error(message);
    }
    return data;
  },

  get(path) { return this._request("GET", path); },
  post(path, body) { return this._request("POST", path, body ?? {}); },
  put(path, body) { return this._request("PUT", path, body ?? {}); },
  del(path) { return this._request("DELETE", path); },
};
