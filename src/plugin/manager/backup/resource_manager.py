import copy
import fnmatch
import logging
from collections import deque

from spaceone.core.manager import BaseManager
from plugin.connector.resource_manager_v1_connector import (
    ResourceManagerV1Connector,
)
from plugin.connector.resource_manager_v3_connector import (
    ResourceManagerV3Connector,
)

_LOGGER = logging.getLogger("spaceone")


class ProjectResourceManager(BaseManager):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.options = kwargs["options"]
        self.exclude_projects = self.options.get("exclude_projects", [])
        self.exclude_folders = self.options.get("exclude_folders", [])
        self.exclude_folders = [
            str(int(folder_id)) for folder_id in self.exclude_folders
        ]

        self.secret_data = kwargs["secret_data"]
        self.trusted_service_account = self.secret_data["client_email"]

        self.resource_manager_v1_connector = ResourceManagerV1Connector(
            secret_data=self.secret_data
        )
        self.resource_manager_v3_connector = ResourceManagerV3Connector(
            secret_data=self.secret_data
        )
        self.results = []

    def create_project_resource_map(self) -> list:
        """sync Google Cloud resources
            :Returns:
                results [
                {
                    name: 'str',
                    data: 'dict',
                    secret_schema_id: 'str',
                    secret_data: 'dict',
                    tags: 'dict',
                    location: 'list'
                }
        ]
        """
        projects_info = self.resource_manager_v1_connector.list_projects()
        organization_info = self._get_organization_info(projects_info)

        parent = organization_info["name"]

        dq = deque()
        dq.append(
            [
                parent,
                [
                    {
                        "name": organization_info["displayName"],
                        "resource_id": parent,
                        "resource_type": "organization",
                    }
                ],
            ]
        )
        while dq:
            for idx in range(len(dq)):
                parent, current_locations = dq.popleft()
                self._create_project_response(parent, current_locations)

                folders_info = self.resource_manager_v3_connector.list_folders(parent)
                for folder_info in folders_info:
                    folder_parent = folder_info["name"]
                    prefix, folder_id = folder_info["name"].split("/")
                    folder_name = folder_info["displayName"]
                    if folder_id not in self.exclude_folders:
                        parent = folder_parent
                        next_locations = copy.deepcopy(current_locations)
                        next_locations.append(
                            {
                                "name": folder_name,
                                "resource_id": folder_parent,
                                "resource_type": "folder",
                            }
                        )
                        dq.append([parent, next_locations])
        _LOGGER.debug(
            f"[create_project_resource_map] Project Resource Map is created by resource manager API (organization: {organization_info['displayName']}))"
        )
        return self.results

    def _get_organization_info(self, projects_info):
        organization_info = {}
        organization_parent = None
        for project_info in projects_info:
            if organization_info:
                break

            parent = project_info.get("parent")
            if (
                parent
                and parent.get("type") == "organization"
                and not organization_parent
            ):
                organization_parent = f"organizations/{parent['id']}"
                organization_info = self.resource_manager_v3_connector.get_organization(
                    organization_parent
                )

        if not organization_info:
            for folder_info in self.resource_manager_v3_connector.search_folders():
                parent = folder_info.get("parent")
                if parent.startswith("organizations"):
                    organization_parent = parent
                    organization_info = (
                        self.resource_manager_v3_connector.get_organization(
                            organization_parent
                        )
                    )

        if not organization_info:
            raise Exception(
                "[create_project_resource_map] The Organization belonging to this ServiceAccount cannot be found."
            )

        _LOGGER.debug(
            f"[create_project_resource_map] Organization information to collect: {organization_info}"
        )

        return organization_info

    @staticmethod
    def _make_result(project_info, locations):
        project_id = project_info["projectId"]
        project_name = project_info["displayName"]
        result = {
            "name": project_name,
            "project_id": project_id,
            "data": project_info,
            "locations": locations,
        }
        return result

    def _create_project_response(self, parent, locations):
        projects_info = self.resource_manager_v3_connector.list_projects(parent)

        if projects_info:
            for project_info in projects_info:
                project_id = project_info["projectId"]
                project_state = project_info["state"]

                if (
                    self._check_exclude_project(project_id)
                    and project_state == "ACTIVE"
                ):
                    self.results.append(self._make_result(project_info, locations))

    def _check_exclude_project(self, project_id):
        for exclude_project_id in self.exclude_projects:
            if fnmatch.fnmatch(project_id, exclude_project_id):
                return False
        return True
