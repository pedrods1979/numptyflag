import json

from numpty_flag.config import load_config


def test_load_config_from_explicit_path(tmp_path):
    custom = tmp_path / "custom_config.json"
    custom.write_text(json.dumps({"proximity_seconds": 42.0}))

    config = load_config(custom)
    assert config["proximity_seconds"] == 42.0


def test_default_config_has_expected_keys():
    config = load_config()
    assert config["proximity_seconds"] == 5.0
    assert config["numpty_score_min"] == 5.0
    assert config["let_him_go_cooldown_seconds"] == 60
