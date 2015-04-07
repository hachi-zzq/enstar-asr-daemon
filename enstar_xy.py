#!/usr/bin/python
# -*- coding: utf-8 -*-


"""
ASR评测 主服务端程序
------------------------------

1. 轮询 Redis 消息队列中新增的 Tape 或 Simple
2. 将其分解为 WAVE PCM 包数据，并进行分组
3. 提交到 ASR LibC 匹配生成 String 结果
4. ASR 结果将生成为 JOSN 文档
5. 回调

"""
import logging
import logging.config
import threading
import time
import sys
import signal

reload(sys)
sys.setdefaultencoding('utf-8')
from asr.asr import AsrClient, ASRException
import config
from mq import DaemonMQ, ClientMQ
from daemon import Daemon


__title__ = 'Enstar Weixin Xiaoying ASR daemon'
__version__ = '1.0.1'
__author__ = 'Haiming Wang<haiming.wang@enstar.com>'
__copyright__ = 'Copyright 2015 EnStar INC PTE. LTD.'
_startTime = time.time()
is_exit = False
error_times = 0


def handler(signum, frame):
    global is_exit
    is_exit = True
    print "receive a signal %d, is_exit = %d" % (signum, is_exit)


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
    lesson_threads_num = config.LESSON_TASK_THREAD
    read_threads_num = config.READ_TASK_THREAD
    read_retry_threads_num = config.READ_RETRY_TASK_THREAD
    threads = []
    for i in range(lesson_threads_num):
        t = threading.Thread(target=deal_lesson, args=(i, ))
        t.setDaemon(True)
        threads.append(t)

    for i in range(read_retry_threads_num):
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

    ClientMQ.push_status_off()


class MyDaemon(Daemon):
    def stop(self):
        global is_exit
        is_exit = True
        ClientMQ.push_status_off()
        super(MyDaemon, self).stop()

    def _run(self):
        print 'py Enstar Weixin Xiaoying Daemon v' + __version__ + ' , ' + __copyright__
        print 'by Haiming Wang'
        print ''
        ClientMQ.push_status_on()
        main()


if __name__ == "__main__":
    logging.config.fileConfig("log.conf")
    daemon = MyDaemon('/tmp/enstar-xy-asr-daemon.pid')
    if len(sys.argv) == 2:
        if 'start' == sys.argv[1]:
            daemon.start()
        elif 'stop' == sys.argv[1]:
            daemon.stop()
        elif 'restart' == sys.argv[1]:
            daemon.restart()
        else:
            print "Unknown command"
            sys.exit(2)
        sys.exit(0)
    else:
        print "usage: %s start|stop|restart" % sys.argv[0]
        sys.exit(2)