"""Proxy manager for outgoing scraper requests.

Supports HTTP, HTTPS, and SOCKS5 proxies.  Multiple proxies can be supplied
as a comma-separated string in ``SHOPSERP_PROXY_URL`` and will be rotated in
round-robin order.
"""

from __future__ import annotations

import itertools
import logging
from typing import Iterator

logger = logging.getLogger(__name__)

# Type alias expected by ``httpx.AsyncClient(proxy=...)``
ProxyDict = dict[str, str]


class ProxyManager:
    """Manage and rotate a pool of proxy URLs.

    Args:
        proxy_url: One or more proxy URLs separated by commas.  Each URL must
            include the scheme (``http://``, ``https://``, or ``socks5://``).
            Pass ``None`` or an empty string to disable proxying.
    """

    _SUPPORTED_SCHEMES = ("http://", "https://", "socks5://")

    def __init__(self, proxy_url: str | None = None) -> None:
        self._proxies: list[str] = []
        self._cycle: Iterator[str] | None = None

        if proxy_url:
            raw_list = [p.strip() for p in proxy_url.split(",") if p.strip()]
            for url in raw_list:
                if not any(url.lower().startswith(s) for s in self._SUPPORTED_SCHEMES):
                    logger.warning(
                        "Skipping proxy with unsupported scheme: %s", url
                    )
                    continue
                self._proxies.append(url)

            if self._proxies:
                self._cycle = itertools.cycle(self._proxies)
                logger.info(
                    "ProxyManager initialised with %d proxy/proxies", len(self._proxies)
                )
            else:
                logger.info("No valid proxies supplied -- direct connections will be used")
        else:
            logger.info("ProxyManager initialised without proxies")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def has_proxies(self) -> bool:
        """Return ``True`` when at least one valid proxy is available."""
        return bool(self._proxies)

    @property
    def proxy_count(self) -> int:
        """Return the number of configured proxies."""
        return len(self._proxies)

    def get_proxy(self) -> str | None:
        """Return the next proxy URL for use with ``httpx.AsyncClient``.

        Returns ``None`` when no proxies are configured, which tells httpx to
        make a direct connection.

        Usage::

            proxy_url = manager.get_proxy()
            async with httpx.AsyncClient(proxy=proxy_url) as client:
                ...
        """
        if self._cycle is None:
            return None
        proxy = next(self._cycle)
        logger.debug("Selected proxy: %s", _mask_credentials(proxy))
        return proxy

    def get_proxy_dict(self) -> ProxyDict | None:
        """Return a mapping suitable for the deprecated ``proxies=`` kwarg.

        Provided for backward-compatibility with libraries that still expect a
        dict of ``{"http://": ..., "https://": ...}``.
        """
        proxy = self.get_proxy()
        if proxy is None:
            return None
        return {"http://": proxy, "https://": proxy}


def _mask_credentials(url: str) -> str:
    """Mask user:password in a proxy URL for safe logging."""
    try:
        if "@" in url:
            scheme_end = url.index("://") + 3
            at_pos = url.index("@")
            return url[:scheme_end] + "***:***" + url[at_pos:]
    except ValueError:
        pass
    return url
