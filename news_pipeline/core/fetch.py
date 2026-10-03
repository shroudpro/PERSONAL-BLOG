from __future__ import annotations

import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from threading import Lock
from typing import Callable
from urllib.parse import urljoin, urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import requests

from news_pipeline.core.normalize import is_domain_allowed


class FetchError(RuntimeError):
    def __init__(self, message: str, *, status_code: int | None = None, url: str | None = None):
        super().__init__(message)
        self.status_code = status_code
        self.url = url


class HttpFetcher:
    def __init__(
        self,
        *,
        session: requests.Session | None = None,
        timeout: tuple[float, float] = (5, 15),
        max_retries: int = 2,
        min_interval: float = 1.0,
        user_agent: str = "PERSONAL-BLOG AI News Collector/0.1",
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.session = session or requests.Session()
        self.timeout = timeout
        self.max_retries = max_retries
        self.min_interval = min_interval
        self.user_agent = user_agent
        self.sleep = sleep
        self._robots: dict[str, RobotFileParser] = {}
        self._last_request: dict[str, float] = {}
        self._lock = Lock()

    def _origin(self, url: str) -> str:
        parsed = urlsplit(url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None or parsed.password is not None:
            raise FetchError(f"Unsupported URL: {url}", url=url)
        try:
            port = parsed.port
        except ValueError as exc:
            raise FetchError(f"Unsupported URL: {url}", url=url) from exc
        netloc = parsed.hostname.casefold()
        if port and not ((parsed.scheme == "http" and port == 80) or (parsed.scheme == "https" and port == 443)):
            netloc = f"{netloc}:{port}"
        return urlunsplit((parsed.scheme, netloc, "", "", ""))

    def _validate_url(self, url: str, allowed_domains: tuple[str, ...] | list[str]) -> None:
        try:
            if not is_domain_allowed(url, allowed_domains):
                raise FetchError(f"URL is outside allowed domains: {url}", url=url)
            self._origin(url)
        except ValueError as exc:
            raise FetchError(f"Unsupported URL: {url}", url=url) from exc

    def _wait_for_host(self, host: str, delay: float) -> None:
        with self._lock:
            remaining = delay - (time.monotonic() - self._last_request.get(host, 0.0))
            if remaining > 0:
                self.sleep(remaining)
            self._last_request[host] = time.monotonic()

    def _robots_for(self, url: str) -> RobotFileParser:
        origin = self._origin(url)
        if origin in self._robots:
            return self._robots[origin]

        robots_url = f"{origin}/robots.txt"
        host = urlsplit(origin).hostname or ""
        self._wait_for_host(host, self.min_interval)
        try:
            response = self.session.get(
                robots_url,
                headers={"User-Agent": self.user_agent, "Accept": "text/plain"},
                timeout=self.timeout,
                allow_redirects=False,
            )
        except requests.RequestException as exc:
            raise FetchError(f"Could not read robots.txt for {origin}: {exc}", url=robots_url) from exc

        parser = RobotFileParser()
        parser.set_url(robots_url)
        if response.status_code in {404, 410}:
            parser.parse([])
        elif 200 <= response.status_code < 300:
            parser.parse(response.text.splitlines())
        else:
            raise FetchError(
                f"robots.txt returned HTTP {response.status_code} for {origin}",
                status_code=response.status_code,
                url=robots_url,
            )
        self._robots[origin] = parser
        return parser

    def _retry_delay(self, response: requests.Response, attempt: int) -> float:
        retry_after = response.headers.get("Retry-After")
        if retry_after:
            try:
                return min(max(float(retry_after), 0.0), 30.0)
            except ValueError:
                try:
                    retry_at = parsedate_to_datetime(retry_after)
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    return min(max((retry_at - datetime.now(timezone.utc)).total_seconds(), 0.0), 30.0)
                except (TypeError, ValueError, OverflowError):
                    pass
        return float(min(2**attempt, 8))

    def get(self, url: str, *, allowed_domains: tuple[str, ...] | list[str]) -> requests.Response:
        redirect_statuses = {301, 302, 303, 307, 308}
        current_url = url
        redirect_count = 0

        while True:
            self._validate_url(current_url, allowed_domains)
            robots = self._robots_for(current_url)
            if not robots.can_fetch(self.user_agent, current_url):
                raise FetchError(f"robots.txt disallows URL: {current_url}", url=current_url)

            origin_host = urlsplit(current_url).hostname or ""
            crawl_delay = robots.crawl_delay(self.user_agent) or 0.0
            delay = max(self.min_interval, float(crawl_delay))
            last_error: Exception | None = None
            response: requests.Response | None = None

            for attempt in range(self.max_retries + 1):
                self._wait_for_host(origin_host, delay)
                try:
                    response = self.session.get(
                        current_url,
                        headers={
                            "User-Agent": self.user_agent,
                            "Accept": "application/atom+xml, application/rss+xml, application/xml, text/html, application/json, */*;q=0.8",
                        },
                        timeout=self.timeout,
                        allow_redirects=False,
                    )
                except requests.RequestException as exc:
                    last_error = exc
                    if attempt >= self.max_retries:
                        break
                    self.sleep(float(min(2**attempt, 8)))
                    continue

                if response.status_code == 429 or 500 <= response.status_code <= 599:
                    if attempt < self.max_retries:
                        self.sleep(self._retry_delay(response, attempt))
                        continue
                break

            if response is None:
                raise FetchError(
                    f"Request failed after retries for {current_url}: {last_error}",
                    url=current_url,
                ) from last_error

            if response.status_code in redirect_statuses:
                location = response.headers.get("Location")
                if not location:
                    raise FetchError(
                        f"HTTP {response.status_code} redirect has no Location for {current_url}",
                        status_code=response.status_code,
                        url=current_url,
                    )
                if redirect_count >= 5:
                    raise FetchError(f"Too many redirects while fetching {url}", url=current_url)

                redirect_url = urljoin(response.url or current_url, location)
                self._validate_url(redirect_url, allowed_domains)
                current_url = redirect_url
                redirect_count += 1
                continue

            if not 200 <= response.status_code < 300:
                raise FetchError(
                    f"HTTP {response.status_code} while fetching {current_url}",
                    status_code=response.status_code,
                    url=current_url,
                )

            # With redirects disabled, response.url must remain the URL whose
            # domain and robots policy were checked before the request.
            self._validate_url(response.url or current_url, allowed_domains)
            if response.url and response.url != current_url:
                raise FetchError(
                    f"Unexpected final response URL after requesting {current_url}: {response.url}",
                    url=response.url,
                )

            content_type = response.headers.get("Content-Type", "").casefold()
            if "text/html" in content_type and "charset=" not in content_type:
                response.encoding = getattr(response, "apparent_encoding", None) or "utf-8"
            return response
