/**
 * scene.js
 * --------
 * Encapsulates the Three.js scene, renderer, lights, and environment.
 * Camera and orbit controls live in camera.js.
 *
 * Usage:
 *   import { Scene3D } from '/static/scene.js';
 *   const scene = new Scene3D(document.getElementById('canvas-pane'));
 *   scene.start();
 */

import * as THREE from 'three';
import { CameraRig }  from '/static/camera.js';
import { Frame }      from '/static/models/frame.js';
import { RotaryAxis } from '/static/models/rotary_axis.js';

/** Maps backend component type names to frontend model constructors. */
const MODEL_MAP = {
  RotaryAxis,
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
    // Ambient — fills shadows softly
    const ambient = new THREE.AmbientLight(0x1a1f26, 3.0);
    this.scene.add(ambient);

    // Key light — warm amber, from upper-front-right
    const key = new THREE.DirectionalLight(0xe8922a, 2.5);
    key.position.set(5, 8, 4);
    key.castShadow = true;
    key.shadow.mapSize.set(1024, 1024);
    key.shadow.camera.near = 0.5;
    key.shadow.camera.far  = 40;
    key.shadow.camera.left = key.shadow.camera.bottom = -8;
    key.shadow.camera.right = key.shadow.camera.top   =  8;
    this.scene.add(key);

    // Fill light — cool blue-grey, from left
    const fill = new THREE.DirectionalLight(0x4a6080, 1.0);
    fill.position.set(-4, 2, -2);
    this.scene.add(fill);

    // Rim light — faint, from behind/below
    const rim = new THREE.PointLight(0x2a3a4a, 2.0, 12);
    rim.position.set(0, -2, -4);
    this.scene.add(rim);
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
    for (const [name, props] of Object.entries(data)) {
      let model = this._components[name];

      // Create model if it doesn't exist yet
      if (!model) {
        const Ctor = MODEL_MAP[props.type];
        if (!Ctor) continue;
        model = new Ctor();
        model.name = name;
        this._components[name] = model;
        this.scene.add(model);
      }

      // Update state
      if (typeof model.setAngle === 'function' && props.position != null) {
        model.setAngle(props.position);
      }
    }

    // Remove models no longer in the backend
    for (const name of Object.keys(this._components)) {
      if (!(name in data)) {
        this.scene.remove(this._components[name]);
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
