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

from datetime import datetime

from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.translate import _

from report import report_sxw

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'format_date': self.format_date,
            'format_date_et': self.format_date_et,
            'get_remaining_leaves': self.get_remaining_leaves,
            'get_taken_leaves': self.get_taken_leaves,
            'get_hrm': self.get_hrm,
        })

    def format_date(self, date_str):
        
        if not date_str:
            return ''
        d = datetime.strptime(date_str, OE_DTFORMAT)
        return d.strftime("%b %d, %Y")

    def format_date_et(self, date_str):
        
        if not date_str:
            return ''
        d = datetime.strptime(date_str, OE_DTFORMAT)
        return self.pool.get('hr.holidays').time2ethiopic(d.year, d.month, d.day)
    
    def get_remaining_leaves(self, leave):
        
        obj = self.pool.get('hr.holidays.status')
        res = obj.get_remaining_days_by_employee(self.cr, self.uid, [leave.holiday_status_id.id],
                                                 leave.employee_id.id)
        if res[leave.holiday_status_id.id].get('max_leaves', False) and res[leave.holiday_status_id.id]['max_leaves'] > 0:
            days = res[leave.holiday_status_id.id]['remaining_leaves']
            if leave.state not in ['validate', 'validate1']:
                days = res[leave.holiday_status_id.id]['remaining_leaves'] - leave.number_of_days_temp
        else:
            days = ''
        
        return days
    
    def get_taken_leaves(self, leave):
        
        obj = self.pool.get('hr.holidays.status')
        res = obj.get_remaining_days_by_employee(self.cr, self.uid, [leave.holiday_status_id.id],
                                                 leave.employee_id.id)
        if res[leave.holiday_status_id.id].get('max_leaves', False) and res[leave.holiday_status_id.id]['max_leaves'] > 0:
            days = res[leave.holiday_status_id.id]['max_leaves'] - res[leave.holiday_status_id.id]['remaining_leaves']
            
            # We only want leaves taken so far, *EXCLUDING* this one
            if leave.state in ['validate', 'validate1']:
                days -= leave.number_of_days_temp
        else:
            days = ''
        
        return days
    
    def get_hrm(self):
        
        hrm_data = ('', '', _('HR Manager'), u'የሠው ሃይል አስተዳደር')
        hrm_dict = self.pool.get('hr.config.settings').get_default_hr_manager_id(self.cr,
                                                                                 self.uid,
                                                                                 False)
        hrm_id = hrm_dict['hr_manager_id']
        if hrm_id != False:
            hrm = self.pool.get('hr.employee').browse(self.cr, self.uid, hrm_id)
            hrm_data = (hrm.name, hrm.ethiopic_name, hrm.contract_id.job_id.name, hrm.contract_id.job_id.ethiopic_name)
        
        return hrm_data
