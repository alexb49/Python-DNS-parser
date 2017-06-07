"""
Logger

General purpose logging module.  All logs will come through as info when function Log() is used,
if you would like to add different logging levels to your module import logging and
use Log('message', logging.ERROR) format.

This also handles file rotation and caps the size of the log file.  Both as globals that can be set.
"""

__author__ = 'Sunrise Cobb <scobb@guardiananalytics.com>'


import logging
import logging.handlers
import traceback
import os


# change param for different logging levels and troubleshooting
LOG_LEVEL = logging.INFO

LOGGER = None

# set log file params
DEFAULT_NAME = 'cmdb'
LOG_FILENAME = '%s.log' % DEFAULT_NAME
MAX_BYTES = 1024 * 1024 * 10  # 10MB files
BACKUP_COUNT = 5


def SetupLogger(path, max_bytes=MAX_BYTES, backup_count=BACKUP_COUNT):
  global DEFAULT_NAME, LOG_FILENAME, MAX_BYTES, BACKUP_COUNT

  name = os.path.splitext(os.path.basename(path))[0]

  DEFAULT_NAME = name
  LOG_FILENAME = path
  MAX_BYTES = max_bytes
  BACKUP_COUNT = backup_count


def GetLogger():
  """Sets up logging. Outputs to both stdout and to log file."""
  global LOGGER

  if not LOGGER:
    # format = '%(asctime)-15s %(levelname)-8s %(trace)-5s %(message)s'
    format = '%(asctime)s %(levelname)8s   %(message)s (%(trace)-5s)'

    LOGGER = logging.getLogger(DEFAULT_NAME)
    LOGGER.setLevel(LOG_LEVEL)

    #NOTE: This cannot be assigned to the LOGGER object, or it will ignore the handlers and not log
    formatter = logging.Formatter(format)

    # rotating file
    file_handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT)
    file_handler.setLevel(LOG_LEVEL)
    file_handler.setFormatter(formatter)
    LOGGER.addHandler(file_handler)

    # stdout
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(LOG_LEVEL)
    stream_handler.setFormatter(formatter)
    LOGGER.addHandler(stream_handler)

  return LOGGER


def Log(text, level=logging.INFO, stack=0):
  """Calls GetLogger() for desired default output logs."""
  logger = GetLogger()

  stack_list = traceback.extract_stack()
  (module_name, line_number) = stack_list[-2][:2]
  #module_name = os.path.splitext(module_name)[0]
  module_name = os.path.splitext(os.path.basename(module_name))[0]

  # Get the mini stack!
  if stack > 0:
    mini_stack_list = stack_list[-(stack+1):-1]

    mini_text = ''
    for mini_stack in mini_stack_list:
      if mini_text:
        mini_text += ' -> '

      (stack_name, stack_line_number) = mini_stack[:2]
      stack_name = os.path.splitext(os.path.basename(stack_name))[0]
      mini_text += '%s:%s' % (stack_name, stack_line_number)

    # Add the mini_text to our text, so we see the mini-stack trace
    text += ' (%s)' % mini_text


  logger.log(level, text, extra={'trace':'%s:%s' % (module_name, line_number)})

