from __future__ import annotations

from typing import Dict, List, Tuple

from domain.step02_output import Step02AstExtractorOutput
from steps.step04.models import Entity, Relation


class LinkerPlugin:
    """Base class for Step04 linker/builder plugins.

    Implementations should derive concrete route and relation constructs
    from Step02 outputs and return new entities/relations without mutating inputs.
    """

    def apply(
        self,
        routes: Dict[str, Entity],
        step02: Step02AstExtractorOutput,
    ) -> Tuple[Dict[str, Entity], List[Relation], Dict[str, Entity]]:
        """Build additional routes and relations.

        Returns a tuple of (new_route_entities, new_relations, new_method_entities).
        """
        raise NotImplementedError
