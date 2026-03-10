"""Job collectors – Source-specific job listing scrapers.

Provides a factory function to create the right collector
based on source configuration.
"""

from src.collectors.base_collector import BaseCollector, RawJob
from src.collectors.linkedin_collector import LinkedInCollector
from src.collectors.naukrigulf_collector import NaukriGulfCollector
from src.collectors.generic_collector import GenericCollector

_COLLECTOR_MAP = {
    "linkedin": LinkedInCollector,
    "naukrigulf": NaukriGulfCollector,
}


def get_collector(source_config: dict, page=None) -> BaseCollector:
    """Factory to create the appropriate collector for a source.

    Args:
        source_config: Source configuration dict from sources.json.
        page: Optional Playwright page to reuse.

    Returns:
        A collector instance for the specified source.
    """
    source_name = source_config["name"]
    collector_class = _COLLECTOR_MAP.get(source_name, GenericCollector)
    return collector_class(source_config, page=page)
