import { polygonArea, type Pt } from '@fpg/geometry-core';
import { useMemo } from 'react';
import { NavLink, Outlet, useParams } from 'react-router-dom';
import { BoundaryEditor } from '../boundary/BoundaryEditor';
import { CodesPage } from '../codes/CodesPage';
import { useBoundary, useProgram, useProject } from '../hooks/queries';
import { ProgramEditor } from '../program/ProgramEditor';

function navClass({ isActive }: { isActive: boolean }) {
  return `px-3 py-1 rounded text-sm ${isActive ? 'bg-accent text-white' : 'text-muted hover:bg-panel-2'}`;
}

export function ProjectLayout() {
  const { id } = useParams<{ id: string }>();
  const { data: project } = useProject(id);
  return (
    <div className="flex h-screen flex-col">
      <nav className="flex items-center gap-2 border-b border-line bg-panel px-3 py-1.5">
        <NavLink to="/" className="text-sm text-muted hover:text-fg">
          ← Projects
        </NavLink>
        <span className="mx-2 font-medium">{project?.name ?? 'Project'}</span>
        <div className="ml-auto flex gap-1">
          <NavLink to={`/projects/${id}/boundary`} className={navClass}>
            Boundary
          </NavLink>
          <NavLink to={`/projects/${id}/program`} className={navClass}>
            Program
          </NavLink>
          <NavLink to={`/projects/${id}/codes`} className={navClass}>
            Codes
          </NavLink>
          <NavLink to={`/projects/${id}`} end className={navClass}>
            Plans
          </NavLink>
        </div>
      </nav>
      <div className="min-h-0 flex-1">
        <Outlet />
      </div>
    </div>
  );
}

export function BoundaryRoute() {
  const { id } = useParams<{ id: string }>();
  const { data } = useBoundary(id);
  return <BoundaryEditor projectId={id ?? ''} initialDoc={data?.doc} />;
}

export function CodesRoute() {
  const { id } = useParams<{ id: string }>();
  return <CodesPage projectId={id ?? ''} />;
}

export function ProgramRoute() {
  const { id } = useParams<{ id: string }>();
  const { data: boundary } = useBoundary(id);
  const { data: program } = useProgram(id);

  const availableMm2 = useMemo(() => {
    const ring = boundary?.doc.levels[0]?.outline.rings[0]?.points;
    if (!ring) return 0;
    return polygonArea(ring.map((p) => [p[0], p[1]] as Pt));
  }, [boundary]);

  return (
    <ProgramEditor projectId={id ?? ''} availableMm2={availableMm2} initialDoc={program?.doc} />
  );
}
