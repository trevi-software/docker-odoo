# -*- encoding: utf-8 -*-
##############################################################################
#
#    Clock Reader for OpenERP
#    Copyright (C) 2004-2009 Moldeo Interactive CT
#    (<http://www.moldeointeractive.com.ar>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import socket
import sys
import binascii
from binascii import hexlify, unhexlify
import time
from time import sleep
from struct import unpack, pack
from urlparse import urlsplit
from sys import stderr
from .. import timeutils as tu

class Clock_F5:
    """
    Class for attendance clocks model F5.
    http://www.digitouno.com.ar/f5.html
    """
    def __init__(self, uri, timeout = 3.0):
        """
        Init the Clock with uri information.

        The following example test the connection and
        read the attendences stored in the clock. After
        delete all entries in the clock and disconnect.

        >>> import time
        >>> C = Clock_F5('udp://localhost:9999/', timeout=3.0)
        >>> C.connect()
        ('Ver 6.10 Jun 19 2007', '~OS=1')
        >>> attendances = [ a for a in C.attendances() ]
        >>> f = open('test.out', 'w')
        >>> for t in attendances: print >> f, t, time.strftime("%d/%m/%Y %H:%M:%S", time.localtime(t[-1]))
        >>> f.close()
        >>> len(attendances) > 0
        True
        >>> C.clean()
        >>> C.disconnect()
        """
        uri = uri.replace('/','').split(':')
        assert(len(uri) == 3)
        assert(uri[0] == 'udp')
        self._server_address = (uri[1], int(uri[2]))
        self._sid = None
        self._time = 0
        self._serial = 0
        self._state = None
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(timeout)

    def _send(self, command, outdata='', time=None, serial=None, size=2048,
              debug=True):
        if serial == None: serial = self._serial + 1
        if time   == None: time = self._time
        if self._sid == None: self._sid = 0
        data = pack("<HHHH", command % 0xFFFF, time % 0xFFFF, self._sid %
                    0xFFFF, serial % 0xFFFF) + outdata
        if debug:
            print >> stderr, "%i:Snd: " % self._time, self._sid, serial, repr(outdata), hexlify(data)
        sleep(0.1)
        self._sock.sendto(data, self._server_address)
        recv = self._sock.recv(size)
        (code, time, sid, nserial) = unpack("<HHHH", recv[:8])
        if debug:
            print >> stderr, "%i:Rcv: " % self._time, self._sid, nserial, repr(recv[8:]), hexlify(recv)
        assert(nserial == serial)
        self._time = time
        self._serial = nserial
        self._sid = sid
        return code, recv[8:]

    def _get_info(self, varname, time=None, serial=None):
        print >> stderr, "get_info {"
        if self._state != 'connected': raise 'not connected'
        code, recv = self._send(11, '~%s\x00' % varname, time=time, serial=serial)
        assert(code == 2000)
        print >> stderr, "get_info }"
        return recv

    def _action0(self): # Aqui se conecta
        print >> stderr, "action0 {"
        assert(self._state == None)
        code, recv = self._send(1000, serial=0, time=64535)
        assert(code == 2000)
        self._state = 'connected'
        print >> stderr, "action0 }"
        return True

    def get_firmware_version(self):
        print >> stderr, "get_firmware_version {"
        assert(self._state == 'connected')
        code, recv = self._send(1100, time=self._time+899)
        assert(code == 2000)
        os = self._get_info('OS', time=self._time+3444)
        print >> stderr, "get_firmware_version }"
        return recv[:-1], os[:-1]

    def _action3(self): # Aqui empieza la lectura
        print >> stderr, "action3 {"
        assert(self._state == 'connected')
        # Aqui no es el mismo numero.
        # Captura 01: -60705;
        # Captura 02: -60706;
        # Captura 03:   4830;
        # Ahora, con el modulo en 0xFFFF, se fija el numero en time-60705
        code, recv = self._send(500, '\xff\x7f\x00\x00', time=self._time-60705)
        assert(code == 2000)
        print >> stderr, "action3 }"
        return True

    def _action4(self):
        print >> stderr, "action4 {"
        assert(self._state == 'connected')
        code, recv = self._send(69, '\xb0\x1f', time=self._time-6182)
        assert(code == 2000)
        print >> stderr, "action4 }"
        return True

    def _action5(self):
        print >> stderr, "action5 {"
        assert(self._state == 'connected')
        code, recv = self._send(1020, '\x03\x01\x00\x00\x07', time=self._time+718)
        assert(code == 65535)
        print >> stderr, "action5 }"
        return True

    def _action6(self):
        print >> stderr, "action6 {"
        assert(self._state == 'connected')
        code, recv = self._send(1003, '\x00\x00\x00\x00', time=self._time-1004)
        assert(code == 2000)
        print >> stderr, "action6 }"
        return True

    def _attendance_iterator(self): # Read data
        print >> stderr, "attendance_iterator {"
        assert(self._state == 'connected')
        code, recv = self._send(13, time=self._time+1986)
        assert(code == 1500)

        print >> stderr, "attendance_iterator :"

        # Leeo todos los datos
        code = 1501
        i = 0
        while code == 1501:
            r = self._sock.recv(2048)
            recv += r[8:]
            (code, ttime, nserial) = unpack("<HIH", r[:8])
            i = i + 1
        self._time = ttime

        print >> stderr, "attendance_iterator ::"

        n = 1
        l = len(recv)-12
        l = ( l / 8 ) * 8

        stream_len, XXX, data_len = unpack('<III', recv[:12])

        assert(l == data_len)

        for i in range(12,l,8):
            trj, code, st = unpack('<HHI', recv[i:i+8])
            dt = st + 940388400 # seconds since the epoch
            verimode = (code & 0x08 and 'fingerprint') or 'keyboard'
            entsal = (code & 0x20 and 'sign_out') or 'sign_in'
            yield (n, trj, verimode, entsal, tu.datetime.fromtimestamp(dt))
            n = n + 1

        print >> stderr, "attendance_iterator }"
        return

    def _action8(self):
        # No es el mismo numero.
        # CAPTURE01:  46085,
        # CAPTURE02:   9272,
        # capture03:   8783,
        # Ahora, con modulo en 0xFFFF aparece un patron.
        times = { 28816: 46085,
                     94:  9272,
                    583:  8783,
                  23900: 51001,
                  24256: 50645 }
        if self._sid in times:
            t = times[self._sid]
        else:
            t = 1000
        os = self._get_info('ExtendFmt', time=self._time + t) # No es el mismo numero
        return True

    def _action9(self):
        assert(self._state == 'connected')
        code, recv = self._send(9, '\x05', time=self._time+6956)
        assert(code == 1500)

        for i in range(7):
            # TODO: Procesar entradas
            recv = self._sock.recv(2048)

        return True

    def _action10(self): # Aqui deberia empezar la desconexion
        assert(self._state == 'connected')
        code, recv = self._send(1020, '\x03\x01\x00\x00\x05', time=self._time+7375)
        assert(code == 65535)
        return True

    def _action11(self):
        assert(self._state == 'connected')
        code, recv = self._send(1002, time=self._time-1003)
        assert(code == 2000)
        return True

    def _action12(self):
        assert(self._state == 'connected')
        code, recv = self._send(1001, time=self._time+998)
        assert(code == 2000)
        return True

    def connect(self):
        """
        Connect with the clock and get information.
        """
        print >> stderr, "connect {"
        self._action0()
        r = self.get_firmware_version()
        print >> stderr, "connect }"
        return r

    def attendances(self):
        """
        Iterator over attendances.
        """
        print >> stderr, "attendances {"
        self._action3()
        self._action4()
        self._action5()
        self._action6()
        for att in self._attendance_iterator():
            yield att
        self._action8()
        self._action9()
        print >> stderr, "attendances }"

    def clean(self):
        """
        Clean information of the clock.
        """
        print >> stderr, "clean {"
        print >> stderr, "clean }"
        #raise NotImplementedError

    def disconnect(self):
        """
        Disconnect from the clock.
        """
        print >> stderr, "disconnect {"
        self._action10()
        self._action11()
        self._action12()
        print >> stderr, "disconnect }"

    def test(self):
        """
        Test the connection with the clock.
        """
        try:
            self.connect()
            self.disconnect()
            return True
        except:
            return False

def test_suite():
    import doctest
    return doctest.DocTestSuite()

if __name__ == "__main__":
    import unittest
    runner = unittest.TextTestRunner()
    runner.run(test_suite())

