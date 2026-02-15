/**
 * main.js
 * -------
 * Application entry point.
 *
 * Responsibilities:
 *   - Mount the Three.js scene into the canvas pane
 *   - Connect to the WebSocket server for live state updates
 *   - Start the render loop
 */

import { Scene3D }           from '/static/scene/scene.js';
import { mountDetailsPanel } from '/static/panels/details_panel.js';
import { mountSceneTree }    from '/static/panels/scene_tree.js';
import { WebSocketClient }   from '/static/websocket_client.js';

mountDetailsPanel();

const container = document.getElementById('canvas-pane');
const scene3d   = new Scene3D(container);

// Connect to the WebSocket server
const config = await fetch('/api/config').then(r => r.json());
const wsUrl  = `ws://${location.hostname}:${config.ws_port}`;

new WebSocketClient(
  wsUrl,
  // On scene definition (first message)
  (definition) => {
    console.log('[main] Received scene definition');
    scene3d.buildFromDefinition(definition);
    mountSceneTree(scene3d.scene);
  },
  // On state update (subsequent messages)
  (update) => {
    scene3d.updateFromState(update);
    // TODO: updateDetailsPanel if needed
  }
);

scene3d.start();