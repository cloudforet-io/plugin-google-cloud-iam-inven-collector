import copy
import os
import abc
import logging
from typing import List, Type, Generator

from spaceone.core.manager import BaseManager
from spaceone.core import utils
from spaceone.core.error import ERROR_NOT_IMPLEMENTED
from spaceone.inventory.plugin.collector.lib import *

from plugin.conf.global_conf import REGION_INFO, ICON_URL_PREFIX

_LOGGER = logging.getLogger(__name__)
CURRENT_DIR = os.path.dirname(__file__)
METRIC_DIR = os.path.join(CURRENT_DIR, "../metrics/")

__all__ = ["ResourceManager"]


class ResourceManager(BaseManager):
    service = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.provider = "google_cloud"
        self.cloud_service_group = None
        self.cloud_service_type = None
        self.service_code = None
        self.is_primary = False
        self.icon = None
        self.labels = []
        self.metadata_path = None

    def __repr__(self):
        return f"{self.__class__.__name__}"

    def collect_resources(self, options: dict, secret_data: dict, schema: str) -> Generator[dict, None, None]:
        try:
            _LOGGER.debug(f"[{self.__repr__()}.collect_resources] Collect cloud service type: {self.service}")
            yield self.get_cloud_service_type()

            _LOGGER.debug(f"[{self.__repr__()}.collect_resources] Collect cloud services: {self.service}")
            response_iterator = self.collect_cloud_services(options, secret_data, schema)
            for response in response_iterator:
                try:
                    yield make_response(
                        resource_type="inventory.CloudService",
                        cloud_service=response,
                        match_keys=[
                            [
                                "reference.resource_id",
                                "provider",
                                "cloud_service_type",
                                "cloud_service_group",
                            ]
                        ],
                    )
                except Exception as e:
                    _LOGGER.error(f"[{self.__repr__()}.collect_resources] Error: {str(e)}", exc_info=True)
                    yield make_error_response(
                        error=e,
                        provider=self.provider,
                        cloud_service_group=self.cloud_service_group,
                        cloud_service_type=self.cloud_service_type,
                    )

        except Exception as e:
            _LOGGER.error(f"[{self.__repr__()}.collect_resources] Error: {str(e)}", exc_info=True)
            yield make_error_response(
                error=e,
                provider=self.provider,
                cloud_service_group=self.cloud_service_group,
                cloud_service_type=self.cloud_service_type,
            )

    @abc.abstractmethod
    def collect_cloud_services(self, options: dict, secret_data: dict, schema: str) -> Generator[dict, None, None]:
        raise ERROR_NOT_IMPLEMENTED()

    def get_cloud_service_type(self) -> dict:
        cloud_service_type = make_cloud_service_type(
            name=self.cloud_service_type,
            group=self.cloud_service_group,
            provider=self.provider,
            metadata_path=self.metadata_path,
            is_primary=self.is_primary,
            is_major=self.is_primary,
            service_code=self.service_code,
            tags={"spaceone:icon": f"{ICON_URL_PREFIX}/{self.icon}"},
            labels=self.labels,
        )

        # metadata = utils.load_yaml(cloud_service_type["json_metadata"])
        # print(utils.dump_json(metadata, 4))

        return make_response(
            resource_type="inventory.CloudServiceType",
            cloud_service_type=cloud_service_type,
            match_keys=[["name", "group", "provider"]],
        )

    @classmethod
    def collect_regions(cls, region: str = None) -> dict:
        for region_code, region_info in copy.deepcopy(REGION_INFO).items():
            if region is not None and region_code != region:
                continue

            region_info["region_code"] = region_code
            return make_response(
                region=region_info,
                match_keys=[["provider", "region_code"]],
                resource_type="inventory.Region",
            )

    @classmethod
    def collect_metrics(cls, service: str) -> dict:
        for dirname in os.listdir(os.path.join(METRIC_DIR, service)):
            for filename in os.listdir(os.path.join(METRIC_DIR, service, dirname)):
                if filename.endswith(".yaml"):
                    file_path = os.path.join(METRIC_DIR, service, dirname, filename)
                    info = utils.load_yaml_from_file(file_path)
                    if filename == "namespace.yaml":
                        yield make_response(
                            namespace=info,
                            match_keys=[],
                            resource_type="inventory.Namespace",
                        )
                    else:
                        yield make_response(
                            metric=info,
                            match_keys=[],
                            resource_type="inventory.Metric",
                        )

    @classmethod
    def list_managers(cls) -> List[Type["ResourceManager"]]:
        return cls.__subclasses__()

    @classmethod
    def get_manager_by_service(cls, service: str) -> Type["ResourceManager"]:
        for manager in cls.list_managers():
            if manager.service == service:
                return manager

        raise ERROR_NOT_IMPLEMENTED()

    @classmethod
    def get_service_names(cls) -> List[str]:
        services_name = set()
        for sub_cls in cls.__subclasses__():
            services_name.add(sub_cls.service)
        return list(services_name)
