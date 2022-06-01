#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyrigth (C) 2013-2015 Michael Telahun Makonnen <mmakonnen@gmail.com>
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

import locale
from datetime import datetime, timedelta
from pytz import timezone, utc

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DATEFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DATETIMEFORMAT
from openerp.tools.float_utils import float_is_zero
from report import report_sxw
from __builtin__ import str

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_no': self.get_no,
            'get_end': self.get_end,
            'get_al_allocations': self.get_al_allocations,
            'get_al_requests': self.get_al_requests,
            'get_al_remain': self.get_al_remain,
            'get_salary': self.get_salary,
            'get_al_value': self.get_al_value,
            'get_al_value_subtotal': self.get_al_value_subtotal,
            'get_al_value_total': self.get_al_value_total,
        })
        
        self.LVCODES = ['LVANNUAL']

        self.start_date = False
        self.end_date = False
        self.department_id = False
        self.employee_id = False
        self.no = 0
        self._al_alloc = 0
        self._al_req = 0
        self._sl = 0
        self._ml = 0
        self._ol = 0
        self.value_subtotal = 0
        self.value_total = 0
    
    def set_context(self, objects, data, ids, report_type=None):
        if data.get('form', False):
            if data['form'].get('date_end', False):
                self.end_date = data['form']['date_end'] + ' 23:59:59'
        
        return super(Parser, self).set_context(objects, data, ids, report_type=report_type)
    
    def get_end(self):
        return datetime.strptime(self.end_date, OE_DATETIMEFORMAT).strftime('%B %d, %Y')

    def fmt_float(self, f, d):
#        locale.setlocale(locale.LC_ALL, '')
#        strAmount = locale.format(("%."+str(d)+"f"), f, grouping=True)
        strFloat = "{0:.2f}".format(f)
        return float(strFloat)
    
    def reset(self, employee_id, department_id):
        
        if not self.employee_id or self.employee_id != employee_id:
            self._al_alloc = 0
            self._al_req = 0
            self.employee_id = employee_id
        
        if not self.department_id or self.department_id != department_id:
            self.value_subtotal = 0
            self.department_id = department_id
        
        return
    
    def get_no(self):
        
        self.no += 1
        return self.no

    def get_salary(self, employee):
        
        res = 0.00
        if employee.contract_id:
            res = employee.contract_id.wage
        return res
    
    def get_al_value(self, employee):
        
        al_remaining = self.get_al_remain(employee.id)
        al_remaining = isinstance(al_remaining, (float, int, long)) and al_remaining or 0.00
        salary = self.get_salary(employee)
        res = salary / 26.0 * al_remaining
        self.value_subtotal += res
        self.value_total += res
        return self.fmt_float(res, 2)
    
    def get_al_value_subtotal(self):
        
        return self.fmt_float(self.value_subtotal, 2)
    
    def get_al_value_total(self):
        
        return self.fmt_float(self.value_total, 2)
        
    def _get_leave_ids(self, employee_id, holiday_type, codes):
        
        if isinstance(codes, str):
            codes = [codes]
        
        leave_obj = self.pool.get('hr.holidays')
        if holiday_type == 'add':
            leave_ids = leave_obj.search(self.cr, self.uid, [('holiday_status_id.code', 'in', codes),
                                                             ('type', '=', holiday_type),
                                                             ('write_date', '<=', self.end_date),
                                                             ('state', 'in', ['validate', 'validate1']),
                                                             ('employee_id', '=', employee_id),
                                                            ])
        else:
            leave_ids = leave_obj.search(self.cr, self.uid, [('holiday_status_id.code', 'in', codes),
                                                             ('type', '=', holiday_type),
                                                             ('date_from', '<=', self.end_date),
                                                             ('state', 'in', ['validate', 'validate1']),
                                                             ('employee_id', '=', employee_id),
                                                            ])
        return leave_ids
    
    def get_leave(self, employee_id, holiday_type, codes):
        
        leave_ids = self._get_leave_ids(employee_id, holiday_type, codes)
        res = len(leave_ids)
        return res
    
    def get_leave_days(self, leave_ids):
        
        sum_days = 0.0
        data = self.pool.get('hr.holidays').read(self.cr, self.uid, leave_ids,
                                                 ['number_of_days'])
        for d in data:
            sum_days += d['number_of_days']
        
        return sum_days
    
    def get_al_allocations(self, employee_id, department_id):
        
        self.reset(employee_id, department_id)
        leave_ids = self._get_leave_ids(employee_id, 'add', ['LVANNUAL'])
        res = self.get_leave_days(leave_ids)
        self._al_alloc += res
        return (res and res or '-')
    
    def get_al_requests(self, employee_id, department_id):
        
        self.reset(employee_id, department_id)
        leave_ids = self._get_leave_ids(employee_id, 'remove', ['LVANNUAL'])
        res = self.get_leave_days(leave_ids)
        self._al_req += res
        return (res and res or '-')
    
    def get_al_remain(self, employee_id):
        
        remain = self._al_alloc + self._al_req
        return (remain and remain or '-')
    
    def get_sum_al_alloc(self):
        return self._al_alloc and self._al_alloc or '-'
    
    def get_sum_al_req(self):
        return self._al_req and self._al_req or '-'
