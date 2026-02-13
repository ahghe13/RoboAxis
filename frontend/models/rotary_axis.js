/**
 * models/rotary_axis.js
 * ---------------------
 * 3D model of a rotary axis: a stationary base with a rotating shaft and disc.
 * Call setAngle() to drive the rotation from simulation state.
 */

import * as THREE from 'three';

export class RotaryAxis extends THREE.Group {
  /**
   * @param {object} [opts]
   * @param {number} [opts.baseRadius=0.5]    Radius of the stationary base.
   * @param {number} [opts.baseHeight=0.3]    Height of the base cylinder.
   * @param {number} [opts.shaftRadius=0.12]  Radius of the rotating shaft.
   * @param {number} [opts.shaftHeight=0.8]   Height of the shaft.
   * @param {number} [opts.discRadius=0.4]    Radius of the top disc.
   * @param {number} [opts.discHeight=0.06]   Thickness of the top disc.
   */
  constructor({
    baseRadius  = 0.5,
    baseHeight  = 0.3,
    shaftRadius = 0.12,
    shaftHeight = 0.8,
    discRadius  = 0.4,
    discHeight  = 0.06,
  } = {}) {
    super();
    this.name = 'RotaryAxis';

    // ── Materials ──────────────────────────────────────────
    const baseMat  = new THREE.MeshStandardMaterial({ color: 0x2a2d31, metalness: 0.6, roughness: 0.4 });
    const shaftMat = new THREE.MeshStandardMaterial({ color: 0x8a8e94, metalness: 0.8, roughness: 0.2 });
    const discMat  = new THREE.MeshStandardMaterial({ color: 0xe8922a, metalness: 0.5, roughness: 0.3 });
    const markerMat = new THREE.MeshStandardMaterial({ color: 0xffffff, metalness: 0.3, roughness: 0.5 });

    // ── Base (stationary) ─────────────────────────────────
    const baseGeo = new THREE.CylinderGeometry(baseRadius, baseRadius, baseHeight, 32);
    const base = new THREE.Mesh(baseGeo, baseMat);
    base.name = 'Base';
    base.position.y = baseHeight / 2;
    base.castShadow = true;
    base.receiveShadow = true;
    this.add(base);

    // ── Rotor (everything that spins) ─────────────────────
    this._rotor = new THREE.Group();
    this._rotor.name = 'Rotor';
    this._rotor.position.y = baseHeight;

    // Shaft
    const shaftGeo = new THREE.CylinderGeometry(shaftRadius, shaftRadius, shaftHeight, 24);
    const shaft = new THREE.Mesh(shaftGeo, shaftMat);
    shaft.name = 'Shaft';
    shaft.position.y = shaftHeight / 2;
    shaft.castShadow = true;
    this._rotor.add(shaft);

    // Top disc
    const discGeo = new THREE.CylinderGeometry(discRadius, discRadius, discHeight, 32);
    const disc = new THREE.Mesh(discGeo, discMat);
    disc.name = 'Disc';
    disc.position.y = shaftHeight + discHeight / 2;
    disc.castShadow = true;
    this._rotor.add(disc);

    // Direction marker on disc (small notch to visualise rotation)
    const markerGeo = new THREE.BoxGeometry(0.04, discHeight + 0.01, discRadius * 0.6);
    const marker = new THREE.Mesh(markerGeo, markerMat);
    marker.name = 'Marker';
    marker.position.set(0, shaftHeight + discHeight / 2, discRadius * 0.55);
    this._rotor.add(marker);

    this.add(this._rotor);
  }

  /**
   * Set the rotor angle.
   * @param {number} degrees  Rotation around the Y axis in degrees.
   */
  setAngle(degrees) {
    this._rotor.rotation.y = THREE.MathUtils.degToRad(degrees);
  }
}