import abc
import logging
import time
from spaceone.core.manager import BaseManager
from spaceone.inventory.plugin.collector.lib import *

from plugin.conf.global_conf import REGION_INFO

_LOGGER = logging.getLogger("spaceone")

__all__ = ["ResourceManager"]


class ResourceManager(BaseManager):
    service = None
    collected_region_codes = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.provider = "google_cloud"
        self.cloud_service_group = ""
        self.cloud_service_type = ""

    def __repr__(self):
        return f"{self.__class__.__name__}({self.cloud_service_group}, {self.cloud_service_type})"

    @classmethod
    def list_managers(cls):
        return cls.__subclasses__()

    @classmethod
    def get_manager_by_service(cls, service):
        for manager in cls.list_managers():
            if manager.service == service:
                yield manager

    def collect_resources(self, options, secret_data, schema):
        project_id = secret_data.get("project_id")
        start_time = time.time()
        _LOGGER.debug(
            f"[START] Collecting {self.__repr__()} (project_id: {project_id})"
        )
        success_count, error_count = [0, 0]
        try:
            yield from self.collect_cloud_service_type()

            cloud_services, total_count = self.collect_cloud_service(
                options, secret_data, schema
            )
            for cloud_service in cloud_services:
                yield cloud_service
            success_count, error_count = total_count

            yield from self.collect_region()

        except Exception as e:
            yield make_error_response(
                error=e,
                provider=self.provider,
                cloud_service_group=self.cloud_service_group,
                cloud_service_type=self.cloud_service_type,
            )

        _LOGGER.debug(
            f"[DONE] {self.__repr__()} Collected Time: {time.time() - start_time:.2f}s, Total Count: {success_count + error_count} (Success: {success_count}, Failure: {error_count})"
        )

    def collect_cloud_service_type(self):
        cloud_service_type = self.create_cloud_service_type()
        yield make_response(
            cloud_service_type=cloud_service_type,
            match_keys=[["name", "group", "provider"]],
            resource_type="inventory.CloudServiceType",
        )

    def collect_cloud_service(self, options, secret_data, schema):
        total_resources = []
        cloud_services, error_resources = self.create_cloud_service(
            options, secret_data, schema
        )
        for cloud_service in cloud_services:
            total_resources.append(
                make_response(
                    cloud_service=cloud_service,
                    match_keys=[
                        [
                            "reference.resource_id",
                            "provider",
                            "cloud_service_type",
                            "cloud_service_group",
                        ]
                    ],
                )
            )
        total_resources.extend(error_resources)
        total_count = [len(cloud_services), len(error_resources)]
        return total_resources, total_count

    def set_region_code(self, region):
        if region not in REGION_INFO:
            region = "global"

        if region not in self.collected_region_codes:
            self.collected_region_codes.append(region)

    def match_region_info(self, region_code):
        match_region_info = REGION_INFO.get(region_code)

        if match_region_info:
            region_info = match_region_info.copy()
            region_info.update(
                {
                    "region_code": region_code,
                    "provider": self.provider,
                }
            )
            return region_info
        return None

    def collect_region(self):
        for region_code in self.collected_region_codes:
            if region := self.match_region_info(region_code):
                yield make_response(
                    region=region,
                    match_keys=[["region_code", "provider"]],
                    resource_type="inventory.Region",
                )

    @staticmethod
    def convert_labels_format(labels):
        convert_labels = []
        for k, v in labels.items():
            convert_labels.append({"key": k, "value": v})
        return convert_labels

    @abc.abstractmethod
    def create_cloud_service_type(self):
        raise NotImplementedError(
            "method `create_cloud_service_type` should be implemented"
        )

    @abc.abstractmethod
    def create_cloud_service(self, options, secret_data, schema):
        raise NotImplementedError("method `create_cloud_service` should be implemented")
