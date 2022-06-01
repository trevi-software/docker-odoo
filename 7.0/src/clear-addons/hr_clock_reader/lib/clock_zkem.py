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

#from zkemapi import zkem

class Clock_Zkem:
    """
    Class for attendance clocks model Zkem from zkemapi
    https://bitbucket.org/johnmc/zkemapi
    """
    def __init__(self, uri, timeout=10):
        uri = uri.replace('/','').split(':')
        assert(len(uri) == 3)
        assert(uri[0] == 'udp')
        self._server_address = (uri[1], int(uri[2]))
        self.clock = zkem()
        self.timeout=timeout

    def connect(self):
        r = self.clock.connect(self._server_address[0],
                               port=self._server_address[1],
                               timeout=self.timeout)
        print "connect: ", r
        return r

    def attendances(self):
        r = self.clock.disable()
        print "disable: ", r
        r = self.clock.get_attendance_log()
        print "get_attendance_log: ", r
        r = self.clock.enable()
        print "enable: ", r

        verimode_dict = {
            'Check In (Code)': 'keyboard',
            'Check In (Fingerprint)': 'fingerprint',
            'Check Out (Code)': 'keyboard',
            'Check Out (Fingerprint)': 'fingerprint',
        }
        entsal_dict = {
            'Check In (Code)': 'sign_in',
            'Check In (Fingerprint)': 'sign_in',
            'Check Out (Code)': 'sign_out',
            'Check Out (Fingerprint)': 'sign_out',
        }

        n = 1
        for att in self.clock.unpack_attendance_log():
            card_id, ttime, mode = tuple(att)
            verimode = verimode_dict[mode]
            entsal = entsal_dict[mode]
            yield (n, card_id, verimode, entsal, ttime)
            n = n + 1

    def disconnect(self):
        r = self.clock.disconnect()
        print "disconnect: ", r

