#! /usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置文件

"""
import os

MAX_ERROR_TIMES = 10
MAX_READ_RETRY_TIMES = 2

# ##ASR server begin
# ASR_IP = '101.231.106.182'
# ASR_PORT = 8765
ASR_IP = 'esu.hivoice.cn'
ASR_PORT = 80
ASR_APP_KEY = 'f4hclgovke2ww7ugouizlsxknnx4wxfexibi3xy5'
# ##ASR server end


# ##redis begin
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 6379
REDIS_DB = 0
REDIS_PASSWORD = None
REDIS_SOCKET_TIMEOUT = None
# ##redis  end


# 相对服务平台API地址
API_FILE_BASE_PATH = '/opt/htdocs/enstar-wx/public'
# ##report save path begin

# 相对运营平台地址
FILE_BASE_PATH = '/opt/htdocs/enstar-wx/public'
# ##report save path begin
#报告存储目录的相对地址
REPORT_RAW_SAVE_PATH = '/data/report/raw'
REPORT_SAVE_PATH = '/data/report'
# ##report save path end

# download path begin
#相对本系统地址
DOWNLOAD_AUDIO_PATH = os.getcwd()+'/usr/audio'
# end

#相对本系统临时目录
USER_TMP_PATH = os.getcwd() + '/usr/tmp'

READ_TASK_THREAD = 6
READ_RETRY_TASK_THREAD = 4
LESSON_TASK_THREAD = 2

