#!/usr/bin/env python

# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

from twisted.python import log, usage
from twisted.internet import defer, task
from twisted.internet.protocol import Protocol, ClientFactory, ServerFactory, Factory
from twisted.protocols import basic
import sys, time, struct
import ipdb

prevTime = 0.0
streamError = []

if sys.platform == 'win32':
    from twisted.internet import win32eventreactor
    win32eventreactor.install()

class OutputProtocol(object,basic.LineOnlyReceiver):
        
    def __init__(self):
        self.delimiter = '\n'
        self.count = 0

    def connectionMade(self):
        print ("Got a RPi connection!")
        self.transport.write("hello :-)!\r\n")

        self.factory.client_list.append(self)

        # dfd = defer.Deferred()
        # dfd.addCallback(self.sendMsg)
        # self.factory.client_list[self]=dfd

    def connectionLost(self, reason):
        print "Lost client %s! Reason: %s\n" % (self, reason)
        # self.factory.client_list.pop(self)
        self.factory.client_list.remove(self)

    # def lineReceived(self,data):
    #     super(InputProtocol,self).writeLog(self.dataBuff)
    #     self.dataBuff=[]
    #     self.count=0

    def sendMsg(self,data):
        '''#header 0x7E is new packet 
        header = '\x7E'
        self.transport.write('header')
        #0x01 is sensor data 
        packetType='\x01'
        self.transport.write(packetType)
        #seven values at 4 bytes each = 28 bytes in total
        packetLength = 28
        self.transport.write(packetLength)
        #for some reason, data is a list of tuples so we need to break it up into a string
        '''
        # for el in data:
        #     self.transport.write(pack('f',el[0])+"\n")

        # self.transport.write("\r\n")
        self.transport.write(str(data)+"\r\n")

class OutputProtocolFactory(ServerFactory):
    
    protocol = OutputProtocol

    def __init__(self):
        # self.client_list = {}
        self.client_list = []
    
    # def recycle(self, client):
    #     for c in self.client_list:
    #         if c == client:
    #             dfd = defer.Deferred()
    #             dfd.addCallback(c.sendMsg)
    #             self.client_list[c], dfd = dfd, None    #make it easier on garbage collector

    def sendToAll(self, data):
        # check if dict is empty
        if self.client_list:
            # for client, dfd in self.client_list.iteritems():
            for client in self.client_list:
                # if dfd is not None:
                    # print ("deferred fired")
                    # dfd.callback(data)
                    # self.recycle(client)
                client.sendMsg(data)

# class InputProtocol(object, basic.LineOnlyReceiver, InputLogger):
class InputProtocol(basic.LineOnlyReceiver):
    
    def __init__(self, outputHandle):
        self.delimiter = '\n'
        self.dataBuff = []
        self.outputHandle= outputHandle
        print ("Input Protocol built")

    def connectionMade(self):
        print ("Connected to Motive")

    def lineReceived(self,data):
        # print ("received line")
        global prevTime

        currTime = time.clock()
        timeInterval = currTime - prevTime

        print 'Size of data: %d\n' %(sys.getsizeof(data))

        timestamp, x, y, z = struct.unpack("!ffff", data)

        print 'timestamp: %f\tx:%f\ty:%f\tz:%f\n' % (timestamp, x, y, z)

        self.dataBuff.append([timestamp, (x,y,z)])

        outputFile.write(str(self.dataBuff))
        outputFile.write('\tTime Interval: %f\tErrors: %s\n' %(timeInterval, streamError))
        prevTime = currTime
        
        # ipdb.set_trace()
            
        self.outputHandle.sendToAll(self.dataBuff)
        self.dataBuff=[]
     
class InputProtocolFactory(ClientFactory):
    # protocol = InputProtocol

    def __init__(self, outputHandle):
        self.outputHandle=outputHandle

    def startedConnecting(self, connector):
        print 'Started to connect.'

    def buildProtocol(self, addr):
        print 'Connected.'
        return InputProtocol(self.outputHandle)

    def clientConnectionLost(self, connector, reason):
        print 'Lost connection.  Reason:', reason
        reactor.stop()
        sys.exit()

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason
        reactor.stop()
        sys.exit()

if __name__ == '__main__':
    from twisted.internet import reactor

    outputFile = open(r'Data Files/motive_results.txt', 'w+')

    out = OutputProtocolFactory()
    reactor.listenTCP(53335, out, interface="192.168.95.109")
    reactor.connectTCP("192.168.95.109",27015,InputProtocolFactory(out))

    reactor.run()

