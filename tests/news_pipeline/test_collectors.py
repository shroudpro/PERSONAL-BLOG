from datetime import datetime, timezone

from news_pipeline.collectors.api import parse_api_response
from news_pipeline.collectors.feed import parse_feed
from news_pipeline.collectors.html import extract_listing_links, parse_article_page
from news_pipeline.collectors.sitemap import parse_sitemap
from news_pipeline.core.models import SourceConfig


FETCHED_AT = datetime(2026, 10, 3, 4, 0, tzinfo=timezone.utc)


def source_config(method: str = "feed") -> SourceConfig:
    return SourceConfig(
        id="sample",
        name="Sample Source",
        source_type="official",
        homepage="https://example.com/",
        enabled=True,
        priority=1,
        fetch_method=method,
        allowed_domains=("example.com",),
        default_tags=("AI",),
        language="en",
        item_url_patterns=(r"/news/",),
    )


def test_parse_rss_feed_keeps_snippet_and_media_metadata() -> None:
    xml = b'''<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
      <channel><title>Sample</title><item>
        <title>New model</title><link>https://example.com/news/model?utm_source=rss</link>
        <guid>model</guid><pubDate>Fri, 02 Oct 2026 12:00:00 +0000</pubDate>
        <description><![CDATA[<p>A <b>short</b> summary.</p>]]></description>
        <media:content url="https://cdn.example.com/model.jpg" medium="image" />
        <media:thumbnail url="https://cdn.example.com/model-thumb.jpg" />
      </item></channel>
    </rss>'''

    items = parse_feed(xml, source_config(), FETCHED_AT, since_hours=168)

    assert len(items) == 1
    assert items[0].url.endswith("?utm_source=rss")
    assert items[0].canonical_url == "https://example.com/news/model"
    assert items[0].summary_raw == "A short summary."
    assert items[0].image_url == "https://cdn.example.com/model.jpg"
    assert items[0].published_at == "2026-10-02T12:00:00Z"


def test_parse_arxiv_atom_feed() -> None:
    atom = b'''<?xml version="1.0" encoding="UTF-8"?>
    <feed xmlns="http://www.w3.org/2005/Atom">
      <entry><id>https://example.com/abs/2609.12345</id><title>  A Research Paper  </title>
        <published>2026-10-02T10:00:00Z</published><summary>Paper abstract snippet.</summary>
        <author><name>Author One</name></author>
        <category term="cs.AI" />
      </entry>
    </feed>'''

    items = parse_feed(atom, source_config(), FETCHED_AT, since_hours=168)

    assert len(items) == 1
    assert items[0].title == "A Research Paper"
    assert items[0].author == "Author One"
    assert items[0].category_raw == "cs.AI"
    assert items[0].content_text == "Paper abstract snippet."


def test_sitemap_parser_handles_urlsets_and_indexes() -> None:
    urlset = b'''<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <url><loc>https://example.com/news/a</loc><lastmod>2026-10-02</lastmod></url>
    </urlset>'''
    index = b'''<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
      <sitemap><loc>https://example.com/sitemap-news.xml</loc></sitemap>
    </sitemapindex>'''

    entries, children = parse_sitemap(urlset)
    index_entries, index_children = parse_sitemap(index)

    assert entries == [("https://example.com/news/a", "2026-10-02")]
    assert children == []
    assert index_entries == []
    assert index_children == ["https://example.com/sitemap-news.xml"]


def test_html_listing_and_article_metadata_are_extracted() -> None:
    listing = '''<html><body><article><a href="/news/a?utm_source=home">Read story</a></article></body></html>'''
    article = '''<html lang="en"><head>
      <link rel="canonical" href="https://example.com/news/a/">
      <meta property="og:title" content="Canonical title">
      <meta property="og:description" content="A short description.">
      <meta property="og:image" content="https://cdn.example.com/a.png">
      <meta property="article:published_time" content="2026-10-02T12:00:00Z">
    </head><body><h1>Fallback title</h1></body></html>'''

    links = extract_listing_links(listing, source_config("html"))
    item = parse_article_page(article, "https://example.com/news/a", source_config("html"), FETCHED_AT)

    assert links == ["https://example.com/news/a?utm_source=home"]
    assert item.title == "Canonical title"
    assert item.canonical_url == "https://example.com/news/a"
    assert item.image_alt is None
    assert item.image_url == "https://cdn.example.com/a.png"
    assert item.summary_raw == "A short description."


def test_api_collector_uses_configured_json_field_mapping() -> None:
    source = SourceConfig(
        **{
            **source_config("api").__dict__,
            "api_items_path": "data.items",
            "api_field_map": {
                "title": "headline",
                "url": "url",
                "published_at": "published",
                "summary": "description",
            },
        }
    )
    payload = {
        "data": {
            "items": [
                {
                    "headline": "API item",
                    "url": "https://example.com/news/api-item",
                    "published": "2026-10-02T12:00:00Z",
                    "description": "API summary",
                }
            ]
        }
    }

    items = parse_api_response(payload, source, FETCHED_AT, since_hours=168)

    assert len(items) == 1
    assert items[0].title == "API item"
    assert items[0].summary_raw == "API summary"
