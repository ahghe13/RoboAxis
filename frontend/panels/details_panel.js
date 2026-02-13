/**
 * details_panel.js
 * ----------------
 * Builds and mounts the #details-panel sidebar into the #app grid.
 *
 * Usage:
 *   import { mountDetailsPanel } from '/static/details_panel.js';
 *   mountDetailsPanel();
 */

export function mountDetailsPanel() {
  const panel = document.createElement('aside');
  panel.id = 'details-panel';
  panel.innerHTML = `
    <div class="panel-section">
      <div class="panel-label">Position</div>
      <div class="readout">
        <span class="key">Angle</span>
        <span class="value" id="pos-angle">0.00°</span>
      </div>
    </div>

    <div class="divider"></div>

    <div class="panel-section">
      <div class="panel-label">Motion</div>
      <div class="readout">
        <span class="key">Speed</span>
        <span class="value" id="pos-speed">0.0 °/s</span>
      </div>
      <div class="readout">
        <span class="key">State</span>
        <span class="value" id="pos-state">idle</span>
      </div>
    </div>

    <div class="divider"></div>

    <div class="panel-section">
      <div class="panel-label">Parameters</div>
      <div class="readout">
        <span class="key">Max speed</span>
        <span class="value" id="param-speed">—</span>
      </div>
      <div class="readout">
        <span class="key">Accel</span>
        <span class="value" id="param-accel">—</span>
      </div>
    </div>
  `;

  document.getElementById('app').appendChild(panel);
}
