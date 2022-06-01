#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyrigth (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>
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

from datetime import datetime, timedelta

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DATEFORMAT
from report import report_sxw

from ethiopic_calendar.ethiopic_calendar import ET_MONTHS_SELECTION_AM
from amount_to_text_am_et import amount_to_text

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_amharic_text': self.get_amharic_text,
            'formatted_ethiopic_dob': self.formatted_ethiopic_dob,
        })
    
    def get_amharic_text(self, amount):
        return u'' + amount_to_text(amount)
    
    def formatted_ethiopic_dob(self, m, d, y):
        
        return u'' + ET_MONTHS_SELECTION_AM[int(m)-1]+' '+str(d)+', '+str(y)
