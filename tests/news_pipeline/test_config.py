from news_pipeline.core.config import load_sources


def test_source_registry_contains_the_ten_planned_sources() -> None:
    sources = load_sources()

    assert [source.id for source in sources] == [
        "openai",
        "anthropic",
        "google-deepmind",
        "google-ai",
        "meta-ai",
        "microsoft-research",
        "nvidia",
        "huggingface",
        "mistral",
        "arxiv",
    ]
    assert sources[5].source_type == "research"
    assert sources[-1].source_type == "research"


def test_all_configured_endpoints_are_within_each_source_allowlist() -> None:
    for source in load_sources():
        assert source.endpoints
