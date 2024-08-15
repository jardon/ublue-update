import pytest
import sys
import os
from unittest.mock import patch, MagicMock, mock_open

# Add the src directory to the sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from ublue_update.config import find_default_config_file, load_value, Config

@patch('ublue_update.config.log')
@patch('ublue_update.config.os.path.isfile')
def test_find_default_config_file_success_first(mock_isfile, mock_log):
    test_path = "/etc/ublue-update/ublue-update.toml"
    mock_isfile.return_value = True
    
    assert find_default_config_file() == test_path
    mock_isfile.assert_called_once_with(test_path)

@patch('ublue_update.config.log')
@patch('ublue_update.config.os.path.isfile')
def test_find_default_config_file_success_second(mock_isfile, mock_log):
    test_path = "/usr/etc/ublue-update/ublue-update.toml"
    mock_isfile.side_effect = [False, True]
    
    assert find_default_config_file() == test_path
    mock_isfile.call_count == 2

def test_load_value_success():
    dct = {"key":"val"}

    assert load_value(dct, "key") == "val"

def test_load_value_fail():
    dct = {"key":"val"}

    assert load_value(dct, "key2") == None

@patch('ublue_update.config.tomllib.load')
@patch('builtins.open', new_callable=mock_open, read_data='mocked file content')
@patch('ublue_update.config.log.debug')
@patch('ublue_update.config.os.path.abspath')
@patch('ublue_update.config.Config.load_values')
def test_load_config(mock_load_values, mock_abspath, mock_debug, mock_open, mock_load):
    config_path = "/path/to/config.toml"
    fd = 3
    mock_open.return_value = fd
    mock_load.return_value = {"test_key", "test_val"}
    mock_abspath.return_value = config_path

    instance = Config()
    instance.load_config(config_path)

    mock_open.assert_called_once_with(config_path, "rb")
    mock_load.assert_called_once_with(fd)
    mock_abspath.assert_called_once_with(config_path)
    mock_debug.assert_called_once_with(f"Configuration loaded from {config_path}")

@patch('ublue_update.config.find_default_config_file')
@patch('ublue_update.config.tomllib.load')
@patch('builtins.open', new_callable=mock_open, read_data='mocked file content')
@patch('ublue_update.config.log.debug')
@patch('ublue_update.config.os.path.abspath')
@patch('ublue_update.config.Config.load_values')
def test_load_config_default(mock_load_values, mock_abspath, mock_debug, mock_open, mock_load, mock_find_default_config_file):
    config_path = "/etc/ublue-update/ublue-update.toml"
    fd = 3
    mock_find_default_config_file.return_value = config_path
    mock_open.return_value = fd
    mock_load.return_value = {"test_key", "test_val"}
    mock_abspath.return_value = config_path

    instance = Config()
    instance.load_config()

    mock_open.assert_called_once_with(config_path, "rb")
    mock_load.assert_called_once_with(fd)
    mock_abspath.assert_called_once_with(config_path)
    mock_debug.assert_called_once_with(f"Configuration loaded from {config_path}")

@patch('ublue_update.config.load_value')
def test_load_values(mock_load_value):
    config = {"key": "val"}
    mock_load_value.side_effect = [
        False,
        None,
        None,
        None,
        None,
        [],
    ]
    
    instance = Config()
    instance.load_values(config)

    mock_load_value.call_count == 6
    assert instance.dbus_notify == False
    assert instance.custom_check_scripts == []
    mock_load_value.assert_any_call(config, "notify", "dbus_notify")
    mock_load_value.assert_any_call(config, "checks", "network_not_metered")
    mock_load_value.assert_any_call(config, "checks", "min_battery_percent")
    mock_load_value.assert_any_call(config, "checks", "max_cpu_load_percent")
    mock_load_value.assert_any_call(config, "checks", "max_mem_percent")
    mock_load_value.assert_any_call(config, "checks", "scripts")
    