/**
 * camera.js
 * ---------
 * Camera setup and orbit controls for the 3D viewport.
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export class CameraRig {
  /**
   * @param {HTMLCanvasElement} domElement  Renderer's canvas for orbit controls.
   * @param {number} aspect  Initial aspect ratio (width / height).
   */
  constructor(domElement, aspect) {
    this.camera = new THREE.PerspectiveCamera(45, aspect, 0.1, 200);
    this.camera.position.set(4, 3, 5);
    this.camera.lookAt(0, 0, 0);

    this.controls = new OrbitControls(this.camera, domElement);
    this.controls.enableDamping      = true;
    this.controls.dampingFactor      = 0.06;
    this.controls.screenSpacePanning = false;
    this.controls.minDistance         = 1.5;
    this.controls.maxDistance         = 30;
    this.controls.maxPolarAngle      = Math.PI * 0.52;  // prevent going underground
    this.controls.target.set(0, 0, 0);
  }

  /** Update aspect ratio (call on container resize). */
  resize(width, height) {
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
  }

  /** Advance orbit-control damping (call each frame). */
  update() {
    this.controls.update();
  }
}