import { Environment, GizmoHelper, GizmoViewport, Grid, Line, OrbitControls, Text } from '@react-three/drei';
import { Canvas, useThree } from '@react-three/fiber';
import { useEffect, useMemo } from 'react';
import * as THREE from 'three';
import type { Plan } from '@fpg/schemas';
import type { ComponentCategory } from '../library/catalog';
import { CATALOG_BY_ID } from '../library/catalog';
import { useEditor } from '../store/editor';
import { findEntryRoom, shortestDoorPaths } from './circulation';
import { formatRoomType, getLevel } from './plan-render';
import {
  type Box,
  MM_TO_M,
  type Opening3D,
  type RoomSlab,
  openings3D,
  roomSlabs,
  wallSegments,
} from './plan-3d';
import { exposureColor, levelSunDirection, roomSunExposure } from './sunlight';

export type CameraView = 'iso' | 'top';

function RoomSlabMesh({
  slab,
  onSelect,
  overrideColor,
}: {
  slab: RoomSlab;
  onSelect: () => void;
  overrideColor?: string;
}) {
  const geometry = useMemo(() => {
    const shape = new THREE.Shape();
    slab.points.forEach((p, i) => (i === 0 ? shape.moveTo(p[0], p[1]) : shape.lineTo(p[0], p[1])));
    return new THREE.ShapeGeometry(shape);
  }, [slab.points]);

  return (
    <mesh
      geometry={geometry}
      // Map plan XY -> world XZ. +π/2 about X sends (x,y)->(x,0,+y) so floor slabs share the same
      // Z sign as the wall boxes (which use +y for Z); -π/2 would mirror them and offset the floors.
      rotation={[Math.PI / 2, 0, 0]}
      position={[0, 0.01, 0]}
      onClick={onSelect}
      receiveShadow
    >
      <meshStandardMaterial
        color={overrideColor ?? slab.color}
        side={THREE.DoubleSide}
        transparent
        opacity={0.85}
      />
    </mesh>
  );
}

function WallMesh({ box }: { box: Box }) {
  return (
    <mesh position={box.center} rotation={[0, box.rotationY, 0]} castShadow receiveShadow>
      <boxGeometry args={box.size} />
      <meshStandardMaterial color="#d7dde6" roughness={0.9} />
    </mesh>
  );
}

const DOOR_LEAF = '#9a6a3c';
const FRAME = '#5b6675';
const GLASS = '#9ecbff';

/** A door sitting in its wall void: a frame (head + jambs) and, for a real door, a leaf + knob. */
function Door3D({ op }: { op: Opening3D }) {
  const { width: w, height: h, thickness: t } = op;
  const fT = Math.min(0.06, w / 6);
  const depth = t + 0.02;
  return (
    <group position={op.center} rotation={[0, op.rotationY, 0]}>
      <mesh position={[0, h / 2 - fT / 2, 0]} castShadow>
        <boxGeometry args={[w, fT, depth]} />
        <meshStandardMaterial color={FRAME} />
      </mesh>
      {[-1, 1].map((s) => (
        <mesh key={s} position={[s * (w / 2 - fT / 2), 0, 0]} castShadow>
          <boxGeometry args={[fT, h, depth]} />
          <meshStandardMaterial color={FRAME} />
        </mesh>
      ))}
      {op.kind !== 'opening' && (
        <>
          <mesh position={[0, -fT / 2, 0]} castShadow>
            <boxGeometry args={[w - fT * 2, h - fT, 0.05]} />
            <meshStandardMaterial color={DOOR_LEAF} roughness={0.7} />
          </mesh>
          <mesh position={[w / 2 - fT * 1.6, 0, 0.05]}>
            <sphereGeometry args={[Math.min(0.04, w / 18), 12, 12]} />
            <meshStandardMaterial color="#d9c089" metalness={0.6} roughness={0.3} />
          </mesh>
        </>
      )}
    </group>
  );
}

/** A glazed window: frame (head/sill/jambs), a cross mullion, and a translucent pane. */
function Window3D({ op }: { op: Opening3D }) {
  const { width: w, height: h, thickness: t } = op;
  const fT = Math.min(0.05, w / 8);
  const depth = t + 0.02;
  const bar = 0.03;
  return (
    <group position={op.center} rotation={[0, op.rotationY, 0]}>
      {[-1, 1].map((s) => (
        <mesh key={`h${s}`} position={[0, s * (h / 2 - fT / 2), 0]} castShadow>
          <boxGeometry args={[w, fT, depth]} />
          <meshStandardMaterial color={FRAME} />
        </mesh>
      ))}
      {[-1, 1].map((s) => (
        <mesh key={`v${s}`} position={[s * (w / 2 - fT / 2), 0, 0]} castShadow>
          <boxGeometry args={[fT, h, depth]} />
          <meshStandardMaterial color={FRAME} />
        </mesh>
      ))}
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[bar, h, depth * 0.9]} />
        <meshStandardMaterial color={FRAME} />
      </mesh>
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[w, bar, depth * 0.9]} />
        <meshStandardMaterial color={FRAME} />
      </mesh>
      <mesh position={[0, 0, 0]}>
        <boxGeometry args={[w - fT * 2, h - fT * 2, 0.02]} />
        <meshStandardMaterial
          color={GLASS}
          transparent
          opacity={0.35}
          metalness={0.1}
          roughness={0.1}
        />
      </mesh>
    </group>
  );
}

/** Fixture box color by catalog category, instead of one flat gray. */
const CATEGORY_COLORS: Record<ComponentCategory, string> = {
  seating: '#c9a079',
  bed: '#6366f1',
  table: '#b08968',
  desk: '#b08968',
  storage: '#8b5e3c',
  sanitary: '#e6f3f7',
  kitchen: '#94a3b8',
  appliance: '#94a3b8',
};

function FixtureMesh({ componentId, pos }: { componentId: string; pos: [number, number, number] }) {
  const def = CATALOG_BY_ID[componentId];
  if (!def) return null;
  const [w, d, h] = def.size_mm;
  return (
    <mesh position={[pos[0] * MM_TO_M, (h / 2) * MM_TO_M, pos[1] * MM_TO_M]} castShadow>
      <boxGeometry args={[w * MM_TO_M, h * MM_TO_M, d * MM_TO_M]} />
      <meshStandardMaterial color={CATEGORY_COLORS[def.category]} />
    </mesh>
  );
}

function CameraRig({ view }: { view: CameraView }) {
  const { camera } = useThree();
  useEffect(() => {
    if (view === 'top') camera.position.set(0, 30, 0.001);
    else camera.position.set(20, 18, 20);
    camera.lookAt(0, 0, 0);
  }, [view, camera]);
  return null;
}

const SUN_DISTANCE = 40;

export function PlanScene3D({
  plan,
  view = 'iso',
  showCirculation = false,
  showSunlight = false,
}: {
  plan: Plan;
  view?: CameraView;
  showCirculation?: boolean;
  showSunlight?: boolean;
}) {
  const selectedLevel = useEditor((s) => s.selectedLevel);
  const select = useEditor((s) => s.select);
  const level = getLevel(plan, selectedLevel);
  const slabs = useMemo(() => (level ? roomSlabs(level) : []), [level]);
  const walls = useMemo(() => (level ? wallSegments(level) : []), [level]);
  const openings = useMemo(() => (level ? openings3D(level) : []), [level]);
  const entry = useMemo(() => (level ? findEntryRoom(level) : undefined), [level]);
  const doorPaths = useMemo(() => (level ? shortestDoorPaths(level) : new Map()), [level]);
  const sun = useMemo(
    () => (level && showSunlight ? levelSunDirection(level) : null),
    [level, showSunlight],
  );
  if (!level) return null;

  const slabById = new Map(slabs.map((s) => [s.id, s]));

  // Deduplicate path edges across rooms that share a leg of the route to the entry.
  const pathEdges: Array<[[number, number, number], [number, number, number]]> = [];
  if (showCirculation) {
    const seen = new Set<string>();
    for (const { path } of doorPaths.values()) {
      for (let i = 0; i + 1 < path.length; i++) {
        const a = path[i] as string;
        const b = path[i + 1] as string;
        const key = a < b ? `${a}|${b}` : `${b}|${a}`;
        if (seen.has(key)) continue;
        seen.add(key);
        const sa = slabById.get(a);
        const sb = slabById.get(b);
        if (!sa || !sb) continue;
        pathEdges.push([
          [sa.centroid[0], 0.05, sa.centroid[1]],
          [sb.centroid[0], 0.05, sb.centroid[1]],
        ]);
      }
    }
  }

  return (
    <Canvas shadows camera={{ position: [20, 18, 20], fov: 50 }}>
      <CameraRig view={view} />
      <ambientLight intensity={showSunlight ? 0.15 : 0.6} />
      <directionalLight
        position={[15, 25, 10]}
        intensity={showSunlight ? 0.25 : 1.1}
        castShadow
      />
      {!showSunlight && <directionalLight position={[-15, 12, -10]} intensity={0.25} />}
      {!showSunlight && <Environment preset="apartment" />}
      {showSunlight && sun && (
        <>
          <directionalLight
            position={[sun.vector[0] * SUN_DISTANCE, sun.vector[1] * SUN_DISTANCE, sun.vector[2] * SUN_DISTANCE]}
            intensity={1.3}
            color="#fff3d4"
          />
          <mesh
            position={[sun.vector[0] * SUN_DISTANCE, sun.vector[1] * SUN_DISTANCE, sun.vector[2] * SUN_DISTANCE]}
          >
            <sphereGeometry args={[2, 24, 24]} />
            <meshStandardMaterial color="#fbbf24" emissive="#fbbf24" emissiveIntensity={2} />
          </mesh>
        </>
      )}
      <Grid
        args={[60, 60]}
        cellSize={1}
        sectionSize={5}
        infiniteGrid
        fadeDistance={80}
        cellColor="#2a2f3a"
        sectionColor="#3b4252"
      />
      {slabs.map((slab) => {
        const room = level.rooms.find((r) => r.id === slab.id);
        const overrideColor =
          showSunlight && room ? exposureColor(roomSunExposure(level, room).score) : undefined;
        return (
          <RoomSlabMesh
            key={slab.id}
            slab={slab}
            onSelect={() => select('room', slab.id)}
            overrideColor={overrideColor}
          />
        );
      })}
      {walls.map((box, i) => (
        <WallMesh key={i} box={box} />
      ))}
      {openings.map((op) =>
        op.kind === 'window' ? <Window3D key={op.id} op={op} /> : <Door3D key={op.id} op={op} />,
      )}
      {level.fixtures.map((fx) => (
        <FixtureMesh key={fx.id} componentId={fx.component_id} pos={fx.transform.pos} />
      ))}
      {slabs.map((slab) => (
        <Text
          key={`label-${slab.id}`}
          position={[slab.centroid[0], 0.35, slab.centroid[1]]}
          rotation={[-Math.PI / 2, 0, 0]}
          fontSize={0.22}
          color="#1f2937"
          anchorX="center"
          anchorY="middle"
        >
          {formatRoomType(slab.type)}
        </Text>
      ))}
      {showCirculation && entry && (
        <>
          {(() => {
            const entrySlab = slabById.get(entry.id);
            if (!entrySlab) return null;
            return (
              <>
                <mesh position={[entrySlab.centroid[0], 0.6, entrySlab.centroid[1]]}>
                  <sphereGeometry args={[0.18, 16, 16]} />
                  <meshStandardMaterial color="#22c55e" emissive="#22c55e" emissiveIntensity={1.5} />
                </mesh>
                <Text
                  position={[entrySlab.centroid[0], 1.0, entrySlab.centroid[1]]}
                  fontSize={0.25}
                  color="#22c55e"
                  anchorX="center"
                  anchorY="middle"
                >
                  Entry
                </Text>
              </>
            );
          })()}
          {pathEdges.map(([a, b], i) => (
            <Line key={`path-${i}`} points={[a, b]} color="#22c55e" lineWidth={3} />
          ))}
          {slabs.map((slab) => {
            if (slab.id === entry.id) return null;
            const info = doorPaths.get(slab.id);
            if (!info) return null;
            return (
              <Text
                key={`doors-${slab.id}`}
                position={[slab.centroid[0], 0.6, slab.centroid[1]]}
                fontSize={0.18}
                color="#16a34a"
                anchorX="center"
                anchorY="middle"
              >
                {`${info.distance} door${info.distance === 1 ? '' : 's'} from entry`}
              </Text>
            );
          })}
        </>
      )}
      <OrbitControls makeDefault />
      <GizmoHelper alignment="bottom-right" margin={[60, 60]}>
        <GizmoViewport labelColor="white" axisHeadScale={1} />
      </GizmoHelper>
    </Canvas>
  );
}
