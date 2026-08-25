"""Learning catalogue integration boundary.

SAKSHYA is specified to recommend training through the iGOT Karmayogi
ecosystem. No live iGOT API is implemented, called, or simulated here - doing
so would mean inventing an interface we have not integrated against.

Instead the boundary is made explicit. `LearningCatalogAdapter` is the contract
any catalogue must satisfy; `LocalCatalogAdapter` is a prototype
implementation backed by sample resources shipped with this repository. An iGOT
adapter is added by implementing this protocol, with no change to the
recommender.

Every resource carries `provider` and `is_prototype_data` so a prototype
resource can never be mistaken for a real iGOT course in the UI or an export.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class ResourceKind:
    """Where a resource sits in the Learn -> Practice -> Prove progression."""

    LEARN = "learn"
    PRACTICE = "practice"
    PROVE = "prove"


@dataclass(frozen=True)
class LearningResource:
    external_id: str
    title: str
    description: str
    kind: str
    competency_code: str
    #: Level this resource is pitched at (1-4).
    target_level: int
    estimated_minutes: int
    provider: str
    #: Competency codes that should be established before starting this.
    prerequisites: tuple[str, ...] = ()
    url: str | None = None
    #: True when the learner can actually complete this inside SAKSHYA today
    #: (currently the simulations). Catalogue entries that merely describe
    #: external material are False, so the recommender never sends a learner
    #: to something they cannot act on.
    is_interactive: bool = False
    is_prototype_data: bool = True


@runtime_checkable
class LearningCatalogAdapter(Protocol):
    """Contract for any learning catalogue, local or external (e.g. iGOT)."""

    name: str
    is_live_integration: bool

    def find_for_competency(
        self, competency_code: str, *, kind: str | None = None
    ) -> list[LearningResource]:
        """Resources that develop the given competency."""
        ...

    def all_resources(self) -> list[LearningResource]:
        ...
