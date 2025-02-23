'''Test Config
'''
from typing import Dict

import pytest
import tomlkit

from label_studio_slack_reporter.label_studio import Reporter


@pytest.fixture(name='config')
def config_fixture() -> Dict:
    """Creates a config settings fixture

    Returns:
        Dict: Dictionary of settings
    """
    with open('config.toml', 'r', encoding='utf-8') as handle:
        config = tomlkit.parse(handle.read())
    return config

@pytest.fixture(name='label_studio_fixture')
def create_label_studio_fixture(config: Dict) -> Reporter:
    """Creates a test reporter fixture

    Args:
        config (Dict): Configuration dict

    Returns:
        Reporter: Test reporter
    """
    reporter = Reporter(
        api_key=config['label_studio']['key'],
        url=config['label_studio']['url'],
        projects=config['label_studio']['project_ids'],
        days=config['label_studio']['report_days'],
    )
    return reporter
