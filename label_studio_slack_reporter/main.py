'''Label Studio Slack Reporter
'''
import argparse
from pathlib import Path

from tomlkit import parse

from label_studio_slack_reporter.config import configure_logging
from label_studio_slack_reporter.label_studio import Reporter


def main() -> None:
    """Main Entry Point
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path)
    args = parser.parse_args()
    configure_logging()

    with open(args.config, 'r', encoding='utf-8') as handle:
        config = parse(handle.read())

    reporter = Reporter(
        url=config['label_studio']['url'],
        api_key=config['label_studio']['key'],
        projects=config['label_studio']['project_ids'],
        days=config['label_studio']['report_days'],
    )
    print(reporter.get_report())

if __name__ == '__main__':
    main()
