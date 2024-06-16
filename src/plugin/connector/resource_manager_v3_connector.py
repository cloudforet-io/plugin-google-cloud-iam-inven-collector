import logging

from plugin.connector import GoogleCloudConnector

__all__ = ["ResourceManagerV3Connector"]

_LOGGER = logging.getLogger(__name__)


class ResourceManagerV3Connector(GoogleCloudConnector):
    google_client_service = "cloudresourcemanager"
    version = "v3"

    def get_project(self, project_id: str = None):
        project_id = project_id or self.project_id
        result = self.client.projects().get(name=f"projects/{project_id}").execute()
        return result

    def get_organization(self, organization_id):
        return self.client.organizations().get(name=organization_id).execute()

    def search_organizations(self):
        results = self.client.organizations().search().execute()
        return results.get("organizations", [])

    def search_folders(self):
        results = self.client.folders().search().execute()
        return results.get("folders", [])

    def list_projects(self, parent):
        result = self.client.projects().list(parent=parent).execute()
        return result.get("projects", [])

    def list_folders(self, parent):
        results = self.client.folders().list(parent=parent).execute()
        return results.get("folders", [])

    def list_project_iam_policies(self, project_id: str = None):
        project_id = project_id or self.project_id
        resource = f"projects/{project_id}"
        result = self.client.projects().getIamPolicy(resource=resource).execute()
        return result.get("bindings", [])

    def list_folder_iam_policies(self, resource):
        result = self.client.folders().getIamPolicy(resource=resource).execute()
        return result.get("bindings", [])

    def list_organization_iam_policies(self, resource):
        result = self.client.organizations().getIamPolicy(resource=resource).execute()
        return result.get("bindings", [])
