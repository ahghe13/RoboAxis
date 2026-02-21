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

import { Scene3D }                                    from '/static/scene/scene.js';
import { mountDetailsPanel, showComponentDetails, updateComponentState, setComponents } from '/static/panels/details_panel.js';
import { mountSceneTree }                            from '/static/panels/scene_tree.js';
import { WebSocketClient }                           from '/static/websocket_client.js';

mountDetailsPanel();

const container = document.getElementById('canvas-pane');
const scene3d   = new Scene3D(container);

// Connect to the WebSocket server
const config = await fetch('/api/config').then(r => r.json());
const wsUrl  = `ws://${location.hostname}:${config.ws_port}`;

/** Re-fetch the full scene definition and rebuild the 3D scene and tree. */
async function rebuildFromServer() {
  const definition = await fetch('/api/scene/definition').then(r => r.json());
  setComponents(definition.components);
  scene3d.buildFromDefinition(definition);
  mountSceneTree(definition, showComponentDetails, onAddRobot);
}

/** Add a robot from a device file, then rebuild. */
async function onAddRobot(filename) {
  await fetch('/api/scene/robots', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device: filename }),
  });
  await rebuildFromServer();
}

new WebSocketClient(
  wsUrl,
  // On scene definition (first message)
  (definition) => {
    console.log('[main] Received scene definition');
    setComponents(definition.components);
    scene3d.buildFromDefinition(definition);
    mountSceneTree(definition, showComponentDetails, onAddRobot);
  },
  // On state update (subsequent messages)
  (update) => {
    scene3d.updateFromState(update);
    updateComponentState(update.components);
  }
);

scene3d.start();