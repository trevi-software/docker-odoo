#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyrigth (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
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

import time

from report import report_sxw

from ethiopic_calendar.ethiopic_calendar import ET_MONTHS_SELECTION_AM, ET_DAYOFMONTH_SELECTION
from ethiopic_calendar.pycalcal import pycalcal as pcc

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'time2ethiopic': self.time2ethiopic,
        })
    
    def time2ethiopic(self, t):
        
        # Convert to Ethiopic calendar
        pccDate = pcc.ethiopic_from_fixed(
                    pcc.fixed_from_gregorian(
                            pcc.gregorian_date(t[0], t[1], t[2])))
        
        return u'' + ET_MONTHS_SELECTION_AM[pccDate[1]-1]+' '+str(pccDate[2])+', '+str(pccDate[0])
