'''Label Studio Slack Reporter
'''
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

from label_studio_sdk.client import LabelStudio
from label_studio_sdk.types import BaseUser
from label_studio_sdk.projects.client_ext import ProjectExt
from slack_sdk import WebClient

# pylint: disable=too-many-locals
def main() -> None:
    """Main Entry Point
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config', type=Path)
    parser.add_argument('-d', '--days', type=int, default=1)
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as handle:
        config_params = json.load(handle)

    ls_client = LabelStudio(
        base_url=config_params['label_studio_url'], api_key=config_params['label_studio_key'])

    project_id = config_params['label_studio_project_id']
    export = get_project_export(ls_client, project_id)
    user_list = ls_client.users.list()
    project_info = ls_client.projects.get(
        id=project_id)
    annotations_count: Dict[int, int] = {user.id: 0 for user in user_list}
    annotations_timestamp: Dict[int, List[datetime]] = {user.id: [] for user in user_list}
    for task in export:
        for annotation in task['annotations']:
            annotations_count[annotation['completed_by']] += 1
            annotation_time = datetime.strptime(
                annotation['created_at'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
            annotations_timestamp[annotation['completed_by']].append(annotation_time)

    recent_annotations, estimated_days = calculate_recent_annotations(
        timestamps=annotations_timestamp, total_tasks=project_info.task_number, days=args.days)

    message = generate_message(user_list, project_info, annotations_count,
                               recent_annotations, estimated_days, args.days)

    slack_client = WebClient(token=config_params['slack_client_secret'])
    slack_client.chat_postMessage(
        channel=config_params['slack_channel_id'],
        text=message
    )

def calculate_recent_annotations(timestamps: Dict[int, List[datetime]],
                                 total_tasks: int,
                                 days: int) -> Tuple[int, float]:
    """Calculates recent annotations

    Args:
        timestamps (Dict[int, List[datetime]]): List of annotation timestamps 
        total_tasks (int): Number of tasks in a project
        days (int): Number of days considered recent

    Returns:
        int: annotations made in the past N days
        float: estimated days to completion
    """
    now = datetime.now()
    total_annotations = sum(len(t) for t in timestamps.values())
    relative_annotations = {
        user_id: sum(1 for timestamp in timestamps if now - timestamp <= timedelta(days))
        for user_id, timestamps in timestamps.items()
    }

    relative_total = sum(relative_annotations.values())
    if relative_total > 0:
        estimated_days = (total_tasks - total_annotations) / (relative_total / days)
    else:
        estimated_days = float('inf')
    return relative_total, estimated_days

# pylint: disable=too-many-arguments, too-many-positional-arguments
def generate_message(user_list: List[BaseUser],
                     project_info: ProjectExt,
                     annotations_count: Dict[int, int],
                     recent_annotations: int,
                     estimated_days: float,
                     days: int) -> str:
    """Generates message

    Args:
        user_list (List[BaseUser]): List of users
        project_info (ProjectExt): Project info
        annotations_count (Dict[int, int]): List of annotations
        recent_annotations (int): Number of annotations made in the past day(s)
        estimated_days (float): Number of days to complete the remaining annotations
        days (int): Number of days considered recent

    Returns:
        str: Formatted message
    """
    message = f'Results for {project_info.title}\n'
    for user in sorted(user_list, key=lambda x: annotations_count[x.id], reverse=True):
        if not user.id in annotations_count:
            count = 0
        else:
            count = annotations_count[user.id]
        message += f'{user.email}: {count}\n'

    message += f'Total: {sum(annotations_count.values())}\n'
    message += f'Estimated time to completion: {estimated_days:.1f} days\n'
    message += f'{recent_annotations} annotations were made in the last {days * 24} hours'
    return message


def get_project_export(ls_client: LabelStudio, project_id: int) -> Dict:
    """Retrieves the project export

    Args:
        ls_client (LabelStudio): LabelStudio client
        project_id (int): Project to export

    Returns:
        Dict: LabelStudio project export
    """
    response = ls_client.projects.exports.create_export(
        id=project_id,
        export_type='JSON',
        download_all_tasks=False,
        download_resources=False
    )
    with TemporaryDirectory() as tmpdir:
        temp_dir = Path(tmpdir)
        temp_file = temp_dir / 'export.json'
        with open(temp_file, 'wb') as handle:
            for blob in response:
                handle.write(blob)
        with open(temp_file, 'r', encoding='utf-8') as handle:
            export = json.load(handle)
    return export


if __name__ == '__main__':
    main()
