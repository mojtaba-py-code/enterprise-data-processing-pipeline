from __future__ import annotations

import json

import pytest

from pipeline.cli import main


def _write_config(tmp_path, out_path):
    cfg = tmp_path / "p.yaml"
    cfg.write_text(
        f"""
name: cli-test
source: {{type: csv, options: {{path: {tmp_path.as_posix()}/in.csv}}}}
sink: {{type: csv, options: {{path: {out_path.as_posix()}}}}}
validation:
  on_error: drop
  schema:
    - {{name: id, type: int, required: true, unique: true}}
""",
        encoding="utf-8",
    )
    (tmp_path / "in.csv").write_text("id\n1\n2\n2\n", encoding="utf-8")
    return cfg


def test_plugins_command(capsys):
    assert main(["plugins"]) == 0
    out = capsys.readouterr().out
    assert "csv" in out and "rename" in out


def test_validate_command(tmp_path, capsys):
    out_path = tmp_path / "out.csv"
    cfg = _write_config(tmp_path, out_path)
    assert main(["validate", "--config", str(cfg)]) == 0
    assert "is valid" in capsys.readouterr().out


def test_run_command_json(tmp_path, capsys):
    out_path = tmp_path / "out.csv"
    cfg = _write_config(tmp_path, out_path)
    assert main(["run", "--config", str(cfg), "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["rows_in"] == 3
    # unique=True flags *both* id=2 rows, so only id=1 remains under drop policy
    assert payload["rows_out"] == 1
    assert payload["rows_rejected"] == 2
    assert out_path.is_file()


def test_run_accepts_a_positional_config(tmp_path, capsys):
    out_path = tmp_path / "out.csv"
    cfg = _write_config(tmp_path, out_path)
    assert main(["run", str(cfg), "--json"]) == 0
    assert json.loads(capsys.readouterr().out)["rows_out"] == 1


def test_validate_accepts_a_positional_config(tmp_path, capsys):
    cfg = _write_config(tmp_path, tmp_path / "out.csv")
    assert main(["validate", str(cfg)]) == 0
    assert "is valid" in capsys.readouterr().out


def test_run_without_a_config_path_returns_error(capsys):
    assert main(["run"]) == 1
    assert "config path is required" in capsys.readouterr().err


def test_config_given_both_ways_returns_error(tmp_path, capsys):
    cfg = _write_config(tmp_path, tmp_path / "out.csv")
    assert main(["validate", str(cfg), "--config", str(cfg)]) == 1
    assert "once" in capsys.readouterr().err


def test_run_missing_config_returns_error(capsys):
    assert main(["run", "--config", "nope.yaml"]) == 1
    assert "error:" in capsys.readouterr().err


def test_no_command_exits():
    with pytest.raises(SystemExit):
        main([])
