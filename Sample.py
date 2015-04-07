#!/usr/bin/python
# -*- coding: utf-8 -*-
from asr import unisound_oraleval as usc

os.system('ln -sf ' + os.getcwd() + '/*.so /usr/asr')
os.system('ldconfig')
import wave
import os

"""
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
    USC_AUDIO_ENCODE_MTD    = 0x0201,    //SSUP_AUDIO_ENC_METH
    USC_AUDIO_ENCODE_MTD8K    = 0x0202,    //SSUP_AUDIO_ENC_METH
    USC_OPT_IMEI_ID        = 0x0c,    //SSUP_IMEI_SET
    USC_OPT_APP_KEY        = 0x0d,    //SSUP_APP_KEY
    USC_OPT_PACKAGE_NAME    = 0x0e,    //SSUP_ASR_OPT_PACKAGE_NAME
    USC_OPT_CARRIER        = 0x0f,    //SSUP_ASR_OPT_CARRIER
    USC_OPT_NETWORK_TYPE    = 0x10,    //SSUP_ASR_OPT_NETWORK_TYPE
    USC_OPT_DEVICE_OS    = 0x11,    //SSUP_ASR_OPT_DEVICE_OS
    USC_USER_ID        = 0x12,    //SSUP_USER_ID
    USC_OPT_COLLECTED_INFO    = 0x13,    //SSUP_COLLECTED_INFO
    USC_REQ_RSP_ENTITY    = 0x14,    //SSUP_REQ_RSP_ENTITY
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


def get_pcm(wav_path):
    pcm_group_size = 32000 * 300 / 1000
    handle = wave.open(wav_path, 'r')
    nframes = handle.getnframes()  # 读取采样点数量
    frames = handle.readframes(nframes)
    pcmdatalist = list()
    for i in range(0, len(frames), pcm_group_size):
        pcmdatalist.append(frames[i:i + pcm_group_size])
    return pcmdatalist


if __name__ == "__main__":

    FRAME_BUF = 32000 * 300 / 1000

    app_key = "u5cfnzbn4pqwsyaeoa36s2olxg4mqzkgefu4k2qo"
    device_id = "user_id"
    serverIP = "eval.hivoice.cn"
    serverPort = 80

    filename = "./test16.pcm"

    recg_result = ""

    # 1. create recognize
    handle = usc.usc_create_service_ext(serverIP, serverPort)
    print handle
    if handle <= 0:
        print "Failed to create service"
        # return
        exit(1)

    # 2. set params
    ret = usc.usc_set_option(handle, 0x0201, "opus")  # AUDIO_ENCODE_MTD
    if ret != 0:
        print "Failed to uscSetOption"
        # return
        exit(1)

    ret = usc.usc_set_option(handle, 0x0d, app_key)  # OPT_SERVICE_KEY
    if ret != 0:
        print "Failed to set app key"
        # return
        exit(1)

    text = '''1001 Last week my four-year-old daughter Sally was invited to a children's party
1002 I decided to take her by train
'''
    ret = usc.usc_set_option(handle, 0x17, text)  # ORAL_EVAL_TEXT
    ret = usc.usc_set_option(handle, 0x1A, "enstar")  # ORAL_EVAL_TaskType

    # 3. start recognize
    ret = usc.usc_start_recognizer(handle)
    print ret
    if ret != 0:
        print "the ret of Start is" + ret
        # return
        exit(1)

    # 4. Get the pcm file
    # file_object = open(filename, 'rb')
    pcm = get_pcm('./usr/001.wav')

    try:
        # 5. Loop, read the pcm file, call uscFeedBuffer and call uscGetResult to get result piece
        for chunk in pcm:
            ret = usc.usc_feed_buffer(handle, chunk, len(chunk))
    finally:
        pass

    # 6. call the uscStopRecognizer and UscGetResult to get the last result piece
    usc.usc_stop_recognizer(handle)
    res_buf = usc.usc_get_result(handle)
    print "recg_result:" + str(res_buf)

    # 7. Release
    usc.usc_release_service(handle)
    handle = None
