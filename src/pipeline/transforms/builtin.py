"""Built-in, safe transformations.

Every transform is declarative and side-effect free: none of them evaluate
arbitrary user code, so a config file can never execute Python. Rich behaviour
(deriving columns, filtering) is expressed through explicit, bounded options.
"""
from __future__ import annotations

from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, field_validator

from pipeline.core.context import PipelineContext
from pipeline.core.exceptions import TransformError
from pipeline.transforms.base import Transform, transform_registry

_CAST_DTYPES: dict[str, str] = {
    "int": "Int64",
    "float": "float64",
    "str": "string",
    "bool": "boolean",
}


class _TransformOptions(BaseModel):
    """Base for the per-transform option models.

    Each transform owns the schema of its own ``options`` block; the core only
    knows that one exists. Unknown keys are refused here, so a typo in a config
    is an error at load time rather than a transform that quietly does
    something else.
    """

    model_config = ConfigDict(extra="forbid")


def _require_columns(df: pd.DataFrame, columns: list[str], transform: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise TransformError(
            f"{transform}: columns not found in data: {missing}. "
            f"Available: {list(df.columns)}"
        )


class RenameOptions(_TransformOptions):
    columns: dict[str, str] = Field(min_length=1, description="Old name -> new name.")


@transform_registry.register("rename")
class Rename(Transform):
    """Rename columns using an ``old -> new`` mapping."""

    options_model = RenameOptions

    def apply(self, df: pd.DataFrame, context: PipelineContext) -> pd.DataFrame:
        mapping = self.options.get("columns")
        if not isinstance(mapping, dict) or not mapping:
            raise TransformError("rename requires a non-empty 'columns' mapping.")
        _require_columns(df, list(mapping), "rename")
        return df.rename(columns=mapping)


class SelectOptions(_TransformOptions):
    columns: list[str] = Field(min_length=1, description="Columns to keep, in order.")


@transform_registry.register("select")
class Select(Transform):
    """Keep only the listed columns, in order."""

    options_model = SelectOptions

    def apply(self, df: pd.DataFrame, context: PipelineContext) -> pd.DataFrame:
        columns = self.options.get("columns")
        if not isinstance(columns, list) or not columns:
            raise TransformError("select requires a non-empty 'columns' list.")
        _require_columns(df, columns, "select")
        return df[columns].copy()


class DropOptions(_TransformOptions):
    columns: list[str] = Field(min_length=1, description="Columns to remove.")


@transform_registry.register("drop")
class Drop(Transform):
    """Drop the listed columns."""

    options_model = DropOptions

    def apply(self, df: pd.DataFrame, context: PipelineContext) -> pd.DataFrame:
        columns = self.options.get("columns")
        if not isinstance(columns, list) or not columns:
            raise TransformError("drop requires a non-empty 'columns' list.")
        _require_columns(df, columns, "drop")
        return df.drop(columns=columns)


class DropNullsOptions(_TransformOptions):
    columns: list[str] | None = Field(
        default=None, description="Columns to check; all of them if unset."
    )


@transform_registry.register("drop_nulls")
class DropNulls(Transform):
    """Drop rows with nulls, optionally restricted to a subset of columns."""

    options_model = DropNullsOptions

    def apply(self, df: pd.DataFrame, context: PipelineContext) -> pd.DataFrame:
        subset = self.options.get("columns")
        if subset is not None:
            if not isinstance(subset, list):
                raise TransformError("drop_nulls 'columns' must be a list.")
            _require_columns(df, subset, "drop_nulls")
        before = len(df)
        result = df.dropna(subset=subset)
        context.increment("rows_dropped_nulls", before - len(result))
        return result


class FillNaOptions(_TransformOptions):
    values: dict[str, Any] = Field(
        min_length=1, description="Column -> replacement value."
    )


@transform_registry.register("fillna")
class FillNa(Transform):
    """Fill nulls per column using a ``column -> value`` mapping."""

    options_model = FillNaOptions

    def apply(self, df: pd.DataFrame, context: PipelineContext) -> pd.DataFrame:
        values = self.options.get("values")
        if not isinstance(values, dict) or not values:
            raise TransformError("fillna requires a non-empty 'values' mapping.")
        _require_columns(df, list(values), "fillna")
        return df.fillna(value=values)


class CastOptions(_TransformOptions):
    # The accepted types are _CAST_DTYPES plus the separately handled datetime.
    columns: dict[str, Literal["int", "float", "str", "bool", "datetime"]] = Field(
        min_length=1, description="Column -> target type."
    )


@transform_registry.register("cast")
class Cast(Transform):
    """Cast columns to ``int``/``float``/``str``/``bool``/``datetime``."""

    options_model = CastOptions

    def apply(self, df: pd.DataFrame, context: PipelineContext) -> pd.DataFrame:
        columns = self.options.get("columns")
        if not isinstance(columns, dict) or not columns:
            raise TransformError("cast requires a non-empty 'columns' mapping.")
        _require_columns(df, list(columns), "cast")
        result = df.copy()
        for column, target in columns.items():
            result[column] = self._cast_series(result[column], str(target), column)
        return result

    @staticmethod
    def _cast_series(series: pd.Series, target: str, column: str) -> pd.Series:
        if target == "datetime":
            return pd.to_datetime(series, errors="coerce")
        if target in ("int", "float"):
            numeric = pd.to_numeric(series, errors="coerce")
            return numeric.astype(_CAST_DTYPES[target])
        if target in _CAST_DTYPES:
            return series.astype(_CAST_DTYPES[target])
        raise TransformError(
            f"cast: unsupported type '{target}' for column '{column}'. "
            f"Supported: {sorted([*_CAST_DTYPES, 'datetime'])}"
        )


class DedupeOptions(_TransformOptions):
    subset: list[str] | None = Field(
        default=None, description="Key columns; the whole row if unset."
    )
    keep: Literal["first", "last", False] = "first"


@transform_registry.register("dedupe")
class Dedupe(Transform):
    """Drop duplicate rows, optionally keyed by a subset of columns."""

    options_model = DedupeOptions

    def apply(self, df: pd.DataFrame, context: PipelineContext) -> pd.DataFrame:
        subset = self.options.get("subset")
        keep = self.options.get("keep", "first")
        if subset is not None:
            if not isinstance(subset, list):
                raise TransformError("dedupe 'subset' must be a list.")
            _require_columns(df, subset, "dedupe")
        before = len(df)
        result = df.drop_duplicates(subset=subset, keep=keep)
        context.increment("rows_deduplicated", before - len(result))
        return result


_OPS = {
    "==": lambda s, v: s == v,
    "!=": lambda s, v: s != v,
    ">": lambda s, v: pd.to_numeric(s, errors="coerce") > v,
    ">=": lambda s, v: pd.to_numeric(s, errors="coerce") >= v,
    "<": lambda s, v: pd.to_numeric(s, errors="coerce") < v,
    "<=": lambda s, v: pd.to_numeric(s, errors="coerce") <= v,
    "in": lambda s, v: s.isin(v),
    "not_in": lambda s, v: ~s.isin(v),
    "contains": lambda s, v: s.astype("string").str.contains(str(v), na=False),
}


class FilterOptions(_TransformOptions):
    column: str = Field(min_length=1)
    op: str
    value: Any = None

    @field_validator("op")
    @classmethod
    def _known_op(cls, value: str) -> str:
        # Read off _OPS so the config schema cannot drift from the implementation.
        if value not in _OPS:
            raise ValueError(f"op must be one of {sorted(_OPS)}")
        return value


@transform_registry.register("filter")
class Filter(Transform):
    """Keep rows where ``column <op> value`` holds."""

    options_model = FilterOptions

    def apply(self, df: pd.DataFrame, context: PipelineContext) -> pd.DataFrame:
        column = self.options.get("column")
        op = self.options.get("op")
        value: Any = self.options.get("value")
        if not isinstance(column, str):
            raise TransformError("filter requires a string 'column'.")
        if op not in _OPS:
            raise TransformError(f"filter 'op' must be one of {sorted(_OPS)}.")
        _require_columns(df, [column], "filter")
        if op in ("in", "not_in") and not isinstance(value, list):
            raise TransformError(f"filter op '{op}' requires a list 'value'.")
        mask = _OPS[op](df[column], value)
        before = len(df)
        result = df[mask.fillna(False)]
        context.increment("rows_filtered_out", before - len(result))
        return result


class SplitColumnOptions(_TransformOptions):
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    delimiter: str = " "
    index: int = 0


@transform_registry.register("split_column")
class SplitColumn(Transform):
    """Split a string column by a delimiter and take one part into ``target``."""

    options_model = SplitColumnOptions

    def apply(self, df: pd.DataFrame, context: PipelineContext) -> pd.DataFrame:
        source = self.options.get("source")
        target = self.options.get("target")
        delimiter = self.options.get("delimiter", " ")
        index = self.options.get("index", 0)
        if not isinstance(source, str) or not isinstance(target, str):
            raise TransformError("split_column requires string 'source' and 'target'.")
        if not isinstance(index, int):
            raise TransformError("split_column 'index' must be an integer.")
        _require_columns(df, [source], "split_column")
        result = df.copy()
        parts = result[source].astype("string").str.split(str(delimiter))
        result[target] = parts.str.get(index)
        return result


class StrCaseOptions(_TransformOptions):
    columns: list[str] = Field(min_length=1)
    mode: Literal["lower", "upper", "title", "strip"] = "lower"


@transform_registry.register("str_case")
class StrCase(Transform):
    """Apply ``lower``/``upper``/``title``/``strip`` to string columns."""

    options_model = StrCaseOptions

    def apply(self, df: pd.DataFrame, context: PipelineContext) -> pd.DataFrame:
        columns = self.options.get("columns")
        mode = str(self.options.get("mode", "lower"))
        if not isinstance(columns, list) or not columns:
            raise TransformError("str_case requires a non-empty 'columns' list.")
        _require_columns(df, columns, "str_case")
        funcs = {
            "lower": lambda s: s.str.lower(),
            "upper": lambda s: s.str.upper(),
            "title": lambda s: s.str.title(),
            "strip": lambda s: s.str.strip(),
        }
        if mode not in funcs:
            raise TransformError(f"str_case 'mode' must be one of {sorted(funcs)}.")
        result = df.copy()
        for column in columns:
            result[column] = funcs[mode](result[column].astype("string"))
        return result


class AddColumnOptions(_TransformOptions):
    name: str = Field(min_length=1)
    value: Any


@transform_registry.register("add_column")
class AddColumn(Transform):
    """Add a constant-valued column."""

    options_model = AddColumnOptions

    def apply(self, df: pd.DataFrame, context: PipelineContext) -> pd.DataFrame:
        name = self.options.get("name")
        if not isinstance(name, str):
            raise TransformError("add_column requires a string 'name'.")
        if "value" not in self.options:
            raise TransformError("add_column requires a 'value'.")
        result = df.copy()
        result[name] = self.options["value"]
        return result
