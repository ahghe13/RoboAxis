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
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { CameraRig }    from '/static/scene/camera.js';
import { createLights } from '/static/scene/lights.js';
import { Frame }         from '/static/models/frame.js';
import { AxisBase, AxisRotor }     from '/static/models/rotary_axis.js';
import { Link }                     from '/static/models/link.js';
import { Joint }                    from '/static/models/joint.js';

/** Cache for loaded GLB models */
const modelCache = new Map();
const gltfLoader = new GLTFLoader();

/**
 * Load a GLB file and extract a specific body/mesh by name.
 * @param {string} modelFile - Path to the GLB file (e.g., "robot.glb")
 * @param {string} bodyName - Name of the specific mesh/object to extract (e.g., "Body", "Body001")
 * @returns {Promise<THREE.Object3D>} The extracted mesh/object
 */
async function loadModelBody(modelFile, bodyName) {
  const filePath = `/static/assets/${modelFile}`;

  // Load the GLB file (cached)
  if (!modelCache.has(filePath)) {
    const promise = new Promise((resolve, reject) => {
      gltfLoader.load(
        filePath,
        (gltf) => resolve(gltf.scene),
        undefined,
        (error) => {
          console.error(`Error loading ${filePath}:`, error);
          reject(error);
        }
      );
    });
    modelCache.set(filePath, promise);
  }

  const model = await modelCache.get(filePath);

  // Find the specific body by name
  let body = null;
  model.traverse((child) => {
    if (child.name === bodyName) {
      body = child;
    }
  });

  if (!body) {
    console.warn(`Body "${bodyName}" not found in ${modelFile}`);
    // Return a placeholder
    const geometry = new THREE.BoxGeometry(0.1, 0.2, 0.1);
    const material = new THREE.MeshStandardMaterial({ color: 0xff00ff });
    return new THREE.Mesh(geometry, material);
  }

  // Clone the body and give each instance its own materials so
  // highlight changes on one component don't bleed into others.
  const clonedBody = body.clone();
  clonedBody.traverse((child) => {
    if (!child.isMesh) return;
    child.material = Array.isArray(child.material)
      ? child.material.map(m => m.clone())
      : child.material.clone();
    child.castShadow    = true;
    child.receiveShadow = true;
  });

  return clonedBody;
}

export class Scene3D {
  /**
   * @param {HTMLElement} container  Element the canvas will be appended to.
   */
  constructor(container) {
    this._container  = container;
    this._animId     = null;
    this._components = {};   // id → THREE.Group
    this._selectedId = null;
    this._raycaster  = new THREE.Raycaster();
    this._raycaster.params.Line.threshold  = 0.01;
    this._raycaster.params.Points.threshold = 0.01;

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

  // ── Scene setup from definition ──────────────────────────────────────────

  /**
   * Build the scene from a static scene definition.
   * @param {Object} definition  Scene definition with { type: "static_scene_definition", components: [...] }
   */
  buildFromDefinition(definition) {
    console.log('[scene] Building scene from definition:', definition);

    // Clear existing components
    for (const name of Object.keys(this._components)) {
      const model = this._components[name];
      if (model.parent) model.parent.remove(model);
      delete this._components[name];
    }
    this._selectedId = null;

    // Create components from definition
    for (const componentDef of definition.components) {
      const { id, component_type, cad_file, cad_body } = componentDef;

      // Create the appropriate model for this component type
      let group;
      if (component_type === 'joint') {
        group = new Joint();
      } else {
        group = new THREE.Group();
        const axesHelper = new THREE.AxesHelper(0.2);
        group.add(axesHelper);
      }
      group.name = id;

      // If a CAD model is specified, load it asynchronously and attach it
      if (cad_file && cad_body) {
        loadModelBody(cad_file, cad_body)
          .then((mesh) => {
            group.add(mesh);
          })
          .catch((err) => {
            console.error(`[scene] Failed to load model for ${id}:`, err);
          });
      }

      // Store and add to scene
      this._components[id] = group;
      this.scene.add(group);

      console.log(`[scene] Created component: ${id} (${component_type})`);
    }
  }

  /**
   * Update scene from a state update.
   * @param {Object} update  State update with { type: "state_update", components: [{id, matrix}, ...] }
   */
  updateFromState(update) {
    // Process each component update
    for (const { id, matrix } of update.components) {
      const model = this._components[id];
      if (!model) {
        console.warn(`[scene] Component not found: ${id}`);
        continue;
      }

      // Apply absolute world transform from 4x4 matrix
      if (matrix) {
        // Backend sends a flat row-major array of 16 values
        const mat = new THREE.Matrix4();
        mat.set(
          matrix[0],  matrix[1],  matrix[2],  matrix[3],
          matrix[4],  matrix[5],  matrix[6],  matrix[7],
          matrix[8],  matrix[9],  matrix[10], matrix[11],
          matrix[12], matrix[13], matrix[14], matrix[15]
        );

        // Apply the matrix and decompose it to update position/rotation/scale
        model.matrix.copy(mat);
        model.matrix.decompose(model.position, model.quaternion, model.scale);
        model.matrixAutoUpdate = false;
      }
    }
  }

  // ── Selection & picking ───────────────────────────────────────────────────

  /**
   * Highlight the component with the given id and unhighlight the previous one.
   * @param {string|null} id
   */
  selectComponent(id) {
    if (this._selectedId && this._components[this._selectedId]) {
      this._setHighlight(this._components[this._selectedId], false);
    }
    this._selectedId = id;
    if (id && this._components[id]) {
      this._setHighlight(this._components[id], true);
    }
  }

  /**
   * Register a callback for click-picks on the canvas.
   * The callback receives the component id of the clicked object.
   * Drags (pointer moved > 5 px) are ignored so orbit control is unaffected.
   * @param {function(string): void} onPick
   */
  setPicking(onPick) {
    const canvas = this.renderer.domElement;
    let downPos = null;

    canvas.addEventListener('pointerdown', (e) => {
      downPos = { x: e.clientX, y: e.clientY };
    });

    canvas.addEventListener('pointerup', (e) => {
      if (!downPos) return;
      const dx = e.clientX - downPos.x;
      const dy = e.clientY - downPos.y;
      downPos = null;
      if (dx * dx + dy * dy > 25) return;   // drag threshold: 5 px

      const rect   = canvas.getBoundingClientRect();
      const ndc    = new THREE.Vector2(
        ((e.clientX - rect.left) / rect.width)  *  2 - 1,
        ((e.clientY - rect.top)  / rect.height) * -2 + 1,
      );

      this._raycaster.setFromCamera(ndc, this.camera);
      const hits = this._raycaster.intersectObjects(Object.values(this._components), true);
      // Prefer mesh hits — line/point helpers have loose thresholds and
      // can intercept clicks far from the visible geometry.
      const target = hits.find(h => h.object.isMesh) ?? hits[0];
      if (target) {
        const id = this._findComponentId(target.object);
        if (id) onPick(id);
      }
    });
  }

  _findComponentId(object) {
    let node = object;
    while (node) {
      if (node.name && this._components[node.name]) return node.name;
      node = node.parent;
    }
    return null;
  }

  _setHighlight(group, on) {
    group.traverse((child) => {
      if (!child.isMesh) return;
      const mats = Array.isArray(child.material) ? child.material : [child.material];
      for (const mat of mats) {
        mat.emissive.set(on ? 0xe8922a : 0x000000);
        mat.emissiveIntensity = on ? 0.35 : 0;
      }
    });
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
