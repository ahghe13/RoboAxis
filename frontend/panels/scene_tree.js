/**
 * scene_tree.js
 * -------------
 * Builds a collapsible tree view from the scene definition
 * and mounts it as its own left-side panel.
 *
 * Usage:
 *   import { mountSceneTree } from '/static/panels/scene_tree.js';
 *   mountSceneTree(sceneDefinition, (component) => { ... });
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

/**
 * Build a hierarchical tree structure from flat component list.
 * @param {Array} components - Flat list of components with parent references
 * @returns {Map} Map of component id to { component, children }
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
 * @param {Object} node      - Node from hierarchy with { component, children }
 * @param {Map}    hierarchy - Full hierarchy map
 * @param {Function|null} onSelect - Called with the component object when selected
 */
function buildNode(node, hierarchy, onSelect) {
  const { component, children } = node;
  const li = document.createElement('li');
  const hasChildren = children.length > 0;

  // Row: toggle + icon + label
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
  label.textContent = `${component.name || component.id} (${component.type})`;
  row.appendChild(label);

  li.appendChild(row);

  // Selection: clicking the row (but not the toggle) selects this component
  row.style.cursor = 'pointer';
  row.addEventListener('click', (e) => {
    if (e.target === toggle) return;

    // Expand/collapse if has children
    if (hasChildren) {
      const collapsed = ul.classList.toggle('st-collapsed');
      toggle.textContent = collapsed ? '▸' : '▾';
    }

    // Update selection highlight
    if (_selectedRow) _selectedRow.classList.remove('st-selected');
    _selectedRow = row;
    row.classList.add('st-selected');

    if (onSelect) onSelect(component);
  });

  // Children (collapsed by default)
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
 * Mount the scene tree as a standalone left-side panel.
 * @param {Object}        sceneDefinition - Scene definition with { type, components }
 * @param {Function|null} onSelect        - Called with component object on selection
 */
export function mountSceneTree(sceneDefinition, onSelect = null) {
  // Reset selection state when tree is rebuilt
  _selectedRow = null;

  // Remove existing panel if any
  const existingPanel = document.getElementById('scene-tree-panel');
  if (existingPanel) existingPanel.remove();

  const panel = document.createElement('aside');
  panel.id = 'scene-tree-panel';

  const section = document.createElement('div');
  section.className = 'panel-section';
  section.innerHTML = `<div class="panel-label">Scene Tree</div>`;

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