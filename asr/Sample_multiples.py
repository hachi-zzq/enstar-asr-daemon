# -*- coding:utf-8 -*-

import os, sys, time
import threading
from Queue import Queue
from unisound_oraleval import USC


SERVER_HOST     = 'eval.hivoice.cn'
SERVER_PORT     = 80

THREAD_NUM      = 4 # 并发线程个数
LOG_FILE        = 'Sample_multiples.log'
log_file        = None

queue = Queue() # 需要被处理的文件队列


def get_filenames(filepath):
    """
    成对获取txt和wav文件名
    @param filepath        存放文件的目录
    """
    file_names = set()
    for parent, _, filenames in os.walk(filepath):
        while filenames:
            f_name = filenames[0]
            filenames.pop(0)
            f_name = f_name.split('.', -1)[0]
            file_names.add(parent + '/' + f_name)
    global queue
    for f_name in file_names:
        queue.put(f_name)

def print_log(log_str):
    if log_file:
        log_file.write(log_str)
        log_file.flush()
    else:
        sys.stdout.write(log_str + '\n')
        sys.stdout.flush()

def do_working():
    
    t = threading.currentThread()
    thread_name = t.name
    sys.stdout.write('start thread: ' + thread_name + '\n')
    sys.stdout.flush()
    
    log_file = open(thread_name + LOG_FILE, 'w')
    
    global queue
    while queue.qsize():
        f_name = queue.get()
        filename_txt = f_name + '.txt'
        filename_wav = f_name + '.wav'
        log_file.write('\n' + thread_name + ' start recognize file: ' + filename_txt + ' ' + filename_wav + '\n')
        
        f = open(filename_txt, 'r')
        content_txt = f.read()
        f.close()

        # properties
        properties = [
                     {'code': 0x02,
                      'value': 'opus'},
                     {'code': 0x0d,
                      'value': 'f4hclgovke2ww7ugouizlsxknnx4wxfexibi3xy5'},
                     {'code': 0x18,
                      'value': content_txt},
                     {'code': 0x19,
                      'value': 'enstar'},
                     ]
        
        # 1. create recognizer
        usc = USC(SERVER_HOST, SERVER_PORT)
    
        # 2. set params
        code, result = usc.usc_set_option(properties)
        if code:
            print 'error code:', code, ', result:', result
            exit(1)
    
        # 3. start recognize
        print thread_name, 'start recognizer ...'
        code, result = usc.usc_start_recognizer()
        if code:
            print 'error code:', code, ', result:', result
            exit(1)
        
        # 4. Get the pcm file
        file_object = open(filename_wav, 'rb')
        try:
            # 5. Loop, read the pcm file, call uscFeedBuffer and call uscGetResult to get result piece
            while True:
                chunk = file_object.read(USC._FRAME_LEN)
                if not chunk:
                    break
                code, result = usc.usc_feed_buffer(chunk, len(chunk))
                if code:
                    print 'feed buffer error:', result
        finally:
            file_object.close()
    
        # get result
        code, result = usc.usc_get_result()
        if code:
            log_file.write('get result error: ' + result)
        else:        
            log_file.write(thread_name + ' start recognize file: ' + filename_txt + ' ' + filename_wav + ' ' + result)
        print (thread_name + ' recognize file: ' + filename_txt + ' ' + filename_wav + ' done')
    
    log_file.close()


if __name__ == '__main__':

    print 'start time:', time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    
    
    get_filenames('./res')

    Threads = []
    for i in range(THREAD_NUM):
        t = threading.Thread(target=do_working, name="Thread"+str(i))
        t.setDaemon(True)
        Threads.append(t)
    
    for t in Threads:
        t.start()

    for t in Threads:
        t.join()
    
    
    print 'end time:', time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print '\n Sample was done.\n'
