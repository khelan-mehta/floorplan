// The known room/space type registry. `RoomType` in the schemas is an open string, so this list
// is advisory (used for palettes, defaults, type inference) — not a closed validation set.

export const KNOWN_ROOM_TYPES = [
  'bedroom',
  'master_bedroom',
  'bathroom',
  'ensuite',
  'wc',
  'kitchen',
  'living',
  'dining',
  'hallway',
  'corridor',
  'entry',
  'lobby',
  'reception',
  'stair',
  'elevator',
  'closet',
  'laundry',
  'utility',
  'garage',
  'office',
  'meeting',
  'balcony',
  'storage',
  'mechanical',
  'retail',
] as const;

export type KnownRoomType = (typeof KNOWN_ROOM_TYPES)[number];

export function isKnownRoomType(value: string): value is KnownRoomType {
  return (KNOWN_ROOM_TYPES as readonly string[]).includes(value);
}
