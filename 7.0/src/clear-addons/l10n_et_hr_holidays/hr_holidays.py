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

from datetime import datetime

from openerp.osv import fields, osv

from ethiopic_calendar.ethiopic_calendar import ET_MONTHS_SELECTION_AM
from ethiopic_calendar.pycalcal import pycalcal as pcc

class hr_holidays_status(osv.Model):
    
    _inherit = 'hr.holidays.status'
    
    _columns = {
        'ethiopic_name': fields.char('Ethiopic Name', size=512),
    }
    
    def get_remaining_days_by_employee(self, cr, uid, ids, employee_id, context=None):
        
        res = dict.fromkeys(ids, {'leaves_taken': 0, 'remaining_leaves': 0, 'max_leaves': 0})
        if employee_id:
            res = self.get_days(cr, uid, ids, employee_id, False, context=context)
        return res

class hr_holidays(osv.Model):
    
    _inherit = 'hr.holidays'

    _columns = {
        'return_date_et': fields.char('Ethiopic Return Date', size=128),
    }
    
    def time2ethiopic(self, year, month, day):
        
        # Convert to Ethiopic calendar
        pccDate = pcc.ethiopic_from_fixed(
                    pcc.fixed_from_gregorian(
                            pcc.gregorian_date(year, month, day)))
        
        return u'' + ET_MONTHS_SELECTION_AM[pccDate[1]-1]+' '+str(pccDate[2])+', '+str(pccDate[0])

    def onchange_enddate(self, cr, uid, ids, employee_id,
                         date_from, date_to, holiday_status_id, no_days, context=None):
        
        res = super(hr_holidays, self).onchange_enddate(cr, uid, ids, employee_id, date_from, date_to,
                                                        holiday_status_id, no_days, context=context)
        if res.get('value', False) and res['value'].get('return_date'):
            dt = datetime.strptime(res['value']['return_date'], '%B %d, %Y')
            res['value'].update({'return_date_et': self.time2ethiopic(int(dt.strftime('%Y')),
                                                                      int(dt.strftime('%m')),
                                                                      int(dt.strftime('%d')))})
        elif res.get('value', False):
            res['value'].update({'return_date_et': False})
        return res
