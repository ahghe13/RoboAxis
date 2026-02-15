from dataclasses import dataclass
from typing import Any

from axis_math import Transform

@dataclass
class Link:
    """
    A rigid body segment in a kinematic chain.

    Links connect joints and define the fixed geometric offset between
    them. They carry no state — only a constant local transform.

    Attributes
    ----------
    name      : str        Identifier for this link.
    transform : Transform  Fixed local offset (relative to parent joint/link).
    """
    name: str
    transform: Transform = Transform()

    def snapshot(self) -> dict[str, Any]:
        """Return JSON-serializable state for this link."""
        return {
            "type": "Link",
            "name": self.name,
        }


