/**
 * scene.js
 * --------
 * Encapsulates the Three.js scene, renderer, camera, and orbit controls.
 * Attach it to any container element; it fills the container and handles
 * resize automatically.
 *
 * Usage:
 *   import { Scene3D } from '/static/scene.js';
 *   const scene = new Scene3D(document.getElementById('canvas-pane'));
 *   scene.start();
 */

import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export class Scene3D {
  /**
   * @param {HTMLElement} container  Element the canvas will be appended to.
   */
  constructor(container) {
    this._container = container;
    this._animId    = null;

    this._initRenderer();
    this._initCamera();
    this._initLights();
    this._initEnvironment();
    this._initControls();
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
    this.camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 200);
    this.camera.position.set(4, 3, 5);
    this.camera.lookAt(0, 0, 0);
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
    // Floor grid — amber tinted
    const grid = new THREE.GridHelper(14, 28, 0x2a2d31, 0x1a1d20);
    grid.position.y = -0.01;
    this.scene.add(grid);

    // Thin axis lines
    const axesMat = (hex) => new THREE.LineBasicMaterial({ color: hex, linewidth: 1 });
    const axesGeo = (from, to) => {
      const g = new THREE.BufferGeometry();
      g.setFromPoints([new THREE.Vector3(...from), new THREE.Vector3(...to)]);
      return g;
    };

    // X — red-ish
    this.scene.add(new THREE.Line(axesGeo([0,0,0],[1.2,0,0]), axesMat(0x7a2020)));
    // Y — green-ish
    this.scene.add(new THREE.Line(axesGeo([0,0,0],[0,1.2,0]), axesMat(0x207a20)));
    // Z — blue-ish
    this.scene.add(new THREE.Line(axesGeo([0,0,0],[0,0,1.2]), axesMat(0x20407a)));
  }

  // ── Orbit controls ────────────────────────────────────────────────────────

  _initControls() {
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping    = true;
    this.controls.dampingFactor    = 0.06;
    this.controls.screenSpacePanning = false;
    this.controls.minDistance      = 1.5;
    this.controls.maxDistance      = 30;
    this.controls.maxPolarAngle    = Math.PI * 0.52;  // prevent going underground
    this.controls.target.set(0, 0, 0);
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
    if (this.camera) {
      this.camera.aspect = width / height;
      this.camera.updateProjectionMatrix();
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
      this.controls.update();
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
