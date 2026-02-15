/**
 * scene.js
 * --------
 * Encapsulates the Three.js scene, renderer, lights, and environment.
 * Camera and orbit controls live in camera.js.
 *
 * Usage:
 *   import { Scene3D } from '/static/scene/scene.js';
 *   const scene = new Scene3D(document.getElementById('canvas-pane'));
 *   scene.start();
 */

import * as THREE from 'three';
import { CameraRig }    from '/static/scene/camera.js';
import { createLights } from '/static/scene/lights.js';
import { Frame }         from '/static/models/frame.js';
import { AxisBase, AxisRotor }     from '/static/models/rotary_axis.js';
import { Link }                     from '/static/models/link.js';
import { Joint }                    from '/static/models/joint.js';
import { RobotLink, RobotJoint }   from '/static/models/three_axis_robot.js';

/** Maps backend component type names to frontend model constructors. */
const MODEL_MAP = {
  AxisBase,
  AxisRotor,
  Link,
  Joint,
  RobotLink,
  RobotJoint,
};

export class Scene3D {
  /**
   * @param {HTMLElement} container  Element the canvas will be appended to.
   */
  constructor(container) {
    this._container  = container;
    this._animId     = null;
    this._components = {};   // name → 3D model instance

    this._initRenderer();
    this._initCamera();
    this._initLights();
    this._initEnvironment();
    this._initResize();
  }

  // ── Renderer ─────────────────────────────────────────────────────────────

  _initRenderer() {
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x0d0e0f);
    // Subtle fog to give depth
    this.scene.fog = new THREE.FogExp2(0x0d0e0f, 0.04);

    this.renderer = new THREE.WebGLRenderer({
      antialias: true,
      powerPreference: 'high-performance',
    });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type    = THREE.PCFSoftShadowMap;
    this.renderer.toneMapping       = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.1;

    this._resize();
    this._container.appendChild(this.renderer.domElement);
  }

  // ── Camera ────────────────────────────────────────────────────────────────

  _initCamera() {
    const { width, height } = this._dimensions();
    this._cameraRig = new CameraRig(this.renderer.domElement, width / height);
    this.camera   = this._cameraRig.camera;
    this.controls = this._cameraRig.controls;
  }

  // ── Lights ────────────────────────────────────────────────────────────────

  _initLights() {
    createLights(this.scene);
  }

  // ── Environment (grid + axis markers) ────────────────────────────────────

  _initEnvironment() {
    this.scene.add(new Frame());
  }

  // ── API sync ────────────────────────────────────────────────────────────

  /**
   * Fetch /api/scene and add/update 3D models to match backend state.
   */
  async syncFromAPI() {
    const res  = await fetch('/api/scene');
    const data = await res.json();
    this._applySnapshot(data);
  }

  /**
   * Apply a scene snapshot: create/update/remove 3D models to match.
   * @param {Object} data  Flat snapshot from backend (name → props).
   *                       Transforms are absolute world matrices (4x4).
   */
  _applySnapshot(data) {
    const seenNames = new Set();

    // Process each component (flat iteration)
    for (const [name, props] of Object.entries(data)) {
      seenNames.add(name);

      // 1. Get or create the model
      let model = this._components[name];
      if (!model) {
        const Ctor = MODEL_MAP[props.type];
        if (!Ctor) continue;
        model = new Ctor();
        model.name = name;
        this._components[name] = model;
        this.scene.add(model);  // Add directly to scene (world space)
      }

      // 2. Apply absolute world transform from 4x4 matrix
      if (props.matrix) {
        // Backend sends 4x4 matrix as nested array [[row0], [row1], [row2], [row3]]
        // in row-major order. Dynamic rotations (from joints/rotors) are already baked in.
        const mat = new THREE.Matrix4();
        mat.set(
          props.matrix[0][0], props.matrix[0][1], props.matrix[0][2], props.matrix[0][3],
          props.matrix[1][0], props.matrix[1][1], props.matrix[1][2], props.matrix[1][3],
          props.matrix[2][0], props.matrix[2][1], props.matrix[2][2], props.matrix[2][3],
          props.matrix[3][0], props.matrix[3][1], props.matrix[3][2], props.matrix[3][3]
        );

        // Apply the matrix and decompose it to update position/rotation/scale
        model.matrix.copy(mat);
        model.matrix.decompose(model.position, model.quaternion, model.scale);
        model.matrixAutoUpdate = false;
      }
    }

    // Remove models no longer in the backend
    for (const name of Object.keys(this._components)) {
      if (!seenNames.has(name)) {
        const model = this._components[name];
        if (model.parent) model.parent.remove(model);
        delete this._components[name];
      }
    }
  }

  /**
   * Called on each WebSocket snapshot to update scene and UI.
   * @param {Object} snapshot  Scene snapshot from backend.
   */
  updateFromSnapshot(snapshot) {
    this._applySnapshot(snapshot);
  }

  // ── Resize handling ───────────────────────────────────────────────────────

  _dimensions() {
    return {
      width:  this._container.clientWidth  || window.innerWidth,
      height: this._container.clientHeight || window.innerHeight,
    };
  }

  _resize() {
    const { width, height } = this._dimensions();
    this.renderer.setSize(width, height);
    if (this._cameraRig) {
      this._cameraRig.resize(width, height);
    }
  }

  _initResize() {
    this._resizeObserver = new ResizeObserver(() => this._resize());
    this._resizeObserver.observe(this._container);
  }

  // ── Render loop ───────────────────────────────────────────────────────────

  start() {
    const tick = () => {
      this._animId = requestAnimationFrame(tick);
      this._cameraRig.update();
      this.renderer.render(this.scene, this.camera);
    };
    tick();
  }

  stop() {
    if (this._animId !== null) {
      cancelAnimationFrame(this._animId);
      this._animId = null;
    }
    this._resizeObserver.disconnect();
  }
}
