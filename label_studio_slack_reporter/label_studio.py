'''Label Studio Interface
'''
import datetime as dt
import json
import logging
from io import BytesIO
from typing import Dict, List, Tuple

from label_studio_sdk.client import LabelStudio
from label_studio_sdk.projects.client_ext import ProjectExt
from label_studio_sdk.types import BaseUser

from label_studio_slack_reporter.metrics import get_counter


class Reporter:
    """Label Studio Report generator
    """

    def __init__(self,
                 url: str,
                 api_key: str,
                 projects: List[int],
                 days: int):
        self.__client = LabelStudio(
            base_url=url, api_key=api_key, timeout=60 * 10  # 10 minutes
        )

        self.__project_ids = projects
        self.__report_days = days
        label_studio_report_errors = get_counter(
            name='label_studio_report_errors',
            documentation='Label Studio Report Generation errors',
            labelnames=['project'],
        )
        label_studio_report_errors.clear()
        self.__log = logging.getLogger('Label Studio')

    def get_project_export(self, project_id: int) -> Dict:
        """Retrieves the project export

        Args:
            project_id (int): Project to export

        Returns:
            Dict: LabelStudio project export
        """
        self.__log.debug('Beginning Export for Project %s', project_id)

        response = self.__client.projects.exports.create(
            project_id=project_id
        )
        if response.status != 'completed':
            raise RuntimeError('Snapshot failed')

        blob_iterator = self.__client.projects.exports.download(
            project_id=project_id,
            export_pk=response.id
        )
        blob = BytesIO()
        for chunk in blob_iterator:
            blob.write(chunk)
        blob.seek(0)
        return json.load(blob)
        # return json.loads(export.json())

    def get_report(self) -> str:
        """Generates the report

        Returns:
            str: Report
        """
        reports = []
        for idx in self.__project_ids:
            try:
                reports.append(self.get_project_report(idx))
            except Exception as exc:  # pylint: disable=broad-exception-caught
                get_counter('label_studio_report_errors').labels(
                    project=idx).inc()
                self.__log.exception('Report generation failed due to %s', exc)

        return '\n\n'.join(reports)

    def calculate_recent_annotations(self,
                                     timestamps: Dict[int, List[dt.datetime]],
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
        now = dt.datetime.now()
        total_annotations = sum(len(t) for t in timestamps.values())
        relative_annotations = {
            user_id: sum(1 for timestamp in timestamps if now -
                         timestamp <= dt.timedelta(days))
            for user_id, timestamps in timestamps.items()
        }

        relative_total = sum(relative_annotations.values())
        if relative_total > 0:
            estimated_days = (total_tasks - total_annotations) / \
                (relative_total / days)
        else:
            estimated_days = float('inf')
        return relative_total, estimated_days

    def get_project_report(self, project_id: int) -> str:
        """Generates the report for the given project

        Args:
            project_id (int): Project ID

        Returns:
            str: Project report
        """
        export = self.get_project_export(project_id)
        user_list = self.__client.users.list()
        project_info = self.__client.projects.get(id=project_id)
        annotations_count: Dict[int, int] = {user.id: 0 for user in user_list}
        annotations_timestamp: Dict[int, List[dt.datetime]] = {
            user.id: [] for user in user_list}
        for task in export:
            for annotation in task['annotations']:
                annotations_count[annotation['completed_by']] += 1
                annotation_time = dt.datetime.strptime(
                    annotation['created_at'].rstrip('Z'), '%Y-%m-%dT%H:%M:%S.%f')
                annotations_timestamp[annotation['completed_by']].append(
                    annotation_time)

        recent_annotations, estimated_days = self.calculate_recent_annotations(
            timestamps=annotations_timestamp,
            total_tasks=project_info.task_number,
            days=self.__report_days)

        message = self.generate_message(
            user_list,
            project_info,
            annotations_count,
            recent_annotations,
            estimated_days,
            self.__report_days)
        return message

    def generate_message(self,
                         user_list: List[BaseUser],
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
        # pylint: disable=too-many-arguments,too-many-positional-arguments
        message = f'Results for {project_info.title}\n'
        for user in sorted(user_list, key=lambda x: annotations_count[x.id], reverse=True):
            if not user.id in annotations_count:
                count = 0
            else:
                count = annotations_count[user.id]
            if count > 0:
                message += f'{user.email}: {count}\n'

        message += f'Total: {sum(annotations_count.values())}\n'
        message += f'Estimated time to completion: {estimated_days:.1f} days\n'
        message += f'{recent_annotations} annotations were made in the last {days * 24} hours'
        return message
