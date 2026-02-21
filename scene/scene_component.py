from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Optional

from axis_math.axis_math import Transform


@dataclass
class SceneComponent:
    """Base node in the scene graph.

    Attributes
    ----------
    id        : str                  Unique identifier for this component.
    transform : Transform            Local transform relative to the parent component.
    children  : list                 Direct child components in the scene hierarchy.
    cad_file  : str | None           Path to the CAD file for this component (optional).
    cad_body  : str | None           Name of the body within the CAD file (optional).
    parent    : SceneComponent | None  Back-reference to the parent component, or None for root nodes.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    transform: Transform = field(default_factory=Transform)
    transform_locked: bool = False
    children: list[SceneComponent] = field(default_factory=list)
    cad_file: Optional[str] = None
    cad_body: Optional[str] = None
    parent: Optional[SceneComponent] = field(default=None, repr=False, compare=False)

    def get_component_type(self) -> str:
        """Return the component type identifier for this component."""
        return "basic_component"

    def set_transform(self, transform: Transform) -> None:
        """Replace the local transform of this component.

        Raises
        ------
        PermissionError
            If ``transform_locked`` is True.
        """
        if self.transform_locked:
            raise PermissionError(f"Transform of '{self.name or self.id}' is locked")
        self.transform = transform

    def get_world_transform(self, parent_transform: Transform) -> Transform:
        """Return the world transform to propagate to children.

        For a plain component this is parent × fixed_offset.
        Subclasses with dynamic state (e.g. Joint) should override this to
        include their runtime contribution.
        """
        return parent_transform.compose(self.transform)

    def get_state(self, parent_transform: Optional[Transform] = None) -> dict[str, Any]:
        """Return the current state of this component as a JSON-serialisable dict.

        Parameters
        ----------
        parent_transform : Transform | None
            World transform of the parent component. Pass ``None`` (default)
            for root nodes; an identity transform is used.
        """
        world_tf = (parent_transform or Transform()).compose(self.transform)

        return {
            "id": self.id,
            "matrix": world_tf.to_matrix().flatten().tolist(),
        }

    def get_component(self, id: str) -> Optional[SceneComponent]:
        """Return the descendant with the given *id*, or ``None`` if not found.

        Searches depth-first through all children recursively.
        """
        for child in self.children:
            if child.id == id:
                return child
            found = child.get_component(id)
            if found is not None:
                return found
        return None

    def add_child(self, child: SceneComponent) -> None:
        """Append *child* to this component's children list and set its parent."""
        self.children.append(child)
        child.parent = self

    def remove_child(self, child: SceneComponent) -> None:
        """Remove *child* from this component's children list and clear its parent."""
        self.children.remove(child)
        child.parent = None

    def static_definition(self) -> list[dict[str, Any]]:
        """Return a flat JSON-serialisable list of definitions for this component and all descendants.

        Each entry represents one component. The list is ordered depth-first
        (parent before children).
        """
        entry: dict[str, Any] = {
            "id": self.id,
            "name": self.name,
            "parent": self.parent.id if self.parent is not None else None,
            "component_type": self.get_component_type(),
            "transform": self.transform.to_dict(),
            "transform_locked": self.transform_locked,
        }
        if self.cad_file is not None:
            entry["cad_file"] = self.cad_file
        if self.cad_body is not None:
            entry["cad_body"] = self.cad_body

        result = [entry]
        for child in self.children:
            result.extend(child.static_definition())

        return result

