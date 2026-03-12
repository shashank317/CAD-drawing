"""
FreeCAD Stepped Revolution Component with GLB/GLTF Export + TechDraw PDF/SVG

Generates the 3D component with dynamic dimensions, exports to GLB/GLTF,
then creates a TechDraw page (Front + Side + Isometric) with auto-dimensions
and exports to both PDF and SVG.

Usage:
    python "also drawing.py" --roller-diameter 160.5 --bearing-width 20 --shaft-diameter 26 --overall-height 50 --base-width 100.5
"""

import subprocess
import os
import sys
import tempfile

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))


def find_freecad():
    possible_paths = [
        r"C:\Program Files\FreeCAD 1.0\bin\FreeCAD.exe",
        r"C:\Program Files\FreeCAD 0.21\bin\FreeCAD.exe",
        r"C:\Program Files\FreeCAD 0.20\bin\FreeCAD.exe",
        r"C:\Program Files\FreeCAD\bin\FreeCAD.exe",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def find_freecadcmd():
    possible_paths = [
        r"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe",
        r"C:\Program Files\FreeCAD 0.21\bin\FreeCADCmd.exe",
        r"C:\Program Files\FreeCAD 0.20\bin\FreeCADCmd.exe",
        r"C:\Program Files\FreeCAD\bin\FreeCADCmd.exe",
    ]
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


# ============================================================================
# DYNAMIC SCRIPT TEMPLATE
# ============================================================================
SCRIPT_TEMPLATE = r'''
import os
import sys
import FreeCAD as App
import Part
import Sketcher
import Mesh
import MeshPart

OUTPUT_PATH = r"{output_path}"
OUTPUT_FORMAT = "{output_format}"


def create_stepped_revolution():
    try:
        doc = App.ActiveDocument
        if doc is None:
            doc = App.newDocument("SteppedRevolution")
    except Exception:
        doc = App.newDocument("SteppedRevolution")

    App.setActiveDocument(doc.Name)
    print("Creating Stepped Revolution component...")

    body = doc.addObject("PartDesign::Body", "Body")
    body.Label = "Body"
    doc.recompute()

    sketch = body.newObject("Sketcher::SketchObject", "Profile")
    sketch.AttachmentSupport = (doc.getObject("XY_Plane"), [""])
    sketch.MapMode = "FlatFace"
    doc.recompute()

    V = App.Vector
    segments = [
        (V(0,    0,   0), V(0,    {y1}, 0)),
        (V(0,    {y1},0), V({x1}, {y1}, 0)),
        (V({x1}, {y1},0), V({x1}, {y2}, 0)),
        (V({x1}, {y2},0), V({x2}, {y2}, 0)),
        (V({x2}, {y2},0), V({x2}, {y3}, 0)),
        (V({x2}, {y3},0), V({x3}, {y3}, 0)),
        (V({x3}, {y3},0), V({x3}, {y4}, 0)),
        (V({x3}, {y4},0), V({x4}, {y4}, 0)),
        (V({x4}, {y4},0), V({x4}, {y5}, 0)),
        (V({x4}, {y5},0), V(0,    {y5}, 0)),
        (V(0,    {y5},0), V(0,    0,    0)),
    ]

    for p1, p2 in segments:
        sketch.addGeometry(Part.LineSegment(p1, p2), False)
    doc.recompute()

    n = len(segments)
    for i in range(n):
        sketch.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i + 1) % n, 1))
    sketch.addConstraint(Sketcher.Constraint("Coincident", 0, 1, -1, 1))
    doc.recompute()

    for i in [0, 2, 4, 6, 8, 10]:
        sketch.addConstraint(Sketcher.Constraint("Vertical", i))
    for i in [1, 3, 5, 7, 9]:
        sketch.addConstraint(Sketcher.Constraint("Horizontal", i))
    doc.recompute()

    sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, 1, 1, {y1}))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, 3, 1, {y2}))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, 5, 1, {y3}))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, 7, 1, {y4}))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, 9, 1, {y5}))
    sketch.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, 1, 2, {x1}))
    sketch.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, 3, 2, {x2}))
    sketch.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, 5, 2, {x3}))
    sketch.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, 7, 2, {x4}))
    doc.recompute()

    sketch.Visibility = False
    doc.recompute()

    rev = body.newObject("PartDesign::Revolution", "Revolution")
    rev.Profile = (sketch, [""])
    rev.ReferenceAxis = (sketch, ["H_Axis"])
    rev.Angle = 360.0
    doc.recompute()

    print("SteppedRevolution created successfully.")
    return doc


def export_model(doc):
    print("Exporting 3D model...")

    fcstd_path = OUTPUT_PATH.replace(".glb", ".FCStd").replace(".gltf", ".FCStd")
    doc.saveAs(fcstd_path)
    print("FCStd saved: " + fcstd_path)

    body = doc.getObject("Body")
    if not body:
        print("Error: Body not found.")
        return False

    try:
        import FreeCADGui as Gui
        import ImportGui
        print("GUI mode: exporting via ImportGui...")
        objs = [body]
        if hasattr(ImportGui, "exportOptions"):
            opts = ImportGui.exportOptions(OUTPUT_PATH)
            ImportGui.export(objs, OUTPUT_PATH, opts)
        else:
            ImportGui.export(objs, OUTPUT_PATH)
        print("GLB saved: " + OUTPUT_PATH)
    except ImportError:
        print("Headless mode: falling back to STL/OBJ...")
        mesh = MeshPart.meshFromShape(
            Shape=body.Shape, LinearDeflection=0.1, AngularDeflection=0.5, Relative=False
        )
        stl_path = OUTPUT_PATH.replace(".glb", ".stl").replace(".gltf", ".stl")
        mesh.write(stl_path)
        print("STL saved: " + stl_path)
        obj_path = OUTPUT_PATH.replace(".glb", ".obj").replace(".gltf", ".obj")
        mesh.write(obj_path)
        print("OBJ saved: " + obj_path)
    except Exception as e:
        print("Export error: " + str(e))

    return True


# ============================================================================
# TECHDRAW
# ============================================================================

def _safe_import_techdraw():
    try:
        import TechDraw as _TD
    except ImportError:
        return None, None

    try:
        import TechDrawGui as _TDG
    except ImportError:
        _TDG = None

    return _TD, _TDG


def _find_template():
    candidates = [
        "C:/Program Files/FreeCAD 1.0/data/Mod/TechDraw/Templates/A3_Landscape_blank.svg",
        "C:/Program Files/FreeCAD 0.21/data/Mod/TechDraw/Templates/A3_Landscape_blank.svg",
        "C:/Program Files/FreeCAD 0.20/data/Mod/TechDraw/Templates/A3_Landscape_blank.svg",
        "C:/Program Files/FreeCAD/data/Mod/TechDraw/Templates/A3_Landscape_blank.svg",
    ]
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def create_techdraw(doc):
    print("Creating TechDraw page...")

    TechDraw, TechDrawGui = _safe_import_techdraw()
    if TechDraw is None:
        print("TechDraw not available - skipping drawing.")
        return

    body = doc.getObject("Body")
    if not body:
        print("Body not found - skipping drawing.")
        return

    # -- Page with A3 template --
    page = doc.addObject("TechDraw::DrawPage", "Page")
    page.Label = "Page"

    tmpl_path = _find_template()
    if tmpl_path:
        tmpl = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
        tmpl.Template = tmpl_path
        page.Template = tmpl
        print("Template: " + tmpl_path)
    else:
        print("No A3 template found - blank page.")

    doc.recompute()

    # Toggle page visibility to update its dimensions (official workaround)
    page.Visibility = False
    page.Visibility = True

    # -- Projection Group (official API pattern from FreeCAD docs) --
    proj_group = doc.addObject("TechDraw::DrawProjGroup", "ProjGroup")
    page.addView(proj_group)
    proj_group.Source = [body]
    proj_group.ProjectionType = "Third Angle"
    proj_group.Scale = 0.5

    # Front MUST be added first — it becomes the Anchor
    front_view = proj_group.addProjection("Front")
    proj_group.Anchor.Direction = (0, -1, 0)
    proj_group.Anchor.XDirection = (1, 0, 0)
    print("Front anchor added to projection group.")

    proj_group.addProjection("Left")
    proj_group.addProjection("Right")
    proj_group.addProjection("FrontBottomLeft")

    proj_group.X = page.PageWidth / 2
    proj_group.Y = page.PageHeight / 2

    doc.recompute()
    print("Projection group added (Front, Left, Right, FrontBottomLeft).")

    # Get references to the projection items
    proj_front = None    # the anchor/front in the proj group
    proj_left = None
    proj_right = None
    for obj in doc.Objects:
        if obj.TypeId == "TechDraw::DrawProjGroupItem":
            if hasattr(obj, "Type"):
                if obj.Type == "Front":
                    proj_front = obj
                elif obj.Type == "Left":
                    proj_left = obj
                elif obj.Type == "Right":
                    proj_right = obj

    # -- Auto-dimension following the exact FreeCAD GUI workflow --
    print("Auto-dimensioning edges...")

    dim_count = 0

    def add_dim_single(view, ref, dim_type, x_pos, y_pos):
        """Add a dimension on a single edge (e.g. Diameter on a circle)."""
        nonlocal dim_count
        dim_name = "Dimension" + str(dim_count).zfill(3)
        try:
            dim = doc.addObject("TechDraw::DrawViewDimension", dim_name)
            dim.Type = dim_type
            dim.MeasureType = "Projected"
            dim.References2D = [(view, ref)]
            page.addView(dim)
            dim.X = float(x_pos)
            dim.Y = float(y_pos)
            doc.recompute()
            dim_count += 1
            print("  " + dim_name + " -> " + dim_type + " on " + view.Name + " " + ref)
            return dim
        except Exception as e:
            print("  Dim failed " + dim_name + ": " + str(e))
            return None

    def add_dim_2refs(view, ref1, ref2, dim_type, x_pos, y_pos):
        """Add a dimension between two vertex references on the same view."""
        nonlocal dim_count
        dim_name = "Dimension" + str(dim_count).zfill(3)
        try:
            dim = doc.addObject("TechDraw::DrawViewDimension", dim_name)
            dim.Type = dim_type
            dim.MeasureType = "Projected"
            dim.References2D = [(view, ref1), (view, ref2)]
            page.addView(dim)
            dim.X = float(x_pos)
            dim.Y = float(y_pos)
            doc.recompute()
            dim_count += 1
            print("  " + dim_name + " -> " + dim_type + " on " + view.Name + " " + ref1 + "+" + ref2)
            return dim
        except Exception as e:
            print("  Dim failed " + dim_name + ": " + str(e))
            return None

    # ── Front view (ProjItem / anchor): vertex-to-vertex DistanceX for step widths ──
    if proj_front:
        print("  Dimensioning front view (step widths)...")
        # Stepped revolution front view vertices define the silhouette steps.
        # Pairs of vertices across each step, measured as DistanceX.
        front_dims = [
            ("Vertex8",  "Vertex15", "DistanceX", -33.6, 80.2),
            ("Vertex6",  "Vertex4",  "DistanceX", -17.1, 84.8),
            ("Vertex13", "Vertex2",  "DistanceX",   5.4, 73.2),
            ("Vertex11", "Vertex0",  "DistanceX",  25.1, 77.8),
            ("Vertex8",  "Vertex0",  "DistanceX",   4.4, 58.8),   # overall width
        ]
        for v1, v2, dtype, xp, yp in front_dims:
            add_dim_2refs(proj_front, v1, v2, dtype, xp, yp)

    # ── Left view (ProjItem001): Diameter dimensions on circular edges ──
    if proj_left:
        print("  Dimensioning left view (diameters)...")
        left_dims = [
            ("Edge2", "Diameter", 47.8, 29.5),
            ("Edge0", "Diameter", -29.6, 26.3),
            ("Edge1", "Diameter", 8.5, -39.3),
        ]
        for eref, dtype, xp, yp in left_dims:
            add_dim_single(proj_left, eref, dtype, xp, yp)

    # ── Right view (ProjItem002): Diameter dimensions on circular edges ──
    if proj_right:
        print("  Dimensioning right view (diameters)...")
        right_dims = [
            ("Edge0", "Diameter", 76.9, 8.8),
            ("Edge1", "Diameter", 99.5, 44.8),
            ("Edge2", "Diameter", 101.5, -34.0),
            ("Edge3", "Diameter", 106.5, 25.1),
        ]
        for eref, dtype, xp, yp in right_dims:
            add_dim_single(proj_right, eref, dtype, xp, yp)

    doc.recompute()
    print("Auto-dimensioning complete.")

    # -- Force TechDraw to fully render all views before export --
    # TechDraw renders asynchronously in GUI mode. We must:
    # 1. Ensure KeepUpdated is True on the page
    # 2. Force recompute of every view
    # 3. Pump the Qt event loop so the renderer finishes

    page.KeepUpdated = True

    # Force each view to recompute individually
    for view_obj in doc.Objects:
        if hasattr(view_obj, "TypeId") and "TechDraw::" in view_obj.TypeId:
            try:
                view_obj.recompute(True)
            except Exception:
                pass
    doc.recompute()

    try:
        import FreeCADGui as Gui
        # Open/activate the TechDraw page so the GUI renders it
        try:
            Gui.ActiveDocument.setEdit(page)
        except Exception:
            pass

        from PySide2 import QtWidgets, QtCore
        app = QtWidgets.QApplication.instance()
        if app:
            print("Waiting for TechDraw views to render...")
            for _ in range(40):
                app.processEvents()
                QtCore.QThread.msleep(250)
            app.processEvents()
            print("Render wait complete (10s).")

        # Close editor
        try:
            Gui.ActiveDocument.resetEdit()
        except Exception:
            pass
    except Exception as ewait:
        print("Qt event processing: " + str(ewait))
        import time
        time.sleep(10)

    doc.recompute()

    # -- Export PDF + SVG --
    base_out = OUTPUT_PATH.replace(".glb", "").replace(".gltf", "")
    pdf_path = base_out + "_drawing.pdf"
    svg_path = base_out + "_drawing.svg"

    # Save FCStd with the drawing included
    doc.save()
    print("FCStd (with drawing) saved.")

    # --- SVG export ---
    svg_ok = False
    try:
        TechDraw.writeSVGPage(page, svg_path)
        if os.path.exists(svg_path) and os.path.getsize(svg_path) > 500:
            print("SVG saved: " + svg_path)
            svg_ok = True
        else:
            print("writeSVGPage SVG file too small/missing.")
    except Exception as e1:
        print("TechDraw.writeSVGPage failed: " + str(e1))

    if not svg_ok and TechDrawGui is not None:
        try:
            TechDrawGui.exportPageAsSvg(page, svg_path)
            if os.path.exists(svg_path) and os.path.getsize(svg_path) > 500:
                print("SVG saved via TechDrawGui: " + svg_path)
                svg_ok = True
        except Exception as e2:
            print("TechDrawGui.exportPageAsSvg failed: " + str(e2))

    # --- PDF export using FreeCADGui.export (exact FreeCAD GUI method) ---
    pdf_ok = False
    try:
        import FreeCADGui
        objs = [page]
        if hasattr(FreeCADGui, "exportOptions"):
            options = FreeCADGui.exportOptions(pdf_path)
            FreeCADGui.export(objs, pdf_path, options)
        else:
            FreeCADGui.export(objs, pdf_path)
        if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 500:
            print("PDF saved via FreeCADGui.export: " + pdf_path)
            pdf_ok = True
        else:
            print("FreeCADGui.export PDF too small/missing.")
    except Exception as e:
        print("FreeCADGui.export PDF failed: " + str(e))

    # Fallback: TechDrawGui.exportPageAsPdf
    if not pdf_ok and TechDrawGui is not None:
        try:
            TechDrawGui.exportPageAsPdf(page, pdf_path)
            if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 500:
                print("PDF saved via TechDrawGui: " + pdf_path)
                pdf_ok = True
        except Exception as e:
            print("TechDrawGui.exportPageAsPdf failed: " + str(e))

    # Fallback: SVG -> PDF conversion
    if not pdf_ok and svg_ok:
        try:
            import cairosvg
            cairosvg.svg2pdf(url=svg_path, write_to=pdf_path)
            print("PDF saved via cairosvg: " + pdf_path)
            pdf_ok = True
        except ImportError:
            pass
        except Exception as e:
            print("cairosvg fallback failed: " + str(e))

    if not pdf_ok and svg_ok:
        try:
            from reportlab.graphics import renderPDF
            from svglib.svglib import svg2rlg
            drawing = svg2rlg(svg_path)
            if drawing:
                renderPDF.drawToFile(drawing, pdf_path)
                print("PDF saved via svglib+reportlab: " + pdf_path)
                pdf_ok = True
        except ImportError:
            pass
        except Exception as e:
            print("svglib fallback failed: " + str(e))

    if not pdf_ok:
        print("WARNING: PDF export failed. SVG available for viewing.")

    print("TechDraw export complete.")
    print("PDF: " + (pdf_path if pdf_ok else "NOT GENERATED"))
    print("SVG: " + (svg_path if svg_ok else "NOT GENERATED"))


# ============================================================================
# ENTRY POINT (runs inside FreeCAD)
# ============================================================================
doc = create_stepped_revolution()
export_model(doc)
create_techdraw(doc)
import sys; sys.exit(0)
'''


def generate_script(output_path, output_format, d_shaft, w_bearing, w_base, h_overall, d_roller):
    if output_path is None:
        output_path = os.path.join(WORKSPACE_DIR, "custom_stepped_revolution." + output_format)

    # Revolution is around H_Axis (X-axis), so:
    #   Y values = RADII  (distance from revolution axis)
    #   X values = AXIAL positions (along the revolution axis)

    # ── Radii (Y values) from diameter-based parameters ──
    r_roller = d_roller / 2.0      # largest radius  (roller OD)
    r_base   = w_base / 2.0        # base/housing radius
    r_shaft  = d_shaft / 2.0       # shaft-level radius (smallest)

    # Profile Y mapping (y2 = peak, descending: y3 > y4 > y5, y1 = inner)
    y2 = r_roller                                          # peak = roller radius
    y3 = r_base                                            # first step down = base radius
    y4 = max(r_shaft + 5.0, (r_base + r_shaft) / 2.0)     # intermediate step
    y1 = max(r_shaft + 2.0, y4 - 5.0)                     # inner section
    y5 = r_shaft                                           # base level = shaft radius

    # Ensure strict ordering: y5 < y1 < y4 < y3 < y2
    y5 = min(y5, y1 - 2.0)
    y1 = min(y1, y4 - 2.0)
    y4 = min(y4, y3 - 2.0)
    y3 = min(y3, y2 - 2.0)

    # ── Axial positions (X values) from height/width parameters ──
    x4 = h_overall                                         # total axial length
    x1 = max(5.0, w_bearing * 0.5)                         # first step
    x2 = max(x1 + 5.0, w_bearing)                          # bearing section width
    x3 = max(x2 + 5.0, h_overall * 0.65)                   # third step

    # Ensure within total height with gaps
    x3 = min(x3, x4 - 5.0)
    x2 = min(x2, x3 - 5.0)
    x1 = min(x1, x2 - 5.0)

    return SCRIPT_TEMPLATE.format(
        output_path=output_path.replace("\\", "\\\\"),
        output_format=output_format,
        x1=x1, x2=x2, x3=x3, x4=x4,
        y1=y1, y2=y2, y3=y3, y4=y4, y5=y5,
    )


def run_freecad_script(script_content, use_gui=False):
    """
    Run FreeCAD with the generated script.

    FIX: avoid capture_output=True with FreeCAD.exe on Windows - it causes
    pipe buffer deadlocks when FreeCAD writes a lot of GUI/Qt output.
    Instead we redirect stdout/stderr to a temp log file and read it after.
    """
    # TechDraw always needs FreeCAD.exe (not Cmd), regardless of use_gui flag
    freecad_exe = find_freecad()
    if freecad_exe is None:
        freecad_exe = find_freecadcmd()
    if freecad_exe is None:
        print("ERROR: FreeCAD not found!")
        return False

    script_path = os.path.join(tempfile.gettempdir(), "_freecad_drawing_script.py")
    log_path = os.path.join(tempfile.gettempdir(), "_freecad_drawing_log.txt")

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    try:
        # Write output to a log file instead of a pipe - avoids Windows deadlock
        with open(log_path, "w", encoding="utf-8") as log_f:
            proc = subprocess.run(
                [freecad_exe, script_path],
                stdout=log_f,
                stderr=log_f,
                timeout=600,   # TechDraw rendering can be slow; 10 min ceiling
            )

        # Read log back and print
        with open(log_path, "r", encoding="utf-8", errors="replace") as log_f:
            log_content = log_f.read()

        print("--- FreeCAD Output ---")
        print(log_content)
        print(f"--- Return code: {proc.returncode} ---")
        return True

    except subprocess.TimeoutExpired:
        print("ERROR: FreeCAD timed out after 600s.")
        return False
    except Exception as e:
        print("ERROR running FreeCAD: " + str(e))
        return False


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="FreeCAD Stepped Revolution + TechDraw PDF/SVG"
    )
    parser.add_argument("--output", "-o", type=str, default=None)
    parser.add_argument("--format", "-f", choices=["glb", "gltf"], default="glb")
    parser.add_argument("--gui", action="store_true")
    parser.add_argument("--roller-diameter", type=float, required=True)
    parser.add_argument("--bearing-width",   type=float, required=True)
    parser.add_argument("--shaft-diameter",  type=float, required=True)
    parser.add_argument("--overall-height",  type=float, required=True)
    parser.add_argument("--base-width",      type=float, required=True)

    args = parser.parse_args()

    print("=" * 60)
    print("Generating Model with Dimensions:")
    print("  Roller Diameter: ", args.roller_diameter)
    print("  Bearing Width:   ", args.bearing_width)
    print("  Shaft Diameter:  ", args.shaft_diameter)
    print("  Overall Height:  ", args.overall_height)
    print("  Base Width:      ", args.base_width)
    print("=" * 60)

    script = generate_script(
        output_path=args.output,
        output_format=args.format,
        d_shaft=args.shaft_diameter,
        w_bearing=args.bearing_width,
        w_base=args.base_width,
        h_overall=args.overall_height,
        d_roller=args.roller_diameter,
    )

    run_freecad_script(script, use_gui=args.gui)
    print("Process complete.")


if __name__ == "__main__":
    main()