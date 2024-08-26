import logging
import requests

logger = logging.getLogger(__name__)

DEFAULT_HEADERS = {
    "User-Agent": "curl/8.7.1",
    "Accept": "*/*",
    "Connection": "keep-alive",
    "Accept-Encoding": "identity",
}


def get_catalog(REGISTRY_URL):
    # logger.info("Fetching catalog from registry")
    response = requests.get(f"{REGISTRY_URL}/v2/_catalog", headers=DEFAULT_HEADERS)
    response.raise_for_status()
    return response.json().get("repositories", [])


def get_tags(REGISTRY_URL, repository):
    # logger.info(f"Fetching tags for repository: {repository}")
    try:
        response = requests.get(
            f"{REGISTRY_URL}/v2/{repository}/tags/list", headers=DEFAULT_HEADERS
        )
        response.raise_for_status()
        return response.json().get("tags", []) or []
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.error(f"Repository {repository} not found.")
            return []
        else:
            logger.error(f"HTTP error occurred: {str(e)}")
            raise


def get_manifest_size(REGISTRY_URL, repository, tag, seen_layers):
    # logger.info(f"Fetching manifest size for {repository}:{tag}")
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
        total_size_bytes = 0

        for layer in layers:
            layer_digest = layer.get("digest")
            if layer_digest not in seen_layers:
                seen_layers.add(layer_digest)
                total_size_bytes += layer.get("size", 0)

        total_size_gb = total_size_bytes / (1024**3)
        # logger.info(f"Total size for {repository}:{tag} is {total_size_gb:.2f} GB")
        return total_size_gb
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            logger.warning(f"Manifest not found for {repository}:{tag}")
            return 0
        else:
            logger.error(f"HTTP error occurred: {str(e)}")
            raise
    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)}")
        return 0
