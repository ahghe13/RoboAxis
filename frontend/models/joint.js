/**
 * models/joint.js
 * ---------------
 * 3D model for a kinematic Joint - represents a degree of freedom.
 * Visualized as a sphere or torus to indicate the rotation point.
 */

import * as THREE from 'three';

export class Joint extends THREE.Group {
  constructor() {
    super();
    this.name = 'Joint';

    // Sphere to represent the joint pivot
    const sphereGeometry = new THREE.SphereGeometry(0.08, 16, 12);
    const sphereMaterial = new THREE.MeshStandardMaterial({
      color: 0xe8922a,
      metalness: 0.6,
      roughness: 0.3,
    });

    const sphere = new THREE.Mesh(sphereGeometry, sphereMaterial);
    sphere.castShadow = true;
    sphere.receiveShadow = true;
    //this.add(sphere);

    // Small ring to indicate rotation axis
    const ringGeometry = new THREE.TorusGeometry(0.12, 0.015, 8, 16);
    const ringMaterial = new THREE.MeshStandardMaterial({
      color: 0xffffff,
      metalness: 0.8,
      roughness: 0.2,
    });

    const ring = new THREE.Mesh(ringGeometry, ringMaterial);
    ring.rotation.x = Math.PI / 2; // Default Y-axis rotation
    //this.add(ring);

    // Add coordinate frame
    const axesHelper = new THREE.AxesHelper(0.2);
    this.add(axesHelper);
  }
}