#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt, QEventLoop, QThread, QObject, pyqtSlot, pyqtSignal
from PyQt5.Qt import QImage

import sys, os

import zmq
import base64
import numpy as np
import cv2

class Spawer(QtCore.QThread):
    #mutex = QtCore.QMutex()
    def __init__(self, on_recive, parent=None):#write_msg, parent=None):
        QtCore.QThread.__init__(self, parent)
        self._stopped = False
        #self.write_msg = write_msg
        self._on_recive = on_recive
        self.stop_trigger.connect(self.stop)

        self.context = zmq.Context()
        self.footage_socket = self.context.socket(zmq.SUB)
        self.footage_socket.bind('tcp://10.42.0.1:60000')
        self.footage_socket.setsockopt_string(zmq.SUBSCRIBE, np.unicode(''))
        self.send_sock = self.context.socket(zmq.PUB)
        self.send_sock.connect('tcp://10.42.0.68:6000')
        
    stop_trigger  = pyqtSignal()
                            
    def run(self):
        #self.write_msg("IMG Handler stared!")
        while not self._stopped:
            buff = self.footage_socket.recv_string()
            img = base64.b64decode(buff)
                #i = QImage()
                #i.loadFromData(img)
                #self._on_recive(i)
            npimg = np.fromstring(img, dtype=np.uint8)
            source = cv2.imdecode(npimg, 1)
            self._on_recive(source)
                #cv2.imshow("Stream", source)
                #cv2.waitKey(1)
            self.send_sock.send(b'ok')
            
        #self.write_msg("IMG Handler Stopped")
            
    def stop(self):
        self._stopped = True
        #self.send_sock.send(b'ok')


    
