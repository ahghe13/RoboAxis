/**
 * scene_tree.js
 * -------------
 * Builds a collapsible tree view from the scene definition
 * and mounts it as its own left-side panel.
 *
 * Usage:
 *   import { mountSceneTree } from '/static/panels/scene_tree.js';
 *   mountSceneTree(sceneDefinition, onSelect, onAddRobot);
 */

const TYPE_ICONS = {
  RobotLink:        '◆',
  RobotJoint:       '◉',
  Link:             '◆',
  Joint:            '◉',
  AxisBase:         '▦',
  AxisRotor:        '⟳',
};

// Currently highlighted row element
let _selectedRow = null;
// Maps component id → row element for programmatic selection
let _rowMap = new Map();

/**
 * Build a hierarchical tree structure from flat component list.
 */
function buildHierarchy(components) {
  const hierarchy = new Map();

  for (const comp of components) {
    hierarchy.set(comp.id, { component: comp, children: [] });
  }

  for (const comp of components) {
    if (comp.parent && hierarchy.has(comp.parent)) {
      hierarchy.get(comp.parent).children.push(comp.id);
    }
  }

  return hierarchy;
}

/**
 * Build a single tree node (li) for a component.
 */
function buildNode(node, hierarchy, onSelect) {
  const { component, children } = node;
  const li = document.createElement('li');
  const hasChildren = children.length > 0;

  const row = document.createElement('span');
  row.className = 'st-row';

  const toggle = document.createElement('span');
  toggle.className = 'st-toggle';
  toggle.textContent = hasChildren ? '▸' : ' ';
  row.appendChild(toggle);

  const icon = document.createElement('span');
  icon.className = 'st-icon';
  icon.textContent = TYPE_ICONS[component.type] || '○';
  row.appendChild(icon);

  const label = document.createElement('span');
  label.className = 'st-label';
  label.textContent = `${component.name || component.id} (${component.component_type})`;
  row.appendChild(label);

  li.appendChild(row);

  _rowMap.set(component.id, row);

  row.style.cursor = 'pointer';
  row.addEventListener('click', (e) => {
    if (e.target === toggle) return;

    if (_selectedRow) _selectedRow.classList.remove('st-selected');
    _selectedRow = row;
    row.classList.add('st-selected');

    if (onSelect) onSelect(component);
  });

  let ul;
  if (hasChildren) {
    ul = document.createElement('ul');
    ul.className = 'st-children st-collapsed';

    for (const childId of children) {
      const childNode = hierarchy.get(childId);
      if (childNode) {
        ul.appendChild(buildNode(childNode, hierarchy, onSelect));
      }
    }
    li.appendChild(ul);

    toggle.addEventListener('click', () => {
      const collapsed = ul.classList.toggle('st-collapsed');
      toggle.textContent = collapsed ? '▸' : '▾';
    });
  }

  return li;
}

/**
 * Show a floating picker of available robot devices below `anchorBtn`.
 * Calls onAddRobot(filename) when the user selects one.
 */
async function _showRobotPicker(anchorBtn, onAddRobot) {
  // Toggle off if already open
  const existing = document.getElementById('st-robot-picker');
  if (existing) {
    existing.remove();
    return;
  }

  let robots;
  try {
    robots = await fetch('/api/devices/robots').then(r => r.json());
  } catch {
    return;
  }

  const picker = document.createElement('div');
  picker.id = 'st-robot-picker';
  picker.className = 'st-picker';

  if (!robots.length) {
    const empty = document.createElement('div');
    empty.className = 'st-picker-empty';
    empty.textContent = 'No robots found';
    picker.appendChild(empty);
  }

  for (const r of robots) {
    const item = document.createElement('button');
    item.className = 'st-picker-item';
    item.innerHTML = `<span class="st-picker-name">${r.name}</span>`
                   + `<span class="st-picker-meta">${r.joint_count}J</span>`;
    item.addEventListener('click', async () => {
      picker.remove();
      await onAddRobot(r.filename);
    });
    picker.appendChild(item);
  }

  // Position fixed below the anchor button
  const rect = anchorBtn.getBoundingClientRect();
  picker.style.top  = `${rect.bottom + 4}px`;
  picker.style.left = `${rect.left}px`;
  document.body.appendChild(picker);

  // Close on outside click
  const closeOnOutside = (e) => {
    if (!picker.contains(e.target) && e.target !== anchorBtn) {
      picker.remove();
      document.removeEventListener('click', closeOnOutside);
    }
  };
  setTimeout(() => document.addEventListener('click', closeOnOutside), 0);
}

/**
 * Mount the scene tree as a standalone left-side panel.
 * @param {Object}        sceneDefinition - Scene definition with { type, components }
 * @param {Function|null} onSelect        - Called with component object on selection
 * @param {Function|null} onAddRobot      - Called with filename when a robot is added;
 *                                          if provided, a "+" button is shown in the header
 */
/**
 * Programmatically select a component by id, expanding collapsed ancestors
 * and scrolling the row into view.
 * @param {string|null} id
 */
export function selectComponentInTree(id) {
  if (_selectedRow) _selectedRow.classList.remove('st-selected');
  _selectedRow = null;
  if (!id) return;

  const row = _rowMap.get(id);
  if (!row) return;

  // Expand every collapsed ancestor list
  let el = row.parentElement;
  while (el && el.id !== 'scene-tree-panel') {
    if (el.classList.contains('st-children') && el.classList.contains('st-collapsed')) {
      el.classList.remove('st-collapsed');
      const toggle = el.parentElement?.querySelector(':scope > .st-row > .st-toggle');
      if (toggle) toggle.textContent = '▾';
    }
    el = el.parentElement;
  }

  _selectedRow = row;
  row.classList.add('st-selected');
  row.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

export function mountSceneTree(sceneDefinition, onSelect = null, onAddRobot = null) {
  _selectedRow = null;
  _rowMap.clear();

  // Close any open picker from a previous mount
  document.getElementById('st-robot-picker')?.remove();

  const existing = document.getElementById('scene-tree-panel');
  if (existing) existing.remove();

  const panel = document.createElement('aside');
  panel.id = 'scene-tree-panel';

  const section = document.createElement('div');
  section.className = 'panel-section';

  // Header row: label + optional add button
  const header = document.createElement('div');
  header.className = 'st-tree-header';

  const labelEl = document.createElement('span');
  labelEl.className = 'panel-label';
  labelEl.textContent = 'Scene Tree';
  header.appendChild(labelEl);

  if (onAddRobot) {
    const addBtn = document.createElement('button');
    addBtn.className = 'st-add-btn';
    addBtn.textContent = '+';
    addBtn.title = 'Add robot from device';
    addBtn.addEventListener('click', () => _showRobotPicker(addBtn, onAddRobot));
    header.appendChild(addBtn);
  }

  section.appendChild(header);

  const tree = document.createElement('ul');
  tree.className = 'scene-tree';

  const hierarchy = buildHierarchy(sceneDefinition.components);
  const roots = sceneDefinition.components.filter(c => !c.parent);

  for (const root of roots) {
    const node = hierarchy.get(root.id);
    if (node) tree.appendChild(buildNode(node, hierarchy, onSelect));
  }

  section.appendChild(tree);
  panel.appendChild(section);

  const app = document.getElementById('app');
  const canvas = document.getElementById('canvas-pane');
  app.insertBefore(panel, canvas);
}