import logging
from typing import Generator
from spaceone.inventory.plugin.collector.lib import *
from plugin.connector.iam_connector import IAMConnector
from plugin.connector.resource_manager_v3_connector import ResourceManagerV3Connector
from plugin.manager.base import ResourceManager

_LOGGER = logging.getLogger("spaceone")


class RoleManager(ResourceManager):
    service = "IAM"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cloud_service_group = "IAM"
        self.cloud_service_type = "Role"
        self.service_code = None
        self.is_primary = False
        self.icon = "iam.svg"
        self.labels = []
        self.metadata_path = "metadata/role.yaml"
        self.iam_connector = None
        self.rm_v3_connector = None

    def collect_cloud_services(
        self, options: dict, secret_data: dict, schema: str
    ) -> Generator[dict, None, None]:
        self.iam_connector = IAMConnector(options, secret_data, schema)
        self.rm_v3_connector = ResourceManagerV3Connector(options, secret_data, schema)
        default_project_id = secret_data.get("project_id")

        # Get all roles
        roles = self.iam_connector.list_roles()
        for role in roles:
            yield self.make_role_info(role, default_project_id, "PREDEFINED")

        # get Organization roles
        organizations = self.rm_v3_connector.search_organizations()
        for organization in organizations:
            yield from self.collect_organization_roles(organization, default_project_id)

        # Get all projects
        projects = self.rm_v3_connector.list_all_projects()
        for project in projects:
            yield from self.collect_project_roles(project["projectId"])

    def collect_organization_roles(
        self, organization: dict, default_project_id: str
    ) -> Generator[dict, None, None]:
        organization_id = organization.get("name")
        organization_name = organization.get("displayName")
        location = f"organizations/{organization_name}"
        roles = self.iam_connector.list_organization_roles(organization_id)
        for role in roles:
            yield self.make_role_info(
                role, default_project_id, "ORGANIZATION", location
            )

    def collect_project_roles(self, project_id: str) -> Generator[dict, None, None]:
        roles = self.iam_connector.list_project_roles(project_id)
        location = f"projects/{project_id}"
        for role in roles:
            yield self.make_role_info(role, project_id, "PROJECT", location)

    def make_role_info(
        self, role: dict, project_id: str, role_type: str, location: str = None
    ) -> dict:
        name = role.get("title")
        role_id = role.get("name")
        role_url = role_id.replace("/", "<")
        role["stage"] = role.get("stage", "ALPHA")

        if role["stage"] == "DISABLED":
            role["status"] = "DISABLED"
        else:
            role["status"] = "ENABLED"

        # Get role details
        if role_type == "PROJECT" or role_type == "ORGANIZATION":
            role["roleType"] = "CUSTOM"
        else:
            role["roleType"] = role_type

        role["includedPermissions"] = role.get("includedPermissions", [])
        role["permissionCount"] = len(role["includedPermissions"])

        return make_cloud_service(
            name=name,
            cloud_service_type=self.cloud_service_type,
            cloud_service_group=self.cloud_service_group,
            provider=self.provider,
            account=location,
            data=role,
            region_code="global",
            reference={
                "resource_id": role_id,
                "external_link": f"https://console.cloud.google.com/iam-admin/roles/details/{role_url}?"
                f"project={project_id}",
            },
            # data_format="grpc",
        )
