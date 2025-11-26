import logging
import os
from time import sleep

import googleapiclient.discovery
import httplib2
import socks
from google_auth_httplib2 import AuthorizedHttp

_LOGGER = logging.getLogger("spaceone")


def api_retry_handler(default_response=None):
    def decorator(method):
        @staticmethod
        def create_http_client():
            https_proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")

            if https_proxy:
                # _LOGGER.info(
                #     f"** Using proxy in environment variable HTTPS_PROXY/https_proxy: {https_proxy}"
                # ) # TOO MANY LOGGING
                try:
                    proxy_url = https_proxy.replace("http://", "").replace(
                        "https://", ""
                    )
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

        def wrapper(self, *args, **kwargs):
            trial = 0
            while trial < 10:
                try:
                    return method(self, *args, **kwargs)
                except Exception as e:
                    _LOGGER.debug(
                        f"{self.__repr__()} Retrying {method.__name__}({args}, {kwargs}, trial={trial + 1}): {str(e)}"
                    )
                    sleep(1 + 0.002**trial)

                    # Proxy HTTP client creation
                    proxy_http = create_http_client()
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

                    trial += 1
            _LOGGER.error(
                f"{self.__repr__()} Failed to {method.__name__}({args}, {kwargs})"
            )
            return default_response

        return wrapper

    return decorator
