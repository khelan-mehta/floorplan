"""Export a Plan to IFC4 tuned for Revit native-category import.

Spatial tree (IfcProject→Site→Building→Storey) + IfcSpace per room (with net floor area) +
IfcWall with extruded-solid geometry + IfcDoor/IfcWindow elements contained in the storey. This
imports into Revit as Levels, Rooms, Walls, Doors and Windows. Boolean opening voids (IfcOpeningElement
cutting the walls) are a follow-up. Built low-level for ifcopenshell version stability. Units: metres.
"""

from __future__ import annotations

import math
import os
import tempfile
from typing import Any

import ifcopenshell
from ifcopenshell import guid

MM = 0.001


def _point2(m: ifcopenshell.file, x: float, y: float) -> Any:
    return m.create_entity("IfcCartesianPoint", Coordinates=[x, y])


def _wall_footprint(a: list[int], b: list[int], thickness_mm: int) -> list[tuple[float, float]]:
    ax, ay, bx, by = a[0] * MM, a[1] * MM, b[0] * MM, b[1] * MM
    length = math.hypot(bx - ax, by - ay) or 1e-6
    nx, ny = -(by - ay) / length, (bx - ax) / length
    h = thickness_mm * MM / 2
    return [
        (ax + nx * h, ay + ny * h),
        (bx + nx * h, by + ny * h),
        (bx - nx * h, by - ny * h),
        (ax - nx * h, ay - ny * h),
    ]


def _build_model(plan: dict[str, Any]) -> ifcopenshell.file:
    m = ifcopenshell.file(schema="IFC4")

    length = m.create_entity("IfcSIUnit", UnitType="LENGTHUNIT", Name="METRE")
    area = m.create_entity("IfcSIUnit", UnitType="AREAUNIT", Name="SQUARE_METRE")
    units = m.create_entity("IfcUnitAssignment", Units=[length, area])

    origin = m.create_entity("IfcCartesianPoint", Coordinates=[0.0, 0.0, 0.0])
    axis = m.create_entity("IfcAxis2Placement3D", Location=origin)
    context = m.create_entity(
        "IfcGeometricRepresentationContext",
        ContextType="Model",
        CoordinateSpaceDimension=3,
        Precision=1e-5,
        WorldCoordinateSystem=axis,
    )
    body = m.create_entity(
        "IfcGeometricRepresentationSubContext",
        ContextIdentifier="Body",
        ContextType="Model",
        ParentContext=context,
        TargetView="MODEL_VIEW",
    )

    project = m.create_entity(
        "IfcProject",
        GlobalId=guid.new(),
        Name="Floor Plan Studio",
        UnitsInContext=units,
        RepresentationContexts=[context],
    )
    site = m.create_entity("IfcSite", GlobalId=guid.new(), Name="Site", CompositionType="ELEMENT")
    building = m.create_entity(
        "IfcBuilding", GlobalId=guid.new(), Name="Building", CompositionType="ELEMENT"
    )
    m.create_entity(
        "IfcRelAggregates", GlobalId=guid.new(), RelatingObject=project, RelatedObjects=[site]
    )
    m.create_entity(
        "IfcRelAggregates", GlobalId=guid.new(), RelatingObject=site, RelatedObjects=[building]
    )

    def placement() -> Any:
        return m.create_entity("IfcLocalPlacement", RelativePlacement=axis)

    for level in plan.get("levels", []):
        storey = m.create_entity(
            "IfcBuildingStorey",
            GlobalId=guid.new(),
            Name=f"Level {level['index']}",
            CompositionType="ELEMENT",
        )
        m.create_entity(
            "IfcRelAggregates", GlobalId=guid.new(), RelatingObject=building, RelatedObjects=[storey]
        )

        spaces = []
        for room in level.get("rooms", []):
            space = m.create_entity(
                "IfcSpace",
                GlobalId=guid.new(),
                Name=room["id"],
                LongName=room["type"],
                CompositionType="ELEMENT",
            )
            spaces.append(space)
            q = m.create_entity(
                "IfcQuantityArea", Name="NetFloorArea", AreaValue=round(room["area_mm2"] / 1_000_000, 3)
            )
            eq = m.create_entity(
                "IfcElementQuantity",
                GlobalId=guid.new(),
                Name="Qto_SpaceBaseQuantities",
                Quantities=[q],
            )
            m.create_entity(
                "IfcRelDefinesByProperties",
                GlobalId=guid.new(),
                RelatedObjects=[space],
                RelatingPropertyDefinition=eq,
            )
        if spaces:
            m.create_entity(
                "IfcRelAggregates", GlobalId=guid.new(), RelatingObject=storey, RelatedObjects=spaces
            )

        elements = []
        for wall in level.get("walls", []):
            pts = [
                _point2(m, x, y)
                for x, y in _wall_footprint(wall["a"], wall["b"], wall["thickness_mm"])
            ]
            polyline = m.create_entity("IfcPolyline", Points=[*pts, pts[0]])
            profile = m.create_entity(
                "IfcArbitraryClosedProfileDef", ProfileType="AREA", OuterCurve=polyline
            )
            solid = m.create_entity(
                "IfcExtrudedAreaSolid",
                SweptArea=profile,
                Position=axis,
                ExtrudedDirection=m.create_entity("IfcDirection", DirectionRatios=[0.0, 0.0, 1.0]),
                Depth=wall["height_mm"] * MM,
            )
            shape = m.create_entity(
                "IfcShapeRepresentation",
                ContextOfItems=body,
                RepresentationIdentifier="Body",
                RepresentationType="SweptSolid",
                Items=[solid],
            )
            prod = m.create_entity("IfcProductDefinitionShape", Representations=[shape])
            elements.append(
                m.create_entity(
                    "IfcWall",
                    GlobalId=guid.new(),
                    Name=wall["id"],
                    ObjectPlacement=placement(),
                    Representation=prod,
                )
            )

        for op in level.get("openings", []):
            cls = {"door": "IfcDoor", "window": "IfcWindow"}.get(op["kind"])
            if cls is None:
                continue
            elements.append(
                m.create_entity(
                    cls,
                    GlobalId=guid.new(),
                    Name=op["id"],
                    ObjectPlacement=placement(),
                    OverallHeight=op["height_mm"] * MM,
                    OverallWidth=op["width_mm"] * MM,
                )
            )

        if elements:
            m.create_entity(
                "IfcRelContainedInSpatialStructure",
                GlobalId=guid.new(),
                RelatingStructure=storey,
                RelatedElements=elements,
            )
    return m


def build_ifc_bytes(plan: dict[str, Any]) -> bytes:
    model = _build_model(plan)
    fd, path = tempfile.mkstemp(suffix=".ifc")
    os.close(fd)
    try:
        model.write(path)
        with open(path, "rb") as fh:
            return fh.read()
    finally:
        os.unlink(path)


def ifc_stats(plan: dict[str, Any]) -> dict[str, int]:
    model = _build_model(plan)
    return {
        "projects": len(model.by_type("IfcProject")),
        "storeys": len(model.by_type("IfcBuildingStorey")),
        "spaces": len(model.by_type("IfcSpace")),
        "walls": len(model.by_type("IfcWall")),
        "doors": len(model.by_type("IfcDoor")),
        "windows": len(model.by_type("IfcWindow")),
    }
