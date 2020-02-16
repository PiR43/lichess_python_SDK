import sys
import json
from typing import Any

if sys.version_info >= (3, 7):
    from asyncio import get_running_loop
else:
    from asyncio import get_event_loop
from aiohttp import ClientSession

from lichess_client.helpers import Response, ResponseEntity, ResponseMetadata
from lichess_client.utils.enums import RequestMethods, StatusTypes
from lichess_client.utils.hrefs import ACCOUNT_URL, LICHESS_URL


class BaseClient:
    """
    ASYNC BaseClient class for handling secure connections with Lichess API via token usage.

    Parameters
    ----------
    token: str, required
        String with token provided from Lichess.org account site.

    loop: asyncio event loop, optional
        Asyncio event loop for async mode operations
    """

    def __init__(self, token: str, *, loop=None) -> None:
        self.loop = loop or (get_running_loop() if sys.version_info >= (3, 7) else get_event_loop())
        self._token = token
        self._headers = {'Authorization': f"Bearer {self._token}"}
        self.session = ClientSession(headers=self._headers, loop=self.loop)

    async def request(self, method: 'RequestMethods', url: str, **kwargs: Any) -> 'Response':
        """
        Request async method.

        Parameters
        ----------
        method: RequestMethods, required
            One of REST method, please refer to lichess_client.utils.enums.RequestMethods

        url: str, required
            URL string for REST API endpoint

        Returns
        -------
        aiohttp.client_reqrep.ClientResponse with response details
        """
        async with self.session.request(method=method.value, url=f"{LICHESS_URL}{url}", **kwargs) as resp:
            body = await resp.read()
            try:
                body = json.loads(body)

            except json.decoder.JSONDecodeError:
                body = 'error'

            response = Response(
                metadata=ResponseMetadata(
                    method=resp.method,
                    url=str(resp.url),
                    content_type=resp.content_type,
                    timestamp=resp.raw_headers[1][1]
                ),
                entity=ResponseEntity(
                    code=resp.status,
                    reason=resp.reason,
                    status=StatusTypes.ERROR if 'error' in body else StatusTypes.SUCCESS,
                    content=body
                )
            )
            return response

    async def request_stream(self, method: 'RequestMethods', url: str, **kwargs: Any) -> 'Response':
        """
        Request streaming async method.

        Parameters
        ----------
        method: RequestMethods, required
            One of REST method, please refer to lichess_client.utils.enums.RequestMethods

        url: str, required
            URL string for REST API endpoint

        Returns
        -------
        aiohttp.client_reqrep.ClientResponse with response details
        """
        async with self.session.request(method=method.value, url=f"{LICHESS_URL}{url}", **kwargs) as resp:
            body = []
            async for data, _ in resp.content.iter_chunks():
                if resp.status == 404:
                    break
                data = data.decode('utf-8', errors='strict')
                body.extend([json.loads(entry) for entry in data.split('\n')[:-1]])

            response = Response(
                metadata=ResponseMetadata(
                    method=resp.method,
                    url=str(resp.url),
                    content_type=resp.content_type,
                    timestamp=resp.raw_headers[1][1]
                ),
                entity=ResponseEntity(
                    code=resp.status,
                    reason=resp.reason,
                    status=StatusTypes.ERROR if 'error' in body else StatusTypes.SUCCESS,
                    content=body
                )
            )
            return response

    async def is_authorized(self) -> bool:
        """
        API authorization check.

        Returns
        -------
        bool (True if authorized else False)
        """
        response = await self.request(method=RequestMethods.GET, url=ACCOUNT_URL)
        return True if response.entity.status == StatusTypes.SUCCESS else False
