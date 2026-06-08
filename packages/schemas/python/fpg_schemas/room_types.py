"""Known room/space type registry (advisory; RoomType is an open string in the schema)."""

from __future__ import annotations

KNOWN_ROOM_TYPES: tuple[str, ...] = (
    "bedroom",
    "master_bedroom",
    "bathroom",
    "ensuite",
    "wc",
    "kitchen",
    "living",
    "dining",
    "hallway",
    "corridor",
    "entry",
    "lobby",
    "reception",
    "stair",
    "elevator",
    "closet",
    "laundry",
    "utility",
    "garage",
    "office",
    "meeting",
    "balcony",
    "storage",
    "mechanical",
    "retail",
)


def is_known_room_type(value: str) -> bool:
    return value in KNOWN_ROOM_TYPES
