import logging


def setup_logging(file_name, file_level=logging.INFO, console_level=logging.INFO, requests_level=logging.CRITICAL):
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Create Console handler
    console_log = logging.StreamHandler()
    console_log.setLevel(console_level)
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
    console_log.setFormatter(formatter)
    logger.addHandler(console_log)

    # Log file
    file_log = logging.FileHandler('%s.log' % (file_name), 'a', encoding='UTF-8')
    file_log.setLevel(file_level)
    formatter = logging.Formatter('%(asctime)s - %(levelname)-8s - %(name)-12s - %(message)s')
    file_log.setFormatter(formatter)
    logger.addHandler(file_log)

    requests_log = logging.getLogger('requests.packages.urllib3')
    requests_log.setLevel(requests_level)

    return logger