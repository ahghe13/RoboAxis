/**
 * details_panel.js
 * ----------------
 * Builds and mounts the #details-panel sidebar into the #app grid.
 *
 * Usage:
 *   import { mountDetailsPanel, showComponentDetails, updateComponentState }
 *     from '/static/panels/details_panel.js';
 *
 *   mountDetailsPanel();
 *   showComponentDetails(component);          // call when a tree node is selected
 *   updateComponentState(update.components);  // call on every state_update message
 */

const STATIC_LABELS = {
  component_type: 'Type',
  parent:         'Parent',
  cad_file:       'Model',
  cad_body:       'Body',
};

const STATE_LABELS = {
  position:     'Position (°)',
  speed:        'Speed (°/s)',
  acceleration: 'Accel (°/s²)',
  is_moving:    'Moving',
};

// Fields that are handled separately (header) or too noisy to display raw
const STATIC_SKIP = new Set(['id', 'name', 'matrix']);
const STATE_SKIP  = new Set(['id', 'matrix']);

let _selectedId = null;

// ── Public API ────────────────────────────────────────────────────────────────

export function mountDetailsPanel() {
  const panel = document.createElement('aside');
  panel.id = 'details-panel';
  _renderEmpty(panel);
  document.getElementById('app').appendChild(panel);
}

export function showComponentDetails(component) {
  _selectedId = component.id;
  const panel = document.getElementById('details-panel');
  if (!panel) return;

  const staticRows = Object.entries(component)
    .filter(([k]) => !STATIC_SKIP.has(k))
    .map(([k, v]) => _row(STATIC_LABELS[k] || k, v))
    .join('');

  panel.innerHTML = `
    <div class="panel-section">
      <div class="panel-label">${component.name || component.id}</div>
      ${staticRows}
    </div>
    <div class="panel-section" id="details-state-section">
      <div class="panel-label">State</div>
      <div class="readout"><span class="key details-empty">Waiting for update…</span></div>
    </div>
  `;
}

export function updateComponentState(stateComponents) {
  if (!_selectedId) return;
  const section = document.getElementById('details-state-section');
  if (!section) return;

  const entry = stateComponents.find(c => c.id === _selectedId);
  if (!entry) return;

  const rows = Object.entries(entry)
    .filter(([k]) => !STATE_SKIP.has(k))
    .map(([k, v]) => _row(STATE_LABELS[k] || k, _format(v)))
    .join('');

  section.innerHTML = `
    <div class="panel-label">State</div>
    ${rows || '<div class="readout"><span class="key details-empty">No state fields</span></div>'}
  `;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function _format(v) {
  if (typeof v === 'boolean') return v ? 'yes' : 'no';
  if (typeof v === 'number')  return v.toFixed(2);
  return v ?? '—';
}

function _row(label, value) {
  return `
    <div class="readout">
      <span class="key">${label}</span>
      <span class="value">${value}</span>
    </div>`;
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