from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.core.errors import ApiError

_SLOT_RE = re.compile(r"^(?P<hour>\d{2}):(?P<minute>\d{2})$")


@dataclass
class ScheduledSlotAssignment:
    publish_at_utc: datetime
    publish_at_local_label: str


class YouTubePublishScheduler:
    def validate_timezone(self, timezone_name: str) -> ZoneInfo:
        try:
            return ZoneInfo(timezone_name)
        except ZoneInfoNotFoundError as exc:
            raise ApiError(422, "invalid_timezone", f"Unknown timezone: {timezone_name}") from exc

    def normalize_slots(self, slots_local: list[str]) -> list[str]:
        normalized: set[str] = set()
        for raw in slots_local:
            match = _SLOT_RE.match(raw.strip())
            if not match:
                raise ApiError(422, "invalid_schedule_slot", f"Invalid local publish slot: {raw}")
            hour = int(match.group("hour"))
            minute = int(match.group("minute"))
            if hour > 23 or minute > 59:
                raise ApiError(422, "invalid_schedule_slot", f"Invalid local publish slot: {raw}")
            normalized.add(f"{hour:02d}:{minute:02d}")
        return sorted(normalized)

    def next_slots(
        self,
        *,
        timezone_name: str,
        slots_local: list[str],
        occupied_utc: list[datetime],
        count: int,
        start_at: datetime | None = None,
    ) -> list[ScheduledSlotAssignment]:
        timezone = self.validate_timezone(timezone_name)
        normalized_slots = self.normalize_slots(slots_local)
        if not normalized_slots:
            raise ApiError(422, "schedule_slots_required", "At least one local publish slot is required.")

        start_utc = (start_at or datetime.now(UTC)).astimezone(UTC)
        occupied = {
            item.astimezone(UTC).replace(second=0, microsecond=0)
            for item in occupied_utc
        }
        local_cursor = start_utc.astimezone(timezone)
        assignments: list[ScheduledSlotAssignment] = []

        for day_offset in range(0, 365):
            local_day = (local_cursor + timedelta(days=day_offset)).date()
            for slot in normalized_slots:
                candidate_utc = self._local_slot_to_utc(local_day, slot, timezone)
                candidate_utc = candidate_utc.replace(second=0, microsecond=0)
                if candidate_utc <= start_utc + timedelta(minutes=1):
                    continue
                if candidate_utc in occupied:
                    continue
                occupied.add(candidate_utc)
                assignments.append(
                    ScheduledSlotAssignment(
                        publish_at_utc=candidate_utc,
                        publish_at_local_label=candidate_utc.astimezone(timezone).strftime("%Y-%m-%d %H:%M %Z"),
                    )
                )
                if len(assignments) >= count:
                    return assignments

        raise ApiError(
            422,
            "schedule_capacity_exhausted",
            "Unable to find enough future publish slots for the requested videos.",
        )

    def _local_slot_to_utc(self, local_day: date, slot: str, timezone: ZoneInfo) -> datetime:
        hour, minute = [int(part) for part in slot.split(":", 1)]
        local_dt = datetime.combine(local_day, time(hour=hour, minute=minute), tzinfo=timezone)
        return local_dt.astimezone(UTC)
