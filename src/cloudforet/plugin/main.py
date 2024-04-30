import logging
import time

from spaceone.inventory.plugin.collector.lib.server import CollectorPluginServer

from cloudforet.plugin.manager import ResourceManager

app = CollectorPluginServer()

_LOGGER = logging.getLogger("spaceone")


@app.route("Collector.init")
def collector_init(params: dict) -> dict:
    return _create_init_metadata()


@app.route("Collector.verify")
def collector_verify(params: dict) -> None:
    pass


@app.route("Collector.collect")
def collector_collect(params: dict) -> dict:
    options = params["options"]
    secret_data = params["secret_data"]
    schema = params.get("schema")

    start_time = time.time()
    _LOGGER.debug(
        f"[START] Start collecting all cloud resources (project_id: {secret_data.get('project_id')})"
    )
    resource_mgrs = ResourceManager.list_managers()
    for manager in resource_mgrs:
        results = manager().collect_resources(options, secret_data, schema)

        for result in results:
            yield result
    _LOGGER.debug(
        f"[DONE] All Cloud Resources Collected Time: {time.time() - start_time:.2f}s (project_id: {secret_data.get('project_id')})"
    )


@app.route("Job.get_tasks")
def job_get_tasks(params: dict) -> dict:
    pass


def _create_init_metadata():
    return {
        "metadata": {
            "supported_resource_type": [
                "inventory.CloudService",
                "inventory.CloudServiceType",
                "inventory.Region",
                "inventory.ErrorResource",
            ],
            "options_schema": {},
        }
    }
