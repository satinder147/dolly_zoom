import os
import logging
import configparser
import logging.handlers

config = configparser.ConfigParser()
config.read('config')


def initialize_logging(logger, logging_level):
    file_name = config['logging']['file']
    folder = '/'.join(file_name.split('/')[:-1])
    if folder:
        if not os.path.exists(folder):
            os.makedirs(folder)
    formatter = logging.Formatter(
        fmt='%(asctime)s - %(levelname)s - %(name)s - %(message)s', datefmt='%m/%d/%Y %H:%M:%S')
    logger.setLevel(logging_level)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    file_handler = logging.handlers.RotatingFileHandler\
        (file_name, mode='a', maxBytes=int(config['logging']['max_file_size']) * 1024 * 1024,
         backupCount=int(config['logging']['backup_count']))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
