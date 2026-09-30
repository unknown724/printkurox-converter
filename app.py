import os
import shutil
import subprocess
import tempfile
import uuid
from fastapi import FastAPI, Request, UploadFile, File, HTTPException
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="PrintKurox Cloud Converter", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "PrintKurox-Cloud-Converter",
        "engine": "LibreOffice Headless",
        "platform": "Hugging Face Space (Docker)"
    }

def run_libreoffice_conversion(input_path: str, out_dir: str) -> str:
    """
    Executes headless LibreOffice with an isolated user profile.
    This prevents concurrency locks when multiple users upload at the same time.
    """
    profile_dir = tempfile.mkdtemp(prefix="lo_profile_")
    try:
        cmd = [
            "soffice",
            "--headless",
            f"-env:UserInstallation=file://{profile_dir}",
            "--convert-to", "pdf:writer_pdf_Export",
            "--outdir", out_dir,
            input_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        expected_pdf = os.path.join(out_dir, f"{base_name}.pdf")
        
        if os.path.exists(expected_pdf) and os.path.getsize(expected_pdf) > 200:
            return expected_pdf
        else:
            raise RuntimeError(f"LibreOffice failed: {result.stderr or result.stdout}")
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)

@app.post("/convert")
@app.post("/convert-docx")
async def convert_document(request: Request, file: UploadFile = File(None)):
    work_dir = tempfile.mkdtemp(prefix="conv_")
    try:
        ext = request.query_params.get("ext", "docx").lstrip(".")
        filename = f"document_{uuid.uuid4().hex[:8]}.{ext}"
        input_path = os.path.join(work_dir, filename)

        # 1. Handle multipart upload (if file provided via form-data)
        if file is not None:
            with open(input_path, "wb") as f_out:
                shutil.copyfileobj(file.file, f_out)
        else:
            # 2. Handle raw binary stream (octet-stream from Next.js server route)
            raw_body = await request.body()
            if not raw_body or len(raw_body) < 100:
                raise HTTPException(status_code=400, detail="Empty or invalid document payload")
            with open(input_path, "wb") as f_out:
                f_out.write(raw_body)

        # Execute conversion
        pdf_path = run_libreoffice_conversion(input_path, work_dir)

        with open(pdf_path, "rb") as f_pdf:
            pdf_bytes = f_pdf.read()

        out_name = f"{os.path.splitext(filename)[0]}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{out_name}"',
                "Content-Length": str(len(pdf_bytes)),
                "X-Converted-By": "PrintKurox-HuggingFace-LibreOffice",
                "Access-Control-Allow-Origin": "*",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
