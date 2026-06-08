import { isKnownRoomType } from '@fpg/schemas';

// Ordered keyword → canonical RoomType rules. First match wins.
const RULES: Array<[RegExp, string]> = [
  [/\b(master|mbr|primary bed)/i, 'master_bedroom'],
  [/\b(bed|bdr|br)\b/i, 'bedroom'],
  [/\bbedroom/i, 'bedroom'],
  [/\b(ensuite|en-suite)/i, 'ensuite'],
  [/\b(wc|toilet|powder|lavatory)/i, 'wc'],
  [/\b(bath|washroom|shower)/i, 'bathroom'],
  [/\b(kitchen|kitchenette|pantry)/i, 'kitchen'],
  [/\b(living|lounge|family|sitting)/i, 'living'],
  [/\bdining/i, 'dining'],
  [/\b(office|study|workspace|work\s?room)/i, 'office'],
  [/\b(meeting|conf|mtg|boardroom)/i, 'meeting'],
  [/\b(reception|lobby|waiting)/i, 'lobby'],
  [/\b(entry|foyer|vestibule|porch)/i, 'entry'],
  [/\b(hall|corridor|passage|circulation)/i, 'corridor'],
  [/\bstair/i, 'stair'],
  [/\b(lift|elevator)/i, 'elevator'],
  [/\b(closet|wardrobe|wic|robe)/i, 'closet'],
  [/\b(laundry|utility)/i, 'laundry'],
  [/\b(garage|parking|carport)/i, 'garage'],
  [/\b(store|storage)/i, 'storage'],
  [/\b(mech|plant|mechanical|riser|shaft)/i, 'mechanical'],
  [/\b(balcony|terrace|deck)/i, 'balcony'],
  [/\bretail|shop/i, 'retail'],
];

export interface InferredType {
  type: string;
  known: boolean;
}

export function slugify(label: string): string {
  return label
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '');
}

/** Infer a canonical RoomType from free-text. Falls back to a slug (a custom, valid type). */
export function inferRoomType(text: string): InferredType {
  const t = text.toLowerCase();
  for (const [re, type] of RULES) {
    if (re.test(t)) return { type, known: true };
  }
  if (isKnownRoomType(t)) return { type: t, known: true };
  const slug = slugify(text);
  return { type: slug || 'storage', known: false };
}
