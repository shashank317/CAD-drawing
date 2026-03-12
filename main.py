import os
import sys
import subprocess
import tempfile
from pathlib import Path

import trimesh
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

app = FastAPI(title="FreeCAD Model Generator")

# --------------- Serve index.html at root ---------------
STATIC_DIR = Path(__file__).resolve().parent / "static"


@app.get("/", response_class=HTMLResponse)
async def serve_index():
    index_file = STATIC_DIR / "index.html"
    return index_file.read_text(encoding="utf-8")


# --------------- Pydantic request model ---------------
class CADParams(BaseModel):
    roller_diameter: float
    bearing_width: float
    shaft_diameter: float
    overall_height: float
    base_width: float


# --------------- Constants ---------------
FREECAD_SCRIPT = r"C:\Users\sumit\FreeCAd scripting\FreeCad\custom_inputs.py"
DRAWING_SCRIPT = str(Path(__file__).resolve().parent / "also drawing.py")
PYTHON_EXE = sys.executable
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
OUTPUT_DIR.mkdir(exist_ok=True)


def _next_output_path() -> Path:
    existing = sorted(
        int(f.stem) for f in OUTPUT_DIR.iterdir()
        if f.is_file() and f.stem.isdigit()
    )
    next_num = (existing[-1] + 1) if existing else 1
    return OUTPUT_DIR / f"{next_num}.glb"


def _run_subprocess_via_logfile(command: list, timeout: int = 300):
    """
    Run a subprocess and capture output via a temp log file instead of a pipe.
    Avoids Windows pipe-buffer deadlocks when FreeCAD.exe writes lots of output.
    Returns (returncode, combined_output_str).
    """
    log_path = os.path.join(tempfile.gettempdir(), "_freecad_server_log.txt")
    with open(log_path, "w", encoding="utf-8") as lf:
        proc = subprocess.run(command, stdout=lf, stderr=lf, timeout=timeout)
    with open(log_path, "r", encoding="utf-8", errors="replace") as lf:
        output = lf.read()
    return proc.returncode, output


# --------------- POST endpoint: 3D model only ---------------
@app.post("/api/generate-cad")
async def generate_cad(params: CADParams):
    output_path = _next_output_path()

    command = [
        PYTHON_EXE, FREECAD_SCRIPT,
        "--roller-diameter", str(params.roller_diameter),
        "--bearing-width",   str(params.bearing_width),
        "--shaft-diameter",  str(params.shaft_diameter),
        "--overall-height",  str(params.overall_height),
        "--base-width",      str(params.base_width),
        "--output",          str(output_path),
    ]

    try:
        returncode, output = _run_subprocess_via_logfile(command, timeout=300)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="FreeCAD process timed out.")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="FreeCAD executable not found.")

    print("=== subprocess output ===")
    print(output)
    print(f"=== return code: {returncode} ===")

    if returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"FreeCAD exited with code {returncode}.\n{output}",
        )

    glb_path  = output_path
    gltf_path = output_path.with_suffix(".gltf")
    stl_path  = output_path.with_suffix(".stl")
    obj_path  = output_path.with_suffix(".obj")

    # Convert STL -> GLB (single binary, no external .bin)
    if not glb_path.exists() and stl_path.exists():
        try:
            mesh = trimesh.load(str(stl_path))
            mesh.export(str(glb_path), file_type="glb")
            print(f"Converted STL to GLB: {glb_path}")
        except Exception as e:
            print(f"GLB conversion failed: {e}")

    if glb_path.exists():
        return FileResponse(str(glb_path), media_type="model/gltf-binary", filename=glb_path.name)
    elif gltf_path.exists():
        return FileResponse(str(gltf_path), media_type="model/gltf+json", filename=gltf_path.name)
    elif stl_path.exists():
        return FileResponse(str(stl_path), media_type="application/octet-stream", filename=stl_path.name)
    elif obj_path.exists():
        return FileResponse(str(obj_path), media_type="application/octet-stream", filename=obj_path.name)
    else:
        raise HTTPException(status_code=500, detail=f"No output file generated.\n{output}")


# --------------- POST endpoint: 3D model + TechDraw PDF/SVG ---------------
@app.post("/api/generate-drawing")
async def generate_drawing(params: CADParams):
    output_path = _next_output_path()

    command = [
        PYTHON_EXE, DRAWING_SCRIPT,
        "--roller-diameter", str(params.roller_diameter),
        "--bearing-width",   str(params.bearing_width),
        "--shaft-diameter",  str(params.shaft_diameter),
        "--overall-height",  str(params.overall_height),
        "--base-width",      str(params.base_width),
        "--output",          str(output_path),
    ]

    try:
        # TechDraw rendering is slow; give it 10 minutes
        returncode, output = _run_subprocess_via_logfile(command, timeout=600)
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="FreeCAD drawing process timed out (600s).")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="FreeCAD executable not found.")

    print("=== drawing subprocess output ===")
    print(output)
    print(f"=== return code: {returncode} ===")

    if returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"FreeCAD exited with code {returncode}.\n{output}",
        )

    # Drawing script outputs:  <stem>_drawing.pdf  and  <stem>_drawing.svg
    base_stem = str(output_path).replace(".glb", "").replace(".gltf", "")
    pdf_path = Path(base_stem + "_drawing.pdf")
    svg_path = Path(base_stem + "_drawing.svg")

    # 3D model files
    glb_path  = output_path
    gltf_path = output_path.with_suffix(".gltf")
    stl_path  = output_path.with_suffix(".stl")

    if not glb_path.exists() and stl_path.exists():
        try:
            mesh = trimesh.load(str(stl_path))
            mesh.export(str(glb_path), file_type="glb")
        except Exception as e:
            print(f"GLB conversion failed: {e}")

    model_file = None
    if glb_path.exists():
        model_file = glb_path.name
    elif gltf_path.exists():
        model_file = gltf_path.name
    elif stl_path.exists():
        model_file = stl_path.name

    return {
        "pdf":    pdf_path.name if pdf_path.exists() else None,
        "svg":    svg_path.name if svg_path.exists() else None,
        "model":  model_file,
        "stdout": output,
    }


# --------------- GET: serve output files (GLB, PDF, SVG, STL …) ---------------
@app.get("/api/output/{filename}")
async def serve_output_file(filename: str):
    if "/" in filename or "\\" in filename or ".." in filename:
        raise HTTPException(status_code=400, detail="Invalid filename.")
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found.")
    media_types = {
        ".pdf":    "application/pdf",
        ".svg":    "image/svg+xml",
        ".glb":    "model/gltf-binary",
        ".gltf":   "model/gltf+json",
        ".stl":    "application/octet-stream",
        ".obj":    "application/octet-stream",
        ".fcstd":  "application/octet-stream",
    }
    media_type = media_types.get(file_path.suffix.lower(), "application/octet-stream")
    # PDF and SVG must be served inline so browsers render them in iframes
    inline_types = {".pdf", ".svg"}
    if file_path.suffix.lower() in inline_types:
        return FileResponse(str(file_path), media_type=media_type)
    return FileResponse(str(file_path), media_type=media_type, filename=filename)


# --------------- Static assets ---------------
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")