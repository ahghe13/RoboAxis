/**
 * websocket_client.js
 * -------------------
 * Connects to the backend WebSocket server, receives scene snapshots,
 * and dispatches updates to the 3D scene and details panel.
 */

export class WebSocketClient {
  /**
   * @param {string} url       WebSocket URL, e.g. "ws://localhost:8765"
   * @param {function} onSnapshot  Callback invoked with each snapshot object
   */
  constructor(url, onSnapshot) {
    this._url = url;
    this._onSnapshot = onSnapshot;
    this._ws = null;
    this._connect();
  }

  _connect() {
    this._ws = new WebSocket(this._url);

    this._ws.onopen = () => {
      console.log(`[ws] Connected to ${this._url}`);
    };

    this._ws.onmessage = (event) => {
      try {
        const snapshot = JSON.parse(event.data);
        this._onSnapshot(snapshot);
      } catch (e) {
        console.warn('[ws] Failed to parse message:', e);
      }
    };

    this._ws.onclose = () => {
      console.log('[ws] Connection closed, reconnecting in 2s…');
      setTimeout(() => this._connect(), 2000);
    };

    this._ws.onerror = (err) => {
      console.warn('[ws] Error:', err);
      this._ws.close();
    };
  }

  close() {
    if (this._ws) {
      this._ws.onclose = null;  // prevent auto-reconnect
      this._ws.close();
      this._ws = null;
    }
  }
}