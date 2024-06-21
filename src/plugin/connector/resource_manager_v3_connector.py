import logging

from plugin.connector import GoogleCloudConnector

__all__ = ["ResourceManagerV3Connector"]

_LOGGER = logging.getLogger("spaceone")


class ResourceManagerV3Connector(GoogleCloudConnector):
    google_client_service = "cloudresourcemanager"
    version = "v3"

    def get_project(self, project_id: str = None):
        project_id = project_id or self.project_id
        result = self.client.projects().get(name=f"projects/{project_id}").execute()
        return result

    def get_folder(self, folder_id):
        return self.client.folders().get(name=folder_id).execute()

    def get_organization(self, organization_id):
        return self.client.organizations().get(name=organization_id).execute()

    def search_organizations(self):
        results = self.client.organizations().search().execute()
        return results.get("organizations", [])

    def search_folders(self):
        results = self.client.folders().search().execute()
        return results.get("folders", [])

    def list_all_projects(self):
        projects = []
        organizations = self.search_organizations()
        for organization in organizations:
            organization_id = organization.get("name")
            projects.extend(self.list_projects(organization_id))

        folders = self.search_folders()
        for folder in folders:
            folder_id = folder.get("name")
            projects.extend(self.list_projects(folder_id))
        return projects

    def list_projects(self, parent):
        result = self.client.projects().list(parent=parent).execute()
        return result.get("projects", [])

    def list_folders(self, parent):
        results = self.client.folders().list(parent=parent).execute()
        return results.get("folders", [])

    def get_project_iam_policies(self, project_id: str = None):
        project_id = project_id or self.project_id
        resource = f"projects/{project_id}"
        body = {"options": {"requestedPolicyVersion": 3}}
        result = self.client.projects().getIamPolicy(resource=resource, body=body).execute()
        return result.get("bindings", [])

    def get_folder_iam_policies(self, resource):
        body = {"options": {"requestedPolicyVersion": 3}}
        result = self.client.folders().getIamPolicy(resource=resource, body=body).execute()
        return result.get("bindings", [])

    def get_organization_iam_policies(self, resource):
        body = {"options": {"requestedPolicyVersion": 3}}
        result = self.client.organizations().getIamPolicy(resource=resource, body=body).execute()
        return result.get("bindings", [])
