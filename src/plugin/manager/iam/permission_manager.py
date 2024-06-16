import logging
from typing import Generator
from spaceone.inventory.plugin.collector.lib import *
from plugin.connector.iam_connector import IAMConnector
from plugin.connector.resource_manager_v1_connector import ResourceManagerV1Connector
from plugin.connector.resource_manager_v3_connector import ResourceManagerV3Connector
from plugin.manager.base import ResourceManager

_LOGGER = logging.getLogger("spaceone")


class PermissionManager(ResourceManager):
    service = "IAM"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cloud_service_group = "IAM"
        self.cloud_service_type = "Permission"
        self.service_code = None
        self.is_primary = True
        self.icon = "iam.svg"
        self.labels = []
        self.metadata_path = "metadata/permission.yaml"
        self.iam_connector = None
        self.rm_v1_connector = None
        self.rm_v3_connector = None
        self.permission_info = {}
        self.service_account_info = {}

    def collect_cloud_services(self, options: dict, secret_data: dict, schema: str) -> Generator[dict, None, None]:
        self.iam_connector = IAMConnector(options, secret_data, schema)
        self.rm_v1_connector = ResourceManagerV1Connector(options, secret_data, schema)
        self.rm_v3_connector = ResourceManagerV3Connector(options, secret_data, schema)

        # Get service account info
        self.get_service_account_info()

        # Get organization permissions
        organizations = self.rm_v3_connector.search_organizations()
        for organization in organizations:
            self.collect_organization_permissions(organization)

        # Get folder permissions
        folders = self.rm_v3_connector.search_folders()
        for folder in folders:
            self.collect_folder_permissions(folder)

        # Get all projects
        projects = self.rm_v1_connector.list_projects()
        for project in projects:
            self.collect_project_permissions(project)

        yield from self.make_permission_info()

    def make_permission_info(self) -> Generator[dict, None, None]:
        for member, permission_info in self.permission_info.items():
            name = permission_info["memberName"]
            project_id = permission_info.get("projectId")

            permission_info["bindingCount"] = len(permission_info["bindings"])

            yield make_cloud_service(
                name=name,
                cloud_service_type=self.cloud_service_type,
                cloud_service_group=self.cloud_service_group,
                provider=self.provider,
                account=project_id,
                data=permission_info,
                region_code="global",
                reference={
                    "resource_id": member,
                },
                data_format="grpc",
            )

    def collect_organization_permissions(self, organization: dict) -> None:
        organization_id = organization.get("name")
        organization_name = organization.get("displayName")
        target = {
            "type": "ORGANIZATION",
            "id": organization_id,
            "name": organization_name,
        }
        bindings = self.rm_v3_connector.get_organization_iam_policies(organization_id)
        for binding in bindings:
            self.parse_binding_info(binding, target)

    def collect_folder_permissions(self, folder: dict) -> None:
        folder_id = folder.get("name")
        folder_name = folder.get("displayName")

        target = {
            "type": "FOLDER",
            "id": folder_id,
            "name": folder_name,
        }
        bindings = self.rm_v3_connector.get_folder_iam_policies(folder_id)
        for binding in bindings:
            self.parse_binding_info(binding, target)

    def collect_project_permissions(self, project: dict) -> None:
        project_id = project.get("projectId")
        project_name = project.get("name")

        target = {
            "type": "PROJECT",
            "id": project_id,
            "name": project_name,
        }

        bindings = self.rm_v3_connector.get_project_iam_policies(project_id)
        for binding in bindings:
            self.parse_binding_info(binding, target)

    def parse_binding_info(self, binding: dict, target: dict) -> None:
        binding_info = {
            "target": target,
        }
        target_type = target.get("type")
        target_name = target.get("name")

        role_id = binding.get("role")
        if role_id.startswith("organizations/"):
            role_details = self.iam_connector.get_organization_role(role_id)
            role_type = "ORGANIZATION"
        elif role_id.startswith("projects/"):
            role_details = self.iam_connector.get_project_role(role_id)
            role_type = "PROJECT"
        else:
            role_details = self.iam_connector.get_role(role_id)
            role_type = "PREDEFINED"

        binding_info["role"] = {
            "id": role_details.get("name"),
            "name": role_details.get("title"),
            "roleType": role_type,
            "description": role_details.get("description"),
            "permissionCount": len(role_details.get("includedPermissions", [])),
        }

        for member in binding.get("members", []):
            member_type, member_id = member.split(":", 1)

            if member not in self.permission_info:
                self.permission_info[member] = {
                    "type": member_type,
                    "memberId": member_id,
                    "memberName": member_id,
                    "bindings": [],
                    "inherited": False,
                    "inheritance": [],
                }

                if member_type == "serviceAccount":
                    if member_id in self.service_account_info:
                        self.permission_info[member]["memberName"] = self.service_account_info[member_id].get("name")
                        self.permission_info[member]["projectId"] = self.service_account_info[member_id].get("projectId")
                    else:
                        self.permission_info[member]["type"] = "googleManagedServiceAccount"

            self.permission_info[member]["bindings"].append(binding_info)

            if target_type in ["ORGANIZATION", "FOLDER"]:
                self.permission_info[member]["inherited"] = True
                if target_name not in self.permission_info[member]["inheritance"]:
                    self.permission_info[member]["inheritance"].append(target_name)

    def get_service_account_info(self):
        # Get all projects
        projects = self.rm_v1_connector.list_projects()
        for project in projects:
            project_id = project["projectId"]
            service_accounts = self.iam_connector.list_service_accounts(project_id)
            for service_account in service_accounts:
                self.service_account_info[service_account["email"]] = {
                    "projectId": project_id,
                    "name": service_account.get("displayName"),
                }
