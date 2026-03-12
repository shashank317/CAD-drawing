from string import Template

"""
also_drawing.py
─────────────────────────────────────────────────────────────────────────────
Launcher script (run with plain Python, outside FreeCAD):
    python "also drawing.py" \
        --roller-diameter 160.5 \
        --bearing-width   20    \
        --shaft-diameter  26    \
        --overall-height  50    \
        --base-width      100.5

What it does:
  1. Finds FreeCAD on Windows automatically
  2. Generates a parametric stepped-revolution 3D body
  3. Exports GLB (GUI) or STL/OBJ (headless fallback)
  4. Creates a TechDraw page with:
       • Custom A0 ISO template (falls back to A3 if not found)
       • Projection group: Front / Left / Right / Top / Bottom / Isometric
       • Auto-dimensioned edges (geometry-based, stable across recomputes)
       • Vertex-pair DistanceY dims on front view (matches manual workflow)
  5. Exports PDF + SVG with multi-fallback chain
─────────────────────────────────────────────────────────────────────────────
"""

import os
import sys
import subprocess
import tempfile

WORKSPACE_DIR = os.path.dirname(os.path.abspath(__file__))


# ─── FREECAD FINDER ──────────────────────────────────────────────────────────

def _find_exe(candidates):
    for p in candidates:
        if os.path.exists(p):
            return p
    return None

def find_freecad():
    return _find_exe([
        r"C:\Program Files\FreeCAD 1.0\bin\FreeCAD.exe",
        r"C:\Program Files\FreeCAD 0.21\bin\FreeCAD.exe",
        r"C:\Program Files\FreeCAD 0.20\bin\FreeCAD.exe",
        r"C:\Program Files\FreeCAD\bin\FreeCAD.exe",
    ])

def find_freecadcmd():
    return _find_exe([
        r"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe",
        r"C:\Program Files\FreeCAD 0.21\bin\FreeCADCmd.exe",
        r"C:\Program Files\FreeCAD 0.20\bin\FreeCADCmd.exe",
        r"C:\Program Files\FreeCAD\bin\FreeCADCmd.exe",
    ])


# ─── INNER SCRIPT (runs inside FreeCAD) ──────────────────────────────────────

INNER_SCRIPT = r'''
"""Inner script — executed by FreeCAD, not plain Python."""
import os, sys, time
import FreeCAD as App
import Part
import Sketcher
import Mesh
import MeshPart

OUTPUT_PATH    = r"$output_path"
OUTPUT_FORMAT  = "$output_format"
CUSTOM_TEMPLATE = r"$template_path"

X1, X2, X3, X4         = $x1, $x2, $x3, $x4
Y1, Y2, Y3, Y4, Y5     = $y1, $y2, $y3, $y4, $y5


# ─────────────────────────────────────────────────────────────────────────────
# 1. BUILD 3D MODEL
# ─────────────────────────────────────────────────────────────────────────────

def create_stepped_revolution():
    try:
        doc = App.ActiveDocument or App.newDocument("SteppedRevolution")
    except Exception:
        doc = App.newDocument("SteppedRevolution")

    App.setActiveDocument(doc.Name)
    print("[+] creating stepped revolution...")

    body   = doc.addObject("PartDesign::Body", "Body")
    sketch = body.newObject("Sketcher::SketchObject", "Profile")
    sketch.AttachmentSupport = (doc.getObject("XY_Plane"), [""])
    sketch.MapMode = "FlatFace"
    doc.recompute()

    V = App.Vector
    segments = [
        (V(0,   0,  0), V(0,   Y1, 0)),
        (V(0,   Y1, 0), V(X1,  Y1, 0)),
        (V(X1,  Y1, 0), V(X1,  Y2, 0)),
        (V(X1,  Y2, 0), V(X2,  Y2, 0)),
        (V(X2,  Y2, 0), V(X2,  Y3, 0)),
        (V(X2,  Y3, 0), V(X3,  Y3, 0)),
        (V(X3,  Y3, 0), V(X3,  Y4, 0)),
        (V(X3,  Y4, 0), V(X4,  Y4, 0)),
        (V(X4,  Y4, 0), V(X4,  Y5, 0)),
        (V(X4,  Y5, 0), V(0,   Y5, 0)),
        (V(0,   Y5, 0), V(0,   0,  0)),
    ]

    for p1, p2 in segments:
        sketch.addGeometry(Part.LineSegment(p1, p2), False)
    doc.recompute()

    n = len(segments)
    for i in range(n):
        sketch.addConstraint(Sketcher.Constraint("Coincident", i, 2, (i+1) % n, 1))
    sketch.addConstraint(Sketcher.Constraint("Coincident", 0, 1, -1, 1))

    for i in [0, 2, 4, 6, 8, 10]:
        sketch.addConstraint(Sketcher.Constraint("Vertical", i))
    for i in [1, 3, 5, 7, 9]:
        sketch.addConstraint(Sketcher.Constraint("Horizontal", i))
    doc.recompute()

    sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, 1, 1, Y1))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, 3, 1, Y2))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, 5, 1, Y3))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, 7, 1, Y4))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, 9, 1, Y5))
    sketch.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, 1, 2, X1))
    sketch.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, 3, 2, X2))
    sketch.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, 5, 2, X3))
    sketch.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, 7, 2, X4))
    doc.recompute()

    sketch.Visibility = False

    rev = body.newObject("PartDesign::Revolution", "Revolution")
    rev.Profile       = (sketch, [""])
    rev.ReferenceAxis = (sketch, ["H_Axis"])
    rev.Angle         = 360.0
    doc.recompute()

    print("[+] revolution created")
    return doc


# ─────────────────────────────────────────────────────────────────────────────
# 2. EXPORT 3D MODEL
# ─────────────────────────────────────────────────────────────────────────────

def export_model(doc):
    print("[+] exporting 3D model...")
    body = doc.getObject("Body")
    if not body:
        print("[!] body not found — skipping 3D export")
        return False

    # save FCStd to temp dir to avoid rename-lock issues
    import tempfile as _tmp
    fcstd_path = os.path.join(_tmp.gettempdir(), "stepped_revolution.FCStd")
    doc.saveAs(fcstd_path)
    print("    FCStd: " + fcstd_path)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    try:
        import FreeCADGui as Gui
        import ImportGui
        if hasattr(ImportGui, "exportOptions"):
            opts = ImportGui.exportOptions(OUTPUT_PATH)
            ImportGui.export([body], OUTPUT_PATH, opts)
        else:
            ImportGui.export([body], OUTPUT_PATH)
        print("    GLB: " + OUTPUT_PATH)
    except ImportError:
        mesh = MeshPart.meshFromShape(
            Shape=body.Shape, LinearDeflection=0.1, AngularDeflection=0.5, Relative=False
        )
        base = OUTPUT_PATH.rsplit(".", 1)[0]
        for ext in ("stl", "obj"):
            p = base + "." + ext
            mesh.write(p)
            print("    " + ext.upper() + ": " + p)
    except Exception as e:
        print("[!] 3D export error: " + str(e))

    return True


# ─────────────────────────────────────────────────────────────────────────────
# 3. TECHDRAW
# ─────────────────────────────────────────────────────────────────────────────

def _find_template():
    if CUSTOM_TEMPLATE and os.path.exists(CUSTOM_TEMPLATE):
        return CUSTOM_TEMPLATE
    try:
        res = App.getResourceDir()
        for name in ("A3_LandscapeTD.svg", "A3_Landscape_blank.svg", "A3_LandscapeISO.svg"):
            c = os.path.join(res, "Mod", "TechDraw", "Templates", name)
            if os.path.exists(c):
                return c
    except Exception:
        pass
    for base in (
        r"C:\Program Files\FreeCAD 1.0",
        r"C:\Program Files\FreeCAD 0.21",
        r"C:\Program Files\FreeCAD 0.20",
        r"C:\Program Files\FreeCAD",
    ):
        for name in ("A3_LandscapeTD.svg", "A3_Landscape_blank.svg"):
            p = os.path.join(base, "data", "Mod", "TechDraw", "Templates", name)
            if os.path.exists(p):
                return p
    return None


def _classify_edge(topo_edge):
    """Geometry-based — stable across recomputes."""
    try:
        curve = topo_edge.Curve
        if isinstance(curve, Part.Circle):
            return "Diameter"
        if isinstance(curve, (Part.Line, Part.LineSegment)):
            v = topo_edge.Vertexes
            if len(v) < 2:
                return None
            d = v[1].Point - v[0].Point
            if abs(d.x) < 1e-4:
                return "DistanceY"
            if abs(d.y) < 1e-4:
                return "DistanceX"
            return "Distance"
    except Exception:
        pass
    return None


def _add_dim(doc, page, view, edge_ref, dim_type, x, y, label):
    try:
        if edge_ref.startswith("Edge"):
            edges = view.getVisibleEdges()
            idx = int(edge_ref.replace("Edge", ""))
            if idx >= len(edges):
                print("    [skip] " + label + " " + edge_ref + " (out of bounds)")
                return None
            actual_type = _classify_edge(edges[idx])
            if dim_type in ("Diameter", "Radius") and actual_type != "Diameter":
                print("    [skip] " + label + " " + edge_ref + " (not a circle, actual: " + str(actual_type) + ")")
                return None
            if dim_type in ("DistanceX", "DistanceY", "Distance") and actual_type == "Diameter":
                print("    [skip] " + label + " " + edge_ref + " (is a circle)")
                return None

        dim = doc.addObject("TechDraw::DrawViewDimension", label)
        dim.Type         = dim_type
        dim.MeasureType  = "Projected"
        dim.References2D = [(view, edge_ref)]
        page.addView(dim)
        dim.X = float(x)
        dim.Y = float(y)
        dim.recompute()
        return dim
    except Exception as e:
        print("    [skip] " + label + " " + dim_type + " " + edge_ref + ": " + str(e))
        return None


def _add_dim_2v(doc, page, view, ref1, ref2, dim_type, x, y, label):
    try:
        dim = doc.addObject("TechDraw::DrawViewDimension", label)
        dim.Type         = dim_type
        dim.MeasureType  = "Projected"
        dim.References2D = [(view, ref1), (view, ref2)]
        page.addView(dim)
        dim.X = float(x)
        dim.Y = float(y)
        dim.recompute()
        return dim
    except Exception as e:
        print("    [skip] " + label + " " + ref1 + "+" + ref2 + ": " + str(e))
        return None


def _auto_dim_view(doc, page, view, x_offset, y_offset, spacing=18, max_dims=20):
    """Walk visible edges, classify geometrically, lay out in grid."""
    try:
        edges = view.getVisibleEdges()
    except Exception as e:
        print("    [!] getVisibleEdges on " + view.Name + ": " + str(e))
        return 0

    dims_added = 0
    col_count  = 4

    for i, edge in enumerate(edges):
        if dims_added >= max_dims:
            break
        dim_type = _classify_edge(edge)
        if dim_type is None:
            continue
        col = dims_added % col_count
        row = dims_added // col_count
        x   = x_offset + col * spacing
        y   = y_offset - row * spacing
        lbl = "Dim_" + view.Name + "_" + str(dims_added).zfill(3)
        if _add_dim(doc, page, view, "Edge" + str(i), dim_type, x, y, lbl):
            print("    " + lbl + ": " + dim_type + " -> Edge" + str(i))
            dims_added += 1

    return dims_added


def _dim_front_vertex_pairs(doc, page, view):
    """
    DistanceY dims between vertex pairs on the front/right view.
    Matches the manual workflow from recorded session:
    each pair = top/bottom of one step in the revolution profile.
    Offsets tuned from actual FreeCAD session log.
    """
    pairs = [
        ("Vertex0",  "Vertex1",  "DistanceY",  108.0,   0.0),
        ("Vertex3",  "Vertex4",  "DistanceY",  149.0,   4.0),
        ("Vertex6",  "Vertex7",  "DistanceY",  185.0,  -6.0),
        ("Vertex10", "Vertex11", "DistanceY",  -54.0,   3.0),
    ]
    added = 0
    for ref1, ref2, dtype, x, y in pairs:
        lbl = "Dim_vstep_" + ref1
        if _add_dim_2v(doc, page, view, ref1, ref2, dtype, x, y, lbl):
            print("    " + lbl + ": " + dtype + " " + ref1 + "+" + ref2)
            added += 1
    return added


def _dim_left_diameters(doc, page, view):
    """
    Diameter dims on left view circular edges.
    Offsets from recorded session (ProjItem003 block).
    """
    entries = [
        ("Edge0", "Diameter",  16.25,  156.2),
        ("Edge1", "Diameter",   1.25,  147.0),
        ("Edge2", "Diameter", -10.0,   160.8),
        ("Edge3", "Diameter", -20.0,   163.2),
        ("Edge4", "Diameter",  74.5,    70.5),
        ("Edge5", "Diameter",  57.8,   104.1),
        ("Edge6", "Diameter", -10.0,   124.9),
        ("Edge7", "Diameter", -20.0,   122.6),
    ]
    added = 0
    for eref, dtype, x, y in entries:
        lbl = "Dim_left_" + eref
        if _add_dim(doc, page, view, eref, dtype, x, y, lbl):
            print("    " + lbl + ": " + dtype + " -> " + eref)
            added += 1
    return added


def _dim_right_view(doc, page, view):
    """
    Diameter dims on right view circular edges.
    Offsets from recorded session (ProjItem002 block).
    """
    entries = [
        ("Edge0", "Diameter",  130.9, -102.4),
        ("Edge1", "Diameter",  241.5,  -59.3),
        ("Edge2", "Diameter",  176.1,  160.4),
        ("Edge3", "Diameter",  179.7,   13.1),
    ]
    added = 0
    for eref, dtype, x, y in entries:
        lbl = "Dim_right_" + eref
        if _add_dim(doc, page, view, eref, dtype, x, y, lbl):
            print("    " + lbl + ": " + dtype + " -> " + eref)
            added += 1
    return added


def _dim_bottom_view(doc, page, view):
    """
    Distance dims on bottom view edges.
    Offsets from recorded session (ProjItem004 block).
    """
    entries = [
        ("Edge0", "DistanceY", 137.0, 0.0),
        ("Edge2", "DistanceY", 179.5, 0.0),
        ("Edge4", "DistanceY", 234.9, 0.0),
        ("Edge7", "DistanceY",  86.8, 0.0),
    ]
    added = 0
    for eref, dtype, x, y in entries:
        lbl = "Dim_bottom_" + eref
        if _add_dim(doc, page, view, eref, dtype, x, y, lbl):
            print("    " + lbl + ": " + dtype + " -> " + eref)
            added += 1
    return added


def _get_proj_items(doc):
    items = {}
    for obj in doc.Objects:
        if obj.TypeId == "TechDraw::DrawProjGroupItem" and hasattr(obj, "Type"):
            items[obj.Type] = obj
    return items


def _wait_for_render(label=""):
    try:
        from PySide2 import QtWidgets, QtCore
        app = QtWidgets.QApplication.instance()
        if app:
            print("[+] waiting for render" + (" (" + label + ")" if label else "") + "...")
            for _ in range(40):
                app.processEvents()
                QtCore.QThread.msleep(250)
            app.processEvents()
            return
    except Exception:
        pass
    print("[+] headless — sleeping 10s" + (" (" + label + ")" if label else "") + "...")
    time.sleep(10)


def create_techdraw(doc):
    print("[+] creating TechDraw page...")

    try:
        import TechDraw
    except ImportError:
        print("[!] TechDraw not available — skipping")
        return

    try:
        import TechDrawGui
    except ImportError:
        TechDrawGui = None

    body = doc.getObject("Body")
    if not body:
        print("[!] body not found — skipping drawing")
        return

    # ── page ─────────────────────────────────────────────────────────────────
    page = doc.addObject("TechDraw::DrawPage", "Page")
    page.KeepUpdated = True

    tmpl_path = _find_template()
    if tmpl_path:
        tmpl          = doc.addObject("TechDraw::DrawSVGTemplate", "Template")
        tmpl.Template = tmpl_path
        page.Template = tmpl
        print("    template: " + tmpl_path)
    else:
        print("    [!] no template — blank page")

    page.Visibility = False
    page.Visibility = True
    doc.recompute()

    # ── projection group ──────────────────────────────────────────────────────
    pg = doc.addObject("TechDraw::DrawProjGroup", "ProjGroup")
    page.addView(pg)
    pg.Source         = [body]
    pg.ProjectionType = "Third Angle"
    pg.Scale          = 0.5
    pg.AutoDistribute = True
    pg.spacingX       = 40
    pg.spacingY       = 40

    # addProjection("Front") creates the Anchor — must be first
    pg.addProjection("Front")
    doc.recompute()

    pg.Anchor.Direction  = App.Vector(0, -1, 0)
    pg.Anchor.XDirection = App.Vector(1,  0, 0)

    for vt in ("Left", "Right", "Top", "Bottom", "FrontBottomLeft"):
        pg.addProjection(vt)

    pg.X = page.PageWidth  / 2
    pg.Y = page.PageHeight / 2
    doc.recompute()
    print("[+] projection group created")

    # ── render wait BEFORE dimensioning ──────────────────────────────────────
    page.KeepUpdated = True
    for obj in doc.Objects:
        if hasattr(obj, "TypeId") and "TechDraw::" in obj.TypeId:
            try:
                obj.recompute(True)
            except Exception:
                pass
    doc.recompute()

    try:
        import FreeCADGui as Gui
        Gui.ActiveDocument.setEdit(page)
    except Exception:
        pass

    _wait_for_render("pre-dimension")

    try:
        import FreeCADGui as Gui
        Gui.ActiveDocument.resetEdit()
    except Exception:
        pass

    doc.recompute()

    # ── dimensions ────────────────────────────────────────────────────────────
    items = _get_proj_items(doc)
    total = 0

    # front view: edge-based auto dims (DistanceX for horizontal steps)
    front = items.get("Front") or pg.Anchor
    n = _auto_dim_view(doc, page, front, 30, -30)
    print("    Front (edges): " + str(n) + " dims")
    total += n

    # front view: vertex-pair DistanceY for step heights (matches manual workflow)
    n = _dim_front_vertex_pairs(doc, page, front)
    print("    Front (vertex pairs): " + str(n) + " dims")
    total += n

    # left view: diameter dims
    left = items.get("Left")
    if left:
        n = _dim_left_diameters(doc, page, left)
        print("    Left (diameters): " + str(n) + " dims")
        total += n

    # right view: diameter dims
    right = items.get("Right")
    if right:
        n = _dim_right_view(doc, page, right)
        print("    Right (diameters): " + str(n) + " dims")
        total += n

    # top view: edge-based auto dims
    top = items.get("Top")
    if top:
        n = _auto_dim_view(doc, page, top, 30, 140)
        print("    Top (edges): " + str(n) + " dims")
        total += n

    # bottom view: manual distance dims
    bottom = items.get("Bottom")
    if bottom:
        n = _dim_bottom_view(doc, page, bottom)
        print("    Bottom (distances): " + str(n) + " dims")
        total += n

    # overall axial length between outermost vertices on front view
    _add_dim_2v(doc, page, front, "Vertex0", "Vertex1", "DistanceX",
                0, -(Y2 * 1.8 + 40), "Dim_overall_length")

    doc.recompute()
    print("[+] " + str(total) + " dimensions added")

    # ── second render wait before export ─────────────────────────────────────
    _wait_for_render("pre-export")
    doc.recompute()

    # ── export ────────────────────────────────────────────────────────────────
    base     = OUTPUT_PATH.rsplit(".", 1)[0]
    pdf_path = base + "_drawing.pdf"
    svg_path = base + "_drawing.svg"

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    doc.save()

    # SVG — TechDrawGui.exportPageAsSvg is the correct API
    svg_ok = False
    if TechDrawGui:
        try:
            TechDrawGui.exportPageAsSvg(page, svg_path)
            if os.path.exists(svg_path) and os.path.getsize(svg_path) > 500:
                print("    SVG: " + svg_path)
                svg_ok = True
        except Exception as e:
            print("    [!] SVG failed: " + str(e))

    # PDF waterfall
    pdf_ok = False
    for attempt in ("gui_export", "techdrawgui", "cairosvg", "reportlab"):
        if pdf_ok:
            break
        if attempt == "gui_export":
            try:
                import FreeCADGui as Gui
                opts = Gui.exportOptions(pdf_path) if hasattr(Gui, "exportOptions") else None
                Gui.export([page], pdf_path, opts) if opts else Gui.export([page], pdf_path)
                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 500:
                    print("    PDF: " + pdf_path)
                    pdf_ok = True
            except Exception:
                pass
        elif attempt == "techdrawgui" and TechDrawGui:
            try:
                TechDrawGui.exportPageAsPdf(page, pdf_path)
                if os.path.exists(pdf_path) and os.path.getsize(pdf_path) > 500:
                    print("    PDF (TechDrawGui): " + pdf_path)
                    pdf_ok = True
            except Exception:
                pass
        elif attempt == "cairosvg" and svg_ok:
            try:
                import cairosvg
                cairosvg.svg2pdf(url=svg_path, write_to=pdf_path)
                print("    PDF (cairosvg): " + pdf_path)
                pdf_ok = True
            except Exception:
                pass
        elif attempt == "reportlab" and svg_ok:
            try:
                from svglib.svglib import svg2rlg
                from reportlab.graphics import renderPDF
                drawing = svg2rlg(svg_path)
                if drawing:
                    renderPDF.drawToFile(drawing, pdf_path)
                    print("    PDF (reportlab): " + pdf_path)
                    pdf_ok = True
            except Exception:
                pass

    if not pdf_ok:
        print("[!] PDF export failed — SVG available if generated")

    print("[+] TechDraw complete")
    print("    PDF: " + (pdf_path if pdf_ok else "NOT GENERATED"))
    print("    SVG: " + (svg_path if svg_ok else "NOT GENERATED"))


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT (inside FreeCAD)
# ─────────────────────────────────────────────────────────────────────────────
doc = create_stepped_revolution()
export_model(doc)
create_techdraw(doc)
# don't call sys.exit() — FreeCAD returns code 1 for it regardless,
# causing the launcher to think it failed even when everything worked.
# Let the script end naturally; launcher checks log content instead.
'''


# ─── PARAMETER CALCULATOR ────────────────────────────────────────────────────

def generate_script(output_path, output_format, d_shaft, w_bearing, w_base, h_overall, d_roller):
    if output_path is None:
        output_path = os.path.join(WORKSPACE_DIR, "output", "model." + output_format)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    r_roller = d_roller / 2.0
    r_base   = w_base   / 2.0
    r_shaft  = d_shaft  / 2.0

    y2 = r_roller
    y3 = r_base
    y4 = max(r_shaft + 5.0, (r_base + r_shaft) / 2.0)
    y1 = max(r_shaft + 2.0, y4 - 5.0)
    y5 = r_shaft

    y5 = min(y5, y1 - 2.0)
    y1 = min(y1, y4 - 2.0)
    y4 = min(y4, y3 - 2.0)
    y3 = min(y3, y2 - 2.0)

    x4 = h_overall
    x1 = max(5.0, w_bearing * 0.5)
    x2 = max(x1 + 5.0, w_bearing)
    x3 = max(x2 + 5.0, h_overall * 0.65)
    x3 = min(x3, x4 - 5.0)
    x2 = min(x2, x3 - 5.0)
    x1 = min(x1, x2 - 5.0)

    template_path = os.path.join(WORKSPACE_DIR, "A0_Landscape_ISO5457_notitleblock.svg")

    return Template(INNER_SCRIPT).substitute(
        output_path=output_path,
        output_format=output_format,
        template_path=template_path,
        x1=x1, x2=x2, x3=x3, x4=x4,
        y1=y1, y2=y2, y3=y3, y4=y4, y5=y5,
    )


# ─── SUBPROCESS RUNNER ───────────────────────────────────────────────────────

def run_freecad_script(script_content):
    exe = find_freecad() or find_freecadcmd()
    if exe is None:
        print("ERROR: FreeCAD not found.")
        return False

    script_path = os.path.join(tempfile.gettempdir(), "_fc_techdraw_script.py")
    log_path    = os.path.join(tempfile.gettempdir(), "_fc_techdraw_log.txt")

    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_content)

    try:
        with open(log_path, "w", encoding="utf-8") as log_f:
            proc = subprocess.run(
                [str(exe), script_path],
                stdout=log_f,
                stderr=log_f,
                timeout=600,
            )

        with open(log_path, "r", encoding="utf-8", errors="replace") as log_f:
            log_content = log_f.read()

        print("--- FreeCAD Output ---")
        print(log_content)
        print("--- FreeCAD exit code: " + str(proc.returncode) + " ---")

        # FreeCAD exits with code 1 on sys.exit(0) — check log instead
        success = "[+] TechDraw complete" in log_content
        return success

    except subprocess.TimeoutExpired:
        print("ERROR: FreeCAD timed out after 600s.")
        return False
    except Exception as e:
        print("ERROR: " + str(e))
        return False


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    import argparse
    p = argparse.ArgumentParser(description="FreeCAD Stepped Revolution + TechDraw PDF/SVG")
    p.add_argument("--output",           "-o", type=str,   default=None)
    p.add_argument("--format",           "-f", choices=["glb", "gltf"], default="glb")
    p.add_argument("--roller-diameter",        type=float, required=True)
    p.add_argument("--bearing-width",          type=float, required=True)
    p.add_argument("--shaft-diameter",         type=float, required=True)
    p.add_argument("--overall-height",         type=float, required=True)
    p.add_argument("--base-width",             type=float, required=True)
    args = p.parse_args()

    print("=" * 60)
    print("Generating Model with Dimensions:")
    print("  Roller Diameter: ", args.roller_diameter)
    print("  Bearing Width:   ", args.bearing_width)
    print("  Shaft Diameter:  ", args.shaft_diameter)
    print("  Overall Height:  ", args.overall_height)
    print("  Base Width:      ", args.base_width)
    print("=" * 60)

    script = generate_script(
        output_path   = args.output,
        output_format = args.format,
        d_shaft       = args.shaft_diameter,
        w_bearing     = args.bearing_width,
        w_base        = args.base_width,
        h_overall     = args.overall_height,
        d_roller      = args.roller_diameter,
    )

    ok = run_freecad_script(script)
    print("Process complete.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()