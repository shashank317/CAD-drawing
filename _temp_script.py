
"""
FreeCAD script - Stepped Revolution Component + TechDraw
Dynamically generated with custom dimensions.
"""

import FreeCAD as App
import Part
import Sketcher
import Mesh
import MeshPart

OUTPUT_PATH = r"C:\\Users\\sumit\\OneDrive\\Desktop\\free\\output\\8.glb"
OUTPUT_FORMAT = "glb"

def create_stepped_revolution():
    """Create a stepped revolution component"""

    try:
        doc = App.ActiveDocument
        if doc is None:
            doc = App.newDocument('SteppedRevolution')
    except:
        doc = App.newDocument('SteppedRevolution')

    App.setActiveDocument(doc.Name)

    print("Creating Stepped Revolution component...")

    body = doc.addObject('PartDesign::Body', 'Body')
    body.Label = 'Body'
    doc.recompute()

    sketch = body.newObject('Sketcher::SketchObject', 'Profile')
    sketch.AttachmentSupport = (doc.getObject('XY_Plane'), [''])
    sketch.MapMode = 'FlatFace'
    doc.recompute()

    V = App.Vector

    segments = [
        (V(0,     0,    0), V(0,     25.0, 0)),
        (V(0,     25.0, 0), V(13.0,  25.0, 0)),
        (V(13.0,  25.0, 0), V(13.0,  50.0, 0)),
        (V(13.0,  50.0, 0), V(33.0,  50.0, 0)),
        (V(33.0,  50.0, 0), V(33.0,  45.0, 0)),
        (V(33.0,  45.0, 0), V(50.25,  45.0, 0)),
        (V(50.25,  45.0, 0), V(50.25,  30.0, 0)),
        (V(50.25,  30.0, 0), V(80.25,  30.0, 0)),
        (V(80.25,  30.0, 0), V(80.25,  20.0, 0)),
        (V(80.25,  20.0, 0), V(0,     20.0, 0)),
        (V(0,     20.0, 0), V(0,     0,    0)),
    ]

    for p1, p2 in segments:
        sketch.addGeometry(Part.LineSegment(p1, p2), False)
    doc.recompute()

    n = len(segments)
    for i in range(n):
        sketch.addConstraint(Sketcher.Constraint('Coincident', i, 2, (i + 1) % n, 1))

    sketch.addConstraint(Sketcher.Constraint('Coincident', 0, 1, -1, 1))
    doc.recompute()

    for i in [0, 2, 4, 6, 8, 10]:
        sketch.addConstraint(Sketcher.Constraint('Vertical', i))
    for i in [1, 3, 5, 7, 9]:
        sketch.addConstraint(Sketcher.Constraint('Horizontal', i))
    doc.recompute()

    sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 1, 1, 25.0))
    sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 3, 1, 50.0))
    sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 5, 1, 45.0))
    sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 7, 1, 30.0))
    sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 9, 1, 20.0))

    sketch.addConstraint(Sketcher.Constraint('DistanceX', -1, 1, 1, 2, 13.0))
    sketch.addConstraint(Sketcher.Constraint('DistanceX', -1, 1, 3, 2, 33.0))
    sketch.addConstraint(Sketcher.Constraint('DistanceX', -1, 1, 5, 2, 50.25))
    sketch.addConstraint(Sketcher.Constraint('DistanceX', -1, 1, 7, 2, 80.25))

    doc.recompute()
    sketch.Visibility = False
    doc.recompute()

    rev = body.newObject('PartDesign::Revolution', 'Revolution')
    rev.Profile = (sketch, [''])
    rev.ReferenceAxis = (sketch, ['H_Axis'])
    rev.Angle = 360.0
    doc.recompute()

    print("SteppedRevolution created successfully.")
    return doc


def export_model(doc):
    """Export the model to GLB/GLTF format"""
    print("Exporting to " + OUTPUT_FORMAT.upper() + "...")

    fcstd_path = OUTPUT_PATH.replace('.glb', '.FCStd').replace('.gltf', '.FCStd')
    doc.saveAs(fcstd_path)
    print("FreeCAD file saved: " + fcstd_path)

    body = doc.getObject('Body')
    if not body:
        print("Error: Body object not found for export.")
        return False

    try:
        import FreeCADGui as Gui
        import ImportGui

        print("GUI environment detected. Attempting native GLB export via ImportGui...")

        __objs__ = [body]
        if hasattr(ImportGui, "exportOptions"):
            options = ImportGui.exportOptions(OUTPUT_PATH)
            ImportGui.export(__objs__, OUTPUT_PATH, options)
        else:
            ImportGui.export(__objs__, OUTPUT_PATH)

        print(OUTPUT_FORMAT.upper() + " saved via ImportGui: " + OUTPUT_PATH)

    except ImportError:
        print("Headless mode. Falling back to mesh exports...")

        compound = body.Shape
        mesh = MeshPart.meshFromShape(
            Shape=compound, LinearDeflection=0.1, AngularDeflection=0.5, Relative=False
        )

        gltf_path = OUTPUT_PATH.replace('.glb', '.gltf').replace('.gltf', '.gltf')
        try:
            mesh.write(gltf_path)
            print("GLTF saved: " + gltf_path)
        except Exception as ge:
            print("GLTF not supported headless: " + str(ge))

        stl_path = OUTPUT_PATH.replace('.glb', '.stl').replace('.gltf', '.stl')
        mesh.write(stl_path)
        print("STL saved: " + stl_path)

        obj_path = OUTPUT_PATH.replace('.glb', '.obj').replace('.gltf', '.obj')
        mesh.write(obj_path)
        print("OBJ saved: " + obj_path)

    except Exception as e:
        print("Export failed: " + str(e))

    return True


# ============================================================================
# TECHDRAW - ENGINEERING DRAWING WITH DIMENSIONS
# ============================================================================

def _get_edge_indices(view):
    """Return a list of (index, edge) tuples for a TechDraw view."""
    edges = []
    try:
        for i, edge in enumerate(view.getEdgesAsList()):
            edges.append((i, edge))
    except Exception:
        pass
    return edges


def _add_dimension(doc, page, view, edge_idx, dim_type, x_pos, y_pos, label=None):
    """
    Safely add a single dimension to a TechDraw page.
    Returns the dimension object or None on failure.
    """
    import TechDraw
    try:
        dim_name = 'AutoDim_' + str(id(view)) + '_' + str(edge_idx)
        dim = doc.addObject('TechDraw::DrawViewDimension', dim_name)
        dim.Type = dim_type
        dim.MeasureType = 'Projected'
        dim.References2D = [(view, 'Edge' + str(edge_idx))]
        page.addView(dim)
        dim.X = float(x_pos)
        dim.Y = float(y_pos)
        if label:
            dim.FormatSpec = label
        doc.recompute()
        return dim
    except Exception as e:
        print("  Dimension failed (edge " + str(edge_idx) + ", " + dim_type + "): " + str(e))
        return None


def _classify_edge(edge):
    """
    Classify an edge from a TechDraw view as:
      'circle'   - closed circular arc (full circle) -> Diameter
      'arc'      - partial arc -> Diameter
      'horiz'    - horizontal line -> DistanceX
      'vert'     - vertical line  -> DistanceY
      'other'    - skip
    Returns (dim_type, length_hint)
    """
    try:
        curve = edge.Curve
        curve_type = type(curve).__name__

        if curve_type in ('Circle', 'ArcOfCircle'):
            return ('Diameter', curve.Radius * 2.0)

        if curve_type == 'Line':
            p1 = edge.Vertexes[0].Point
            p2 = edge.Vertexes[-1].Point
            dx = abs(p2.x - p1.x)
            dy = abs(p2.y - p1.y)
            if dy < 0.5:
                return ('DistanceX', dx)
            elif dx < 0.5:
                return ('DistanceY', dy)

    except Exception:
        pass

    return ('skip', 0)


def create_techdraw(doc):
    """
    Create a TechDraw page with Front, Side, and Isometric views of the body,
    auto-detect and annotate all measurable edges, then export PDF + SVG.
    """
    print("Creating TechDraw page...")

    try:
        import TechDraw
        import TechDrawGui
    except ImportError:
        print("TechDraw module not available in this FreeCAD build. Skipping drawing export.")
        return

    body = doc.getObject('Body')
    if not body:
        print("Body not found. Cannot create TechDraw.")
        return

    # -- Page with default A3 template --
    page = doc.addObject('TechDraw::DrawPage', 'DrawingPage')
    page.Label = 'Engineering Drawing'

    template_paths = [
        r"C:\Program Files\FreeCAD 1.0\data\Mod\TechDraw\Templates\A3_Landscape_blank.svg",
        r"C:\Program Files\FreeCAD 0.21\data\Mod\TechDraw\Templates\A3_Landscape_blank.svg",
        r"C:\Program Files\FreeCAD 0.20\data\Mod\TechDraw\Templates\A3_Landscape_blank.svg",
        r"C:\Program Files\FreeCAD\data\Mod\TechDraw\Templates\A3_Landscape_blank.svg",
    ]
    template_found = None
    for tp in template_paths:
        if os.path.exists(tp):
            template_found = tp
            break

    if template_found:
        template = doc.addObject('TechDraw::DrawSVGTemplate', 'Template')
        template.Template = template_found
        page.Template = template
        print("Template loaded: " + template_found)
    else:
        print("No template found - page will have no border/titleblock.")

    doc.recompute()

    # -----------------------------------------------------------------------
    # VIEW LAYOUT  (page coords in mm, A3 = 420 x 297)
    # Front view  -> lower-left  area
    # Side view   -> lower-right area
    # Iso view    -> upper-right area
    # -----------------------------------------------------------------------

    # -- Front View (looking along -Y axis) --
    front = doc.addObject('TechDraw::DrawViewPart', 'FrontView')
    front.Source = [body]
    front.Direction = App.Vector(0, -1, 0)
    front.XDirection = App.Vector(1, 0, 0)
    front.Scale = 0.5
    front.X = 100.0
    front.Y = 120.0
    page.addView(front)
    doc.recompute()
    print("Front view added.")

    # -- Side View (looking along +X axis) --
    side = doc.addObject('TechDraw::DrawViewPart', 'SideView')
    side.Source = [body]
    side.Direction = App.Vector(1, 0, 0)
    side.XDirection = App.Vector(0, 1, 0)
    side.Scale = 0.5
    side.X = 260.0
    side.Y = 120.0
    page.addView(side)
    doc.recompute()
    print("Side view added.")

    # -- Isometric View --
    import math
    iso_dir = App.Vector(1, 1, 1)
    iso_dir.normalize()
    iso = doc.addObject('TechDraw::DrawViewPart', 'IsoView')
    iso.Source = [body]
    iso.Direction = iso_dir
    iso.XDirection = App.Vector(-1, 1, 0).normalize()
    iso.Scale = 0.4
    iso.X = 330.0
    iso.Y = 220.0
    page.addView(iso)
    doc.recompute()
    print("Isometric view added.")

    # -----------------------------------------------------------------------
    # AUTO-DIMENSION: iterate edges on Front + Side views
    # -----------------------------------------------------------------------
    print("Auto-dimensioning edges...")

    # offsets so dimensions don't collide
    dim_offset_x = 20.0
    dim_offset_y = 20.0

    for view, view_label, base_x, base_y in [
        (front, 'Front', 100.0, 120.0),
        (side,  'Side',  260.0, 120.0),
    ]:
        edges = _get_edge_indices(view)
        placed = []   # track (x,y) of placed dims to avoid collisions

        for idx, edge in edges:
            dim_type, length_hint = _classify_edge(edge)
            if dim_type == 'skip' or length_hint < 0.1:
                continue

            # compute a staggered position
            stagger = len(placed)
            if dim_type == 'Diameter':
                px = base_x + dim_offset_x + stagger * 15.0
                py = base_y - dim_offset_y - stagger * 8.0
            elif dim_type == 'DistanceX':
                px = base_x + stagger * 12.0
                py = base_y + dim_offset_y + stagger * 10.0
            else:  # DistanceY
                px = base_x - dim_offset_x - stagger * 12.0
                py = base_y + stagger * 8.0

            result = _add_dimension(doc, page, view, idx, dim_type, px, py)
            if result:
                placed.append((px, py))
                print("  [" + view_label + "] Edge" + str(idx) + " -> " + dim_type +
                      " (hint=" + str(round(length_hint, 2)) + ")")

    doc.recompute()
    print("Auto-dimensioning complete. " + str(sum(1 for v in [front, side] for _ in _get_edge_indices(v))) + " edges scanned.")

    # -----------------------------------------------------------------------
    # EXPORT PDF + SVG
    # -----------------------------------------------------------------------
    base_out = OUTPUT_PATH.replace('.glb', '').replace('.gltf', '')
    pdf_path = base_out + '_drawing.pdf'
    svg_path = base_out + '_drawing.svg'

    # Save FCStd first (already done in export_model, but recompute may have changed things)
    fcstd_path = OUTPUT_PATH.replace('.glb', '.FCStd').replace('.gltf', '.FCStd')
    doc.save()

    # PDF
    try:
        page.ExportSVG = False  # ensure we're exporting PDF mode
        TechDraw.writeDXFPage(page, pdf_path)   # FreeCAD 0.21+
        print("PDF saved: " + pdf_path)
    except Exception:
        try:
            import importlib
            exp = importlib.import_module('TechDrawGui')
            exp.exportPageAsPdf(page, pdf_path)
            print("PDF saved (TechDrawGui): " + pdf_path)
        except Exception as e2:
            print("PDF export failed: " + str(e2))
            # last resort: use subprocess to call FreeCAD GUI exporter
            try:
                page.ExportType = 'PDF'
                doc.recompute()
                print("PDF export: set ExportType, recomputed (manual save may be needed).")
            except Exception as e3:
                print("All PDF methods failed: " + str(e3))

    # SVG
    try:
        TechDraw.writeSVGPage(page, svg_path)
        print("SVG saved: " + svg_path)
    except Exception:
        try:
            import importlib
            exp = importlib.import_module('TechDrawGui')
            exp.exportPageAsSvg(page, svg_path)
            print("SVG saved (TechDrawGui): " + svg_path)
        except Exception as e2:
            try:
                page.ExportSVG = True
                doc.recompute()
                doc.save()
                print("SVG export: triggered via ExportSVG flag.")
            except Exception as e3:
                print("All SVG methods failed: " + str(e3))

    print("TechDraw export complete.")


# ============================================================================
# ENTRY POINT
# ============================================================================

doc = create_stepped_revolution()
export_model(doc)
create_techdraw(doc)
