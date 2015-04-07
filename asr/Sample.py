# -*- coding:utf-8 -*-

from unisound_oraleval import USC


# SERVER_HOST     = "192.168.5.70"
# SERVER_PORT     = 8765
SERVER_HOST     = 'eval.hivoice.cn'
SERVER_PORT     = 80


def test():
    
    text_file = open('./res/02SpareThatSpider.txt', 'r')
    text_content = text_file.read()
    text_file.close()

    print text_content
    # properties
    properties = [
                 {'code': 0x02,
                  'value': 'opus'},
                 {'code': 0x0d,
                  'value': 'f4hclgovke2ww7ugouizlsxknnx4wxfexibi3xy5'},
                 {'code': 0x18,
                  'value': text_content},
                 {'code': 0x19,
                  'value': 'enstar'},
                 ]
    
    # 1. create recognizer
    usc = USC(SERVER_HOST, SERVER_PORT)

    # 2. set params
    code, result = usc.usc_set_option(properties)
    if code != 0:
        print 'error code:', code, ', result:', result
        exit(1)

    # 3. start recognize
    print 'start recognizer ...'
    code, result = usc.usc_start_recognizer()
    if code != 0:
        print 'error code:', code, ', result:', result
        exit(1)
    
    # 4. Get the pcm file
    file_object = open('./res/02SpareThatSpider.wav', 'rb')
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
    print 'start get result ...'
    code, result = usc.usc_get_result()
    
    print result


if __name__ == '__main__':
    test()
    print 'done'

