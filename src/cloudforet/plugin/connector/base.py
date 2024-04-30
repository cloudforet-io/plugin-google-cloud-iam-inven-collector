import google.oauth2.service_account
import googleapiclient
import googleapiclient.discovery
import logging

from spaceone.core.connector import BaseConnector

_LOGGER = logging.getLogger(__name__)


class GoogleCloudConnector(BaseConnector):
    google_client_service = None
    version = None

    def __init__(self, *args, **kwargs):
        """
        kwargs
            - schema
            - options
            - secret_data

        secret_data(dict)
            - type: ..
            - project_id: ...
            - token_uri: ...
            - ...
        """

        super().__init__(*args, **kwargs)
        secret_data = kwargs.get("secret_data")
        self.project_id = secret_data.get("project_id")
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
