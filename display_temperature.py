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

import consumer_IB

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
        self.node_listener = consumer_IB.BeeArenaListener (proj_conf, path, verb = False, logfile = None)
        self.node_listener.start_rx ()
        # self.dict_casus_interface = {
        #     a_casu_number : assisipy.casu (rtc_file_name = a_rtc_filename, log = False)
        #     for a_casu_number, a_rtc_filename in casus_data
        # }
        self.initUI()
        self.timer = QtCore.QBasicTimer ()
        self.timer.start (SPEED, self)
        
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
#        self.drawNode (event, qp, 'casu-053', 50, 50)
#        self.drawNode (event, qp, 'casu-054', 250, 50)
#        self.drawNode (event, qp, 'casu-048', 450, 50)
        qp.end()

#    def keyPressEvent (self, event):
#        if event is not None:
#            print ('Key event {}'.format (event))
#            self.timer.stop ()
#            sys.exit (0)

    def update_casu_temp (self):
        # for casu_number, casu_interface in self.dict_casus_interface:
        #     self.temp_data [casu_number] = casu_interface.get_temp (assisipy.TEMP_WAX)
        for node_id in self.temp_data.keys ():
            #what = self.node_listener.get_latest_inval (node_id)
            ret, newstatedata = self.node_listener.process_all_input(
                node_id,
                stdstr=False,
             verb=False)
            if ret:
                self.temp_data [node_id] = float (newstatedata ['tref'])
            else:
                print ('Nothing for {}'.format (node_id))
            
    def timerEvent (self, event):
        print ('time')
        self.update_casu_temp ()
        self.update ()
        
    def drawNode (self, event, qp, casu, x, y, w, h):
        print ('Drawing casu {}'.format (casu))
        temperature = self.temp_data [casu]
        if temperature >= MIN_TEMPERATURE and temperature <= MAX_TEMPERATURE:
            temp_relative = (temperature - MIN_TEMPERATURE) / float (MAX_TEMPERATURE - MIN_TEMPERATURE)
            if temp_relative < 0.5:
                color = QtGui.QColor (0, 32, 255 - int (temp_relative * 255))
            else:
                color = QtGui.QColor (int ((temp_relative - 0.5) * 255), 32, 0)
            pen = QtGui.QPen (color)
            pen.setWidth (10)
            qp.setPen (pen)
            qp.drawEllipse (x, y, w, h)
                       
def main():
    app = QtGui.QApplication(sys.argv)
    print (sys.argv)
    ex = Example(['A', 'B', 'C'], '/home/pi/code/cfgs/1-line3/1-line3.conf', '/home/pi/code/cfgs/1-line3/')
#    ex = Example(['casu-053', 'casu-048', 'casu-054'], '/home/assisi/assisi/pedro/ARS18/cfgs/1-line3/1-line3.conf', '/home/assisi/assisi/pedro/ARS18/cfgs/1-line3/')
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
    
