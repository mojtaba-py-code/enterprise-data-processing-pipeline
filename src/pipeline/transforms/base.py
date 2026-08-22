"""Transform abstraction and registry."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

import pandas as pd
from pydantic import BaseModel

from pipeline.core.context import PipelineContext
from pipeline.core.registry import Registry


class Transform(ABC):
    """A pure-ish function ``DataFrame -> DataFrame`` configured by options."""

    #: Pydantic model describing the options this transform accepts. Loading a
    #: config validates ``options`` against it, so a misspelled key fails the
    #: run before the first row is touched.
    options_model: ClassVar[type[BaseModel] | None] = None

    def __init__(self, **options: object) -> None:
        self.options = options

    @abstractmethod
    def apply(self, df: pd.DataFrame, context: PipelineContext) -> pd.DataFrame:
        """Return a new DataFrame with the transform applied."""


transform_registry: Registry[Transform] = Registry("transform")
