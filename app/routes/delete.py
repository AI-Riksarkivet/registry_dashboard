from fastapi import APIRouter, HTTPException
import requests
import os
import logging

logger = logging.getLogger(__name__)

REGISTRY_URL = os.getenv("REGISTRY_URL")
DEFAULT_HEADERS = {
    "User-Agent": "curl/8.7.1",
    "Accept": "*/*",
    "Connection": "keep-alive",
    "Accept-Encoding": "identity",
}

delete_router = APIRouter()


def get_manifest_digest(repository, tag):
    headers = {
        "User-Agent": "curl/8.7.1",
        "Accept": "application/vnd.docker.distribution.manifest.v2+json",
        "Connection": "keep-alive",
        "Accept-Encoding": "identity",
    }

    logger.info(f"Fetching digest for {repository}:{tag}")
    response = requests.get(
        f"{REGISTRY_URL}/v2/{repository}/manifests/{tag}", headers=headers
    )

    logger.info(f"GET {response.url} - Status Code: {response.status_code}")

    if response.status_code == 404:
        logger.error(f"Repository {repository} with tag {tag} not found.")
        return None

    response.raise_for_status()
    digest = response.headers.get("Docker-Content-Digest")
    logger.info(f"Digest for {repository}:{tag} is {digest}")
    return digest


@delete_router.delete("/delete/{repo_name}/{tag}")
async def delete_image(repo_name: str, tag: str):
    try:
        logger.info(f"Received request to delete image: {repo_name}:{tag}")

        digest = get_manifest_digest(repo_name, tag)

        if not digest:
            logger.error(f"Digest not found for {repo_name}:{tag}")
            raise HTTPException(
                status_code=404,
                detail=f"Repository {repo_name} with tag {tag} not found",
            )

        logger.info(f"Deleting {repo_name}:{tag} with digest {digest}")
        delete_response = requests.delete(
            f"{REGISTRY_URL}/v2/{repo_name}/manifests/{digest}",
            headers=DEFAULT_HEADERS,
        )

        logger.info(
            f"DELETE {delete_response.url} - Status Code: {delete_response.status_code}"
        )

        if delete_response.status_code == 202:
            logger.info(f"Image {repo_name}:{tag} deleted successfully")
            return {"message": f"Image {repo_name}:{tag} deleted successfully"}
        elif delete_response.status_code == 404:
            logger.error(f"Failed to delete {repo_name}:{tag} - Not Found")
            raise HTTPException(status_code=404, detail=f"Image not found for deletion")
        else:
            logger.error(
                f"Deletion failed with status code {delete_response.status_code}"
            )
            raise HTTPException(
                status_code=500, detail=f"Deletion is not supported by the registry"
            )

    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP Error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except KeyError:
        logger.error("Failed to retrieve image digest")
        raise HTTPException(status_code=500, detail="Failed to retrieve image digest")
