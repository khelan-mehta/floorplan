// Deterministic, computed-from-data "AI summary" of a plan — no LLM call, works offline.

import type { Plan, PlanLevel } from '@fpg/schemas';
import type { ValidationReport } from '../api/types';
import { circulationEdges, corridorRoomIds, findEntryRoom } from '../viewport/circulation';
import { formatRoomType } from '../viewport/plan-render';
import { roomSunExposure } from '../viewport/sunlight';

function describeCirculation(level: PlanLevel): string {
  const entry = findEntryRoom(level);
  const corridorIds = corridorRoomIds(level);
  const edges = circulationEdges(level);
  if (!entry) return '';

  const reachable = new Set<string>([entry.id]);
  let changed = true;
  while (changed) {
    changed = false;
    for (const edge of edges) {
      const aRoom = level.rooms.find(
        (r) => r.centroid[0] === edge.a[0] && r.centroid[1] === edge.a[1],
      );
      const bRoom = level.rooms.find(
        (r) => r.centroid[0] === edge.b[0] && r.centroid[1] === edge.b[1],
      );
      if (!aRoom || !bRoom) continue;
      if (reachable.has(aRoom.id) && !reachable.has(bRoom.id)) {
        reachable.add(bRoom.id);
        changed = true;
      } else if (reachable.has(bRoom.id) && !reachable.has(aRoom.id)) {
        reachable.add(aRoom.id);
        changed = true;
      }
    }
  }

  let sentence = `You enter through the ${formatRoomType(entry.type)}, which connects to ${
    reachable.size - 1
  } other room${reachable.size - 1 === 1 ? '' : 's'} via doors.`;
  if (corridorIds.size > 0) {
    sentence += ` ${corridorIds.size} corridor room${corridorIds.size === 1 ? '' : 's'} link the spaces together.`;
  }
  return sentence;
}

function describeSunlight(level: PlanLevel): string {
  const scored = level.rooms
    .map((room) => ({ room, exposure: roomSunExposure(level, room) }))
    .filter((r) => r.exposure.dominant !== null);
  if (scored.length === 0) return '';

  const best = scored.reduce((a, b) => (b.exposure.score > a.exposure.score ? b : a));
  const worst = scored.reduce((a, b) => (b.exposure.score < a.exposure.score ? b : a));

  if (best.room.id === worst.room.id) {
    return `The ${formatRoomType(best.room.type)} gets the most consistent daylight, facing ${best.exposure.dominant}.`;
  }
  return `The ${formatRoomType(best.room.type)} gets the most daylight (facing ${best.exposure.dominant}), while the ${formatRoomType(
    worst.room.type,
  )} gets the least (facing ${worst.exposure.dominant}).`;
}

/** Build a 3-5 sentence plain-language summary from the plan and (if available) its
 * validation report — entirely deterministic, computed from data already on the plan. */
export function buildPlanSummary(plan: Plan, validation?: ValidationReport | null): string {
  const sentences: string[] = [];

  const level = plan.levels[0];
  const roomCount = plan.levels.reduce((sum, l) => sum + l.rooms.length, 0);
  const totalAreaM2 =
    plan.levels.reduce((sum, l) => sum + l.rooms.reduce((s, r) => s + r.area_mm2, 0), 0) / 1e6;
  sentences.push(
    `This plan has ${plan.levels.length} level${plan.levels.length === 1 ? '' : 's'} with ${roomCount} room${
      roomCount === 1 ? '' : 's'
    } totalling ${totalAreaM2.toFixed(1)} m².`,
  );

  if (typeof plan.score === 'number') {
    let scoreSentence = `The layout score is ${(plan.score * 100).toFixed(0)}%`;
    if (plan.score_breakdown) {
      const { adjacency, area_fit } = plan.score_breakdown;
      const parts: string[] = [];
      if (typeof adjacency === 'number') parts.push(`adjacency ${(adjacency * 100).toFixed(0)}%`);
      if (typeof area_fit === 'number') parts.push(`area fit ${(area_fit * 100).toFixed(0)}%`);
      if (parts.length > 0) scoreSentence += ` (${parts.join(', ')})`;
    }
    sentences.push(scoreSentence + '.');
  }

  if (validation) {
    const categories = Object.entries(validation.category_scores ?? {});
    if (categories.length > 0) {
      const lowest = categories.reduce((a, b) => (b[1] < a[1] ? b : a));
      sentences.push(
        `Code-compliance is ${(validation.score * 100).toFixed(0)}% overall; the weakest category is ${lowest[0]} at ${(
          lowest[1] * 100
        ).toFixed(0)}%.`,
      );
    }
    const errors = validation.results.filter((r) => r.status === 'fail' && r.severity === 'error');
    if (errors.length > 0) {
      sentences.push(
        `There ${errors.length === 1 ? 'is' : 'are'} ${errors.length} unresolved compliance error${
          errors.length === 1 ? '' : 's'
        } to address.`,
      );
    }
  }

  if (level) {
    const circulation = describeCirculation(level);
    if (circulation) sentences.push(circulation);
    const sunlight = describeSunlight(level);
    if (sunlight) sentences.push(sunlight);
  }

  return sentences.join(' ');
}
