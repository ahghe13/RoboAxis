"""
scene.py
--------
Root node of the 3D scene graph.
"""
from __future__ import annotations

from typing import Any, Optional

from axis_math import Transform
try:
    from scene.scene_component import SceneComponent
except ImportError:
    from scene_component import SceneComponent  # type: ignore[no-redef]


class Scene(SceneComponent):
    """Root node of the scene graph.

    Inherits the full tree structure from SceneComponent and overrides
    static_definition and get_state to wrap results in typed message dicts
    for the frontend.
    """

    def __init__(self) -> None:
        super().__init__()
        self.name = "scene"

    def get_component_type(self) -> str:
        return "scene"

    def static_definition(self) -> dict[str, Any]:
        """Return the full scene structure as a typed message.

        Returns:
            {
                "type": "static_scene_definition",
                "components": [ {id, parent, component_type, ...}, ... ]
            }
        """
        return {
            "type": "static_scene_definition",
            "components": super().static_definition(),
        }

    def get_state(self, parent_transform: Optional[Transform] = None) -> dict[str, Any]:
        """Return world-space transforms for every node as a typed message.

        Recursively walks the scene tree, accumulating world transforms.

        Returns:
            {
                "type": "state_update",
                "components": [ {id, matrix}, ... ]
            }
        """
        components: list[dict[str, Any]] = []

        def collect(node: SceneComponent, parent_tf: Transform) -> None:
            components.append(node.get_state(parent_tf))
            child_tf = node.get_world_transform(parent_tf)
            for c in node.children:
                collect(c, child_tf)

        for child in self.children:
            collect(child, Transform())

        return {
            "type": "state_update",
            "components": components,
        }


if __name__ == "__main__":
    import json

    # Build a small tree: scene → base → arm → tool
    scene = Scene()

    base = SceneComponent(id="base", transform=Transform(position=(1.0, 0.0, 0.0)),
                          cad_file="robot.step", cad_body="Base")
    arm  = SceneComponent(id="arm",  transform=Transform(position=(0.0, 1.0, 0.0)),
                          cad_file="robot.step", cad_body="Arm")
    tool = SceneComponent(id="tool", transform=Transform(position=(0.0, 0.5, 0.0)))

    scene.add_child(base)
    base.add_child(arm)
    arm.add_child(tool)

    print("=== static_definition ===")
    print(json.dumps(scene.static_definition(), indent=2))

    print("\n=== get_state ===")
    print(json.dumps(scene.get_state(), indent=2))