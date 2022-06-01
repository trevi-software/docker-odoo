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

import logging
_l = logging.getLogger(__name__)

class hr_al(osv.TransientModel):
    
    _name = 'hr.holidays.al'
    
    _columns = {
        'department_id': fields.many2one('hr.department', 'Department'),
        'al_line_ids': fields.one2many('hr.holidays.al.line', 'al_id', 'Annual Leave Lines'),
    }
    

    def _get_lines(self, cr, uid, context=None):
        
        if context == None:
            context= {}
        
        res = []
        ee_obj = self.pool.get('hr.employee')
        department_id = context.get('active_id', False)
        ee_ids = ee_obj.search(cr, uid, [('department_id', '=', department_id),
                                         ('active', '=', True)], context=context)
        data = ee_obj.read(cr, uid, ee_ids, ['initial_annual_leave'], context=context)
        for record in data:
            vals = {
                    'employee_id': record['id'],
                    'days': record['initial_annual_leave'],
            }
                
            res.append(vals)
        return res
    
    def _get_department(self, cr, uid, context=None):
        
        if context == None:
            context= {}
        department_id = context.get('active_id', False)
        return  department_id
    
    _defaults = {
        'department_id': _get_department,
        'al_line_ids': _get_lines,
    }
    
    def _add(self, cr, uid, ee_id, days, context=None):
        
        if days < 0.01:
            return 
        
        # Get Annual Leave Holiday Status
        #
        al_status_ids = self.pool.get('hr.holidays.status').search(cr, uid, [('code', '=', 'LVANNUAL')],
                                                                   context=context)
        if len(al_status_ids) == 0:
            return
        
        # If there is already initial annual leave don't double-add
        #
        ee_obj = self.pool.get('hr.employee')
        eedata = ee_obj.read(cr, uid, ee_id, ['initial_annual_leave'], context=context)
        if eedata.get('initial_annual_leave', False) and eedata['initial_annual_leave'] > 0:
            return
        
        # Get associated accrual account
        #
        accrual_obj = self.pool.get('hr.accrual')
        accrual_line_obj = self.pool.get('hr.accrual.line')
        
        accrual_ids = accrual_obj.search(cr, uid, [('holiday_status_id', '=', al_status_ids[0])],
                                         context=context)
        
        if len(accrual_ids) == 0:
            return
        
        # Deposit to the accrual account
        #
        accrual_line = {
            'date': datetime.now().strftime(OE_DATEFORMAT),
            'accrual_id': accrual_ids[0],
            'employee_id': ee_id,
            'amount': days,
        }
        line_id = accrual_line_obj.create(cr, uid, accrual_line, context=context)
        accrual_obj.write(cr, uid, accrual_ids[0], {'line_ids': [(4, line_id)]})
        
        # Add the leave and trigger validation workflow
        #
        leave_allocation = {
            'name': 'Initial Annual Leave transfered from previous system',
            'type': 'add',
            'employee_id': ee_id,
            'number_of_days_temp': days,
            'holiday_status_id': al_status_ids[0],
            'from_accrual': True,
        }
        holiday_id = self.pool.get('hr.holidays').create(cr, uid, leave_allocation, context=context)
        netsvc.LocalService('workflow').trg_validate(uid, 'hr.holidays', holiday_id, 'validate', cr)
        ee_obj.write(cr, uid, ee_id, {'initial_annual_leave': days}, context=context)
    
    def add_records(self, cr, uid, ids, context=None):
        
        data = self.read(cr, uid, ids[0], ['al_line_ids'], context=context)
        for line in self.pool.get('hr.holidays.al.line').browse(cr, uid, data['al_line_ids'],
                                                                context=context):
            self._add(cr, uid, line.employee_id.id, line.days, context=context)
        
        return {'type': 'ir.actions.act_window_close'}

class hr_al_line(osv.TransientModel):
    
    _name = 'hr.holidays.al.line'
    
    _columns = {
        'al_id': fields.many2one('hr.holidays.al', 'Annual Leave by Dept.'),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'days': fields.float('Days', required=True),
    }
