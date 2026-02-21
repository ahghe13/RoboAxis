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

let _selectedId        = null;
let _components        = [];  // full flat component list for name lookups
let _stateMap          = new Map();  // id → latest state entry

// ── Public API ────────────────────────────────────────────────────────────────

export function setComponents(components) {
  _components = components;
}

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
    .map(([k, v]) => {
      if (k === 'parent' && v) {
        const parentComp = _components.find(c => c.id === v);
        v = parentComp ? (parentComp.name || v) : v;
      }
      return _row(STATIC_LABELS[k] || k, v);
    })
    .join('');

  const robot = _findRobot(component);
  const jogHTML = robot ? _buildJogSection(robot) : '';

  panel.innerHTML = `
    <div class="panel-section">
      <div class="panel-label">${component.name || component.id}</div>
      ${_row('ID', component.id)}
      ${staticRows}
    </div>
    <div class="panel-section" id="details-state-section">
      <div class="panel-label">State</div>
      <div class="readout"><span class="key details-empty">Waiting for update…</span></div>
    </div>
    ${jogHTML}
  `;

  if (robot) {
    _attachJogHandlers(panel, robot.id);
  }
}

export function updateComponentState(stateComponents) {
  // Keep the state map fresh for all components
  for (const entry of stateComponents) {
    _stateMap.set(entry.id, entry);
  }

  if (!_selectedId) return;

  // Update the live state section for the selected component
  const stateSection = document.getElementById('details-state-section');
  if (stateSection) {
    const entry = _stateMap.get(_selectedId);
    if (entry) {
      const rows = Object.entries(entry)
        .filter(([k]) => !STATE_SKIP.has(k))
        .map(([k, v]) => _row(STATE_LABELS[k] || k, _format(v)))
        .join('');

      stateSection.innerHTML = `
        <div class="panel-label">State</div>
        ${rows || '<div class="readout"><span class="key details-empty">No state fields</span></div>'}
      `;
    }
  }

  // Update live position readouts inside the jog panel
  const jogSection = document.getElementById('details-jog-section');
  if (jogSection) {
    jogSection.querySelectorAll('[data-joint-id]').forEach(el => {
      const state = _stateMap.get(el.dataset.jointId);
      if (state?.position !== undefined) {
        el.textContent = `${state.position.toFixed(1)}°`;
      }
    });
  }
}

// ── Jog helpers ───────────────────────────────────────────────────────────────

/**
 * Walk up the parent chain of `component` to find the nearest SerialRobot
 * ancestor (including the component itself if it is one).
 */
function _findRobot(component) {
  if (component.component_type === 'serial_robot') return component;
  let current = component;
  while (current?.parent) {
    const parent = _components.find(c => c.id === current.parent);
    if (!parent) break;
    if (parent.component_type === 'serial_robot') return parent;
    current = parent;
  }
  return null;
}

/**
 * Follow the chained parent→child structure to collect all joints
 * belonging to `robot` in kinematic order (root to tip).
 *
 * Serial robots chain joints as: robot → joint1 → joint2 → …
 * Each joint's parent is the previous joint (or the robot for joint1).
 */
function _getRobotJoints(robot) {
  const joints = [];
  const allJoints = _components.filter(c => c.component_type === 'joint');
  let parentId = robot.id;
  while (true) {
    const joint = allJoints.find(c => c.parent === parentId);
    if (!joint) break;
    joints.push(joint);
    parentId = joint.id;
  }
  return joints;
}

function _buildJogSection(robot) {
  const joints = _getRobotJoints(robot);
  if (!joints.length) return '';

  const rows = joints.map((j, i) => `
    <div class="jog-row">
      <span class="jog-label">J${i + 1}</span>
      <div class="jog-controls">
        <button class="jog-btn" data-joint="${i}" data-dir="ccw" title="Jog CCW">−</button>
        <span class="jog-pos" data-joint-id="${j.id}">—</span>
        <button class="jog-btn" data-joint="${i}" data-dir="cw"  title="Jog CW">+</button>
      </div>
    </div>
  `).join('');

  return `
    <div class="panel-section" id="details-jog-section">
      <div class="panel-label">Jog</div>
      ${rows}
    </div>
  `;
}

function _attachJogHandlers(panel, robotId) {
  panel.querySelectorAll('.jog-btn').forEach(btn => {
    const jointIndex = parseInt(btn.dataset.joint, 10);
    const dir = btn.dataset.dir;

    const sendJog = (direction) => {
      fetch(`/api/scene/${robotId}/jog`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ joint: jointIndex, direction }),
      }).catch(() => {});
    };

    btn.addEventListener('mousedown', (e) => {
      e.preventDefault();
      sendJog(dir);
    });

    const stop = () => sendJog('stop');
    btn.addEventListener('mouseup',    stop);
    btn.addEventListener('mouseleave', stop);
  });
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