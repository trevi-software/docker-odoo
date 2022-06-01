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

from datetime import datetime, timedelta

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.translate import _

class enroll_employee(osv.TransientModel):
    
    _name = 'hr.benefit.enroll.employee'
    _description = 'Employee Benefit Enrollment Form'
    
    _columns = {
        'benefit_id': fields.many2one('hr.benefit', 'Benefit', required=True),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'start_date': fields.date('Enrollment Date', required=True),
        'end_date': fields.date('Termination Date'),
    }
    
    def _get_benefit(self, cr, uid, context=None):
        
        if context == None:
            context = {}
        return context.get('active_id', False)
    
    _defaults = {
        'benefit_id': _get_benefit,
        'start_date': datetime.today().strftime(OE_DFORMAT),
    }
    
    def do_enroll(self, cr, uid, ids, context=None):
        
        policy_obj = self.pool.get('hr.benefit.policy')
        data = self.read(cr, uid, ids[0], [], context=context)
        benefit_id = data.get('benefit_id', False) and data['benefit_id'][0] or False
        employee_id = data.get('employee_id', False) and data['employee_id'][0] or False
        start = data.get('start_date', False)
        end = data.get('end_date', False)
        
        if not benefit_id or not employee_id:
            return {'type': 'ir.actions.act_window_close'}

        vals = {
            'benefit_id': benefit_id,
            'employee_id': employee_id,
            'start_date': start,
            'end_date': end,
        }
        policy_obj.create(cr, uid, vals, context=context)
        
        return {'type': 'ir.actions.act_window_close'}
