import logging
from spaceone.inventory.plugin.collector.lib import *
from cloudforet.plugin.config.global_conf import ASSET_URL
from cloudforet.plugin.connector.iam_connector import IAMConnector
from cloudforet.plugin.connector.resource_manager_v3_connector import (
    ResourceManagerV3Connector,
)
from cloudforet.plugin.manager import ResourceManager
from cloudforet.plugin.manager.resource_manager import ProjectResourceManager

_LOGGER = logging.getLogger("spaceone")


class IAMManager(ResourceManager):
    service = "IAM"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.cloud_service_group = "IAM"
        self.cloud_service_type = "ServiceAccount"
        self.metadata_path = "plugin/metadata/service_account.yaml"
        self.check_organization_or_folder = []
        self.organization_map = {}
        self.organization_role_map = {}
        self.folder_map = {}
        self.default_roles = []

    def create_cloud_service_type(self):
        return make_cloud_service_type(
            name=self.cloud_service_type,
            group=self.cloud_service_group,
            provider=self.provider,
            metadata_path=self.metadata_path,
            is_primary=True,
            is_major=True,
            service_code="Cloud IAM",
            tags={"spaceone:icon": f"{ASSET_URL}/iam.svg"},
            labels=["Application Integration"],
        )

    def create_cloud_service(self, options, secret_data, schema):
        project_id = secret_data["project_id"]

        project_resource_manager = ProjectResourceManager(
            options=options, secret_data=secret_data, schema=schema
        )
        project_resource_map = project_resource_manager.create_project_resource_map()
        project_count_map = self._create_count_map(project_resource_map)

        iam_connector = IAMConnector(
            options=options, secret_data=secret_data, schema=schema
        )

        self.default_roles = iam_connector.list_roles()

        rm_v3_connector = ResourceManagerV3Connector(
            options=options, secret_data=secret_data, schema=schema
        )

        cloud_services = []
        error_responses = []
        for project_info in project_resource_map:
            if locations := project_info.get("locations", []):
                for location in locations:
                    resource_name = location.get("name")
                    resource_id = location.get("resource_id")
                    resource_type = location.get("resource_type")
                    resource_map_key = f"{resource_id}:{resource_name}"
                    if (
                        resource_type == "organization"
                        and resource_id not in self.check_organization_or_folder
                    ):
                        self.check_organization_or_folder.append(resource_id)
                        self.organization_role_map = (
                            iam_connector.list_organization_roles(resource_id)
                        )
                        org_role_bindings = (
                            rm_v3_connector.list_organization_iam_policies(resource_id)
                        )
                        self.organization_map[
                            resource_map_key
                        ] = self._change_member_format(org_role_bindings)
                    elif (
                        resource_type == "folder"
                        and resource_id not in self.check_organization_or_folder
                    ):
                        self.check_organization_or_folder.append(resource_id)
                        folder_role_bindings = rm_v3_connector.list_folder_iam_policies(
                            resource_id
                        )
                        self.folder_map[resource_map_key] = self._change_member_format(
                            folder_role_bindings
                        )
        _LOGGER.debug(
            f"A map containing role-binding information of Organization and Folder is created"
        )

        for project_info in project_resource_map:
            current_project_id = project_info["project_id"]
            service_accounts = iam_connector.list_service_accounts(current_project_id)

            if service_accounts:
                project_roles = iam_connector.list_project_roles(current_project_id)
                project_iam_polices = rm_v3_connector.list_project_iam_policies(
                    current_project_id
                )
                print(project_iam_polices)
                project_policy_map = self._change_member_format(project_iam_polices)

                for service_account in iam_connector.list_service_accounts(
                    current_project_id
                ):
                    try:
                        name = service_account.get("name")
                        email = service_account.get("email")
                        sa_name, domain = email.split("@")

                        sa_keys = iam_connector.list_service_account_keys(
                            current_project_id, email
                        )

                        if domain.endswith("iam.gserviceaccount.com"):
                            inherit_info = self._check_inherited(email, project_roles)

                            if inherit_info:
                                count_map_matching_key = f"{inherit_info['resourceId']}:{inherit_info['resourceName']}"
                                affected_projects_count = project_count_map.get(
                                    count_map_matching_key, {}
                                ).get("count", 0)
                                affected_projects = project_count_map.get(
                                    count_map_matching_key, {}
                                ).get("projects_info", [])
                            else:
                                affected_projects_count = 0
                                affected_projects = []

                            service_account["display"] = {
                                "inheritInfo": inherit_info,
                                "inheritance": True if inherit_info else False,
                                "resourceType": inherit_info.get(
                                    "resourceType", "project"
                                ),
                                "serviceAccountKeys": sa_keys,
                                "activateKeys": len(sa_keys),
                                "roles": self._create_roles(
                                    project_policy_map[f"serviceAccount:{email}"],
                                    project_roles,
                                ),
                                "affectedProjectsCount": int(affected_projects_count),
                                "affectedProjects": affected_projects,
                            }

                            self.set_region_code("global")

                            print(service_account)
                            print()

                            cloud_services.append(
                                make_cloud_service(
                                    name=email,
                                    cloud_service_type=self.cloud_service_type,
                                    cloud_service_group=self.cloud_service_group,
                                    provider=self.provider,
                                    account=project_id,
                                    data=service_account,
                                    region_code="global",
                                    reference={
                                        "resource_id": name,
                                        "external_link": f"https://console.cloud.google.com/iam-admin/serviceaccounts?project={project_id}",
                                    },
                                )
                            )

                    except Exception as e:
                        _LOGGER.error(f"Error on service account: {service_account}")

                        error_responses.append(
                            make_error_response(
                                error=e,
                                provider=self.provider,
                                cloud_service_group=self.cloud_service_group,
                                cloud_service_type=self.cloud_service_type,
                            )
                        )

        return cloud_services, error_responses

    @staticmethod
    def _create_count_map(project_resource_map):
        count_map = {}
        for project_info in project_resource_map:
            locations = project_info.get("locations", [])

            for location in locations:
                project = project_info.get("data")
                resource_id = location.get("resource_id")
                resource_type = location.get("resource_type")
                resource_name = location.get("name")
                resource_map_key = f"{resource_id}:{resource_name}"
                if resource_map_key not in count_map:
                    count_map[resource_map_key] = {
                        "count": 1,
                        "projects_info": [project],
                        "resource_type": resource_type,
                    }
                else:
                    count_map[resource_map_key]["count"] += 1
                    count_map[resource_map_key]["projects_info"].append(project)
        return count_map

    @staticmethod
    def _change_member_format(role_bindings) -> dict:
        member_map = {}
        for role_binding in role_bindings:
            role = role_binding.get("role")
            members = role_binding.get("members", [])
            for member in members:
                if member not in member_map:
                    member_map[member] = []
                member_map[member].append(role)

        return member_map

    def _check_inherited(self, email, project_roles):
        matching_key = f"serviceAccount:{email}"

        for org_key, org_value in self.organization_map.items():
            resource_id, resource_name = org_key.split(":")

            if matching_key in org_value:
                roles = self._create_roles(org_value[matching_key], project_roles)
                del self.organization_map[org_key]

                return {
                    "resourceId": resource_id,
                    "resourceType": "organization",
                    "resourceName": resource_name,
                    "roles": roles,
                }

        for folder_key, folder_value in self.folder_map.items():
            resource_id, resource_name = folder_key.split(":")

            if matching_key in folder_value:
                roles = self._create_roles(folder_value[matching_key], project_roles)
                del self.folder_map[folder_key]

                return {
                    "resourceId": resource_id,
                    "resourceType": "folder",
                    "resourceName": resource_name,
                    "roles": roles,
                }

        return {}

    def _create_roles(self, roles, project_roles):
        role_list = []
        for role in roles:
            if role.startswith("organization"):
                for org_role in self.organization_role_map:
                    if role == org_role.get("name"):
                        org_role["type"] = "ORGANIZATION ROLE"
                        role_list.append(org_role)
            elif role.startswith("project"):
                for project_role in project_roles:
                    if role == project_role.get("name"):
                        project_role["type"] = "PROJECT ROLE"
                        role_list.append(project_role)
            else:
                for default_role in self.default_roles:
                    if role == default_role.get("name"):
                        default_role["type"] = "MANAGED ROLE"
                        role_list.append(default_role)
        return role_list
