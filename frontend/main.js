/**
 * main.js
 * -------
 * Application entry point.
 *
 * Responsibilities:
 *   - Mount the Three.js scene into the canvas pane
 *   - Start the render loop
 *
 * Future additions (UI controls, API polling, axis model) belong in
 * separate modules imported here.
 */

import { Scene3D } from '/static/scene.js';

const container = document.getElementById('canvas-pane');
const scene3d   = new Scene3D(container);

scene3d.start();
