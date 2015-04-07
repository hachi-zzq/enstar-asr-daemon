# -*- coding: utf-8 -*-

__author__ = 'haiming'

import json
import os
import logging

import redis

import config
from models import Lesson, Read


# W2 SERVER
_r = redis.StrictRedis(host=config.REDIS_HOST, port=config.REDIS_PORT, db=config.REDIS_DB)

REDIS_KEY_ASR_STATUS = 'enstar:xy:asr:status'
MQ_READ_RETRY = 'enstar:xy:read:analyze:retry'
MQ_LESSON_ANALYZE_INPUT = 'enstar:xy:lesson:analyze:input'
MQ_LESSON_ANALYZE_OUTPUT = 'enstar:xy:lesson:analyze:output'
MQ_READ_ANALYZE_INPUT = 'enstar:xy:read:analyze:input'
MQ_READ_ANALYZE_OUTPUT = 'enstar:xy:read:analyze:output'



class DaemonMQ:
    def __init__(self):
        pass

    @staticmethod
    def get_lesson():
        """
        解析 JSON, 送去评分
        :return:
        """
        lesson_m = _r.rpop(MQ_LESSON_ANALYZE_INPUT)
        if lesson_m:
            logging.debug("Get redis[" + MQ_LESSON_ANALYZE_INPUT + "] message:%s" % (lesson_m,))
            message = json.loads(lesson_m)
            wt = Lesson()
            wt.message = lesson_m
            wt.lesson_id = message.get('lessonId')
            wt.sentences = message.get('sentences')
            wt.wav_path = message.get('audioPath')
            wt.language = message.get('language')
            return wt
        return None

    @staticmethod
    def get_read():
        """
        解析 JSON, 送去评分
        :return:
        """
        read_m = _r.rpop(MQ_READ_ANALYZE_INPUT)
        if read_m:
            logging.debug("Get redis[" + MQ_READ_ANALYZE_INPUT + "] message:%s" % (read_m,))
            message = json.loads(read_m)
            wt = Read()
            wt.message = read_m
            wt.lesson_id = message.get('lessonId')
            wt.read_id = message.get('readId')
            wt.user_id = message.get('userId')
            wt.homework_id = message.get('homeworkId')
            wt.lesson_report_guid = message.get('lessonReportGuid')
            wt.submission_time = message.get('submissionTime')
            wt.lesson_report_path = message.get('lessonReportPath')
            wt.sentences = message.get('sentences')
            wt.wav_path = message.get('audioPath')
            wt.language = message.get('language')
            return wt
        return None

    @staticmethod
    def get_retry_read():
        """
        解析 JSON, 送去评分
        :return:
        """
        read_m = _r.rpop(MQ_READ_RETRY)
        if read_m:
            logging.debug("Get redis[%s] message:%s" % (MQ_READ_RETRY, read_m,))
            message = json.loads(read_m)
            wt = Read()
            wt.message = read_m
            wt.lesson_id = message.get('lessonId')
            wt.times = message.get('times')
            wt.read_id = message.get('readId')
            wt.user_id = message.get('userId')
            wt.homework_id = message.get('homeworkId')
            wt.lesson_report_guid = message.get('lessonReportGuid')
            wt.submission_time = message.get('submissionTime')
            wt.lesson_report_path = message.get('lessonReportPath')
            wt.sentences = message.get('sentences')
            wt.wav_path = message.get('audioPath')
            wt.language = message.get('language')
            return wt
        return None


class ClientMQ:
    def __init__(self):
        pass

    @staticmethod
    def _push_new_message(mq_name, msg):
        logging.debug("Push redis[%s] message:%s" % (mq_name, msg))
        _r.lpush(mq_name, json.dumps(msg))
        return True

    @staticmethod
    def change_lesson_analyze_status(wt, status='PROCESSING'):
        msg = {
            'lessonId': wt.lesson_id,
            'status': status
        }
        ClientMQ._push_new_message(MQ_LESSON_ANALYZE_OUTPUT, msg)

    @staticmethod
    def change_read_analyze_status(wt, status='PROCESSING'):
        msg = {
            'lesson_id': wt.lesson_id,
            'readId': wt.read_id,
            'userId': wt.user_id,
            'homeworkId': wt.homework_id,
            'submissionTime': wt.submission_time,
            'audioPath': wt.wav_path,
            'language': wt.language,
            'status': status
        }
        ClientMQ._push_new_message(MQ_READ_ANALYZE_OUTPUT, msg)

    @staticmethod
    def push_lesson_report(report, asr_time=0):
        status = "SUCCESS"
        if not report.available:
            status = 'UNAVAILABLE'
        msg = {
            'lessonId': report.wt.lesson_id,
            'status': status,
            'reportPath': report.name,
            'asr_time': asr_time,
            'available': report.available
        }
        ClientMQ._push_new_message(MQ_LESSON_ANALYZE_OUTPUT, msg)

    @staticmethod
    def push_read_report(report, asr_time=0):
        msg = {
            'lesson_id': report.wt.lesson_id,
            'readId': report.wt.read_id,
            'userId': report.wt.user_id,
            'lessonReportGuid': report.wt.lesson_report_guid,
            'homeworkId': report.wt.homework_id,
            'submissionTime': report.wt.submission_time,
            'audioPath': report.wt.wav_path,
            'language': report.wt.language,
            'reportPath': report.name,
            'asr_time': asr_time,
            'status': 'SUCCESS'
        }
        ClientMQ._push_new_message(MQ_READ_ANALYZE_OUTPUT, msg)

    @staticmethod
    def push_read_retry(msg):
        message = json.loads(msg)
        times = message.get('times', 0)
        times += 1
        message['times'] = times
        ClientMQ._push_new_message(MQ_READ_RETRY, message)

    @staticmethod
    def push_status_on():
        _r.set(REDIS_KEY_ASR_STATUS, "on")

    @staticmethod
    def push_status_off():
        _r.set(REDIS_KEY_ASR_STATUS, "off")