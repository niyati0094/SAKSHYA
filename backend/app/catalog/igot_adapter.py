"""iGOT Karmayogi catalogue adapter — deliberately non-functional.

This file exists to be read, not to be called.

No complete public specification of the iGOT Karmayogi API - endpoints, auth
model, or response schema - is available. Writing a client against a guessed
contract would produce code that looks like an integration and is actually
fiction, and a demo built on it would be a fabrication.

So the integration boundary is real and the implementation is honestly empty.
Every method raises `IntegrationNotAuthorized`. Nothing here returns a
simulated response, ever.

What would be required to make this functional is a governance process, not a
coding task:

  1. Authorisation from Karmayogi Bharat / the Capacity Building Commission.
  2. A data-sharing agreement covering competency evidence exchange.
  3. A security and privacy review.
  4. Deployment inside government infrastructure.
  5. The published API contract this class would then be written against.

DoPT's Karmayogi Guidelines (2023) anticipate data exchange with training
providers and existing LMS platforms, which is why this pathway is realistic.
Until that process completes, `LocalCatalogAdapter` serves the prototype and
SAKSHYA delivers its value standalone.
"""

from __future__ import annotations

from app.catalog.base import LearningResource


class IntegrationNotAuthorized(RuntimeError):
    """Raised whenever the iGOT adapter is invoked.

    Carries the reason so that a caller - or a curious judge reading a stack
    trace - sees exactly why no data came back.
    """

    def __init__(self, operation: str) -> None:
        super().__init__(
            f"iGOT Karmayogi integration is not authorised, so '{operation}' "
            "cannot be performed. No public API specification exists for this "
            "platform, and SAKSHYA does not fabricate responses. Enabling this "
            "adapter requires authorisation from Karmayogi Bharat / CBC, a "
            "data-sharing agreement, a security review, and deployment inside "
            "government infrastructure. See app/catalog/igot_adapter.py."
        )
        self.operation = operation


class IGotAdapter:
    """Satisfies `LearningCatalogAdapter`. Returns nothing, by design."""

    name = "iGOT Karmayogi (not authorised)"
    is_live_integration = False

    #: Read by the UI so the boundary is visible to a user, not just a reader.
    authorisation_required = (
        "Karmayogi Bharat / CBC authorisation, a data-sharing agreement, a "
        "security and privacy review, and deployment inside government "
        "infrastructure."
    )

    def find_for_competency(
        self, competency_code: str, *, kind: str | None = None
    ) -> list[LearningResource]:
        raise IntegrationNotAuthorized("find_for_competency")

    def all_resources(self) -> list[LearningResource]:
        raise IntegrationNotAuthorized("all_resources")
