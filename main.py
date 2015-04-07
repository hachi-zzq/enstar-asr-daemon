# -*- coding: utf-8 -*-

"""
EnStar 主服务端程序
------------------------------

1. 轮询 Redis 消息队列中新增的 Tape 或 Simple
2. 将其分解为 WAVE PCM 包数据，并进行分组
3. 提交到 ASR LibC 匹配生成 String 结果
4. ASR 结果将生成为 XML 文档
5. 回写到消息队列，通知 PHP 程序写库

"""
import logging
import logging.config
import threading
import signal
import sys

reload(sys)
sys.setdefaultencoding('utf-8')
from asr.asr import AsrClient


__title__ = 'NEC ROCKET'
__version__ = '1.0.1'
__author__ = 'Haiming Wang<haiming.wang@enstar.com>'
__copyright__ = 'Copyright 2015 Enstar INC PTE. LTD.'

import time
import config
from mq import ClientMQ
from mq import DaemonMQ
from models import Lesson

_startTime = time.time()

is_exit = False
error_times = 0


def get_report_by_wt(wt):
    """提交文本和声音给 ASR 识别"""
    _client = {}
    try:
        _client = AsrClient(config.ASR_APP_KEY, config.ASR_IP, config.ASR_PORT, wt)
        _client.post_request()
        _asr_result = _client.get_result()
        _report = _asr_result.to_report(wt)
        _report.save_raw_report()
        _report.covert()
        _report.save_new_report()
        return _report
    except Exception, e:
        print e


def test_asr():
    _wt = Lesson()
    _wt.wav_path = '/data/audio/001.wav'
    _wt.sentences = [
        {
            "id": 1001,
            "text": "Last week my four-year-old daughter Sally was invited to a children's party.",
            "asrText": "Last week my four-year-old daughter Sally was invited to a children's party"
        },
        {
            "id": 1002,
            "text": "I decided to take her by train.",
            "asrText": "I decided to take her by train"
        }
    ]

    _asr_result = get_report_by_wt(_wt)
    return _asr_result



def deal_lesson(num):
    global is_exit
    global error_times
    while not is_exit:
        lesson = None
        _client = {}
        try:
            lesson = DaemonMQ.get_lesson()
        except Exception, e:
            logging.exception(e)
        if lesson:
            try:
                ClientMQ.change_lesson_analyze_status(lesson)
                t1 = time.time()
                _client = AsrClient(config.ASR_APP_KEY, config.ASR_IP, config.ASR_PORT, lesson)
                _client.post_request()
                _asr_result = _client.get_result()
                asr_time = time.time() - t1
                _report = _asr_result.to_report(lesson)
                _report.save_raw_report()
                _report.covert()
                _report.save_new_report()
                ClientMQ.push_lesson_report(_report, asr_time)
                logging.info('Lesson task [%s] completed time [%f].' % (lesson.lesson_id, time.time() - t1))
                ClientMQ.push_status_on()
                error_times = 0
            except Exception, e:
                ClientMQ.change_lesson_analyze_status(lesson, "FAIL")
                logging.error('Lesson task [%s] error.' % (lesson.lesson_id,))
                error_times += 1
                logging.exception(e)
                if error_times > config.MAX_ERROR_TIMES:
                    ClientMQ.push_status_off()
            finally:
                del _client

        time.sleep(2)
    else:
        print "receive a signal to exit, lesson thread[%d] stop." % num


def deal_read(num):
    global is_exit
    global error_times
    while not is_exit:
        read = None
        _client = {}
        try:
            read = DaemonMQ.get_read()
        except Exception, e:
            logging.exception(e)
        if read:
            try:
                ClientMQ.change_read_analyze_status(read)
                t1 = time.time()
                _client = AsrClient(config.ASR_APP_KEY, config.ASR_IP, config.ASR_PORT, read)
                _client.post_request()
                _asr_result = _client.get_result()
                asr_time = time.time() - t1
                _report = _asr_result.to_report(read)
                _report.save_raw_report()
                _report.covert()
                _report.save_new_report()
                ClientMQ.push_read_report(_report, asr_time)
                logging.info('Read task [%s] completed time [%f].' % (read.read_id, time.time() - t1))
                ClientMQ.push_status_on()
                error_times = 0
            except Exception, e:
                ClientMQ.push_read_retry(read.message)
                logging.error('Read task [%s] error.' % (read.read_id, ))
                error_times += 1
                logging.exception(e)
                if error_times > config.MAX_ERROR_TIMES:
                    ClientMQ.push_status_off()
            finally:
                del _client
        time.sleep(2)
    else:
        print "receive a signal to exit, read thread[%d] stop." % num


def deal_read_retry(num):
    global is_exit
    while not is_exit:
        _client = {}
        read_retry = None
        try:
            read_retry = DaemonMQ.get_retry_read()
        except Exception, e:
            logging.exception(e)
        if read_retry:
            try:
                t1 = time.time()
                _client = AsrClient(config.ASR_APP_KEY, config.ASR_IP, config.ASR_PORT, read_retry)
                _client.post_request()
                _asr_result = _client.get_result()
                asr_time = time.time() - t1
                _report = _asr_result.to_report(read_retry)
                _report.save_raw_report()
                _report.covert()
                _report.save_new_report()
                ClientMQ.push_read_report(_report, asr_time)
                logging.info('Read retry task [%s] completed time [%f].' % (read_retry.read_id, time.time() - t1))
            except Exception, e:
                read_retry.times += 1
                if read_retry.times > config.MAX_READ_RETRY_TIMES:
                    ClientMQ.change_read_analyze_status(read_retry, "FAIL")
                else:
                    ClientMQ.push_read_retry(read_retry.message)
                logging.error('Read retry task [%s] error.' % (read_retry.read_id, ))
                logging.exception(e)
            finally:
                del _client
        time.sleep(2)
    else:
        print "receive a signal to exit, read thread[%d] stop." % num


def handler(signum, frame):
    global is_exit
    is_exit = True
    print "receive a signal %d, is_exit = %d" % (signum, is_exit)


def main():
    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    lesson_threads_num = 2
    read_threads_num = 4
    threads = []
    for i in range(lesson_threads_num):
        t = threading.Thread(target=deal_lesson, args=(i, ))
        t.setDaemon(True)
        threads.append(t)

    for i in range(read_threads_num):
        t = threading.Thread(target=deal_read_retry, args=(i, ))
        t.setDaemon(True)
        threads.append(t)

    for i in range(read_threads_num):
        t = threading.Thread(target=deal_read, args=(i, ))
        t.setDaemon(True)
        threads.append(t)

    for thread in threads:
        thread.start()

    while True:
        alive = False
        for i in range(len(threads)):
            alive = alive or threads[i].isAlive()
        if not alive:
            break
        time.sleep(4)

    for t in threads:
        t.join()


if __name__ == "__main__":
    print 'pyEnStarD Daemon v' + __version__ + ' , ' + __copyright__
    print 'by Haiming Wang'
    print ''
    logging.config.fileConfig("log.conf")
    print "====== start ====="
    main()
    print "====== end ====="




