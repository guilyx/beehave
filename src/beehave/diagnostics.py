"""Non-fatal findings reported alongside a result."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from beehave.model import SourceLocation


class Severity(str, Enum):
    """How much a diagnostic matters."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass(frozen=True)
class Diagnostic:
    """Something worth telling the user that does not stop the analysis.

    Attributes:
        code: A stable, machine-readable identifier such as ``"approximated"``.
        message: A plain-English explanation.
        severity: How much it matters.
        node_type: The node type the diagnostic is about, if any.
        location: Where in the source it was found, if known.
    """

    code: str
    message: str
    severity: Severity = Severity.WARNING
    node_type: str | None = None
    location: SourceLocation | None = field(default=None, compare=False)

    def __str__(self) -> str:
        where = f"{self.location}: " if self.location else ""
        return f"{where}{self.severity.value}: {self.message} [{self.code}]"
