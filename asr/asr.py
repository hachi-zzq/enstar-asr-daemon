#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
封装ASR所有服务
"""
import logging
from unisound_oraleval import USC
from models import LessonReport, ReadReport, Lesson, Read


__author__ = 'Haiming'

"""
1. 接口初始化
int usc_create_service_ext(HANDLE* handle, const char* uri, unsigned short port);

2. 设置必要参数
int usc_set_option(HANDLE Handle,int option_id, const char* value);

3. 开始评测
int usc_start_recognizer(HANDLE Handle);

4. 上传语音数据
int usc_feed_buffer(HANDLE Handle, char* buffer, int len);

5. 评测结束
int usc_stop_recognizer(HANDLE Handle);

6. 获得评测结果
const char* usc_get_result(HANDLE Handle);

7. 释放评测资源
void usc_release_service(service_handle);

enum
{
    USC_RECOGNIZER_OK    = 0,
    USC_OK            = 0,
    USC_VP_OK        = 0,
    USC_HAS_PARTIAL_RESULT    = 2,

    USC_CONNECTION_ERROR    = -10000,
    USC_KEY_NOT_VALID    = -20001,
    USC_SERVER_ERROR    = -20002,
    USC_INPUT_PARAMETER_ERROR    = -30000,
    USC_SDK_INTERNAL_ERROR    =-40000,
    USC_ATTR_ERROR_FROM_SERVER    = -50000,
    USC_SERVER_LOGIC_ERROR    = -50001,


    USC_EXPIRED_LICENSE        = -80000,
    USC_FATAL_ERROR            = -80001,
    USC_INVALID_PARAMETERS        = -80002,
    USC_RECEIVE_TOO_LONG_RESP    = -80003,
    USC_INPUT_BUFFER_TOO_SHORT    = -80004,

    USC_VP_ERROR            = -90000,
    USC_VP_INIT_FAIL        = -90001,
    USC_VP_GET_NO_MODEL_PATH    = -90002,
    USC_VP_REG_FAIL            = -90003,
    USC_VP_LOGIN_FAIL        = -90004,

    USC_EVAL_NO_TEXT_UPLOAD        = -11001,
    USC_EVAL_SERVER_ERROR        = -11002,
    USC_EVAL_NOT_COLLECTED_WORD    = -11003,
    USC_EVAL_SPEECH_TOO_LONG    = -11004,
};

enum
{
    USC_AUDIO_ENCODE_MTD    = 0x0201,    #SSUP_AUDIO_ENC_METH
    USC_AUDIO_ENCODE_MTD8K    = 0x0202,    #SSUP_AUDIO_ENC_METH
    USC_OPT_IMEI_ID        = 0x0c,    #SSUP_IMEI_SET
    USC_OPT_APP_KEY        = 0x0d,    #SSUP_APP_KEY
    USC_OPT_PACKAGE_NAME    = 0x0e,    #SSUP_ASR_OPT_PACKAGE_NAME
    USC_OPT_CARRIER        = 0x0f,    #SSUP_ASR_OPT_CARRIER
    USC_OPT_NETWORK_TYPE    = 0x10,    #SSUP_ASR_OPT_NETWORK_TYPE
    USC_OPT_DEVICE_OS    = 0x11,    #SSUP_ASR_OPT_DEVICE_OS
    USC_USER_ID        = 0x12,    #SSUP_USER_ID
    USC_OPT_COLLECTED_INFO    = 0x13,    #SSUP_COLLECTED_INFO
    USC_REQ_RSP_ENTITY    = 0x14,    #SSUP_REQ_RSP_ENTITY
    USC_ORAL_EVAL_TEXT    = 0x17,
        USC_ORAL_TASK_TYPE      = 0x1A,
        USC_ORAL_CONF_OP1       = 0x1B,
        USC_ORAL_CONF_OP2       = 0x1C,
    USC_VP_REG_ON        = 0x1D,
    USC_VP_ORAL_ON        = 0x1E,
    USC_VP_CHECK_VP_ON    = 0x1F,
    USC_VP_USER_ID        = 0x20,
};
"""
PCM_GROUP_SIZE = 32000 * 300 / 1000


class ASRException(Exception):
    """
    ASR servive异常
    """

    def __init__(self, *args, **kwargs):
        super(ASRException, self).__init__(*args, **kwargs)


class _Option(object):
    """
    提供ASR服务参数
    """
    USC_AUDIO_ENCODE_MTD = 0x0201  # SSUP_AUDIO_ENC_METH
    USC_AUDIO_ENCODE_MTD8K = 0x0202  # SSUP_AUDIO_ENC_METH
    USC_OPT_IMEI_ID = 0x0c  # SSUP_IMEI_SET
    USC_OPT_APP_KEY = 0x0d  # SSUP_APP_KEY
    USC_OPT_PACKAGE_NAME = 0x0e  # SSUP_ASR_OPT_PACKAGE_NAME
    USC_OPT_CARRIER = 0x0f  # SSUP_ASR_OPT_CARRIER
    USC_OPT_NETWORK_TYPE = 0x10  # SSUP_ASR_OPT_NETWORK_TYPE
    USC_OPT_DEVICE_OS = 0x11  # SSUP_ASR_OPT_DEVICE_OS
    USC_USER_ID = 0x12  # SSUP_USER_ID
    USC_OPT_COLLECTED_INFO = 0x13  # SSUP_COLLECTED_INFO
    USC_REQ_RSP_ENTITY = 0x14  # SSUP_REQ_RSP_ENTITY
    USC_ORAL_EVAL_TEXT = 0x17
    USC_ORAL_TASK_TYPE = 0x1A
    USC_ORAL_CONF_OP1 = 0x1B
    USC_ORAL_CONF_OP2 = 0x1C
    USC_VP_REG_ON = 0x1D
    USC_VP_ORAL_ON = 0x1E
    USC_VP_CHECK_VP_ON = 0x1F
    USC_VP_USER_ID = 0x20


class _AsrService(object):
    """
    提供ASR测评服务
    """

    def __init__(self, ip, port):
        self._ip = ip
        self._port = port
        self._usc = USC(ip, port)

    def set_option(self, properties):
        """传递设置选项"""
        try:
            code, result = self._usc.usc_set_option(properties)
            if code != 0:
                raise ASRException("ASR set option error[%d]." % (code,))
        except Exception, e:
            raise ASRException(e)
        return result

    def start_recognizer(self):
        """开始评测"""
        logging.debug('====== ASR start recognizer ======')
        try:
            code, result = self._usc.usc_start_recognizer()
            if code != 0:
                raise ASRException("ASR start recognizer error[%d]." % (code,))
        except Exception, e:
            raise ASRException(e)
        return result

    def feed_buffer(self, pcm_path):
        """上传"""
        logging.debug('====== ASR feed buffer ======')
        file_object = open(pcm_path, 'rb')
        try:
            while True:
                chunk = file_object.read(USC._FRAME_LEN)
                if not chunk:
                    break
                code, result = self._usc.usc_feed_buffer(chunk, len(chunk))
                if code != 0:
                    raise ASRException('ASR feed buffer error[%d:%s].' % (code, result))
        except Exception, e:
            logging.exception('ASR feed buffer error.')
            raise ASRException(e)
        finally:
            file_object.close()

    def get_result(self):
        """返回结果"""
        logging.debug('====== ASR get result ======')
        try:
            code, result = self._usc.usc_get_result()
            if not result:
                raise ASRException("ASR get result NULL")
        except Exception, e:
            raise ASRException(e)
        return result


class AsrClient(object):
    def __init__(self, app_key, ip, port, wt=None):
        self._wt = wt
        self._service = _AsrService(ip, port)
        self._app_key = app_key

    @property
    def wt(self):
        return self._wt

    @wt.setter
    def wt(self, value):
        self._wt = value
        self._wt.wav_to_pcm()

    def _set_options(self):
        properties = [{'code': 0x02, 'value': 'opus'}, {'code': 0x0d, 'value': self._app_key},
                      {'code': 0x18, 'value': self.wt.text_content}, {'code': 0x19, 'value': 'enstar'}]
        self._service.set_option(properties)

    def post_request(self):
        self._set_options()
        self._service.start_recognizer()
        self._service.feed_buffer(self.wt.wav_local_path)

    def get_result(self):
        return AsrResult(self._service.get_result())

    def __del__(self):
        try:
            del self._wt
        except:
            pass


class AsrResult(object):
    def __init__(self, content):
        print content
        self._content = content

    def to_report(self, wt):
        _report = None
        if isinstance(wt, Lesson):
            _report = LessonReport(wt, self._content)

        if isinstance(wt, Read):
            _report = ReadReport(wt, self._content)

        return _report