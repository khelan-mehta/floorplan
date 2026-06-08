import {
  Badge,
  Button,
  Dialog,
  DialogClose,
  DialogContent,
  DialogTitle,
  DialogTrigger,
  Field,
  Input,
  Panel,
  toast,
} from '@fpg/ui';
import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useCreateProject, useProjects } from '../hooks/queries';
import { useAuth } from '../store/auth';

export function Dashboard() {
  const navigate = useNavigate();
  const logout = useAuth((s) => s.logout);
  const { data: projects, isLoading, isError } = useProjects();

  return (
    <div className="mx-auto max-w-5xl p-6">
      <header className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Projects</h1>
        <div className="flex gap-2">
          <Button variant="secondary" onClick={() => navigate('/demo')}>
            Open demo
          </Button>
          <CreateProjectDialog />
          <Button
            variant="ghost"
            onClick={() => {
              logout();
              navigate('/login');
            }}
          >
            Sign out
          </Button>
        </div>
      </header>

      {isLoading && <p className="text-muted">Loading…</p>}
      {isError && (
        <Panel className="p-4 text-sm">
          <p className="mb-2 text-warn">Couldn’t reach the API.</p>
          <p className="text-muted">
            Start the backend with <code>pnpm dev</code>, or{' '}
            <Link to="/demo" className="text-accent">
              open the offline demo plan
            </Link>
            .
          </p>
        </Panel>
      )}

      {projects && projects.length === 0 && (
        <p className="text-muted">No projects yet. Create one to get started.</p>
      )}

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {projects?.map((p) => (
          <Link key={p.id} to={`/projects/${p.id}`}>
            <Panel className="p-4 transition-colors hover:border-accent">
              <div className="mb-2 flex items-center justify-between">
                <h2 className="font-medium">{p.name}</h2>
                <Badge tone="accent">{p.units}</Badge>
              </div>
              <p className="text-xs text-muted">
                {p.current_plan_id ? 'Has plans' : 'No plans yet'}
              </p>
            </Panel>
          </Link>
        ))}
      </div>
    </div>
  );
}

function CreateProjectDialog() {
  const navigate = useNavigate();
  const create = useCreateProject();
  const [name, setName] = useState('');

  const submit = async () => {
    try {
      const project = await create.mutateAsync({ name });
      navigate(`/projects/${project.id}`);
    } catch {
      toast.error('Could not create project (is the API running?)');
    }
  };

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="primary">New project</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogTitle>New project</DialogTitle>
        <div className="mt-3 flex flex-col gap-3">
          <Field label="Name">
            <Input value={name} onChange={(e) => setName(e.target.value)} autoFocus />
          </Field>
          <div className="flex justify-end gap-2">
            <DialogClose asChild>
              <Button variant="ghost">Cancel</Button>
            </DialogClose>
            <Button variant="primary" disabled={!name || create.isPending} onClick={submit}>
              Create
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
