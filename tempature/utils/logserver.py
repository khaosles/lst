#!usr/bin/env python
# -*- coding: utf-8 -*-

"""
    @author: khaosles
    @date: 2021/10/23 22:13
"""

import os, sys, re
import logging

class LogServer(object):

    def __init__(self, logFile, loggerName=None):

        # the log dir path
        logPath = os.path.dirname(logFile)
        # if log dir path not exists, create the file path
        if logPath != "" and not os.path.isdir(logPath):
            # create the path
            os.makedirs(logPath)

        # get a logger with the specified name
        if loggerName is None:
            loggerName = self.__whoImportMe()

        # create a logger
        self.logger = logging.getLogger(loggerName)

        # create a file handler
        handler = logging.FileHandler(logFile)
        handler.setLevel(logging.INFO)   # set the switch level of outputting the file log

        # define the format of the handler
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.DEBUG)  # set the global switch level

        # output to console
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.DEBUG)
        self.logger.addHandler(ch)

    def error(self, msg):
        """
        error log
        """
        self.logger.error(msg)
        self.logger.handlers[0].flush()

    def info(self, msg):
        """
        log info
        """
        self.logger.info(msg)
        self.logger.handlers[0].flush()

    def __whoImportMe(self):
        return sys._getframe(2).f_code.co_filename