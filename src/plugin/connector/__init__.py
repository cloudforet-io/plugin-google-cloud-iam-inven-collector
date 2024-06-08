import google.oauth2.service_account
import googleapiclient
import googleapiclient.discovery
import logging

from spaceone.core.connector import BaseConnector

_LOGGER = logging.getLogger(__name__)


class GoogleCloudConnector(BaseConnector):
    google_client_service = None
    version = None

    def __init__(self, options: dict, secret_data: dict, schema: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.project_id = secret_data["project_id"]
        self.credentials = (
            google.oauth2.service_account.Credentials.from_service_account_info(
                secret_data
            )
        )

        self.client = googleapiclient.discovery.build(
            self.google_client_service,
            self.version,
            credentials=self.credentials,
        )
