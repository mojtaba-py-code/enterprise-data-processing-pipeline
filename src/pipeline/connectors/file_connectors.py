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
    pandas, so this is an allow-list, not a hint: a keyword absent from it is
    a config error rather than a silently different parse. That makes the list
    load-bearing in both directions — it has to be narrow enough to catch a
    typo and wide enough for a real CSV, so it covers the ordinary parsing,
    typing, row-selection, missing-value and number/date keywords below, and
    the README reproduces it in full.

    What is missing is missing deliberately, on one rule: an option may
    describe the data, never reach past it.

    * ``converters`` (and, on pandas 2.x, ``date_parser``) take callables. A
      config file in this project can never execute Python, and an allow-list
      that admitted a callable would hand that back.
    * ``usecols``, ``skiprows`` and ``on_bad_lines`` also accept callables in
      pandas; the types below are narrow enough to refuse those forms while
      keeping the useful ones.
    * ``storage_options`` carries filesystem credentials and aims the read at
      a remote host — the clearest case of reaching past the data.
    * ``iterator`` and ``chunksize`` make ``read_csv`` return a reader rather
      than a DataFrame, which breaks this connector's contract halfway
      through a run: exactly the failure the allow-list exists to prevent.
    * ``dialect`` names an object in the ``csv`` module instead of describing
      the file, and everything it can set is already reachable through
      ``sep``, ``quotechar``, ``quoting``, ``doublequote``, ``escapechar``,
      ``lineterminator`` and ``skipinitialspace``.
    * ``memory_map`` tunes how the file handle is opened, not how the bytes
      are parsed; a config that wants it is describing the host, not the data.

    Widening the list is still a one-line change — but it is a change to the
    README's documented set as well, which must stay identical to this one.
    """

    # Delimiting and quoting.
    sep: str | None = None
    delimiter: str | None = None
    quotechar: str = '"'
    quoting: int = Field(default=0, ge=0, le=3, description="A csv.QUOTE_* constant.")
    doublequote: bool = True
    escapechar: str | None = None
    lineterminator: str | None = None
    skipinitialspace: bool = False

    # Columns, headers and dtypes.
    header: Literal["infer"] | int | list[int] | None = "infer"
    names: list[str] | None = None
    usecols: list[str] | list[int] | None = None
    index_col: int | str | None = None
    dtype: str | dict[str, str] | None = None
    dtype_backend: Literal["numpy_nullable", "pyarrow"] | None = None
    true_values: list[str] | None = None
    false_values: list[str] | None = None

    # Which rows are read at all.
    skiprows: int | list[int] | None = None
    skipfooter: int = 0
    nrows: int | None = None
    skip_blank_lines: bool = True
    comment: str | None = None
    on_bad_lines: Literal["error", "warn", "skip"] = "error"

    # Missing values.
    na_values: str | list[str] | None = None
    keep_default_na: bool = True
    na_filter: bool = True

    # Numbers and dates.
    thousands: str | None = None
    decimal: str = "."
    float_precision: Literal["high", "legacy", "round_trip"] | None = None
    parse_dates: bool | list[str] | None = None
    date_format: str | dict[str, str] | None = None
    dayfirst: bool = False
    cache_dates: bool = True

    # Reading the file itself.
    encoding: str | None = None
    encoding_errors: str = "strict"
    compression: str | None = "infer"
    engine: Literal["c", "python", "pyarrow"] | None = None
    low_memory: bool = True


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
