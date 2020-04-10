#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
import cv2
import numpy as np
import threading

from multiprocessing import Process, Queue

import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCServer

import os

import base64
import zmq

#my libraries(in the same folder)
from serial_test import ArdHandler
import FR

RTP_PORT = 5000        #порт отправки RTP видео
CONTROL_PORT = 60001
worker = None

# проверка доступности камеры, возвращает True, если камера доступна в системе
def checkCamera():
    res = os.popen('vcgencmd get_camera').readline().replace('\n','') #читаем результат, удаляем \n
    dct = {}
    for param in res.split(' '): #разбираем параметры
        tmp = param.split('=')
        dct.update({tmp[0]: tmp[1]}) #помещаем в словарь
    return (dct['supported'] and dct['detected'])

def getIP():
    #cmd = 'hostname -I | cut -d\' \' -f1'
    #ip = subprocess.check_output(cmd, shell = True) #получаем IP
    res = os.popen('hostname -I | cut -d\' \' -f1').readline().replace('\n','') #получаем IP, удаляем \n
    return res



class Worker():
    def __init__(self):
       self.pc  = xmlrpc.client.ServerProxy('http://%s:%d' % ("10.42.0.1", 60002))
       self.ardHandler = ArdHandler(func=self.func_for_pc)
       self.fr = FR.FR(self)
       self.q = Queue()
       self.conn = Queue()
       self._stopped = False
       #self.cap = cv2.VideoCapture(0)

    def func_for_pc(self, msg):
        _ = self.pc.comReceiver(msg)

    def stop(self):
        #self.pc.comReceiver("RPi: Worker stopped!")
        print("Stoped commend receive")
        self._stopped = True
        self.ardHandler.stop()
        self.conn.put("stop")
        #raise SystemExit
        
            
def read():
    time.sleep(2)
    iden = worker.ardHandler.read()
    worker.func_for_pc("read")
    time.sleep(1)
    worker.func_for_pc("camera")
    time.sleep(1)
    worker.func_for_pc("square face")
    time.sleep(3)
    ans = worker.fr.read(iden-1)
    if ans == -1:
        worker.pc.comReceiver("error")
    else:
        if ans: worker.pc.comReceiver("match")
        else:   worker.pc.comReceiver("No match")
    time.sleep(2)
    worker.pc.comReceiver("return")
        
def read_mode():
    th = threading.Thread(target=read)
    th.start()
    return 0

def write():
    time.sleep(2)
    worker.ardHandler.write(len(worker.fr.known_face_encodings) + 1)
    time.sleep(1)
    worker.func_for_pc("camera")
    time.sleep(1)
    worker.func_for_pc("square face")
    time.sleep(3)
    worker.fr.write()
    time.sleep(3)
    worker.pc.comReceiver("return")

def write_mode():
    #print("Entered into write mode")
    th = threading.Thread(target=write)
    th.start()
    #print("done")
    return 0

def stop():
    th = threading.Thread(target=worker.stop)
    th.start()
    #worker.stop()
    return 0

def VideoStreaming(q, conn):
    cap = cv2.VideoCapture(0)
    _stopped = False
    
    context = zmq.Context()
    footage_socket = context.socket(zmq.PUB)
    footage_socket.connect('tcp://10.42.0.1:60000')
    recv_sock = context.socket(zmq.SUB)
    recv_sock.bind('tcp://10.42.0.69:6000')
    recv_sock.setsockopt_string(zmq.SUBSCRIBE, np.unicode(''))
    
    while not _stopped:
        #if not conn.empty: _stopped = True
        ret, frame = cap.read()
        if q.empty():
            q.put(frame)
        if ret:
            encoded, buffer = cv2.imencode('.jpg', frame)
            jpg_as_text = base64.b64encode(buffer)
            footage_socket.send(jpg_as_text)

            _ = recv_sock.recv_string()
    print("VideoStreaming stopped")

    
print('Start program')

assert checkCamera(), 'Raspberry Pi camera not found'
print('Raspberry Pi camera found')

# Получаем свой IP адрес
ip = getIP()
assert ip != '', 'Invalid IP address'
print('Robot IP address: %s' % ip)

print('OpenCV version: %s' % cv2.__version__)

print('initiating Serial communication with Arduino')

#initalize main object
worker = Worker()

# XML-RPC сервер управления в отдельном потоке
serverControl = SimpleXMLRPCServer((ip, CONTROL_PORT)) #запуск XMLRPC сервера
serverControl.logRequests = False #оключаем логирование
print('Control XML-RPC server listening on %s:%d' % (ip, CONTROL_PORT))

# register our functions
serverControl.register_function(read_mode)
serverControl.register_function(write_mode)
serverControl.register_function(stop)

#запускаем сервер в отдельном потоке
serverControlThread = threading.Thread(target = serverControl.serve_forever)
serverControlThread.daemon = True
serverControlThread.start()

pr = Process(target=VideoStreaming, args=(worker.q, worker.conn))
pr.start()

#главный цикл программы    
import gi
from gi.repository import GObject

GObject.threads_init()
mainloop = GObject.MainLoop()

try:
    #worker.pc.comReceiver("RPi: Worker started!")
    mainloop.run()

except (KeyboardInterrupt, SystemExit):
    print('Ctrl+C pressed')
    


#останов сервера
serverControl.server_close()
pr.join()

print('Program over...')


