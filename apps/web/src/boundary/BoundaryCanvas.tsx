import type Konva from 'konva';
import { useEffect, useMemo, useRef, useState } from 'react';
import { Circle, Group, Layer, Line, Rect, Stage, Text } from 'react-konva';
import { type Pt, polygonArea, snapAngle, snapToGrid } from '@fpg/geometry-core';
import { envelope } from './boundary-model';
import { useBoundary } from './store';

const flat = (pts: Pt[]) => pts.flatMap((p) => [p[0], p[1]]);
const mid = (a: Pt, b: Pt): Pt => [(a[0] + b[0]) / 2, (a[1] + b[1]) / 2];
const lenM = (a: Pt, b: Pt) => Math.hypot(b[0] - a[0], b[1] - a[1]) / 1000;

/** A length tag drawn at a point, kept at a constant on-screen size regardless of zoom. */
function DimLabel({
  p,
  text,
  scale,
  tone = '#e6e6e6',
}: {
  p: Pt;
  text: string;
  scale: number;
  tone?: string;
}) {
  const fs = 13 / scale;
  const padX = 4 / scale;
  const w = (text.length * fs) / 1.8 + padX * 2;
  const h = fs + padX;
  return (
    <Group x={p[0]} y={p[1]} listening={false}>
      <Rect x={-w / 2} y={-h / 2} width={w} height={h} fill="#0b0d12cc" cornerRadius={3 / scale} />
      <Text
        x={-w / 2}
        y={-h / 2 + padX / 2}
        width={w}
        text={text}
        fontSize={fs}
        fill={tone}
        align="center"
      />
    </Group>
  );
}

export function BoundaryCanvas() {
  const s = useBoundary();
  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 800, h: 600 });
  const [scale, setScale] = useState(0.04);
  const [pos, setPos] = useState({ x: 40, y: 40 });
  const [cursor, setCursor] = useState<Pt | null>(null);

  const level = s.levels.find((l) => l.index === s.selectedLevel);
  const env = useMemo(() => envelope(s.site), [s.site]);
  const drawing = s.tool !== 'select';

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([e]) => {
      if (e) setSize({ w: e.contentRect.width, h: e.contentRect.height });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  const worldFromPointer = (stage: Konva.Stage): Pt | null => {
    const p = stage.getPointerPosition();
    if (!p) return null;
    let world: Pt = [(p.x - pos.x) / scale, (p.y - pos.y) / scale];
    if (s.ortho && s.draft.length > 0)
      world = snapAngle(s.draft[s.draft.length - 1] as Pt, world, 45);
    if (s.snap) world = snapToGrid(world, s.gridMm);
    return [Math.round(world[0]), Math.round(world[1])];
  };

  const onClick = (e: Konva.KonvaEventObject<MouseEvent>) => {
    const stage = e.target.getStage();
    if (!stage) return;
    // Click on empty space in select mode clears the vertex selection.
    if (s.tool === 'select') {
      if (e.target === stage) s.selectVertex(null);
      return;
    }
    const w = worldFromPointer(stage);
    if (w) s.pushDraft(w);
  };

  const onMouseMove = (e: Konva.KonvaEventObject<MouseEvent>) => {
    const stage = e.target.getStage();
    if (!stage) return;
    setCursor(worldFromPointer(stage));
  };

  const onWheel = (e: Konva.KonvaEventObject<WheelEvent>) => {
    e.evt.preventDefault();
    const stage = e.target.getStage();
    const pointer = stage?.getPointerPosition();
    if (!pointer) return;
    const mouseWorld = { x: (pointer.x - pos.x) / scale, y: (pointer.y - pos.y) / scale };
    const next = e.evt.deltaY > 0 ? scale / 1.1 : scale * 1.1;
    setScale(next);
    setPos({ x: pointer.x - mouseWorld.x * next, y: pointer.y - mouseWorld.y * next });
  };

  const gridLines = useMemo(() => {
    const lines: number[][] = [];
    const step = s.gridMm * 10;
    for (let x = -10000; x <= 40000; x += step) lines.push([x, -10000, x, 40000]);
    for (let y = -10000; y <= 40000; y += step) lines.push([-10000, y, 40000, y]);
    return lines;
  }, [s.gridMm]);

  const outline = level?.outline ?? [];
  const closed = outline.length >= 3;

  // Edge dimension labels for the committed outline.
  const edgeLabels = useMemo(() => {
    if (outline.length < 2) return [];
    const labels: { p: Pt; text: string }[] = [];
    const n = closed ? outline.length : outline.length - 1;
    for (let i = 0; i < n; i++) {
      const a = outline[i] as Pt;
      const b = outline[(i + 1) % outline.length] as Pt;
      labels.push({ p: mid(a, b), text: `${lenM(a, b).toFixed(2)} m` });
    }
    return labels;
  }, [outline, closed]);

  const areaLabel = useMemo(() => {
    if (!closed) return null;
    const cx = outline.reduce((s2, p) => s2 + p[0], 0) / outline.length;
    const cy = outline.reduce((s2, p) => s2 + p[1], 0) / outline.length;
    const m2 = polygonArea(outline) / 1_000_000;
    return { p: [cx, cy] as Pt, text: `${m2.toFixed(1)} m²` };
  }, [outline, closed]);

  return (
    <div ref={containerRef} className="h-full w-full">
      <Stage
        width={size.w}
        height={size.h}
        scaleX={scale}
        scaleY={scale}
        x={pos.x}
        y={pos.y}
        draggable={!drawing}
        onClick={onClick}
        onMouseMove={onMouseMove}
        onMouseLeave={() => setCursor(null)}
        onDblClick={() => s.commitDraft()}
        onWheel={onWheel}
        onDragEnd={(e) => setPos({ x: e.target.x(), y: e.target.y() })}
      >
        <Layer listening={false}>
          {gridLines.map((l, i) => (
            <Line key={i} points={l} stroke="#222733" strokeWidth={1 / scale} />
          ))}
        </Layer>
        <Layer>
          {/* parcel + envelope */}
          {s.site && s.site.parcel.length >= 3 && (
            <Line
              points={flat(s.site.parcel)}
              closed
              stroke="#64748b"
              strokeWidth={2 / scale}
              dash={[10 / scale, 6 / scale]}
            />
          )}
          {env && (
            <Line
              points={flat(env)}
              closed
              stroke="#22c55e"
              strokeWidth={2 / scale}
              fill="#22c55e22"
            />
          )}

          {/* committed outline */}
          {outline.length >= 2 && (
            <Line
              points={flat(outline)}
              closed={closed}
              stroke="#3b82f6"
              strokeWidth={3 / scale}
              fill={closed ? '#3b82f633' : undefined}
            />
          )}

          {/* edge-insert handles (select mode) */}
          {!drawing &&
            closed &&
            outline.map((a, i) => {
              const b = outline[(i + 1) % outline.length] as Pt;
              const m = mid(a as Pt, b);
              return (
                <Circle
                  key={`ins-${i}`}
                  x={m[0]}
                  y={m[1]}
                  radius={5 / scale}
                  fill="#0b0d12"
                  stroke="#3b82f6"
                  strokeWidth={1.5 / scale}
                  onClick={(e) => {
                    e.cancelBubble = true;
                    s.insertVertex(s.selectedLevel, i, m);
                  }}
                />
              );
            })}

          {/* vertex handles (select mode): drag to move, click to select, right-click to delete */}
          {!drawing &&
            outline.map((v, idx) => {
              const selected = s.selectedVertex === idx;
              return (
                <Circle
                  key={`v-${idx}`}
                  x={v[0]}
                  y={v[1]}
                  radius={(selected ? 9 : 7) / scale}
                  fill={selected ? '#f59e0b' : '#3b82f6'}
                  stroke="#fff"
                  strokeWidth={1.5 / scale}
                  draggable
                  onClick={(e) => {
                    e.cancelBubble = true;
                    s.selectVertex(idx);
                  }}
                  onDragStart={() => {
                    s.selectVertex(idx);
                    s.beginHistory();
                  }}
                  onDragMove={(e) =>
                    s.moveVertex(s.selectedLevel, idx, [
                      Math.round(e.target.x()),
                      Math.round(e.target.y()),
                    ])
                  }
                  onContextMenu={(e) => {
                    e.evt.preventDefault();
                    e.cancelBubble = true;
                    s.deleteVertex(s.selectedLevel, idx);
                  }}
                />
              );
            })}

          {/* draft polyline (drawing) */}
          {s.draft.length > 0 && (
            <>
              <Line points={flat(s.draft)} stroke="#f59e0b" strokeWidth={2 / scale} />
              {s.draft.map((v, i) => (
                <Rect
                  key={`d-${i}`}
                  x={v[0] - 4 / scale}
                  y={v[1] - 4 / scale}
                  width={8 / scale}
                  height={8 / scale}
                  fill="#f59e0b"
                />
              ))}
              {/* live rubber-band segment + length to the cursor */}
              {drawing && cursor && (
                <>
                  <Line
                    points={[...(s.draft[s.draft.length - 1] as Pt), ...cursor]}
                    stroke="#f59e0b"
                    strokeWidth={1.5 / scale}
                    dash={[8 / scale, 6 / scale]}
                  />
                  <DimLabel
                    p={mid(s.draft[s.draft.length - 1] as Pt, cursor)}
                    text={`${lenM(s.draft[s.draft.length - 1] as Pt, cursor).toFixed(2)} m`}
                    scale={scale}
                    tone="#f59e0b"
                  />
                </>
              )}
            </>
          )}

          {/* draft edge labels */}
          {s.draft.length >= 2 &&
            s.draft
              .slice(0, -1)
              .map((a, i) => (
                <DimLabel
                  key={`dl-${i}`}
                  p={mid(a as Pt, s.draft[i + 1] as Pt)}
                  text={`${lenM(a as Pt, s.draft[i + 1] as Pt).toFixed(2)} m`}
                  scale={scale}
                  tone="#f59e0b"
                />
              ))}

          {/* committed dimensions + area */}
          {edgeLabels.map((l, i) => (
            <DimLabel key={`el-${i}`} p={l.p} text={l.text} scale={scale} />
          ))}
          {areaLabel && (
            <DimLabel p={areaLabel.p} text={areaLabel.text} scale={scale} tone="#3b82f6" />
          )}

          {/* snap/cursor dot while drawing */}
          {drawing && cursor && (
            <Circle
              x={cursor[0]}
              y={cursor[1]}
              radius={4 / scale}
              fill="#f59e0b"
              listening={false}
            />
          )}
        </Layer>
      </Stage>
    </div>
  );
}
