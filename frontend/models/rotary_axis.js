/**
 * models/rotary_axis.js
 * ---------------------
 * 3D models for the two parts of a rotary axis:
 *   - AxisBase  — stationary base cylinder
 *   - AxisRotor — rotating shaft, disc, and direction marker
 *
 * The backend automatically creates both scene nodes when a RotaryAxis
 * is added, with the rotor parented to the base.
 */

import * as THREE from 'three';

// ── Materials (shared) ──────────────────────────────────────────────────────

const baseMat   = new THREE.MeshStandardMaterial({ color: 0x2a2d31, metalness: 0.6, roughness: 0.4 });
const shaftMat  = new THREE.MeshStandardMaterial({ color: 0x8a8e94, metalness: 0.8, roughness: 0.2 });
const discMat   = new THREE.MeshStandardMaterial({ color: 0xe8922a, metalness: 0.5, roughness: 0.3 });
const markerMat = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.3, roughness: 0.5 });

// ── AxisBase ────────────────────────────────────────────────────────────────

export class AxisBase extends THREE.Group {
  constructor({
    baseRadius = 0.5,
    baseHeight = 0.3,
  } = {}) {
    super();
    this.name = 'AxisBase';

    const geo  = new THREE.CylinderGeometry(baseRadius, baseRadius, baseHeight, 32);
    const mesh = new THREE.Mesh(geo, baseMat);
    mesh.name = 'Base';
    mesh.position.y = baseHeight / 2;
    mesh.castShadow    = true;
    mesh.receiveShadow = true;
    this.add(mesh);
  }
}

// ── AxisRotor ───────────────────────────────────────────────────────────────

export class AxisRotor extends THREE.Group {
  constructor({
    shaftRadius = 0.12,
    shaftHeight = 0.8,
    discRadius  = 0.4,
    discHeight  = 0.06,
  } = {}) {
    super();
    this.name = 'AxisRotor';

    // Shaft
    const shaftGeo = new THREE.CylinderGeometry(shaftRadius, shaftRadius, shaftHeight, 24);
    const shaft = new THREE.Mesh(shaftGeo, shaftMat);
    shaft.name = 'Shaft';
    shaft.position.y = shaftHeight / 2;
    shaft.castShadow = true;
    this.add(shaft);

    // Top disc
    const discGeo = new THREE.CylinderGeometry(discRadius, discRadius, discHeight, 32);
    const disc = new THREE.Mesh(discGeo, discMat);
    disc.name = 'Disc';
    disc.position.y = shaftHeight + discHeight / 2;
    disc.castShadow = true;
    this.add(disc);

    // Direction marker
    const markerGeo = new THREE.BoxGeometry(0.04, discHeight + 0.01, discRadius * 0.6);
    const marker = new THREE.Mesh(markerGeo, markerMat);
    marker.name = 'Marker';
    marker.position.set(0, shaftHeight + discHeight / 2, discRadius * 0.55);
    this.add(marker);
  }

  /**
   * Set the rotor angle.
   * @param {number} degrees  Rotation around the Y axis in degrees.
   */
  setAngle(degrees) {
    this.rotation.y = THREE.MathUtils.degToRad(degrees);
  }
}