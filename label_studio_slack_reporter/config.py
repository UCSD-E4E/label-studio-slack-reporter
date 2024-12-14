'''Config
'''
import logging
import logging.handlers
import os
import time
from pathlib import Path

import platformdirs

platform_dirs = platformdirs.PlatformDirs('label_studio_slack_reporter')

IS_DOCKER = os.environ.get('E4E_DOCKER', False)


def get_log_path() -> Path:
    """Retrieves the logging directory

    Returns:
        Path: Log directory
    """
    if IS_DOCKER:
        log_path = Path('/e4e/logs')
    elif 'E4E_LOGS_DIR' in os.environ:
        log_path = Path(os.environ['E4E_LOGS_DIR'])
    else:
        log_path = platform_dirs.user_log_path
    log_path.mkdir(parents=True, exist_ok=True)
    return log_path


def get_data_path() -> Path:
    """Retrieves the data directory

    Returns:
        Path: Data directory
    """
    if IS_DOCKER:
        data_path = Path('/e4e/data')
    elif 'E4E_DATA_DIR' in os.environ:
        data_path = Path(os.environ['E4E_DATA_DIR'])
    else:
        data_path = platform_dirs.user_data_path
    data_path.mkdir(parents=True, exist_ok=True)
    return data_path


def get_cache_path() -> Path:
    """Retrieves the cache path

    Returns:
        Path: Cache path
    """
    if IS_DOCKER:
        cache_path = Path('/e4e/cache')
    elif 'E4E_CACHE_DIR' in os.environ:
        cache_path = Path(os.environ['E4E_CACHE_DIR'])
    else:
        cache_path = platform_dirs.user_cache_path
    cache_path.mkdir(parents=True, exist_ok=True)
    return cache_path


def configure_logging():
    """Configures logging
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)

    log_dest = get_log_path().joinpath('service.log')
    print(f'Logging to "{log_dest.as_posix()}"')

    log_file_handler = logging.handlers.TimedRotatingFileHandler(
        filename=log_dest,
        when='midnight',
        backupCount=5
    )
    log_file_handler.setLevel(logging.DEBUG)

    msg_fmt = '%(asctime)s.%(msecs)03dZ - %(name)s - %(levelname)s - %(message)s'
    root_formatter = logging.Formatter(msg_fmt, datefmt='%Y-%m-%dT%H:%M:%S')
    log_file_handler.setFormatter(root_formatter)
    root_logger.addHandler(log_file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    error_formatter = logging.Formatter(msg_fmt, datefmt='%Y-%m-%dT%H:%M:%S')
    console_handler.setFormatter(error_formatter)
    root_logger.addHandler(console_handler)
    logging.Formatter.converter = time.gmtime

    # logging_levels: Dict[str, str] = get_params(
    #     keys=['logging', 'levels'], default={})
    # for logger_name, level in logging_levels.items():
    #     logger = logging.getLogger(logger_name)
    #     logger.setLevel(logging.getLevelNamesMapping()[level])

    logging.info('Log path: %s', get_log_path())
    logging.info('Data path: %s', get_data_path())
    logging.info('Cache path: %s', get_cache_path())
