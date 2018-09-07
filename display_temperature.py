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

import assisipy

import inter_domset.ISI.consumer_IB

MIN_TEMPERATURE = 26
MAX_TEMPERATURE = 39
SPEED = 1000

class Example(QtGui.QWidget):
    
    def __init__(self, list_nodes, proj_conf, path = '.'):
        super(Example, self).__init__()
        self.temp_data = {
            a_node : 29
            for a_node in list_nodes
        }
        self.node_listener = inter_domset.ISI.consumer_IB.BeeArenaListener (proj_conf, path, verb = False, logfile = None)
        self.node_listener.start_rx ()
        # self.dict_casus_interface = {
        #     a_casu_number : assisipy.casu (rtc_file_name = a_rtc_filename, log = False)
        #     for a_casu_number, a_rtc_filename in casus_data
        # }
        self.initUI()
        self.timer = QtCore.QBasicTimer ()
        self.timer.start (SPEED, self)
        
    def initUI(self):      
        self.setGeometry(300, 300, 280, 170)
        self.setWindowTitle('CASU temperature')
        self.show()

    def paintEvent(self, event):
        qp = QtGui.QPainter()
        qp.begin(self)
        self.drawNode (event, qp, 32, 100, 100)
        qp.end()

    def update_casu_temp (self):
        # for casu_number, casu_interface in self.dict_casus_interface:
        #     self.temp_data [casu_number] = casu_interface.get_temp (assisipy.TEMP_WAX)
        for node_id in self.list_nodes:
            what = self.node_listener.get_latest_inval (node_id)
            if what is not None:
                print (what)
                self.temp_data [node_id] = what.get ('Temp')[-1]
            
    def timerEvent (self, event):
        print ('time')
        self.update_casu_temp ()
        self.update ()
        
    def drawNode (self, event, qp, casu, x, y):
        print ('Drawing casu {}'.format (casu))
        temperature = self.temp_data [casu]
        if temperature >= MIN_TEMPERATURE and temperature <= MAX_TEMPERATURE:
            temp_relative = (temperature - MIN_TEMPERATURE) / float (MAX_TEMPERATURE - MIN_TEMPERATURE)
            if temp_relative < 0.5:
                color = QtGui.QColor (0, 32, 255 - int (temp_relative * 255))
            else:
                color = QtGui.QColor (int ((temp_relative - 0.5 * 255)), 32, 0)
            pen = QtGui.QPen (color)
            pen.setWidth (10)
            qp.setPen (pen)
            qp.drawEllipse (x, y, 100, 100)
            # qp.setPen (QtGui.QColor (255, 255, 255))
            # qp.drawEllipse (x + 5, y + 5, 90, 90)
                       
def main():
    app = QtGui.QApplication(sys.argv)
    print (sys.argv)
    ex = Example([], sys.argv [1])
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
    
