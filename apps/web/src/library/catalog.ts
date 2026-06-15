// Interior component catalog (Phase 12). Frontend catalog for placement/swap; a server-side
// registry with glTF assets + IFC mappings is a follow-up. Sizes are millimetres [width, depth, height].

export type ComponentCategory =
  | 'seating'
  | 'bed'
  | 'table'
  | 'storage'
  | 'sanitary'
  | 'kitchen'
  | 'appliance'
  | 'desk';

export interface ComponentDef {
  id: string;
  label: string;
  category: ComponentCategory;
  size_mm: [number, number, number];
  wall_mounted: boolean;
  /** Room types this component suits (for swap suggestions). */
  affinity: string[];
}

export const CATALOG: ComponentDef[] = [
  {
    id: 'bed-double',
    label: 'Double Bed',
    category: 'bed',
    size_mm: [1500, 2000, 600],
    wall_mounted: true,
    affinity: ['bedroom', 'master_bedroom'],
  },
  {
    id: 'bed-single',
    label: 'Single Bed',
    category: 'bed',
    size_mm: [1000, 2000, 600],
    wall_mounted: true,
    affinity: ['bedroom'],
  },
  {
    id: 'nightstand',
    label: 'Nightstand',
    category: 'storage',
    size_mm: [450, 400, 500],
    wall_mounted: true,
    affinity: ['bedroom', 'master_bedroom'],
  },
  {
    id: 'wardrobe',
    label: 'Wardrobe',
    category: 'storage',
    size_mm: [1200, 600, 2100],
    wall_mounted: true,
    affinity: ['bedroom', 'master_bedroom', 'closet'],
  },
  {
    id: 'sofa',
    label: 'Sofa',
    category: 'seating',
    size_mm: [2000, 900, 800],
    wall_mounted: true,
    affinity: ['living'],
  },
  {
    id: 'coffee-table',
    label: 'Coffee Table',
    category: 'table',
    size_mm: [1100, 600, 400],
    wall_mounted: false,
    affinity: ['living'],
  },
  {
    id: 'bookshelf',
    label: 'Bookshelf',
    category: 'storage',
    size_mm: [900, 300, 1800],
    wall_mounted: true,
    affinity: ['living', 'office'],
  },
  {
    id: 'dining-table',
    label: 'Dining Table',
    category: 'table',
    size_mm: [1600, 900, 750],
    wall_mounted: false,
    affinity: ['dining', 'living'],
  },
  {
    id: 'kitchen-counter',
    label: 'Kitchen Counter',
    category: 'kitchen',
    size_mm: [3000, 600, 900],
    wall_mounted: true,
    affinity: ['kitchen'],
  },
  {
    id: 'fridge',
    label: 'Refrigerator',
    category: 'appliance',
    size_mm: [700, 700, 1800],
    wall_mounted: true,
    affinity: ['kitchen'],
  },
  {
    id: 'toilet',
    label: 'Toilet',
    category: 'sanitary',
    size_mm: [380, 680, 800],
    wall_mounted: true,
    affinity: ['bathroom', 'ensuite', 'wc'],
  },
  {
    id: 'basin',
    label: 'Basin',
    category: 'sanitary',
    size_mm: [550, 450, 850],
    wall_mounted: true,
    affinity: ['bathroom', 'ensuite', 'wc'],
  },
  {
    id: 'shower',
    label: 'Shower',
    category: 'sanitary',
    size_mm: [900, 900, 2000],
    wall_mounted: true,
    affinity: ['bathroom', 'ensuite'],
  },
  {
    id: 'desk',
    label: 'Desk',
    category: 'desk',
    size_mm: [1400, 700, 750],
    wall_mounted: true,
    affinity: ['office'],
  },
  {
    id: 'office-chair',
    label: 'Office Chair',
    category: 'seating',
    size_mm: [600, 600, 1100],
    wall_mounted: false,
    affinity: ['office'],
  },
  {
    id: 'shelving-unit',
    label: 'Shelving Unit',
    category: 'storage',
    size_mm: [900, 400, 1800],
    wall_mounted: true,
    affinity: ['storage', 'utility', 'garage', 'mechanical', 'laundry'],
  },
  {
    id: 'bench',
    label: 'Bench',
    category: 'seating',
    size_mm: [1200, 400, 450],
    wall_mounted: true,
    affinity: ['entry', 'lobby', 'reception', 'hallway', 'corridor'],
  },
];

export const CATALOG_BY_ID: Record<string, ComponentDef> = Object.fromEntries(
  CATALOG.map((c) => [c.id, c]),
);

/** Default furniture set per room type (ids placed by auto-furnish). */
export const ROOM_FURNITURE: Record<string, string[]> = {
  master_bedroom: ['bed-double', 'nightstand', 'wardrobe'],
  bedroom: ['bed-single', 'nightstand', 'wardrobe'],
  living: ['sofa', 'coffee-table', 'bookshelf'],
  dining: ['dining-table'],
  kitchen: ['kitchen-counter', 'fridge'],
  bathroom: ['toilet', 'basin', 'shower'],
  ensuite: ['toilet', 'basin', 'shower'],
  wc: ['toilet', 'basin'],
  office: ['desk', 'office-chair', 'bookshelf'],
  hallway: ['bench'],
  corridor: ['bench'],
  entry: ['bench', 'bookshelf'],
  lobby: ['bench', 'bookshelf'],
  reception: ['bench', 'bookshelf'],
  closet: ['wardrobe'],
  laundry: ['shelving-unit'],
  utility: ['shelving-unit'],
  garage: ['shelving-unit'],
  mechanical: ['shelving-unit'],
  storage: ['shelving-unit'],
  meeting: ['dining-table', 'office-chair'],
};

export function componentsForRoom(roomType: string): ComponentDef[] {
  return CATALOG.filter((c) => c.affinity.includes(roomType));
}
