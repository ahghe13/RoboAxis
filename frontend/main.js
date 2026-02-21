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
import { mountSceneTree, selectComponentInTree }     from '/static/panels/scene_tree.js';
import { WebSocketClient }                           from '/static/websocket_client.js';

mountDetailsPanel();

const container = document.getElementById('canvas-pane');
const scene3d   = new Scene3D(container);

// Flat component list kept in sync for id → component lookups
let _allComponents = [];

/** Called whenever a component is selected from either the tree or the viewport. */
function onSelect(component) {
  showComponentDetails(component);
  scene3d.selectComponent(component.id);
  selectComponentInTree(component.id);
}

// Register 3D click-picking once; the callback closes over _allComponents
scene3d.setPicking((id) => {
  const component = _allComponents.find(c => c.id === id);
  if (component) onSelect(component);
});

// Connect to the WebSocket server
const config = await fetch('/api/config').then(r => r.json());
const wsUrl  = `ws://${location.hostname}:${config.ws_port}`;

/** Apply a received scene definition to all subsystems. */
function applyDefinition(definition) {
  _allComponents = definition.components;
  setComponents(definition.components);
  scene3d.buildFromDefinition(definition);
  mountSceneTree(definition, onSelect, onAddRobot);
}

/** Re-fetch the full scene definition and rebuild the 3D scene and tree. */
async function rebuildFromServer() {
  const definition = await fetch('/api/scene/definition').then(r => r.json());
  applyDefinition(definition);
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
    applyDefinition(definition);
  },
  // On state update (subsequent messages)
  (update) => {
    scene3d.updateFromState(update);
    updateComponentState(update.components);
  }
);

scene3d.start();