/**
 * models/link.js
 * --------------
 * 3D model for a kinematic Link - a rigid body segment.
 * Visualized as a simple cylinder or box to show the connection.
 */

import * as THREE from 'three';

export class Link extends THREE.Group {
  constructor() {
    super();
    this.name = 'Link';

    // Simple cylinder to represent the link structure
    const geometry = new THREE.CylinderGeometry(0.05, 0.05, 0.2, 8);
    const material = new THREE.MeshStandardMaterial({
      color: 0x4a6080,
      metalness: 0.4,
      roughness: 0.6,
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    //this.add(mesh);

    // Add a small coordinate frame to show orientation
    const axesHelper = new THREE.AxesHelper(0.15);
    this.add(axesHelper);
  }
}