import logging
from typing import Generator
from spaceone.inventory.plugin.collector.lib import *
from plugin.connector.iam_connector import IAMConnector
from plugin.connector.resource_manager_v3_connector import ResourceManagerV3Connector
from plugin.manager.base import ResourceManager

_LOGGER = logging.getLogger("spaceone")


class ServiceAccountManager(ResourceManager):
    service = "IAM"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cloud_service_group = "IAM"
        self.cloud_service_type = "ServiceAccount"
        self.service_code = None
        self.is_primary = True
        self.icon = "iam.svg"
        self.labels = []
        self.metadata_path = "metadata/service_account.yaml"
        self.iam_connector = None
        self.rm_v3_connector = None

    def collect_cloud_services(self, options: dict, secret_data: dict, schema: str) -> Generator[dict, None, None]:
        self.iam_connector = IAMConnector(options, secret_data, schema)

        service_accounts = self.iam_connector.list_service_accounts()
        if service_accounts:
            for service_account in service_accounts:
                yield self.make_cloud_service_info(service_account)

    def make_cloud_service_info(self, service_account):
        project_id = self.iam_connector.project_id
        name = service_account.get("displayName")
        email = service_account.get("email")
        resource_id = service_account.get("name")
        unique_id = service_account.get("uniqueId")
        disabled = service_account.get("disabled")
        if disabled:
            service_account["status"] = "DISABLED"
        else:
            service_account["status"] = "ENABLED"

        # Get service account keys
        keys = self.iam_connector.list_service_account_keys(email)
        for key in keys:
            key["name"] = key.get("name").split("/")[-1]

        service_account["keys"] = keys
        service_account["keyCount"] = len(keys)

        return make_cloud_service(
            name=name,
            cloud_service_type=self.cloud_service_type,
            cloud_service_group=self.cloud_service_group,
            provider=self.provider,
            account=project_id,
            data=service_account,
            region_code="global",
            reference={
                "resource_id": resource_id,
                "external_link": f"https://console.cloud.google.com/iam-admin/serviceaccounts/details/{unique_id}?"
                                 f"authuser=2&project={project_id}",
            },
            # data_format="grpc",
        )