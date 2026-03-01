"""Feed manager for tracking incident lifecycle changes."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from .entry import VicEmergencyIncident

_LOGGER = logging.getLogger(__name__)


@dataclass
class FeedDiff:
    """Result of comparing two successive feed snapshots for a zone."""

    new: list[VicEmergencyIncident]
    updated: list[tuple[VicEmergencyIncident, list[str]]]
    removed: list[VicEmergencyIncident]
    current: dict[str, VicEmergencyIncident]


_DIFF_FIELDS = ("status", "feedtype", "description", "size", "resources", "latitude", "longitude", "updated")


class FeedManager:
    """Track active incidents for a single zone and compute diffs."""

    def __init__(self) -> None:
        self._previous: dict[str, VicEmergencyIncident] = {}

    def update(self, incidents: list[VicEmergencyIncident]) -> FeedDiff:
        """Compare incoming incidents against previous snapshot."""
        current = {i.id: i for i in incidents}

        new: list[VicEmergencyIncident] = []
        updated: list[tuple[VicEmergencyIncident, list[str]]] = []
        removed: list[VicEmergencyIncident] = []

        for incident_id, incident in current.items():
            prev = self._previous.get(incident_id)
            if prev is None:
                new.append(incident)
            else:
                changed = _detect_changes(prev, incident)
                if changed:
                    updated.append((incident, changed))

        for incident_id, prev_incident in self._previous.items():
            if incident_id not in current:
                removed.append(prev_incident)

        self._previous = current

        if new or updated or removed:
            _LOGGER.debug(
                "Feed diff: %d new, %d updated, %d removed (total: %d)",
                len(new), len(updated), len(removed), len(current),
            )

        return FeedDiff(new=new, updated=updated, removed=removed, current=current)

    def reset(self) -> None:
        self._previous.clear()


def _detect_changes(prev: VicEmergencyIncident, curr: VicEmergencyIncident) -> list[str]:
    changed: list[str] = []
    for field_name in _DIFF_FIELDS:
        if getattr(prev, field_name, None) != getattr(curr, field_name, None):
            changed.append(field_name)
    return changed
