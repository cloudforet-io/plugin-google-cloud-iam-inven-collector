import logging
import os

import google.oauth2.service_account
import googleapiclient
import googleapiclient.discovery
import httplib2
import socks
from google_auth_httplib2 import AuthorizedHttp
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

        proxy_http = self._create_http_client()
        if proxy_http:
            self.client = googleapiclient.discovery.build(
                self.google_client_service,
                self.version,
                http=AuthorizedHttp(
                    self.credentials.with_scopes(
                        [
                            "https://www.googleapis.com/auth/cloud-platform"
                        ]  # FOR PROXY SCOPE SUPPORT
                    ),
                    http=proxy_http,
                ),
            )
        else:
            self.client = googleapiclient.discovery.build(
                self.google_client_service,
                self.version,
                credentials=self.credentials,
            )

    def _create_http_client(self):
        https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

        if https_proxy:
            # _LOGGER.info(
            #     f"** Using proxy in environment variable HTTPS_PROXY/https_proxy: {https_proxy}"
            # ) # TOO MANY LOGGING
            try:
                proxy_url = https_proxy.replace("http://", "").replace("https://", "")
                if ":" in proxy_url:
                    proxy_host, proxy_port = proxy_url.split(":", 1)
                    proxy_port = int(proxy_port)

                proxy_info = httplib2.ProxyInfo(
                    proxy_host=proxy_host,
                    proxy_port=proxy_port,
                    proxy_type=socks.PROXY_TYPE_HTTP,
                )

                return httplib2.Http(
                    proxy_info=proxy_info, disable_ssl_certificate_validation=True
                )
            except Exception as e:
                _LOGGER.warning(
                    f"Failed to configure proxy. Using direct connection.: {e}. "
                )
                return None
        else:
            return None
