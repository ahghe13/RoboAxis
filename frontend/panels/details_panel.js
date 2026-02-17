/**
 * details_panel.js
 * ----------------
 * Builds and mounts the #details-panel sidebar into the #app grid.
 *
 * Usage:
 *   import { mountDetailsPanel, showComponentDetails } from '/static/panels/details_panel.js';
 *   mountDetailsPanel();
 *   showComponentDetails(component);   // call when a tree node is selected
 */

const FIELD_LABELS = {
  type:       'Type',
  axis:       'Axis',
  parent:     'Parent',
  length:     'Length',
  model_file: 'Model',
  model_body: 'Body',
  max_speed:  'Max speed',
  acceleration: 'Accel',
};

export function mountDetailsPanel() {
  const panel = document.createElement('aside');
  panel.id = 'details-panel';
  _renderEmpty(panel);
  document.getElementById('app').appendChild(panel);
}

export function showComponentDetails(component) {
  const panel = document.getElementById('details-panel');
  if (!panel) return;

  // Fields to show: everything except id (used as the heading)
  const entries = Object.entries(component).filter(([k]) => k !== 'id');

  const rows = entries.map(([k, v]) => {
    const label = FIELD_LABELS[k] || k;
    return `
      <div class="readout">
        <span class="key">${label}</span>
        <span class="value">${v ?? '—'}</span>
      </div>`;
  }).join('');

  panel.innerHTML = `
    <div class="panel-section">
      <div class="panel-label">${component.id}</div>
      ${rows}
    </div>
  `;
}

function _renderEmpty(panel) {
  panel.innerHTML = `
    <div class="panel-section">
      <div class="panel-label">Details</div>
      <div class="readout">
        <span class="key details-empty">No component selected</span>
      </div>
    </div>
  `;
}