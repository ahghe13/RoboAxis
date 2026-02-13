/**
 * scene_tree.js
 * -------------
 * Builds a collapsible tree view of the Three.js scene graph
 * and mounts it as its own left-side panel.
 *
 * Usage:
 *   import { mountSceneTree } from '/static/scene_tree.js';
 *   mountSceneTree(scene3d.scene);
 */

const TYPE_ICONS = {
  Scene:            '⊞',
  Group:            '▦',
  Mesh:             '◆',
  Line:             '╱',
  LineSegments:     '╱',
  Points:           '·',
  AmbientLight:     '☀',
  DirectionalLight: '☀',
  PointLight:       '☀',
  SpotLight:        '☀',
  HemisphereLight:  '☀',
  PerspectiveCamera:'▣',
  OrthographicCamera:'▣',
  GridHelper:       '⊞',
  AxesHelper:       '✛',
};

/**
 * Build a single tree node (li) for a Three.js object.
 */
function buildNode(obj) {
  const li = document.createElement('li');
  const hasChildren = obj.children.length > 0;

  // Row: toggle + icon + label
  const row = document.createElement('span');
  row.className = 'st-row';

  const toggle = document.createElement('span');
  toggle.className = 'st-toggle';
  toggle.textContent = hasChildren ? '▸' : ' ';
  row.appendChild(toggle);

  const icon = document.createElement('span');
  icon.className = 'st-icon';
  icon.textContent = TYPE_ICONS[obj.type] || '○';
  row.appendChild(icon);

  const label = document.createElement('span');
  label.className = 'st-label';
  const name = obj.name ? ` "${obj.name}"` : '';
  label.textContent = `${obj.type}${name}`;
  row.appendChild(label);

  li.appendChild(row);

  // Children (collapsed by default for non-Scene)
  if (hasChildren) {
    const ul = document.createElement('ul');
    ul.className = 'st-children';
    for (const child of obj.children) {
      ul.appendChild(buildNode(child));
    }
    li.appendChild(ul);

    // Start expanded for the root Scene, collapsed otherwise
    if (obj.type !== 'Scene') {
      ul.classList.add('st-collapsed');
    } else {
      toggle.textContent = '▾';
    }

    toggle.addEventListener('click', () => {
      const collapsed = ul.classList.toggle('st-collapsed');
      toggle.textContent = collapsed ? '▸' : '▾';
    });

    row.style.cursor = 'pointer';
    row.addEventListener('click', (e) => {
      if (e.target === toggle) return;  // already handled
      const collapsed = ul.classList.toggle('st-collapsed');
      toggle.textContent = collapsed ? '▸' : '▾';
    });
  }

  return li;
}

/**
 * Mount the scene tree as a standalone left-side panel.
 * @param {THREE.Scene} threeScene  The Three.js scene to visualise.
 */
export function mountSceneTree(threeScene) {
  const panel = document.createElement('aside');
  panel.id = 'scene-tree-panel';

  const section = document.createElement('div');
  section.className = 'panel-section';
  section.innerHTML = `<div class="panel-label">Scene Graph</div>`;

  const tree = document.createElement('ul');
  tree.className = 'scene-tree';
  tree.appendChild(buildNode(threeScene));
  section.appendChild(tree);

  panel.appendChild(section);

  // Insert before canvas-pane so grid order is: header, scene-tree, canvas, panel
  const app = document.getElementById('app');
  const canvas = document.getElementById('canvas-pane');
  app.insertBefore(panel, canvas);
}