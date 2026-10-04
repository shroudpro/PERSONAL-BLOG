import pytest

from news_pipeline.core.fetch import FetchError, HttpFetcher


class FakeResponse:
    def __init__(self, url: str, status: int = 200, content: bytes = b"ok", text: str | None = None):
        self.url = url
        self.status_code = status
        self.content = content
        self.text = text if text is not None else content.decode("utf-8", errors="replace")
        self.headers = {"Content-Type": "text/plain; charset=utf-8"}


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        response = self.responses.pop(0)
        return response


def test_fetcher_allows_missing_robots_file_and_returns_response() -> None:
    session = FakeSession(
        [
            FakeResponse("https://example.com/robots.txt", status=404),
            FakeResponse("https://example.com/feed.xml", content=b"<rss />"),
        ]
    )
    fetcher = HttpFetcher(session=session, min_interval=0, sleep=lambda _: None)

    response = fetcher.get("https://example.com/feed.xml", allowed_domains=("example.com",))

    assert response.status_code == 200
    assert len(session.calls) == 2
    assert session.calls[-1][1]["headers"]["User-Agent"].startswith("PERSONAL-BLOG")


def test_fetcher_obeys_robots_disallow_without_requesting_page() -> None:
    robots = b"User-agent: *\nDisallow: /private\n"
    session = FakeSession([FakeResponse("https://example.com/robots.txt", content=robots, text=robots.decode())])
    fetcher = HttpFetcher(session=session, min_interval=0, sleep=lambda _: None)

    with pytest.raises(FetchError, match="robots.txt"):
        fetcher.get("https://example.com/private/feed.xml", allowed_domains=("example.com",))

    assert len(session.calls) == 1


def test_fetcher_retries_transient_server_error_once() -> None:
    session = FakeSession(
        [
            FakeResponse("https://example.com/robots.txt", status=404),
            FakeResponse("https://example.com/feed.xml", status=503),
            FakeResponse("https://example.com/feed.xml", content=b"ready"),
        ]
    )
    fetcher = HttpFetcher(session=session, min_interval=0, max_retries=1, sleep=lambda _: None)

    response = fetcher.get("https://example.com/feed.xml", allowed_domains=("example.com",))

    assert response.content == b"ready"
    assert len(session.calls) == 3


def test_fetcher_rejects_redirect_outside_source_domains() -> None:
    session = FakeSession(
        [
            FakeResponse("https://example.com/robots.txt", status=404),
            FakeResponse(
                "https://example.com/feed.xml",
                status=302,
            ),
        ]
    )
    session.responses[1].headers["Location"] = "https://notexample.com/feed.xml"
    fetcher = HttpFetcher(session=session, min_interval=0, sleep=lambda _: None)

    with pytest.raises(FetchError, match="outside allowed domains"):
        fetcher.get("https://example.com/feed.xml", allowed_domains=("example.com",))

    assert [call[0] for call in session.calls] == [
        "https://example.com/robots.txt",
        "https://example.com/feed.xml",
    ]
    assert session.calls[-1][1]["allow_redirects"] is False


def test_fetcher_checks_robots_before_requesting_redirect_target() -> None:
    robots = b"User-agent: *\nDisallow: /private\n"
    redirect = FakeResponse("https://example.com/feed.xml", status=302)
    redirect.headers["Location"] = "/private/feed.xml"
    session = FakeSession(
        [
            FakeResponse("https://example.com/robots.txt", content=robots, text=robots.decode()),
            redirect,
        ]
    )
    fetcher = HttpFetcher(session=session, min_interval=0, sleep=lambda _: None)

    with pytest.raises(FetchError, match="robots.txt disallows"):
        fetcher.get("https://example.com/feed.xml", allowed_domains=("example.com",))

    assert [call[0] for call in session.calls] == [
        "https://example.com/robots.txt",
        "https://example.com/feed.xml",
    ]


def test_fetcher_follows_allowed_redirect_after_checks() -> None:
    redirect = FakeResponse("https://example.com/feed.xml", status=301)
    redirect.headers["Location"] = "/feed/latest.xml"
    session = FakeSession(
        [
            FakeResponse("https://example.com/robots.txt", status=404),
            redirect,
            FakeResponse("https://example.com/feed/latest.xml", content=b"ready"),
        ]
    )
    fetcher = HttpFetcher(session=session, min_interval=0, sleep=lambda _: None)

    response = fetcher.get("https://example.com/feed.xml", allowed_domains=("example.com",))

    assert response.content == b"ready"
    assert [call[0] for call in session.calls] == [
        "https://example.com/robots.txt",
        "https://example.com/feed.xml",
        "https://example.com/feed/latest.xml",
    ]


def test_fetcher_rejects_redirect_outside_allowed_asset_prefix() -> None:
    redirect = FakeResponse("https://cdn.example.com/press/cover.png", status=302)
    redirect.headers["Location"] = "/uploads/cover.png"
    session = FakeSession([
        FakeResponse("https://cdn.example.com/robots.txt", status=404),
        redirect,
    ])
    fetcher = HttpFetcher(session=session, min_interval=0, sleep=lambda _: None)

    with pytest.raises(FetchError, match="outside allowed URL prefixes"):
        fetcher.get(
            "https://cdn.example.com/press/cover.png",
            allowed_domains=("cdn.example.com",),
            allowed_url_prefixes=("https://cdn.example.com/press/",),
            stream=True,
        )

    assert session.calls[-1][1]["stream"] is True
