import logging
from dateutil.parser import parse
from typing import Generator
from spaceone.inventory.plugin.collector.lib import *
from plugin.connector.iam_connector import IAMConnector
from plugin.connector.resource_manager_v3_connector import ResourceManagerV3Connector
from plugin.connector.logging_connector import LoggingConnector
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
        self.logging_connector = None
        self.location_info = {
            "FOLDER": {},
            "PROJECT": {},
        }

    def collect_cloud_services(
        self, options: dict, secret_data: dict, schema: str
    ) -> Generator[dict, None, None]:
        self.iam_connector = IAMConnector(options, secret_data, schema)
        self.rm_v3_connector = ResourceManagerV3Connector(options, secret_data, schema)
        self.logging_connector = LoggingConnector(
            options=options, secret_data=secret_data, schema=schema
        )

        # Get all projects
        projects = self.rm_v3_connector.list_all_projects()
        if not projects:
            yield from self.collect_service_accounts(secret_data.get("project_id"))
        else:
            for project in projects:
                if project["projectId"].startswith("sys-"):
                    continue

                yield from self.collect_service_accounts(project["projectId"])

    def collect_service_accounts(self, project_id: str) -> Generator[dict, None, None]:
        service_accounts = self.iam_connector.list_service_accounts(project_id)
        for service_account in service_accounts:
            yield self.make_cloud_service_info(service_account, project_id)

    def make_cloud_service_info(self, service_account: dict, project_id: str) -> dict:
        name = service_account.get("displayName")
        email = service_account.get("email")
        resource_id = service_account.get("name")
        unique_id = service_account.get("uniqueId")
        disabled = service_account.get("disabled")
        if disabled:
            service_account["status"] = "DISABLED"
        else:
            service_account["status"] = "ENABLED"
        service_account["lastActivityTime"] = (
            self.logging_connector.get_last_log_entry_timestamp(project_id, email)
        )
        service_account["lastActivityDescription"] = (
            f"Activity log found in the past {self.logging_connector.log_search_period.lower()}"
            if service_account["lastActivityTime"]
            else f"No activity log found in the past {self.logging_connector.log_search_period.lower()}"
        )
        keys = self.get_service_account_keys(email, project_id)
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
                f"project={project_id}",
            },
            # data_format="grpc",
        )

    def get_service_account_keys(self, email: str, project_id: str) -> list:
        keys = self.iam_connector.list_service_account_keys(email, project_id)
        for key in keys:
            key_full_name = key.get("name")
            key["name"] = key_full_name.split("/")[-1]
            key["status"] = "ACTIVE"

            creation_time = key.get("validAfterTime")
            expiration_time = key.get("validBeforeTime")

            if expiration_time:
                if parse(expiration_time) < parse(creation_time):
                    key["status"] = "EXPIRED"

        return keys
