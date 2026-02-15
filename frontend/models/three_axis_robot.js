/**
 * models/three_axis_robot.js
 * ---------------------------
 * 3D model loader for the ThreeAxisRobot using the GLB asset.
 * The robot.glb file contains 3 bodies corresponding to the robot segments.
 */

import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// Cache for the loaded robot model
let robotModelCache = null;
const loader = new GLTFLoader();

/**
 * Load the robot GLB file (cached after first load).
 * @returns {Promise<THREE.Group>} The loaded GLTF scene.
 */
async function loadRobotModel() {
  if (robotModelCache) {
    return robotModelCache.clone();
  }

  return new Promise((resolve, reject) => {
    loader.load(
      '/static/assets/robot.glb',
      (gltf) => {
        robotModelCache = gltf.scene;
        resolve(robotModelCache.clone());
      },
      undefined,
      (error) => {
        console.error('Error loading robot.glb:', error);
        reject(error);
      }
    );
  });
}

/**
 * Extract the 3 bodies from the loaded GLB model.
 * @param {THREE.Group} model - The loaded GLTF scene.
 * @returns {Object} Object with base, link1, link2 meshes.
 */
function extractRobotBodies(model) {
  const bodies = { base: null, link1: null, link2: null };

  // Traverse the model and find meshes
  // Assuming the GLB has 3 distinct meshes/groups
  const meshes = [];
  model.traverse((child) => {
    if (child.isMesh) {
      meshes.push(child.clone());
    }
  });

  // Assign meshes to robot parts (adjust based on actual GLB structure)
  if (meshes.length >= 3) {
    bodies.base = meshes[0];
    bodies.link1 = meshes[1];
    bodies.link2 = meshes[2];
  } else {
    console.warn(`Expected 3 meshes in robot.glb, found ${meshes.length}`);
    // Fallback: use first mesh for all parts or create placeholders
    bodies.base = meshes[0]?.clone() || createPlaceholder();
    bodies.link1 = meshes[1]?.clone() || createPlaceholder();
    bodies.link2 = meshes[2]?.clone() || createPlaceholder();
  }

  return bodies;
}

/**
 * Create a placeholder mesh if GLB loading fails or has missing parts.
 */
function createPlaceholder() {
  const geometry = new THREE.BoxGeometry(0.1, 0.2, 0.1);
  const material = new THREE.MeshStandardMaterial({ color: 0xff00ff });
  return new THREE.Mesh(geometry, material);
}

/**
 * Link model - uses the second body from robot.glb.
 */
export class RobotLink extends THREE.Group {
  constructor() {
    super();
    this.name = 'RobotLink';
    this._meshReady = false;

    // Load async and add to group when ready
    loadRobotModel().then((model) => {
      const bodies = extractRobotBodies(model);
      const mesh = bodies.link1; // Use middle segment for links
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      this.add(mesh);
      this._meshReady = true;
    }).catch((err) => {
      console.error('Failed to load robot link mesh:', err);
      this.add(createPlaceholder());
    });

    // Add coordinate frame for debugging
    const axesHelper = new THREE.AxesHelper(0.15);
    this.add(axesHelper);
  }
}

/**
 * Joint model - uses the first body from robot.glb.
 */
export class RobotJoint extends THREE.Group {
  constructor() {
    super();
    this.name = 'RobotJoint';
    this._meshReady = false;

    // Load async and add to group when ready
    loadRobotModel().then((model) => {
      const bodies = extractRobotBodies(model);
      const mesh = bodies.base; // Use base for joints (pivots)
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      this.add(mesh);
      this._meshReady = true;
    }).catch((err) => {
      console.error('Failed to load robot joint mesh:', err);
      this.add(createPlaceholder());
    });

    // Add coordinate frame
    const axesHelper = new THREE.AxesHelper(0.2);
    this.add(axesHelper);
  }
}