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

// Fields handled separately or not suitable for raw display
const STATIC_SKIP = new Set(['id', 'name', 'matrix', 'transform']);
const STATE_SKIP  = new Set(['id', 'matrix']);

let _selectedId   = null;
let _components   = [];           // full flat component list
let _stateMap     = new Map();    // id → latest state entry
let _transformMap = new Map();    // id → {position, rotation, scale}

// ── Public API ────────────────────────────────────────────────────────────────

export function setComponents(components) {
  _components = components;
  _transformMap.clear();
  for (const c of components) {
    if (c.transform) {
      _transformMap.set(c.id, {
        position: [...c.transform.position],
        rotation: [...c.transform.rotation],
        scale:    [...c.transform.scale],
      });
    }
  }
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
    ${_buildTransformSection(component)}
    ${jogHTML}
  `;

  _attachTransformHandlers(panel, component.id);
  if (robot) {
    _attachJogHandlers(panel, robot.id);
  }
}

export function updateComponentState(stateComponents) {
  for (const entry of stateComponents) {
    _stateMap.set(entry.id, entry);
  }

  if (!_selectedId) return;

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

// ── Transform editor ──────────────────────────────────────────────────────────

function _buildTransformSection(component) {
  const tf = _transformMap.get(component.id)
    ?? { position: [0, 0, 0], rotation: [0, 0, 0], scale: [1, 1, 1] };

  const locked = component.transform_locked ?? false;
  const disabledAttr = locked ? ' disabled' : '';

  const tfRow = (label, field, vals) => `
    <div class="tf-row">
      <span class="tf-row-label">${label}</span>
      ${['X', 'Y', 'Z'].map((axis, i) => `
        <label class="tf-field">
          <span class="tf-axis tf-${axis.toLowerCase()}">${axis}</span>
          <input class="tf-input" data-tf="${field}" data-idx="${i}"
                 type="number" step="any" value="${vals[i].toFixed(3)}"${disabledAttr}>
        </label>
      `).join('')}
    </div>
  `;

  return `
    <div class="panel-section" id="details-tf-section">
      <div class="panel-label">Transform${locked ? ' <span class="tf-locked">locked</span>' : ''}</div>
      <div class="tf-group">
        ${tfRow('Pos', 'position', tf.position)}
        ${tfRow('Rot', 'rotation', tf.rotation)}
        ${tfRow('Scl', 'scale',    tf.scale)}
      </div>
    </div>
  `;
}

function _attachTransformHandlers(panel, componentId) {
  const commit = () => {
    const tf = { position: [0, 0, 0], rotation: [0, 0, 0], scale: [1, 1, 1] };
    panel.querySelectorAll('.tf-input').forEach(input => {
      const field = input.dataset.tf;
      const idx   = parseInt(input.dataset.idx, 10);
      tf[field][idx] = parseFloat(input.value) || 0;
    });

    fetch(`/api/scene/${componentId}/transform`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(tf),
    })
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (data?.transform) {
          _transformMap.set(componentId, data.transform);
        }
      })
      .catch(() => {});
  };

  panel.querySelectorAll('.tf-input').forEach(input => {
    input.addEventListener('change', commit);
    input.addEventListener('keydown', e => {
      if (e.key === 'Enter') input.blur();
    });
  });
}

// ── Jog helpers ───────────────────────────────────────────────────────────────

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