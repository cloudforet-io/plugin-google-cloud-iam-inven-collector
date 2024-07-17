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

    def collect_cloud_services(
        self, options: dict, secret_data: dict, schema: str
    ) -> Generator[dict, None, None]:
        self.identity_connector = CloudIdentityConnector(options, secret_data, schema)
        self.rm_v3_connector = ResourceManagerV3Connector(options, secret_data, schema)

        for organization in self.rm_v3_connector.search_organizations():
            yield from self.collect_groups(organization)

    def collect_groups(self, organization: dict) -> Generator[dict, None, None]:
        customer_id = organization.get("directoryCustomerId")
        organization_id = organization.get("name")
        organization_name = organization.get("displayName")
        groups = self.identity_connector.list_groups(customer_id)
        for group in groups:
            yield self.make_group_info(group, organization_id, organization_name)

    def make_group_info(
        self, group: dict, organization_id: str, organization_name: str
    ) -> dict:
        group_id = group.get("name")
        name = group.get("displayName")
        organization_id = organization_id.split("/")[-1]

        group["members"] = self.get_group_members(group_id)
        group["memberCount"] = len(group["members"])

        return make_cloud_service(
            name=name,
            cloud_service_type=self.cloud_service_type,
            cloud_service_group=self.cloud_service_group,
            provider=self.provider,
            account=f"organizations/{organization_name}",
            data=group,
            region_code="global",
            reference={
                "resource_id": group_id,
                "external_link": f"https://console.cloud.google.com/iam-admin/{group_id}?"
                f"orgonly=true&organizationId={organization_id}&supportedpurview=organizationId",
            },
            # data_format="grpc",
        )

    def get_group_members(self, group_id: str) -> list:
        changed_members = []
        members = self.identity_connector.list_memberships(group_id)
        for member in members:
            member_name = member.get("name")
            member_info = self.identity_connector.get_membership(member_name)
            roles = member_info.get("roles", [])
            if len(roles) > 1:
                for role in roles:
                    if role.get("name") != "MEMBER":
                        member_info["role"] = role.get("name")

                member_info["role"] = "MEMBER"
            changed_members.append(member_info)

        return changed_members
