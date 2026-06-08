import type Konva from 'konva';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Circle, Group, Layer, Line, Rect, Stage, Text } from 'react-konva';
import type { Plan } from '@fpg/schemas';
import { CATALOG_BY_ID } from '../library/catalog';
import { useEditor } from '../store/editor';
import { getLevel, levelBBox, ringToFlatPoints, roomColor, type Point } from './plan-render';

interface Props {
  plan: Plan;
  editable?: boolean;
  onMoveVertex?: (roomId: string, ptIndex: number, world: Point) => void;
  onMoveOpening?: (openingId: string, offsetMm: number) => void;
}

/** 2D plan renderer with pan/zoom. Y is flipped so north is up. Editable = draggable room vertices. */
export function PlanCanvas2D({ plan, editable = false, onMoveVertex, onMoveOpening }: Props) {
  const selectedLevel = useEditor((s) => s.selectedLevel);
  const select = useEditor((s) => s.select);
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 800, h: 600 });
  const [scale, setScale] = useState(0.05);
  const [pos, setPos] = useState({ x: 0, y: 0 });

  const level = getLevel(plan, selectedLevel);
  const bbox = useMemo(() => (level ? levelBBox(level) : null), [level]);

  // View transform: flip Y within the bbox so +Y (north) points up on screen.
  const toView = (p: Point): [number, number] => [p[0], bbox ? bbox.maxY - p[1] : -p[1]];

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      const cr = entry?.contentRect;
      if (cr) setSize({ w: cr.width, h: cr.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Fit-to-view whenever the level or container size changes.
  useEffect(() => {
    if (!bbox || bbox.width === 0 || bbox.height === 0) return;
    const pad = 0.9;
    const s = Math.min(size.w / bbox.width, size.h / bbox.height) * pad;
    setScale(s);
    setPos({
      x: size.w / 2 - (bbox.width / 2) * s,
      y: size.h / 2 - (bbox.height / 2) * s,
    });
    // Fit only on level/size change (not on every geometry edit), so editing doesn't reset the view.
  }, [level?.index, size.w, size.h]);

  if (!level || !bbox) return null;

  const onWheel = (e: Konva.KonvaEventObject<WheelEvent>) => {
    e.evt.preventDefault();
    const stage = e.target.getStage();
    if (!stage) return;
    const old = scale;
    const pointer = stage.getPointerPosition();
    if (!pointer) return;
    const mouseWorld = { x: (pointer.x - pos.x) / old, y: (pointer.y - pos.y) / old };
    const next = e.evt.deltaY > 0 ? old / 1.1 : old * 1.1;
    setScale(next);
    setPos({ x: pointer.x - mouseWorld.x * next, y: pointer.y - mouseWorld.y * next });
  };

  return (
    <div ref={containerRef} className="h-full w-full">
      <Stage
        width={size.w}
        height={size.h}
        scaleX={scale}
        scaleY={scale}
        x={pos.x}
        y={pos.y}
        draggable
        onWheel={onWheel}
        onDragEnd={(e) => setPos({ x: e.target.x(), y: e.target.y() })}
      >
        <Layer>
          {/* rooms */}
          {level.rooms.map((room) => {
            const outer = room.polygon.rings[0]?.points ?? [];
            const flat = ringToFlatPoints(outer.map(toView));
            return (
              <Group key={room.id} onClick={() => select('room', room.id)}>
                <Line points={flat} closed fill={roomColor(room.type)} opacity={0.5} />
                <Line points={flat} closed stroke={roomColor(room.type)} strokeWidth={20} />
              </Group>
            );
          })}
          {/* walls */}
          {level.walls.map((w) => {
            const [ax, ay] = toView(w.a as Point);
            const [bx, by] = toView(w.b as Point);
            return (
              <Line
                key={w.id}
                points={[ax, ay, bx, by]}
                stroke="#e6e6e6"
                strokeWidth={w.thickness_mm}
                lineCap="round"
                onClick={() => select('wall', w.id)}
              />
            );
          })}
          {/* openings */}
          {level.openings.map((o) => {
            const wall = level.walls.find((w) => w.id === o.wall_id);
            if (!wall) return null;
            const [ax, ay] = wall.a as Point;
            const [bx, by] = wall.b as Point;
            const len = Math.hypot(bx - ax, by - ay) || 1;
            const ux = (bx - ax) / len;
            const uy = (by - ay) / len;
            // centre of the opening = offset + half width along the wall
            const c = Math.min(o.offset_mm + o.width_mm / 2, len);
            const wp: Point = [ax + ux * c, ay + uy * c];
            const [vx, vy] = toView(wp);
            return (
              <Circle
                key={o.id}
                x={vx}
                y={vy}
                radius={o.width_mm / 2}
                fill={o.kind === 'door' ? '#f59e0b' : '#22d3ee'}
                stroke="#0b0d12"
                strokeWidth={30}
                draggable={editable && !!onMoveOpening}
                onClick={() => select('opening', o.id)}
                onDragMove={(e) => {
                  const wx = e.target.x();
                  const wy = bbox.maxY - e.target.y();
                  const proj = (wx - ax) * ux + (wy - ay) * uy; // centre along wall
                  onMoveOpening?.(o.id, Math.round(proj - o.width_mm / 2));
                }}
              />
            );
          })}
          {/* fixtures (furniture / fittings) */}
          {level.fixtures.map((fx) => {
            const def = CATALOG_BY_ID[fx.component_id];
            if (!def) return null;
            const [w, d] = def.size_mm;
            const [vx, vy] = toView([fx.transform.pos[0], fx.transform.pos[1]]);
            return (
              <Rect
                key={fx.id}
                x={vx - w / 2}
                y={vy - d / 2}
                width={w}
                height={d}
                fill="#475569"
                stroke="#94a3b8"
                strokeWidth={20}
                onClick={() => select('fixture', fx.id)}
              />
            );
          })}
          {/* room tags (counter-flip so text is upright) */}
          {level.rooms.map((room) => {
            const [cx, cy] = toView(room.centroid as Point);
            return (
              <Text
                key={`t-${room.id}`}
                x={cx}
                y={cy}
                text={room.type}
                fontSize={400}
                fill="#0b0d12"
                listening={false}
              />
            );
          })}
          {/* editable room vertices */}
          {editable &&
            level.rooms.flatMap((room) =>
              (room.polygon.rings[0]?.points ?? []).map((pt, i) => {
                const [vx, vy] = toView(pt as Point);
                return (
                  <Circle
                    key={`v-${room.id}-${i}`}
                    x={vx}
                    y={vy}
                    radius={120}
                    fill="#3b82f6"
                    stroke="#fff"
                    strokeWidth={20}
                    draggable
                    onDragEnd={(e) => {
                      const worldX = Math.round(e.target.x());
                      const worldY = Math.round(bbox.maxY - e.target.y());
                      onMoveVertex?.(room.id, i, [worldX, worldY]);
                    }}
                  />
                );
              }),
            )}
        </Layer>
      </Stage>
    </div>
  );
}
