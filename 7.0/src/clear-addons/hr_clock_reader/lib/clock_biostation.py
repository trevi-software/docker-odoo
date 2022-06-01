#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import xmlrpclib

from datetime import datetime

class Clock_BioStation:
    
    # This module is for:
    #     BioStation and related scanners manufactured by Suprema (supremainc.com)
    #
    # I do not currently have a Linux SDK for these machines so, I created a
    # minimal console application for windows that reads successful ID events
    # from the machine and outputs it to stdout in CSV format. A minimal python
    # XMLRPC server that runs on the windows machine is used to query this
    # information from the scanner upon request. This module implements the
    # XMLRPC client to query said data.
    #
    
    def __init__(self, uri, server_uri=None, timeout=0):

        self.clock_uri = uri
        uri = uri.replace('/','').split(':')
        assert(len(uri) == 3)
        assert(uri[0] == 'tcp')
        self._clock_address = (uri[1], int(uri[2]))

        self.server_uri = server_uri
        self._server_address = None
        if server_uri not in [None, False]:
            server_uri = server_uri.replace('/','').split(':')
            assert(len(uri) == 3)
            assert(uri[0] == 'tcp')
            self._server_address = (server_uri[1], int(server_uri[2]))

        self._device_id = 0
        self._timeout = timeout
    
    def _do_query(self, dtStart=None, dtEnd=None):

        s = xmlrpclib.ServerProxy(self.server_uri)
        
        res = []
        if dtStart == None and dtEnd == None:
            try:
                output = s.get_all_identifications(self._clock_address[0], self._clock_address[1])
            except:
                return res
        else:
            strStart = ''
            strEnd = ''
            if dtStart != None:
                strStart = dtStart.strftime('%Y-%m-%d %H:%M:%S')
            if dtEnd != None:
                strEnd = dtEnd.strftime('%Y-%m-%d %H:%M:%S')
            
            try:
                output = s.get_identifications(self._clock_address[0], self._clock_address[1],
                                               strStart, strEnd)
            except:
                return res

        res = output.split('\n')
        return res
    
    def attendances(self, dtStart=None, dtEnd=None):
        
        res = []
        csv_list = self._do_query(dtStart, dtEnd)
        if len(csv_list) > 0:
            i = 1
            _found_start = False
            for line in csv_list:
                if line in ['START'] and not _found_start:
                    _found_start = True
                    continue
                elif line in ['END']:
                    break
                elif not _found_start:
                    continue
                
                _split = line.split(',')
                if _split[2] == 'Identify Success':
                    dt = datetime.strptime(_split[1], '%Y-%m-%d %H:%M:%S')
                    action = 'sign_in'
                    res.append((i, int(_split[0]), 'fingerprint', action, dt))
                
                i += 1
        
        return res
    
    def connect(self):
        
        s = xmlrpclib.ServerProxy(self.server_uri)
        try:
            s.test_connection(self._clock_address[0], self._clock_address[1])
        except xmlrpclib.Fault:
            return False
        except xmlrpclib.ProtocolError:
            return False
        except xmlrpclib.Error:
            return False
        except:
            return False
        return True
    
    def disconnect(self):
        
        return True
    
    def clean(self):
        
        return True
