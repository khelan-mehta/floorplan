import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import type { Boundary, ProgramGraph } from '@fpg/schemas';
import { api } from '../api/client';

export function useProjects() {
  return useQuery({ queryKey: ['projects'], queryFn: api.listProjects });
}

export function useProject(id: string | undefined) {
  return useQuery({
    queryKey: ['project', id],
    queryFn: () => api.getProject(id as string),
    enabled: !!id,
  });
}

export function usePlans(projectId: string | undefined) {
  return useQuery({
    queryKey: ['plans', projectId],
    queryFn: () => api.listPlans(projectId as string),
    enabled: !!projectId,
  });
}

export function usePlan(planId: string | undefined) {
  return useQuery({
    queryKey: ['plan', planId],
    queryFn: () => api.getPlan(planId as string),
    enabled: !!planId,
  });
}

export function useCreateProject() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.createProject,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects'] }),
  });
}

export function useBoundary(projectId: string | undefined) {
  return useQuery({
    queryKey: ['boundary', projectId],
    queryFn: () => api.getBoundary(projectId as string),
    enabled: !!projectId,
    retry: false,
  });
}

export function usePutBoundary(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (doc: Boundary) => api.putBoundary(projectId, doc),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['boundary', projectId] }),
  });
}

export function useProgram(projectId: string | undefined) {
  return useQuery({
    queryKey: ['program', projectId],
    queryFn: () => api.getProgram(projectId as string),
    enabled: !!projectId,
    retry: false,
  });
}

export function usePutProgram(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (doc: ProgramGraph) => api.putProgram(projectId, doc),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['program', projectId] }),
  });
}

export function useCodes() {
  return useQuery({ queryKey: ['codes'], queryFn: api.listCodes, retry: false });
}

export function useCodeQuery() {
  return useMutation({
    mutationFn: (b: { jurisdiction_id: string; query: string; top_k?: number }) =>
      api.queryCodes(b),
  });
}

export function useGenerate(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (b: { count?: number; seed?: number }) => api.generate(projectId, b),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plans', projectId] }),
  });
}

export function useCritique(planId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (feedback: string) => api.critiquePlan(planId as string, feedback),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['plans'] });
      qc.invalidateQueries({ queryKey: ['plan'] });
      qc.invalidateQueries({ queryKey: ['project'] });
    },
  });
}
