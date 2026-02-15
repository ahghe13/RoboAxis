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

  // Clone the body so it can be added to multiple scenes
  const clonedBody = body.clone();
  if (clonedBody.isMesh) {
    clonedBody.castShadow = true;
    clonedBody.receiveShadow = true;
  }

  return clonedBody;
}

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

    // Create components from definition
    for (const componentDef of definition.components) {
      const { id, type, model_file, model_body } = componentDef;

      // Create a group container for this component
      const group = new THREE.Group();
      group.name = id;

      // Add coordinate frame (axes helper)
      const axesHelper = new THREE.AxesHelper(0.2);
      group.add(axesHelper);

      // If model file is specified, load the 3D model asynchronously
      if (model_file && model_body) {
        loadModelBody(model_file, model_body)
          .then((mesh) => {
            group.add(mesh);
            console.log(`[scene] Loaded model for ${id}: ${model_file}/${model_body}`);
          })
          .catch((err) => {
            console.error(`[scene] Failed to load model for ${id}:`, err);
          });
      }

      // Store and add to scene
      this._components[id] = group;
      this.scene.add(group);

      console.log(`[scene] Created component: ${id} (${type})`);
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
        // Backend sends 4x4 matrix as nested array [[row0], [row1], [row2], [row3]]
        const mat = new THREE.Matrix4();
        mat.set(
          matrix[0][0], matrix[0][1], matrix[0][2], matrix[0][3],
          matrix[1][0], matrix[1][1], matrix[1][2], matrix[1][3],
          matrix[2][0], matrix[2][1], matrix[2][2], matrix[2][3],
          matrix[3][0], matrix[3][1], matrix[3][2], matrix[3][3]
        );

        // Apply the matrix and decompose it to update position/rotation/scale
        model.matrix.copy(mat);
        model.matrix.decompose(model.position, model.quaternion, model.scale);
        model.matrixAutoUpdate = false;
      }
    }
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
