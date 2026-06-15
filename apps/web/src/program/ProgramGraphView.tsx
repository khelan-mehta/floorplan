import {
  Background,
  Controls,
  type Connection,
  type Edge,
  type Node,
  ReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { useCallback, useMemo } from 'react';
import { roomColor } from '../viewport/plan-render';
import { useProgram } from './store';

type XY = { x: number; y: number };

/** Deterministic force-directed (Fruchterman–Reingold) layout so connected rooms cluster and
 * unrelated ones spread out — a readable architectural bubble diagram. */
function forceLayout(ids: string[], springs: [string, string][]): Record<string, XY> {
  const n = Math.max(1, ids.length);
  const pos: Record<string, XY> = {};
  ids.forEach((id, i) => {
    const a = (i / n) * Math.PI * 2;
    pos[id] = { x: Math.cos(a) * 240, y: Math.sin(a) * 240 };
  });
  const k = 200; // ideal edge length
  const iters = 400;
  for (let it = 0; it < iters; it++) {
    const disp: Record<string, XY> = {};
    ids.forEach((id) => (disp[id] = { x: 0, y: 0 }));
    for (let i = 0; i < ids.length; i++) {
      for (let j = i + 1; j < ids.length; j++) {
        const a = pos[ids[i]!]!;
        const b = pos[ids[j]!]!;
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const d = Math.hypot(dx, dy) || 0.01;
        const rep = (k * k) / d / d;
        disp[ids[i]!]!.x += (dx / d) * rep * k;
        disp[ids[i]!]!.y += (dy / d) * rep * k;
        disp[ids[j]!]!.x -= (dx / d) * rep * k;
        disp[ids[j]!]!.y -= (dy / d) * rep * k;
      }
    }
    for (const [s, t] of springs) {
      if (!pos[s] || !pos[t]) continue;
      const dx = pos[s]!.x - pos[t]!.x;
      const dy = pos[s]!.y - pos[t]!.y;
      const d = Math.hypot(dx, dy) || 0.01;
      const att = (d * d) / k;
      disp[s]!.x -= (dx / d) * att;
      disp[s]!.y -= (dy / d) * att;
      disp[t]!.x += (dx / d) * att;
      disp[t]!.y += (dy / d) * att;
    }
    const temp = Math.max(4, 60 * (1 - it / iters));
    for (const id of ids) {
      const dd = disp[id]!;
      const dl = Math.hypot(dd.x, dd.y) || 0.01;
      const m = Math.min(dl, temp);
      pos[id]!.x += (dd.x / dl) * m;
      pos[id]!.y += (dd.y / dl) * m;
    }
  }
  return pos;
}

/** Bubble-diagram-style graph: nodes = rooms, edges = adjacencies. Drag to connect. */
export function ProgramGraphView() {
  const nodes = useProgram((s) => s.nodes);
  const edges = useProgram((s) => s.edges);
  const addEdge = useProgram((s) => s.addEdge);

  const layout = useMemo(() => {
    const ids = nodes.map((n) => n.id);
    const springs = edges
      .filter((e) => e.relation !== 'not_adjacent')
      .map((e) => [e.a, e.b] as [string, string]);
    return forceLayout(ids, springs);
  }, [nodes, edges]);

  const rfNodes: Node[] = useMemo(
    () =>
      nodes.map((n) => {
        const p = layout[n.id] ?? { x: 0, y: 0 };
        return {
          id: n.id,
          position: { x: p.x, y: p.y },
          data: { label: n.label ?? n.type },
          style: {
            background: roomColor(n.type),
            color: '#0b0d12',
            border: 'none',
            borderRadius: 999,
            padding: 8,
            fontSize: 12,
            width: 110,
            textAlign: 'center' as const,
          },
        };
      }),
    [nodes, layout],
  );

  const rfEdges: Edge[] = useMemo(
    () =>
      edges.map((e) => ({
        id: `${e.a}-${e.b}`,
        source: e.a,
        target: e.b,
        label: e.relation.replace('connected_', ''),
        animated: e.relation === 'connected_open',
        style: { stroke: e.relation === 'not_adjacent' ? '#d1242f' : '#9aa0a6' },
      })),
    [edges],
  );

  const onConnect = useCallback(
    (c: Connection) => {
      if (c.source && c.target)
        addEdge({ a: c.source, b: c.target, relation: 'adjacent', weight: 70 });
    },
    [addEdge],
  );

  return (
    <div className="h-full w-full">
      <ReactFlow nodes={rfNodes} edges={rfEdges} onConnect={onConnect} fitView colorMode="dark">
        <Background />
        <Controls />
      </ReactFlow>
    </div>
  );
}
