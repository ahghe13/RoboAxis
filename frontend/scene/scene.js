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
import { AxisBase, AxisRotor } from '/static/models/rotary_axis.js';

/** Maps backend component type names to frontend model constructors. */
const MODEL_MAP = {
  AxisBase,
  AxisRotor,
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
   * @param {Object} data  Snapshot object from backend (name → props).
   */
  _applySnapshot(data) {
    // 1. Create any new models (before parenting, so parents exist first)
    for (const [name, props] of Object.entries(data)) {
      if (!this._components[name]) {
        const Ctor = MODEL_MAP[props.type];
        if (!Ctor) continue;
        const model = new Ctor();
        model.name = name;
        this._components[name] = model;
      }
    }

    // 2. Update parenting, transforms, and state
    for (const [name, props] of Object.entries(data)) {
      const model = this._components[name];
      if (!model) continue;

      // Attach to parent (or scene root). Three.js auto-removes from old parent.
      const targetParent = props.parent
        ? this._components[props.parent]
        : this.scene;
      if (targetParent && model.parent !== targetParent) {
        targetParent.add(model);
      }

      // Update local transform (relative to parent)
      if (props.transform) {
        const t = props.transform;
        model.position.set(...t.position);
        model.rotation.set(
          THREE.MathUtils.degToRad(t.rotation[0]),
          THREE.MathUtils.degToRad(t.rotation[1]),
          THREE.MathUtils.degToRad(t.rotation[2]),
        );
        model.scale.set(...t.scale);
      }

      // Update component state
      if (typeof model.setAngle === 'function' && props.position != null) {
        model.setAngle(props.position);
      }
    }

    // 3. Remove models no longer in the backend
    for (const name of Object.keys(this._components)) {
      if (!(name in data)) {
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
