from __future__ import annotations

import pytest

from pipeline.core.config import load_config, parse_config
from pipeline.core.exceptions import ConfigError

MINIMAL = {
    "name": "t",
    "source": {"type": "csv", "options": {"path": "in.csv"}},
    "sink": {"type": "csv", "options": {"path": "out.csv"}},
}


def test_parse_minimal_config():
    cfg = parse_config(MINIMAL)
    assert cfg.name == "t"
    assert cfg.source.type == "csv"
    assert cfg.validation.on_error == "quarantine"
    assert cfg.observability.log_level == "INFO"


def test_schema_alias_is_populated():
    raw = {**MINIMAL, "validation": {"schema": [{"name": "id", "type": "int"}]}}
    cfg = parse_config(raw)
    assert cfg.validation.schema_[0].name == "id"


def test_pipeline_wrapper_is_unwrapped():
    cfg = parse_config({"pipeline": MINIMAL})
    assert cfg.name == "t"


def test_unknown_field_is_rejected():
    with pytest.raises(ConfigError):
        parse_config({**MINIMAL, "bogus": 1})


def test_known_connector_option_is_accepted():
    raw = {**MINIMAL, "source": {"type": "csv", "options": {"path": "in.csv", "sep": ";"}}}
    cfg = parse_config(raw)
    assert cfg.source.options["sep"] == ";"


def test_unknown_connector_option_is_rejected():
    # 'delimeter' is a plausible typo that pandas would reject at read time,
    # long after the run started.
    raw = {**MINIMAL, "source": {"type": "csv", "options": {"path": "in.csv", "delimeter": ";"}}}
    with pytest.raises(ConfigError, match="delimeter"):
        parse_config(raw)


def test_option_the_connector_would_ignore_is_rejected():
    # JsonReader reads only 'lines'; a csv keyword here used to be dropped in
    # silence, which is the failure mode this guards against.
    raw = {**MINIMAL, "source": {"type": "json", "options": {"path": "in.json", "sep": ";"}}}
    with pytest.raises(ConfigError, match="sep"):
        parse_config(raw)


def test_transform_options_are_validated():
    ok = parse_config(
        {**MINIMAL, "transforms": [{"type": "str_case", "options": {"columns": ["e"]}}]}
    )
    assert ok.transforms[0].options["columns"] == ["e"]

    with pytest.raises(ConfigError, match="mode"):
        parse_config(
            {
                **MINIMAL,
                "transforms": [
                    {"type": "str_case", "options": {"columns": ["e"], "mode": "sideways"}}
                ],
            }
        )


def test_transform_option_error_names_its_position():
    raw = {
        **MINIMAL,
        "transforms": [
            {"type": "select", "options": {"columns": ["a"]}},
            {"type": "filter", "options": {"column": "a", "op": "~~", "value": 1}},
        ],
    }
    with pytest.raises(ConfigError, match=r"transforms\[1\]"):
        parse_config(raw)


def test_unknown_plugin_type_is_rejected():
    with pytest.raises(ConfigError, match="Unknown reader"):
        parse_config({**MINIMAL, "source": {"type": "nosuch", "options": {}}})


def test_bad_log_level_is_rejected():
    with pytest.raises(ConfigError):
        parse_config({**MINIMAL, "observability": {"log_level": "LOUD"}})


def test_missing_file_raises():
    with pytest.raises(ConfigError):
        load_config("does/not/exist.yaml")


def test_load_from_yaml_file(tmp_path):
    path = tmp_path / "p.yaml"
    path.write_text(
        "name: y\n"
        "source: {type: memory, options: {key: a}}\n"
        "sink: {type: memory, options: {key: b}}\n",
        encoding="utf-8",
    )
    cfg = load_config(path)
    assert cfg.name == "y"
    assert cfg.source.options["key"] == "a"
