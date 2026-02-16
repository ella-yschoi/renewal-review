from app.config import settings
from app.domain.models.policy import RenewalPair
from app.domain.ports.data_source import DataSourcePort

_data_source: DataSourcePort | None = None


def _get_data_source() -> DataSourcePort:
    global _data_source
    if _data_source is None:
        if settings.db_url:
            from app.adaptor.persistence.db_loader import DbDataSource

            _data_source = DbDataSource()
        else:
            from app.adaptor.persistence.json_loader import JsonDataSource

            _data_source = JsonDataSource()
    return _data_source


def load_pairs(sample: int | None = None) -> list[RenewalPair]:
    return _get_data_source().load_pairs(sample)


def total_count() -> int:
    return _get_data_source().total_count()


def invalidate_cache() -> None:
    _get_data_source().invalidate_cache()
