#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
ZetCode PySide tutorial 

In this example, we draw text in Russian azbuka.

author: Jan Bodnar
website: zetcode.com 
last edited: August 2011
"""

import sys
from PySide import QtGui, QtCore
import math

import assisipy

import consumer_IB

MIN_TEMPERATURE = 26
MAX_TEMPERATURE = 39
SPEED = 1000

class Example(QtGui.QWidget):
    
    def __init__(self, list_nodes, proj_conf, path = '.'):
        super(Example, self).__init__()
        self.temp_data = {
            #a_node : MIN_TEMPERATURE + (MAX_TEMPERATURE - MIN_TEMPERATURE) / 2 + 1
            a_node : MIN_TEMPERATURE
            for a_node in list_nodes
        }
        self.bee_activity_data = {
            a_node : 0.0
            for a_node in list_nodes
        }
        if proj_conf is not None:
            self.node_listener = consumer_IB.BeeArenaListener (proj_conf, path, verb = False, logfile = None)
            self.node_listener.start_rx ()
        else:
            self.node_listener = None
        self.initUI()
        self.timer = QtCore.QBasicTimer ()
        self.timer.start (SPEED, self)
        self.counter = 0
        
    def initUI(self):      
        self.setGeometry(0, 0, 1200, 800)
        self.setWindowTitle('CASU temperature')
        self.show()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawNode (event, qp, 'A', 1190, 580, 100, 100)
        self.drawNode (event, qp, 'B', 960, 340, 300, 140)
        self.drawNode (event, qp, 'C', 740, 375, 100, 100)
        qp.end()

#    def keyPressEvent (self, event):
#        if event is not None:
#            print ('Key event {}'.format (event))
#            self.timer.stop ()
#            sys.exit (0)

    def update_casu_temp (self):
        if self.node_listener is None:
            return
        for node_id in self.temp_data.keys ():
            ret, newstatedata = self.node_listener.process_all_input(
                node_id,
                stdstr=False,
             verb=False)
            if ret:
                self.temp_data [node_id] = float (newstatedata ['tref'])
                self.bee_activity_data [node_id] = float (newstatedata ['avg'])
            else:
                print ('Nothing for {}'.format (node_id))
            
    def timerEvent (self, event):
        print ('time')
        self.update_casu_temp ()
        self.update ()
        self.counter += 1
        #self.temp_data [self.temp_data.keys () [0]] = self.temp_data [self.temp_data.keys () [0]] + 0.5
        
    def drawNode (self, event, qp, casu, x, y, w, h):
        print ('Drawing casu {}'.format (casu))
        temperature = self.temp_data [casu]
        if temperature >= MIN_TEMPERATURE and temperature <= MAX_TEMPERATURE:
            temp_relative = (temperature - MIN_TEMPERATURE) / float (MAX_TEMPERATURE - MIN_TEMPERATURE)
            if temp_relative < 0.5:
                color = QtGui.QColor (
                    0,
                    int (temp_relative * 32),
                    int ((1 - 2 * temp_relative) * 255)
                )
                shake_period = 10
                shake_intensity = 1
            else:
                color = QtGui.QColor (
                    int (2 * (temp_relative - 0.5) * 255),
                    int ((1 - temp_relative) * 32),
                    0
                )
                shake_period = 30
                shake_intensity = 2
            pen = QtGui.QPen (color)
            pen.setWidth (int (
                10
                #+ 10 * self.bee_activity_data [casu]
                + shake_intensity * math.sin (self.counter * shake_period)))
            qp.setPen (pen)
            qp.drawEllipse (x, y, w, h)
                       
def main():
    app = QtGui.QApplication(sys.argv)
    print (sys.argv)
    ex = Example(['A', 'B', 'C'], '/home/pi/code/cfgs/1-line3/1-line3.conf', '/home/pi/code/cfgs/1-line3/')
    #    ex = Example(['casu-053', 'casu-048', 'casu-054'], '/home/assisi/assisi/pedro/ARS18/cfgs/1-line3/1-line3.conf', '/home/assisi/assisi/pedro/ARS18/cfgs/1-line3/')
    #ex = Example (['A', 'B', 'C'], None)
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
    
