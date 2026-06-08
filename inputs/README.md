# Test inputs — 3-bedroom house

Sample inputs for exercising the Floor Plan Studio end to end. A single source of truth
(`program-graph.json`) plus convenience exports derived from it.

| File | What it is | How to use |
|------|------------|------------|
| `area-program.xlsx` | The **area-programming spreadsheet** (Department, Room Name, Type, Qty, Target/Min Area m²). | In the app: **Program → Import** → pick this file (columns auto-map). |
| `adjacency-matrix.csv` / `.xlsx` | The **room adjacency map** (rooms × rooms; each cell is the relation). | Reference for entering edges in **Program → Graph/Matrix**, or read into your own tooling. |
| `program-graph.json` | The **canonical `ProgramGraph`** (nodes + edges + `entry`) — area program *and* adjacency in one schema-valid document. | `PUT /projects/{id}/program`, or feed straight to `POST /generate`. Validates against `program-graph.schema.json`. |
| `boundary.json` | A matching **14 m × 10 m building outline** (140 m²) with a parcel + 2 m setbacks. | **Boundary → Import**, or `PUT /projects/{id}/boundary`. Big enough for the 130 m² programme. |

## The programme

12 rooms, 130 m²: entry, living, dining, kitchen, master bedroom (+ensuite), 2 bedrooms,
bathroom, hallway, laundry, garage. Adjacencies wire a normal house (public zone open-plan,
private zone off the hall, wet rooms grouped).

`entry` block: **2 exterior doors** (front door on the **south** facade at the `entry`, plus a
secondary door — the generator picks the garage), and the circulation is routed from the entry so
every room is reachable (egress).

## Quick generate via the API

```bash
# (stack up + logged in; replace TOKEN/PID)
curl -s -X PUT  localhost:8000/projects/$PID/boundary -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data @boundary.json
curl -s -X PUT  localhost:8000/projects/$PID/program  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' --data @program-graph.json
curl -s -X POST "localhost:8000/projects/$PID/generate" -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' -d '{"count":6}'
```

> Regenerate from `inputs/` (kept in sync) — `area-program.xlsx` and `adjacency-matrix.*` are
> derived from `program-graph.json`.
