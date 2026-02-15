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

// Populate 3D models from backend, then build the scene tree
await scene3d.syncFromAPI();
mountSceneTree(scene3d.scene);

// Connect to the WebSocket server for live updates
const config = await fetch('/api/config').then(r => r.json());
const wsUrl  = `ws://${location.hostname}:${config.ws_port}`;

new WebSocketClient(wsUrl, (snapshot) => {
  scene3d.updateFromSnapshot(snapshot);
  updateDetailsPanel(snapshot);
});

scene3d.start();

/**
 * Update the details panel readouts from a scene snapshot.
 * Recursively searches the hierarchical snapshot for the first AxisRotor.
 */
function updateDetailsPanel(snapshot) {
  // Recursively find the first AxisRotor in the hierarchy
  function findRotor(node) {
    if (node.type === 'AxisRotor') return node;
    if (node.children) {
      for (const child of Object.values(node.children)) {
        const found = findRotor(child);
        if (found) return found;
      }
    }
    return null;
  }

  let props = null;
  for (const root of Object.values(snapshot)) {
    props = findRotor(root);
    if (props) break;
  }
  if (!props) return;

  const angle = document.getElementById('pos-angle');
  const speed = document.getElementById('pos-speed');
  const state = document.getElementById('pos-state');
  const maxSpd = document.getElementById('param-speed');
  const accel  = document.getElementById('param-accel');

  if (angle && props.position != null)
    angle.textContent = `${props.position.toFixed(2)}°`;
  if (speed && props.speed != null)
    speed.textContent = `${props.speed.toFixed(1)} °/s`;
  if (state && props.state != null)
    state.textContent = props.state;
  if (maxSpd && props.max_speed != null)
    maxSpd.textContent = `${props.max_speed} °/s`;
  if (accel && props.acceleration != null)
    accel.textContent = `${props.acceleration} °/s²`;
}