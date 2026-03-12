"""
FreeCAD Stepped Revolution Component with GLB/GLTF Export - Dynamic Parameters

This script opens FreeCAD, generates the component with dynamic dimensions, and exports to GLB/GLTF.

Usage:
    python custom_inputs.py --roller-diameter 160.5 --bearing-width 20 --shaft-diameter 26 --overall-height 50 --base-width 100.5
    python custom_inputs.py --output custom_model.glb --roller-diameter 160.5 ...
"""

import subprocess
import os
import sys

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
SCRIPT_TEMPLATE = '''
"""
FreeCAD script - Stepped Revolution Component
Dynamically generated with custom dimensions.
"""

import FreeCAD as App
import Part
import Sketcher
import Mesh
import MeshPart

OUTPUT_PATH = r"{output_path}"
OUTPUT_FORMAT = "{output_format}"

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

    # -- Document & Body --
    body = doc.addObject('PartDesign::Body', 'Body')
    body.Label = 'Body'
    doc.recompute()

    # -- Sketch on XY Plane --
    sketch = body.newObject('Sketcher::SketchObject', 'Profile')
    sketch.AttachmentSupport = (doc.getObject('XY_Plane'), [''])
    sketch.MapMode = 'FlatFace'
    doc.recompute()

    V = App.Vector

    # Profile geometry (dynamic points based on input)
    segments = [
        (V(0,     0,    0), V(0,     {y1}, 0)),
        (V(0,     {y1}, 0), V({x1},  {y1}, 0)),
        (V({x1},  {y1}, 0), V({x1},  {y2}, 0)),
        (V({x1},  {y2}, 0), V({x2},  {y2}, 0)),
        (V({x2},  {y2}, 0), V({x2},  {y3}, 0)),
        (V({x2},  {y3}, 0), V({x3},  {y3}, 0)),
        (V({x3},  {y3}, 0), V({x3},  {y4}, 0)),
        (V({x3},  {y4}, 0), V({x4},  {y4}, 0)),
        (V({x4},  {y4}, 0), V({x4},  {y5}, 0)),
        (V({x4},  {y5}, 0), V(0,     {y5}, 0)),
        (V(0,     {y5}, 0), V(0,     0,    0)),
    ]

    for p1, p2 in segments:
        sketch.addGeometry(Part.LineSegment(p1, p2), False)
    doc.recompute()

    # Close polygon
    n = len(segments)
    for i in range(n):
        sketch.addConstraint(Sketcher.Constraint('Coincident', i, 2, (i + 1) % n, 1))
    
    # Lock origin
    sketch.addConstraint(Sketcher.Constraint('Coincident', 0, 1, -1, 1))
    doc.recompute()

    # Horizontal / vertical constraints
    for i in [0, 2, 4, 6, 8, 10]:
        sketch.addConstraint(Sketcher.Constraint('Vertical', i))
    for i in [1, 3, 5, 7, 9]:
        sketch.addConstraint(Sketcher.Constraint('Horizontal', i))
    doc.recompute()

    # Dimensional Constraints (Using exact coordinates)
    sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 1, 1, {y1}))
    sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 3, 1, {y2}))
    sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 5, 1, {y3}))
    sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 7, 1, {y4}))
    sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, 9, 1, {y5}))

    sketch.addConstraint(Sketcher.Constraint('DistanceX', -1, 1, 1, 2, {x1}))
    sketch.addConstraint(Sketcher.Constraint('DistanceX', -1, 1, 3, 2, {x2}))
    sketch.addConstraint(Sketcher.Constraint('DistanceX', -1, 1, 5, 2, {x3}))
    sketch.addConstraint(Sketcher.Constraint('DistanceX', -1, 1, 7, 2, {x4}))
    
    doc.recompute()
    sketch.Visibility = False
    doc.recompute()

    # Revolution
    rev = body.newObject('PartDesign::Revolution', 'Revolution')
    rev.Profile = (sketch, [''])
    rev.ReferenceAxis = (sketch, ['H_Axis'])
    rev.Angle = 360.0
    doc.recompute()

    print("SteppedRevolution created successfully with custom dimensions.")
    return doc

def export_model(doc):
    """Export the model to GLB/GLTF format"""
    print("Exporting to " + OUTPUT_FORMAT.upper() + "...")
    
    # Save FreeCAD document first
    fcstd_path = OUTPUT_PATH.replace('.glb', '.FCStd').replace('.gltf', '.FCStd')
    doc.saveAs(fcstd_path)
    print("FreeCAD file saved: " + fcstd_path)

    body = doc.getObject('Body')
    if not body:
        print("Error: Body object not found for export.")
        return False

    try:
        # User provided GUI-based export script
        import FreeCADGui as Gui
        import ImportGui
        
        print("FreeCAD GUI environment detected. Attempting native GLB export via ImportGui...")
        
        __objs__ = [body]
        if hasattr(ImportGui, "exportOptions"):
            options = ImportGui.exportOptions(OUTPUT_PATH)
            ImportGui.export(__objs__, OUTPUT_PATH, options)
        else:
            ImportGui.export(__objs__, OUTPUT_PATH)
            
        print(OUTPUT_FORMAT.upper() + " successfully saved via ImportGui: " + OUTPUT_PATH)
        
    except ImportError:
        print("Headless mode detected (FreeCADCmd). ImportGui not available.")
        print("Falling back to GLTF/STL/OBJ...")
        
        # Fallback to mesh export for headless
        compound = body.Shape
        mesh = MeshPart.meshFromShape(
            Shape=compound, LinearDeflection=0.1, AngularDeflection=0.5, Relative=False
        )
        
        gltf_path = OUTPUT_PATH.replace('.glb', '.gltf').replace('.gltf', '.gltf')
        try:
            mesh.write(gltf_path)
            print("GLTF saved: " + gltf_path)
        except Exception as ge:
            print("GLTF export not supported in headless: " + str(ge))
        
        stl_path = OUTPUT_PATH.replace('.glb', '.stl').replace('.gltf', '.stl')
        mesh.write(stl_path)
        print("STL saved: " + stl_path)
        
        obj_path = OUTPUT_PATH.replace('.glb', '.obj').replace('.gltf', '.obj')
        mesh.write(obj_path)
        print("OBJ saved: " + obj_path)
    except Exception as e:
        print("Export failed: " + str(e))
    
    return True

doc = create_stepped_revolution()
export_model(doc)
'''

def generate_script(output_path, output_format, d_shaft, w_bearing, w_base, h_overall, d_roller):
    if output_path is None:
        output_path = os.path.join(WORKSPACE_DIR, "custom_stepped_revolution." + output_format)
    
    # Mapping UI Dimensions to Sketch Coordinates (Radii and Heights)
    # Original Reference from pully1.py:
    # Radii X: 0 | 13 | 33 | 100.5 | 160.5
    # Heights Y: 0 | 20 | 25 | 32.5 | 45 | 50
    #
    # Current Mappings based on intuition from standard pulley parameters:
    # x1 = Shaft Radius = d_shaft / 2
    # y5 = Bearing Width / 2 (Assuming inner bearing seat starts here, roughly 20 in original) -> Let's map this properly
    # Let's parameterize the 4 steps based on the 5 inputs.
    
    # Radii
    x1 = d_shaft / 2.0                 # Inner Shaft 
    x2 = x1 + 20.0                     # Inner Hub (Approximation, can be parameterized further)
    x3 = w_base                        # Wait, base width as radius? Let's assume w_base is a diameter or radius. Let's say radius.
    x4 = d_roller / 2.0                # Outer Roller Radius
    
    # Heights
    y5 = 20.0                          # Base height (inner)
    y1 = y5 + 5.0                      # Inner Hub height
    y4 = y1 + 7.5                      # Web/Spoke base height
    y3 = y4 + 12.5                     # Outer rim base height
    y2 = h_overall                     # Overall max height
    
    # Ensure logical progression based on FreeCAD sketch logic (Constraints require increasing values or specific orders depending on geometry logic).
    # Since we need a concrete formula, and looking at the original:
    # y1 (0-25) -> y5 (20) in original. The indices in the array match up to:
    # (0,0)->(0,y1) : axis
    # (0,y1)->(x1,y1) : shelf
    # (x1,y1)->(x1,y2) : step up
    # (x1,y2)->(x2,y2) : shelf
    # (x2,y2)->(x2,y3) : step down
    # (x2,y3)->(x3,y3) : shelf
    # (x3,y3)->(x3,y4) : step down
    # (x3,y4)->(x4,y4) : shelf
    # (x4,y4)->(x4,y5) : outer wall drop
    # (x4,y5)->(0,y5) : base return

    # Let's map them properly based on the original sketch's intent!
    # Original:
    # x1=13 (Shaft Dia=26), x2=33 (Hub Dia=66), x3=100.5 (Base Width?), x4=160.5 (Roller Dia=321?)
    # y1=25, y2=50(overall), y3=45, y4=32.5, y5=20(inner base)
    
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
        y1=y1, y2=y2, y3=y3, y4=y4, y5=y5
    )


def run_freecad_script(script_content, use_gui=False):
    if use_gui:
        freecad_exe = find_freecad()
    else:
        freecad_exe = find_freecadcmd()
        if freecad_exe is None:
            freecad_exe = find_freecad()
    
    if freecad_exe is None:
        print("ERROR: FreeCAD not found!")
        return False
    
    import tempfile
    script_path = os.path.join(tempfile.gettempdir(), "_freecad_cad_script.py")
    with open(script_path, 'w', encoding='utf-8') as f:
        f.write(script_content)
    
    try:
        if use_gui:
            subprocess.Popen([freecad_exe, script_path])
        else:
            result = subprocess.run([freecad_exe, script_path], capture_output=True, text=True, timeout=300)
            print("--- FreeCAD Output ---")
            print(result.stdout)
            if result.stderr:
                print("--- FreeCAD Errors ---")
                print(result.stderr)
        return True
    except Exception as e:
        print("Error: " + str(e))
        return False

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="FreeCAD Stepped Revolution with Custom Dimensions")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output file path")
    parser.add_argument("--format", "-f", choices=["glb", "gltf"], default="glb", help="Output format (glb or gltf)")
    parser.add_argument("--gui", action="store_true", help="Open FreeCAD GUI")
    
    # Custom Dimensions
    parser.add_argument("--roller-diameter", type=float, required=True, help="Roller Diameter (D)")
    parser.add_argument("--bearing-width", type=float, required=True, help="Bearing Width (B)")
    parser.add_argument("--shaft-diameter", type=float, required=True, help="Shaft Diameter (d)")
    parser.add_argument("--overall-height", type=float, required=True, help="Overall Height (H)")
    parser.add_argument("--base-width", type=float, required=True, help="Base Width (W)")
    
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
        d_roller=args.roller_diameter
    )
    
    run_freecad_script(script, use_gui=args.gui)
    print("Process complete.")

if __name__ == "__main__":
    main()
