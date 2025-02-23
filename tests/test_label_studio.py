"""Tests Label Studio interface
"""
from typing import Dict

from label_studio_slack_reporter.label_studio import Reporter


def test_get_export(config: Dict, label_studio_fixture: Reporter):
    """Tests running export

    Args:
        config (Dict): Config
        label_studio_fixture (Reporter): Reporter
    """
    export = label_studio_fixture.get_project_export(
        project_id=config['label_studio']['project_ids'][0]
    )
    assert isinstance(export, list)
    assert all(isinstance(task, dict) for task in export)
    assert all('id' in task for task in export)
    assert all('project' in task for task in export)
    assert all(task['project'] == config['label_studio']
               ['project_ids'][0] for task in export)
    assert all('annotations' in task for task in export)
    assert all(isinstance(task['annotations'], list) for task in export)
