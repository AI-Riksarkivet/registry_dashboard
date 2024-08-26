from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import logging
from urllib.parse import urlparse
import uvicorn
from dotenv import load_dotenv
import sys
from app.routes.health import health_router
from app.routes.delete import delete_router
from app.utils import get_catalog, get_tags, get_manifest_size

log_file = "app.log"
logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(log_file)
log_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
file_handler.setFormatter(log_formatter)
logger.addHandler(file_handler)


load_dotenv(override=True)

REGISTRY_URL = os.getenv("REGISTRY_URL")

parsed_url = urlparse(REGISTRY_URL)
REGISTRY_NAME = f"{parsed_url.hostname}:{parsed_url.port}"

logger.info(f"Starting application with REGISTRY_URL={REGISTRY_URL}")

app = FastAPI()


templates = Jinja2Templates(directory="app/templates")


@app.get("/")
async def list_images(request: Request):
    data = []
    total_size_gb = 0.0
    seen_layers = set()
    repositories = get_catalog(REGISTRY_URL)

    for repository in repositories:
        tags = get_tags(REGISTRY_URL, repository)
        if not tags:
            continue
        for tag in tags:
            size = get_manifest_size(REGISTRY_URL, repository, tag, seen_layers)
            total_size_gb += size

            name = repository

            data.append(
                {
                    "name": name,
                    "tag": tag,
                    "size": f"{size:.2f} GB",
                    "size_numeric": size,
                }
            )

    logger.info("Rendering template with image data")
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "data": data,
            "total_size_gb": f"{total_size_gb:.2f} GB",
            "REGISTRY_NAME": REGISTRY_NAME,
        },
    )


app.include_router(
    health_router, prefix="/health", tags=["health"], include_in_schema=True
)
app.include_router(delete_router)


app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    file_path = os.path.join("app", "static", "favicon.ico")
    return FileResponse(file_path)


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    logger.info(f"Starting server on {host}:{port}")
    uvicorn.run("app.main:app", host=host, port=port)
