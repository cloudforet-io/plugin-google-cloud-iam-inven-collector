import logging
from typing import Generator
from spaceone.inventory.plugin.collector.lib import *
from plugin.connector.cloud_identity_connector import CloudIdentityConnector
from plugin.connector.resource_manager_v3_connector import ResourceManagerV3Connector
from plugin.manager.base import ResourceManager

_LOGGER = logging.getLogger("spaceone")


class GroupManager(ResourceManager):
    service = "IAM"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cloud_service_group = "IAM"
        self.cloud_service_type = "Group"
        self.service_code = None
        self.is_primary = False
        self.icon = "iam.svg"
        self.labels = []
        self.metadata_path = "metadata/group.yaml"
        self.identity_connector = None
        self.rm_v3_connector = None

    def collect_cloud_services(self, options: dict, secret_data: dict, schema: str) -> Generator[dict, None, None]:
        self.identity_connector = CloudIdentityConnector(options, secret_data, schema)
        self.rm_v3_connector = ResourceManagerV3Connector(options, secret_data, schema)
        for organization in self.rm_v3_connector.search_organizations():
            print(organization)
            customer_id = organization.get('directoryCustomerId')
            groups = self.identity_connector.list_groups(customer_id)
            print(groups)
