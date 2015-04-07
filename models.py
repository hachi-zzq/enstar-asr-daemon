# -*- coding: utf-8 -*-
import random
import string
import urllib2

__author__ = 'haiming'

import wave, os, subprocess, datetime
import json
import report_util
import config
import logging

PCM_RATE_HZ = 16000


def generate_random_string(length=8):
    """
    生成随机字符串
    :param length:
    :return:
    """
    return ''.join(random.sample(string.ascii_letters + string.digits, length))


class WaveText(object):
    """声音样本"""
    # 任务类型
    TASK_TYPE_READ = 'READ'
    TASK_TYPE_LESSON = 'LESSON'

    def __init__(self):
        self._wav_path = ''
        self.wav_local_path = ''
        self._is_need_convert = False
        self.lesson_id = ''
        self._sentences = ''
        self.text_content = ''
        self.language = ''
        self.message = []
        self._task_type = ''  # 任务类型

    def audio_to_pcm(self):
        """
        将不符合要求的音频转码，
        如果音频在远程，则下载来
        :return:
        """
        # 判断是哪个平台的文件
        if self._task_type == self.TASK_TYPE_LESSON:
            self.wav_local_path = config.FILE_BASE_PATH + self.wav_path
        elif self._task_type == self.TASK_TYPE_READ:
            self.wav_local_path = config.API_FILE_BASE_PATH + self.wav_path

        if self.wav_path.startswith('http') or self.wav_path.startswith('ftp'):
            _file_name = self.wav_path[self.wav_path.rindex("/") + 1:]
            self.wav_local_path = os.path.join(config.DOWNLOAD_AUDIO_PATH, _file_name)
            WaveText.download_file(self.wav_path, self.wav_local_path)
        self._is_need_convert = not self.check_wave(self.wav_local_path)  # 检测采样率和声道
        if self._is_need_convert:
            target_name = os.path.join(config.USER_TMP_PATH, generate_random_string() + '.wav')
            self.arm_to_pcm(self.wav_local_path, target_name)
            self.wav_local_path = target_name

    @property
    def wav_path(self):
        return self._wav_path

    @wav_path.setter
    def wav_path(self, value):
        self._wav_path = value
        self.audio_to_pcm()

    @property
    def sentences(self):
        return self._sentences

    @sentences.setter
    def sentences(self, value):
        self._sentences = value
        text_tmp = ""
        for sentence in self._sentences:
            text_tmp += "%s\n" % (sentence['asrText'].replace('[[', '').replace(']]', ''),)
        self.text_content = str(text_tmp)

    @staticmethod
    def download_file(url, file_name):
        try:
            u = urllib2.urlopen(url)
            dir = os.path.dirname(file_name)
            if not os.path.exists(dir):
                os.makedirs(dir)
            f = open(file_name, 'wb')
            meta = u.info()
            file_size = int(meta.getheaders("Content-Length")[0])
            file_size_dl = 0
            block_sz = 8192
            while True:
                buffer = u.read(block_sz)
                if not buffer:
                    break
                file_size_dl += len(buffer)
                f.write(buffer)
            f.close()
            logging.debug('download file ' + url + ' success')
        except Exception, e:
            logging.error('Download file ' + url + ' to file ' + file_name + ' error.')
            raise e

    @staticmethod
    def check_wave(wave_path):
        """
        检测语音文件是否满足需求
        :param wave_path:
        :return:
        """
        ext_name = os.path.splitext(wave_path)[1]
        if ext_name not in ['.wav', '.pcm']:
            return False
        handle = wave.open(wave_path, 'r')
        channel = handle.getnchannels()
        rate = handle.getframerate()
        handle.close()
        return rate == PCM_RATE_HZ and channel == 1

    @staticmethod
    def arm_to_pcm(source, target, rate_hz=PCM_RATE_HZ):
        """
        转码
        :param source:
        :param tagete:
        :param rate_hz:
        :return:
        """
        dir = os.path.dirname(target)
        if not os.path.exists(dir):
            os.makedirs(dir)
        run_script = os.getcwd() + "/bin/ffmpeg -i " + source + " -ar " + str(rate_hz) + " " + target
        subprocess.call(run_script, shell=True)
        return True

    def __del__(self):
        if self._is_need_convert:  # 删除转换后的临时文件
            os.remove(self.wav_local_path)


class Lesson(WaveText):
    """范文样本"""

    def __init__(self):
        WaveText.__init__(self)
        self._task_type = WaveText.TASK_TYPE_LESSON


class Read(WaveText):
    """录音样本"""

    def __init__(self):
        WaveText.__init__(self)
        self._task_type = WaveText.TASK_TYPE_READ
        self.read_id = 0
        self.lesson_report_path = ''
        self.submission_time = ''
        self.read_id = None
        self.user_id = None
        self.user_id = None
        self.homework_id = None
        self.lesson_report_guid = ''
        self.times = 0


class Report(object):
    """报告"""

    def __init__(self, wt, raw_content):
        self.available = True
        self.total_points = 0
        self.raw = raw_content
        self.wt = wt
        self.build_time = datetime.datetime.today().isoformat()
        self.processed_report = {}
        # 报告文件名
        self.name = ''

    def save_raw_report(self, path=config.FILE_BASE_PATH):
        """
        保存原始报告
        :param path:
        :return:
        """
        _dir_name = ''
        if isinstance(self.wt, Lesson):
            _dir_name = 'lesson'
        if isinstance(self.wt, Read):
            _dir_name = 'read'
        file_path = path + os.path.join(config.REPORT_RAW_SAVE_PATH, _dir_name, os.path.split(self.name)[1])
        json_content = json.loads(self.raw)
        json_content = json.dumps(json_content)
        dir = os.path.dirname(file_path)
        if not os.path.exists(dir):
            os.makedirs(dir)
        with open(file_path, 'w') as f:
            f.write(json_content)

    def save_new_report(self, path=config.FILE_BASE_PATH):
        """
        保存处理过的新报告
        :param path:
        :return:
        """
        file_path = path + self.name
        json_content = json.dumps(self.processed_report)
        dir = os.path.dirname(file_path)
        if not os.path.exists(dir):
            os.makedirs(dir)
        with open(file_path, 'w') as f:
            f.write(json_content)

    def covert(self):
        """
        转换成Enstar需要的报告
        :param sentences:
        :return:
        """
        pass


class LessonReport(Report):
    """范文样本报告"""

    def __init__(self, wt, raw_content):
        Report.__init__(self, wt, raw_content)
        self.name = os.path.join(config.REPORT_SAVE_PATH, 'lesson',
                                 str(wt.lesson_id) + '_' + generate_random_string() + '.json')

    def covert(self):
        self.processed_report, self.available = report_util.convert(json.loads(self.raw), self.wt.sentences)
        return self.processed_report


class ReadReport(Report):
    """录音样本报告"""

    def __init__(self, wt, raw_content):
        Report.__init__(self, wt, raw_content)
        self.final_report = {}
        self.lesson_report_path = wt.lesson_report_path
        self.name = os.path.join(config.REPORT_SAVE_PATH, 'read', str(wt.user_id),
                                 str(wt.read_id) + '_' + generate_random_string() + '.json')

    def covert(self):
        self.processed_report, self.available = report_util.convert(json.loads(self.raw), self.wt.sentences,
                                                                    report_util.REPORT_TYPE_READ)
        self.processed_report = self._calculate()
        return self.processed_report

    def _calculate(self):
        """
        计算阅读报告的成绩
        :param read_report:
        :return:
        """
        try:
            lesson_report_file = open(config.FILE_BASE_PATH + self.lesson_report_path, 'r')
            lesson_report = json.load(lesson_report_file)
            self.final_report = report_util.calculate(self.processed_report, lesson_report)
            return self.final_report
        except IOError, e:
            logging.exception("Open " + config.FILE_BASE_PATH + self.lesson_report_path + " error")
            raise e



