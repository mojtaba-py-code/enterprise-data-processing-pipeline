"""File-based connectors: CSV and JSON readers and writers."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field

from pipeline.connectors.base import Reader, Writer, reader_registry, writer_registry
from pipeline.core.exceptions import ConnectorError


class _PathOptions(BaseModel):
    """Every file connector is addressed by a path and nothing else implicit."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(min_length=1, description="File to read from or write to.")


class CsvReaderOptions(_PathOptions):
    """The ``pandas.read_csv`` keywords a config may set.

    :meth:`CsvReader.read` forwards every option except ``path`` straight to
    pandas, so the accepted set is written down rather than left open: a
    misspelled keyword is then a config error instead of a silently different
    parse. Widening the list is a one-line change here.
    """

    sep: str | None = None
    delimiter: str | None = None
    header: Literal["infer"] | int | list[int] | None = "infer"
    names: list[str] | None = None
    usecols: list[str] | list[int] | None = None
    dtype: str | dict[str, str] | None = None
    encoding: str | None = None
    skiprows: int | list[int] | None = None
    nrows: int | None = None
    na_values: str | list[str] | None = None
    keep_default_na: bool = True
    parse_dates: bool | list[str] | None = None
    index_col: int | str | None = None
    comment: str | None = None
    quotechar: str = '"'
    escapechar: str | None = None
    thousands: str | None = None
    decimal: str = "."
    compression: str | None = "infer"
    on_bad_lines: Literal["error", "warn", "skip"] = "error"


class CsvWriterOptions(_PathOptions):
    """``CsvWriter.write`` reads only ``index``; anything else would be inert."""

    index: bool = False


class JsonReaderOptions(_PathOptions):
    """``JsonReader.read`` reads only ``lines``; anything else would be inert."""

    lines: bool = False


class JsonWriterOptions(_PathOptions):
    """The ``DataFrame.to_json`` keywords a config may set."""

    orient: Literal["records", "columns", "index", "split", "table", "values"] = "records"
    lines: bool = False
    indent: int | None = None


def _require_path(options: dict[str, object], kind: str) -> Path:
    path = options.get("path")
    if not isinstance(path, str) or not path:
        raise ConnectorError(f"{kind} connector requires a non-empty 'path' option.")
    return Path(path)


@reader_registry.register("csv")
class CsvReader(Reader):
    """Read a CSV file into a DataFrame."""

    options_model = CsvReaderOptions

    def read(self) -> pd.DataFrame:
        path = _require_path(self.options, "csv")
        if not path.is_file():
            raise ConnectorError(f"CSV source not found: {path}")
        read_kwargs = {k: v for k, v in self.options.items() if k != "path"}
        try:
            return pd.read_csv(path, **read_kwargs)
        except Exception as exc:  # noqa: BLE001 - normalise to ConnectorError
            raise ConnectorError(f"Failed to read CSV {path}: {exc}") from exc


@writer_registry.register("csv")
class CsvWriter(Writer):
    """Write a DataFrame to a CSV file (creating parent dirs)."""

    options_model = CsvWriterOptions

    def write(self, df: pd.DataFrame) -> None:
        path = _require_path(self.options, "csv")
        path.parent.mkdir(parents=True, exist_ok=True)
        index = bool(self.options.get("index", False))
        try:
            df.to_csv(path, index=index)
        except Exception as exc:  # noqa: BLE001
            raise ConnectorError(f"Failed to write CSV {path}: {exc}") from exc


@reader_registry.register("json")
class JsonReader(Reader):
    """Read a JSON file (records or lines) into a DataFrame."""

    options_model = JsonReaderOptions

    def read(self) -> pd.DataFrame:
        path = _require_path(self.options, "json")
        if not path.is_file():
            raise ConnectorError(f"JSON source not found: {path}")
        lines = bool(self.options.get("lines", False))
        try:
            return pd.read_json(path, lines=lines)
        except Exception as exc:  # noqa: BLE001
            raise ConnectorError(f"Failed to read JSON {path}: {exc}") from exc


@writer_registry.register("json")
class JsonWriter(Writer):
    """Write a DataFrame to a JSON file."""

    options_model = JsonWriterOptions

    def write(self, df: pd.DataFrame) -> None:
        path = _require_path(self.options, "json")
        path.parent.mkdir(parents=True, exist_ok=True)
        orient = str(self.options.get("orient", "records"))
        lines = bool(self.options.get("lines", False))
        indent = self.options.get("indent", 2 if not lines else None)
        try:
            df.to_json(path, orient=orient, lines=lines, indent=indent)
        except Exception as exc:  # noqa: BLE001
            raise ConnectorError(f"Failed to write JSON {path}: {exc}") from exc
