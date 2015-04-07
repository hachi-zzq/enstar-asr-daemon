#!/usr/bin/python
# -*- coding: utf-8 -*-
import struct, socket, traceback, time
from ctypes import CDLL, c_int, c_long, c_char_p, create_string_buffer


class MSG(object):
    _START = 1
    _STOP = 16
    _RESUME = 17
    _CANCEL = 18
    _GET_RESULT = 19

    def __init__(self):
        self._total_len = 6
        self._packer = ''
        self._header = None
        self._property = []
        self._wav_data = ''
        return

    def setHeader(self, code):
        """
        \xe8\xae\xbe\xe7\xbd\xae\xe5\x8c\x85\xe7\x9a\x84\xe5\xa4\xb48\xe4\xb8\xaa\xe5\xad\x97\xe8\x8a\x82\xef\xbc\x8c\xe9\x99\xa4\xe4\xba\x86\xe7\xac\xac\xe4\xba\x94\xe4\xb8\xaa\xe5\xad\x97\xe8\x8a\x82\xe4\xb8\xbacode\xef\xbc\x8c\xe5\x85\xb6\xe5\xae\x83\xe5\xad\x97\xe8\x8a\x82\xe5\x86\x85\xe5\xae\xb9\xe9\x83\xbd\xe5\x9b\xba\xe5\xae\x9a
        """
        if code not in [MSG._START,
                        MSG._STOP,
                        MSG._RESUME,
                        MSG._CANCEL,
                        MSG._GET_RESULT]:
            return (-1, 'code error')
        self._header = [77,
                        64,
                        2,
                        1,
                        code,
                        1,
                        0,
                        0]
        return (0, 'ok')

    def setProperty(self, code, value):
        """
        \xe8\xae\xbe\xe7\xbd\xae\xe5\xb1\x9e\xe6\x80\xa7
        """
        if not isinstance(code, int):
            return (-1, 'code error')
        if not value:
            return (-1, 'value error')
        self._total_len += 8 + len(value)
        self._property.append((code, value))
        return (0, 'ok')

    def setDatas(self, datas, length):
        """
        \xe8\xae\xbe\xe7\xbd\xae\xe9\x9f\xb3\xe9\xa2\x91\xe6\x95\xb0\xe6\x8d\xae
        """
        if len(datas) != length:
            return (-1, 'data length error')
        self._wav_data += datas
        self._total_len += length
        return (0, 'ok')

    def packMsg(self):
        """
        \xe6\x89\x93\xe5\x8c\x85\xe6\x95\xb0\xe6\x8d\xae
        """
        try:
            if not self._header:
                return (-1, 'header error')
            for value in self._header:
                self._packer += struct.pack('!B', value)

            self._packer += struct.pack('!I', self._total_len)
            property_len = len(self._property)
            self._packer += struct.pack('!I', property_len)
            if self._property:
                for item in self._property:
                    self._packer += struct.pack('!4BI', item[0], 0, 0, 0, len(item[1]))

                for item in self._property:
                    for i in list(item[1]):
                        self._packer += struct.pack('!B', ord(i) ^ ord('@'))

            if self._wav_data:
                self._packer += self._wav_data
            self._packer += struct.pack('!2B', 33, 64)
            return (0, 'ok')
        except:
            traceback.print_exc()
            return (-1, 'pack data error!')

    def unpackData(self, data):
        """
        \xe8\xa7\xa3\xe5\x8c\x85\xe6\x95\xb0\xe6\x8d\xae
        """
        self._packer = data
        try:
            results = {}
            tmp = self._packer[:4]
            self._packer = self._packer[4:]
            property_len = struct.unpack('!I', tmp)[0]
            for _ in xrange(property_len):
                tmp = self._packer[:8]
                self._packer = self._packer[8:]
                code = '%X' % struct.unpack('!4BI', tmp)[0]
                length = struct.unpack('!4BI', tmp)[-1]
                self._property.append((code, length))

            if len(self._property) > 0:
                propertys = []
                for item in self._property:
                    tmp = self._packer[:item[1]]
                    self._packer = self._packer[item[1]:]
                    value = ''
                    for i in list(tmp):
                        value += chr(struct.unpack('!B', i)[0] ^ ord('@'))

                    propertys.append({'code': item[0],
                                      'value': value})

                results['propertys'] = propertys
            result_data = self._packer
            if len(result_data) > 0:
                result = ''
                for i in list(result_data):
                    ch = chr(struct.unpack('!B', i)[0] ^ 1)
                    if ch == '\x00' or ch == '\x01':
                        continue
                    result += ch

                results['result'] = result
            return (0, results)
        except:
            print traceback.print_exc()
            return (-1, 'unpack data error!')


class Request(object):
    def __init__(self, host, port, propertys):
        self._host = host
        self._port = port
        self._propertys = propertys
        self._recv_datas = None
        self._send_data_len = 0
        self._send_datas = ''
        return

    def connect2Server(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((self._host, self._port))
        self._connection = s

    def closeConnection(self):
        self._connection.close()

    def recvDatas(self, recv_len):
        try:
            len_tmp = 0
            recv_data = ''
            while len_tmp < recv_len:
                tmp = self._connection.recv(recv_len - len_tmp)
                len_tmp += len(tmp)
                recv_data += tmp

            return recv_data
        except:
            traceback.print_exc()
            return ''

    def start(self):
        """
        \xe5\x8f\x91\xe9\x80\x81start\xef\xbc\x8c\xe5\xb9\xb6\xe6\x8e\xa5\xe6\x94\xb6\xe6\x9c\x8d\xe5\x8a\xa1\xe7\xab\xaf\xe8\xbf\x94\xe5\x9b\x9e\xe7\x9a\x84\xe5\x89\x8d4\xe4\xb8\xaa\xe5\xad\x97\xe8\x8a\x82\xef\xbc\x8c\xe8\xaf\xbb\xe5\x8f\x96\xe7\xac\xac4\xe4\xb8\xaa\xe5\xad\x97\xe8\x8a\x82\xe8\xbf\x94\xe5\x9b\x9e\xef\xbc\x8c0\xe8\xa1\xa8\xe7\xa4\xba\xe5\x92\x8c\xe6\x9c\x8d\xe5\x8a\xa1\xe7\xab\xaf\xe5\xbb\xba\xe7\xab\x8b\xe8\xbf\x9e\xe6\x8e\xa5\xe6\x88\x90\xe5\x8a\x9f
        """
        try:
            m = MSG()
            m.setHeader(MSG._START)
            for item in self._propertys:
                m.setProperty(item['code'], item['value'])

            m.packMsg()
            self.connect2Server()
            self._connection.send(m._packer)
            recv_data = self.recvDatas(8)
            code = struct.unpack('!4B', recv_data[:4])[3]
            if code:
                return (-1, 'error code: %X' % code)
            msg_len = struct.unpack('!I', recv_data[4:])[0]
            recv_data = self.recvDatas(msg_len)
            code, result = MSG().unpackData(recv_data)
            if code:
                return (-1, result)
            return (0, result)
        except:
            traceback.print_exc()
            return (-1, 'start error!')

    def sendDatas(self, datas, data_len):
        """
        \xe5\x8f\x91\xe9\x80\x81\xe9\x9f\xb3\xe9\xa2\x91\xe6\x95\xb0\xe6\x8d\xae
        """
        try:
            m = MSG()
            m.setHeader(MSG._RESUME)
            m.setDatas(datas, data_len)
            m.packMsg()
            send_len = 0
            while send_len < data_len:
                send_len += self._connection.send(m._packer[send_len:])

        except:
            traceback.print_exc()

    def getResult(self):
        """
        \xe8\xaf\xbb\xe5\x8f\x96\xe8\xbf\x94\xe5\x9b\x9e\xe7\x9a\x84\xe7\xbb\x93\xe6\x9e\x9c
        """
        try:
            m = MSG()
            m.setHeader(MSG._STOP)
            m.packMsg()
            self._connection.send(m._packer)
            recv_data = self.recvDatas(8)
            code = struct.unpack('!4B', recv_data[:4])[3]
            if code:
                return (-1, 'error code: %X' % code)
            msg_len = struct.unpack('!I', recv_data[4:])[0]
            recv_data = ''
            recv_data_len = 0
            while recv_data_len < msg_len:
                recv_data += self.recvDatas(msg_len - recv_data_len)
                recv_data_len += len(recv_data)

            self.close()
            code, result = MSG().unpackData(recv_data)
            if code:
                return (-1, result)
            return (0, result['result'])
        except:
            traceback.print_exc()
            return (-1, 'get result error!')

    def close(self):
        """
        \xe5\x85\xb3\xe9\x97\xad\xe6\x9c\xac\xe6\xac\xa1\xe4\xbb\xbb\xe5\x8a\xa1
        """
        self.closeConnection()


class USC(object):
    _FRAME_LEN = 640

    def __init__(self, server_ip, server_port):
        self._server_host = server_ip
        self._server_port = server_port
        self._request = None
        self._propertys = None
        self._lib_encoder = CDLL('OpusEncoder.so')
        self._lib_encoder.initEncoder.argtypes = []
        self._lib_encoder.initEncoder.restype = c_long
        self._lib_encoder.destroy.argtypes = [c_long]
        self._lib_encoder.encode.argtypes = [c_long, c_char_p, c_char_p]
        self._lib_encoder.encode.restype = c_int
        self._encoder = self._lib_encoder.initEncoder()
        self._out_str = create_string_buffer(USC._FRAME_LEN)
        self._opusbuf = None
        return

    def usc_set_option(self, propertys):
        if not isinstance(propertys, list):
            return (-1, 'propertys not list')
        for item in propertys:
            if not isinstance(item, dict):
                return (-1, 'propertys item not dict')

        self._propertys = propertys
        return (0, 'ok')

    def usc_start_recognizer(self):
        self._request = Request(self._server_host, self._server_port, self._propertys)
        return self._request.start()

    def usc_feed_buffer(self, data, length):
        flush = False
        try:
            if len(data) < 640:
                data += '\x00' * (640 - len(data))
                flush = True
            data_len = self._lib_encoder.encode(self._encoder, data, self._out_str)
            send_datas = struct.pack('H' + str(data_len) + 's', data_len, self._out_str.raw)
            if not self._opusbuf:
                self._opusbuf = send_datas
            else:
                self._opusbuf = self._opusbuf + send_datas
            if len(self._opusbuf) >= 1000 or flush:
                self._request.sendDatas(self._opusbuf, len(self._opusbuf))
                time.sleep(0.1)
                self._opusbuf = None
            return (0, 'ok')
        except:
            print traceback.print_exc()
            return (-1, 'feed buffer error!')

        return

    def usc_get_result(self):
        return self._request.getResult()


def test():
    serverIP = '192.168.5.70'
    serverPort = 8765
    text_content = 'good'
    properties = [{'code': 2,
                   'value': 'opus'},
                  {'code': 13,
                   'value': 'zpbfrnoef722gn6q435beiebqm2cgxyhcofwi3il'},
                  {'code': 24,
                   'value': text_content},
                  {'code': 25,
                   'value': 'enstar'}]
    usc = USC(serverIP, serverPort)
    code, result = usc.usc_set_option(properties)
    if code:
        print 'error code:', code, ', reuslt:', result
        exit(1)
    code, result = usc.usc_start_recognizer()
    if code:
        print 'error code:', code, ', reuslt:', result
        exit(1)
    file_object = open('./res/good.wav', 'rb')
    try:
        while True:
            chunk = file_object.read(USC._FRAME_LEN)
            if not chunk:
                break
            code, result = usc.usc_feed_buffer(chunk, len(chunk))
            if code:
                print 'feed buffer error:', result

    finally:
        file_object.close()

    code, result = usc.usc_get_result()
    if code:
        print 'get result error:', result
    else:
        print 'result:', result


if __name__ == '__main__':
    test()
    print 'done'