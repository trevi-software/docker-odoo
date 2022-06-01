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

from openerp import netsvc
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DATEFORMAT

class hr_employee(osv.Model):
    
    _name = 'hr.employee'
    _inherit= 'hr.employee'
    
    _columns = {
        'initial_annual_leave': fields.float('Initial Annual Leave', readonly=True),
    }
    
    def create(self, cr, uid, vals, context=None):
        
        ee_id = super(hr_employee, self).create(cr, uid, vals, context=context)
        
        if not vals.get('initial_annual_leave', False):
            return ee_id
        
        # Get Annual Leave Holiday Status
        #
        al_status_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code', '=', 'LVANNUAL')],
                                                                  context=context)
        if len(al_status_ids) == 0:
            return ee_id
        
        # Get associated accrual account
        #
        accrual_obj = self.pool.get('hr.accrual')
        accrual_line_obj = self.pool.get('hr.accrual.line')
        
        accrual_ids = accrual_obj.search(cr, uid, [('holiday_status_id', '=', al_status_ids[0])],
                                         context=context)
        
        if len(accrual_ids) == 0:
            return ee_id
        
        # Deposit to the accrual account
        #
        accrual_line = {
            'date': datetime.now().strftime(OE_DATEFORMAT),
            'accrual_id': accrual_ids[0],
            'employee_id': ee_id,
            'amount': vals['initial_annual_leave'],
        }
        line_id = accrual_line_obj.create(cr, uid, accrual_line, context=context)
        accrual_obj.write(cr, uid, accrual_ids[0], {'line_ids': [(4, line_id)]})
        
        # Add the leave and trigger validation workflow
        #
        leave_allocation = {
            'name': 'Imported Annual Leave',
            'type': 'add',
            'employee_id': ee_id,
            'number_of_days_temp': vals['initial_annual_leave'],
            'holiday_status_id': al_status_ids[0],
            'from_accrual': True,
        }
        holiday_id = self.pool.get('hr.holidays').create(cr, uid, leave_allocation, context=context)
        netsvc.LocalService('workflow').trg_validate(uid, 'hr.holidays', holiday_id, 'validate', cr)
        
        return ee_id
        