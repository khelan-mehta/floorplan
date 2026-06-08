// One-click import of an approved Floor Plan Studio plan as native Revit elements.
// Authored scaffold (not compiled here — needs Revit API + .NET). It fetches a Plan document from
// the API and builds Walls (Doors/Windows hosting + Rooms are added as the mapping matures).

using System;
using System.Collections.Generic;
using System.Linq;
using System.Net.Http;
using System.Text.Json;
using Autodesk.Revit.Attributes;
using Autodesk.Revit.DB;
using Autodesk.Revit.UI;

namespace FpgStudio.RevitAddin
{
    [Transaction(TransactionMode.Manual)]
    public class ImportPlanCommand : IExternalCommand
    {
        private const double MmToFeet = 1.0 / 304.8; // Revit internal units are feet

        public Result Execute(ExternalCommandData data, ref string message, ElementSet elements)
        {
            UIDocument uidoc = data.Application.ActiveUIDocument;
            Document doc = uidoc.Document;

            // In a real build: prompt for API base URL + token + plan id (or list approved plans).
            string apiBase = Environment.GetEnvironmentVariable("FPG_API") ?? "http://localhost:8000";
            string planId = PromptForPlanId();
            if (string.IsNullOrEmpty(planId)) return Result.Cancelled;

            JsonElement plan;
            try
            {
                using var http = new HttpClient();
                string json = http.GetStringAsync($"{apiBase}/plans/{planId}").Result;
                plan = JsonDocument.Parse(json).RootElement.GetProperty("doc");
            }
            catch (Exception ex)
            {
                message = $"Could not fetch plan: {ex.Message}";
                return Result.Failed;
            }

            Level level = new FilteredElementCollector(doc)
                .OfClass(typeof(Level)).Cast<Level>().FirstOrDefault();
            if (level == null) { message = "No level in document."; return Result.Failed; }

            using var tx = new Transaction(doc, "Import Floor Plan Studio plan");
            tx.Start();
            int created = 0;
            foreach (JsonElement lvl in plan.GetProperty("levels").EnumerateArray())
            {
                foreach (JsonElement wall in lvl.GetProperty("walls").EnumerateArray())
                {
                    XYZ a = PointFromMm(wall.GetProperty("a"));
                    XYZ b = PointFromMm(wall.GetProperty("b"));
                    double height = wall.GetProperty("height_mm").GetDouble() * MmToFeet;
                    Wall.Create(doc, Line.CreateBound(a, b), level.Id, false);
                    created++;
                }
            }
            tx.Commit();

            TaskDialog.Show("Floor Plan Studio", $"Imported {created} walls. (Doors/windows/rooms: follow-up.)");
            return Result.Succeeded;
        }

        private static XYZ PointFromMm(JsonElement pt)
        {
            var coords = pt.EnumerateArray().Select(e => e.GetDouble()).ToArray();
            return new XYZ(coords[0] * MmToFeet, coords[1] * MmToFeet, 0);
        }

        private static string PromptForPlanId()
        {
            // Placeholder: a real add-in shows a WPF dialog listing the user's approved plans.
            return Environment.GetEnvironmentVariable("FPG_PLAN_ID") ?? "";
        }
    }
}
