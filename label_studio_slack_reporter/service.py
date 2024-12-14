'''Service
'''
from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path
from queue import Empty, Full, Queue
from threading import Event, Thread
from typing import Dict, List

import pycron
from prometheus_client import start_http_server
from tomlkit import parse

from label_studio_slack_reporter.config import configure_logging
from label_studio_slack_reporter.label_studio import Reporter
from label_studio_slack_reporter.metrics import (get_summary,
                                                 system_monitor_thread)
from label_studio_slack_reporter.output import AbstractOutput, SlackOutput


class Service:
    """Main service
    """
    # pylint: disable=too-many-instance-attributes
    OUTPUT_TYPE_MAPPING = {
        'slack': SlackOutput
    }

    def __init__(self,
                 config: Path,
                 debug: bool = False):
        self.stop_event = Event()
        self.__debug = debug

        if not config.is_file():
            raise ValueError('Config path is not a file!')

        with open(config, 'r', encoding='utf-8') as handle:
            self.__config = parse(handle.read())

        self.__job_queue: Queue[List[AbstractOutput]] = Queue(16)

        self.jobs: Dict[str, List[AbstractOutput]] = {}
        self.__log = logging.getLogger('Service')
        self.__configure_schedule()

        self.__scheduler_thread = Thread(target=self.scheduler)
        self.__worker_thread = Thread(target=self.do_jobs)

        self.__reporter = Reporter(
            url=self.__config['label_studio']['url'],
            api_key=self.__config['label_studio']['key'],
            projects=self.__config['label_studio']['project_ids'],
            days=self.__config['label_studio']['report_days'],
        )
        self.__prometheus_port = int(self.__config['prometheus']['port'])

        self.__report_timer = get_summary(
            name='report_generation_duration',
            documentation='Report generation duration',
            unit='second'
        )

        self.__output_timer = get_summary(
            name='output_duration',
            documentation='Output generation duration',
            unit='second',
            labelnames=['job']
        )

    def __configure_schedule(self):
        for output_unit, output_config in self.__config['output'].items():
            if 'schedule' not in output_config:
                raise KeyError(f'Expected schedule in output.{output_unit}')
            if not isinstance(output_config['schedule'], str):
                raise TypeError(f'Expected output.{output_unit}.schedule to be '
                                'a string')
            if 'type' not in output_config:
                raise KeyError(f'Expected type in output.{output_unit}')
            if not isinstance(output_config['type'], str):
                raise TypeError(f'Expected output.{output_unit}.type to be a '
                                'string')
            if output_config['type'] not in self.OUTPUT_TYPE_MAPPING:
                raise ValueError(f'output.{output_unit}.type = '
                                 f'{output_config["type"]} is not a '
                                 'recognized output type')
            job_schedule = output_config['schedule']
            new_jpb = self.OUTPUT_TYPE_MAPPING[output_config['type']](
                job_name=output_unit,
                **output_config)
            if job_schedule not in self.jobs:
                self.jobs[job_schedule] = [new_jpb]
            else:
                self.jobs[job_schedule].append(new_jpb)

    def do_jobs(self):
        """Executes the jobs specified
        """
        while not self.stop_event.is_set():
            try:
                jobs = self.__job_queue.get(timeout=5)
            except Empty:
                continue
            with self.__report_timer.time():
                message = self.__reporter.get_report()
            for job in jobs:
                try:
                    if not self.__debug:
                        with self.__output_timer.labels(job=job.name).time():
                            job.execute(message=message)
                        self.__log.info('Executed %s', job.name)
                except Exception:  # pylint: disable=broad-exception-caught
                    self.__log.exception('Failed to execute %s', job.name)

    def run(self):
        """Main entry point
        """
        start_http_server(port=self.__prometheus_port)
        self.__scheduler_thread.start()
        self.__worker_thread.start()
        system_monitor_thread.start()

        self.__log.info('Running')
        self.stop_event.wait()

        self.__worker_thread.join()
        self.__scheduler_thread.join()

    def scheduler(self):
        """Scheduler thread
        """
        while not self.stop_event.is_set():
            for job_cron, jobs in self.jobs.items():
                if pycron.is_now(job_cron):
                    try:
                        self.__job_queue.put(jobs, timeout=30)
                    except Full:
                        self.__log.critical('Job queue full!', exc_info=True)
            time.sleep(30)


def main():
    """Main entry point
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--debug', action='store_true')

    args = vars(parser.parse_args())
    configure_logging()

    Service(**args).run()


if __name__ == '__main__':
    main()
