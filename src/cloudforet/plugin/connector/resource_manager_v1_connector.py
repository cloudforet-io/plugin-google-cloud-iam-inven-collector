import logging

from cloudforet.plugin.connector.base import GoogleCloudConnector

__all__ = ["ResourceManagerV1Connector"]

_LOGGER = logging.getLogger(__name__)


class ResourceManagerV1Connector(GoogleCloudConnector):
    google_client_service = "cloudresourcemanager"
    version = "v1"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.secret_data = kwargs.get("secret_data", {})

    def list_projects(self):
        result = self.client.projects().list().execute()
        return result.get("projects", [])
