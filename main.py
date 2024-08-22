from fastapi import FastAPI, Request, HTTPException
from fastapi.templating import Jinja2Templates
import requests
import os
import uvicorn
from dotenv import load_dotenv


load_dotenv()

REGISTRY_URL = os.getenv("REGISTRY_URL")

app = FastAPI()
templates = Jinja2Templates(directory="templates")

DEFAULT_HEADERS = {
    "User-Agent": "curl/8.7.1",
    "Accept": "*/*",
    "Connection": "keep-alive",
    "Accept-Encoding": "identity",
}


def get_catalog():
    response = requests.get(f"{REGISTRY_URL}/v2/_catalog", headers=DEFAULT_HEADERS)
    response.raise_for_status()
    return response.json().get("repositories", [])


def get_tags(repository):
    try:
        response = requests.get(
            f"{REGISTRY_URL}/v2/{repository}/tags/list", headers=DEFAULT_HEADERS
        )
        response.raise_for_status()
        return response.json().get("tags", [])
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            print(f"Repository {repository} not found.")
            return []
        else:
            raise


def get_manifest_size(repository, tag):
    try:
        headers = {
            "User-Agent": "curl/8.7.1",
            "Accept": "application/vnd.docker.distribution.manifest.v2+json",
            "Connection": "keep-alive",
            "Accept-Encoding": "identity",
        }

        response = requests.get(
            f"{REGISTRY_URL}/v2/{repository}/manifests/{tag}", headers=headers
        )
        response.raise_for_status()
        manifest = response.json()

        layers = manifest.get("layers", [])
        total_size_bytes = sum(layer.get("size", 0) for layer in layers)
        total_size_gb = total_size_bytes / (1024**3)

        return total_size_gb
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            return 0
        else:
            raise
    except Exception:
        return 0


def get_manifest_digest(repository, tag):
    headers = {
        "User-Agent": "curl/8.7.1",
        "Accept": "application/vnd.docker.distribution.manifest.v2+json",
        "Connection": "keep-alive",
        "Accept-Encoding": "identity",
    }

    response = requests.get(
        f"{REGISTRY_URL}/v2/{repository}/manifests/{tag}", headers=headers
    )
    response.raise_for_status()
    return response.headers.get("Docker-Content-Digest")


@app.delete("/delete/{repository}/{tag}")
async def delete_image(repository: str, tag: str):
    try:
        # First, get the digest of the manifest you want to delete
        response = requests.head(
            f"{REGISTRY_URL}/v2/{repository}/manifests/{tag}",
            headers={"Accept": "application/vnd.docker.distribution.manifest.v2+json"},
        )
        response.raise_for_status()
        digest = response.headers["Docker-Content-Digest"]

        # Now, delete the manifest by digest
        delete_response = requests.delete(
            f"{REGISTRY_URL}/v2/{repository}/manifests/{digest}",
            headers=DEFAULT_HEADERS,
        )
        if delete_response.status_code == 202:
            return {"message": f"Image {repository}:{tag} deleted successfully"}
        else:
            return {"message": f"Deletion is not supported by the registry"}

    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise HTTPException(status_code=404, detail="Image not found")
        else:
            raise HTTPException(status_code=500, detail=str(e))
    except KeyError:
        raise HTTPException(status_code=500, detail="Failed to retrieve image digest")


@app.get("/")
async def list_images(request: Request):
    data = []
    total_size_gb = 0.0
    repositories = get_catalog()

    for repository in repositories:
        tags = get_tags(repository)
        for tag in tags:
            size = get_manifest_size(repository, tag)
            total_size_gb += size
            data.append(
                {"repository": repository, "tag": tag, "size": f"{size:.2f} GB"}
            )

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "data": data, "total_size_gb": f"{total_size_gb:.2f} GB"},
    )


if __name__ == "__main__":
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host=host, port=port)
