/**
 * lights.js
 * ---------
 * Creates and configures all scene lights.
 *
 * Usage:
 *   import { createLights } from '/static/scene/lights.js';
 *   createLights(scene);
 */

import * as THREE from 'three';

/**
 * Add the standard lighting rig to the given scene.
 * @param {THREE.Scene} scene
 */
export function createLights(scene) {
  // Ambient — fills shadows softly
  const ambient = new THREE.AmbientLight(0x1a1f26, 3.0);
  scene.add(ambient);

  // Key light — warm amber, from upper-front-right
  const key = new THREE.DirectionalLight(0xe8922a, 2.5);
  key.position.set(5, 8, 4);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  key.shadow.camera.near = 0.5;
  key.shadow.camera.far  = 40;
  key.shadow.camera.left = key.shadow.camera.bottom = -8;
  key.shadow.camera.right = key.shadow.camera.top   =  8;
  scene.add(key);

  // Fill light — cool blue-grey, from left
  const fill = new THREE.DirectionalLight(0x4a6080, 1.0);
  fill.position.set(-4, 2, -2);
  scene.add(fill);

  // Rim light — faint, from behind/below
  const rim = new THREE.PointLight(0x2a3a4a, 2.0, 12);
  rim.position.set(0, -2, -4);
  scene.add(rim);
}