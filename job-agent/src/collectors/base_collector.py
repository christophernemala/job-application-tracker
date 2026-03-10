"""Base collector – Abstract interface for all job source collectors.

All source-specific collectors inherit from BaseCollector and implement
the collect() method. This ensures consistent data flow and logging.
"""

import abc
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RawJob:
    """Raw job data as collected from a source before normalization.

    This is the standard output format for all collectors.
    """
    source: str
    title: str
    url: str
    company: Optional[str] = None
    location: Optional[str] = None
    salary_text: Optional[str] = None
    posted_date: Optional[str] = None
    description: Optional[str] = None
    apply_type: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    collected_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> dict:
        """Convert to dictionary for storage."""
        return {
            "source": self.source,
            "title": self.title,
            "url": self.url,
            "company": self.company,
            "location": self.location,
            "salary_text": self.salary_text,
            "posted_date": self.posted_date,
            "description": self.description,
            "apply_type": self.apply_type,
            "metadata": self.metadata,
            "collected_at": self.collected_at,
        }


class BaseCollector(abc.ABC):
    """Abstract base class for job collectors.

    Subclasses must implement collect() which returns a list of RawJob objects.
    """

    def __init__(self, source_config: dict):
        """Initialize with source configuration from sources.json.

        Args:
            source_config: Dict from sources.json for this source.
        """
        self.source_config = source_config
        self.source_name = source_config["name"]
        self.search_urls = source_config.get("search_urls", [])
        self.role_search_strings = source_config.get("role_search_strings", [])
        self.requires_login = source_config.get("requires_login", False)
        self.logger = get_logger(f"collector.{self.source_name}")

    @abc.abstractmethod
    def collect(self) -> list[RawJob]:
        """Collect job listings from the source.

        Returns:
            List of RawJob objects with raw data from the source.
        """
        ...

    def _log_collection_result(self, jobs: list[RawJob]) -> None:
        """Log the result of a collection run."""
        self.logger.info(
            "[%s] Collected %d jobs from %d search URLs",
            self.source_name, len(jobs), len(self.search_urls),
        )
        if jobs:
            titles = [j.title for j in jobs[:5]]
            self.logger.debug("[%s] Sample titles: %s", self.source_name, titles)
