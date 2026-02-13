/**
 * models/frame.js
 * ---------------
 * Reference frame: floor grid and colour-coded axis lines.
 */

import * as THREE from 'three';

export class Frame extends THREE.Group {
  /**
   * @param {object}  [opts]
   * @param {number}  [opts.gridSize=14]      Total grid extent.
   * @param {number}  [opts.gridDivisions=28] Number of grid cells.
   * @param {number}  [opts.axisLength=1.2]   Length of each axis line.
   */
  constructor({ gridSize = 14, gridDivisions = 28, axisLength = 1.2 } = {}) {
    super();
    this.name = 'Frame';

    // Floor grid
    const grid = new THREE.GridHelper(gridSize, gridDivisions, 0x2a2d31, 0x1a1d20);
    grid.position.y = -0.01;
    this.add(grid);

    // Axis lines
    const makeLine = (from, to, color) => {
      const geo = new THREE.BufferGeometry().setFromPoints([
        new THREE.Vector3(...from),
        new THREE.Vector3(...to),
      ]);
      return new THREE.Line(geo, new THREE.LineBasicMaterial({ color, linewidth: 1 }));
    };

    this.add(makeLine([0, 0, 0], [axisLength, 0, 0], 0x7a2020));  // X — red
    this.add(makeLine([0, 0, 0], [0, axisLength, 0], 0x207a20));  // Y — green
    this.add(makeLine([0, 0, 0], [0, 0, axisLength], 0x20407a));  // Z — blue
  }
}