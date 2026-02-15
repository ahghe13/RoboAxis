/**
 * websocket_client.js
 * -------------------
 * Connects to the backend WebSocket server, receives scene snapshots,
 * and dispatches updates to the 3D scene and details panel.
 */

export class WebSocketClient {
  /**
   * @param {string} url            WebSocket URL, e.g. "ws://localhost:8765"
   * @param {function} onDefinition Callback invoked with scene definition
   * @param {function} onUpdate     Callback invoked with state updates
   */
  constructor(url, onDefinition, onUpdate) {
    this._url = url;
    this._onDefinition = onDefinition;
    this._onUpdate = onUpdate;
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
        const message = JSON.parse(event.data);

        if (message.type === 'static_scene_definition') {
          this._onDefinition(message);
        } else if (message.type === 'state_update') {
          this._onUpdate(message);
        } else {
          console.warn('[ws] Unknown message type:', message.type);
        }
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