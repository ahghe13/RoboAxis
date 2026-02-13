/**
 * models/scene_object.js
 * ----------------------
 * Interface for objects that can describe themselves in the UI.
 * Subclasses must implement getName() and getProperties().
 */

import * as THREE from 'three';

export class SceneObject extends THREE.Group {
  /** @returns {string} Display name of this object. */
  getName() {
    throw new Error('getName() not implemented');
  }

  /** @returns {object} Key-value properties describing current state. */
  getProperties() {
    throw new Error('getProperties() not implemented');
  }
}