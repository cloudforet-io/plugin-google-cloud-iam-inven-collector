import logging
import time
from typing import Generator

from spaceone.core.error import ERROR_REQUIRED_PARAMETER
from spaceone.inventory.plugin.collector.lib.server import CollectorPluginServer
from .manager.base import ResourceManager

app = CollectorPluginServer()

_LOGGER = logging.getLogger("spaceone")


@app.route("Collector.init")
def collector_init(params: dict) -> dict:
    return _create_init_metadata()


@app.route("Collector.collect")
def collector_collect(params: dict) -> Generator[dict, None, None]:
    options = params["options"]
    secret_data = params["secret_data"]
    schema = params.get("schema")
    project_id = secret_data.get("project_id")

    _check_secret_data(secret_data)

    from spaceone.core import utils
    print("secret_data: ", utils.dump_json(secret_data))
    start_time = time.time()
    _LOGGER.debug(
        f"[collector_collect] Start Collecting Cloud Resources (project_id: {project_id})"
    )
    resource_mgrs = ResourceManager.list_managers()
    for resource_mgr in resource_mgrs:
        yield from resource_mgr().collect_resources(options, secret_data, schema)

    _LOGGER.debug(
        f"[collector_collect] Finished Collecting Cloud Resources "
        f"(project_id: {project_id}, duration: {time.time() - start_time:.2f}s)"
    )


def _create_init_metadata() -> dict:
    return {
        "metadata": {
            "supported_resource_type": [
                "inventory.CloudService",
                "inventory.CloudServiceType",
                "inventory.Region",
                "inventory.ErrorResource",
            ],
        }
    }


def _check_secret_data(secret_data: dict) -> None:
    if "type" not in secret_data:
        raise ERROR_REQUIRED_PARAMETER(key="secret_data.type")

    if "private_key_id" not in secret_data:
        raise ERROR_REQUIRED_PARAMETER(key="secret_data.private_key_id")

    if "private_key" not in secret_data:
        raise ERROR_REQUIRED_PARAMETER(key="secret_data.private_key")

    if "client_email" not in secret_data:
        raise ERROR_REQUIRED_PARAMETER(key="secret_data.client_email")

    if "client_id" not in secret_data:
        raise ERROR_REQUIRED_PARAMETER(key="secret_data.client_id")

    if "auth_uri" not in secret_data:
        raise ERROR_REQUIRED_PARAMETER(key="secret_data.auth_uri")

    if "token_uri" not in secret_data:
        raise ERROR_REQUIRED_PARAMETER(key="secret_data.token_uri")

    if "auth_provider_x509_cert_url" not in secret_data:
        raise ERROR_REQUIRED_PARAMETER(key="secret_data.auth_provider_x509_cert_url")

    if "project_id" not in secret_data:
        raise ERROR_REQUIRED_PARAMETER(key="secret_data.project_id")
