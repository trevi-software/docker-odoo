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

import netsvc
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT

class employee_set_inactive(osv.TransientModel):
    
    _name = 'hr.employee.inactive'
    _description = 'Set Employee Inactive Wizard'
    
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True, readonly=True),
        'date': fields.date('Date', required=True),
        'reason': fields.selection([
                                    ('contract_end', 'Contract Ended'),
                                    ('resignation', 'Resignation'),
                                    ('dismissal', 'Dismissal'),
                                   ],
                                   'Reason', required=True),
        'notes': fields.text('Notes'),
    }
    
    def _get_employee(self, cr, uid, context=None):
        
        if context == None:
            context = {}
        
        return context.get('active_id', False)
    
    _defaults = {
        'date': datetime.now().strftime(DEFAULT_SERVER_DATE_FORMAT),
        'employee_id': _get_employee,
    }
    
    def set_employee_inactive(self, cr, uid, ids, context=None):
        
        data = self.read(cr, uid, ids[0], ['employee_id', 'date', 'reason', 'notes'], context=context)
        vals = {
            'name': data['date'],
            'employee_id': data['employee_id'][0],
            'reason': data['reason'],
            'notes': data['notes'],
        }
        
        # Write the data about the deactivation and bring it up for the user to edit
        #
        term_id = self.pool.get('hr.employee.termination').create(cr, uid, vals, context=context)
        res_model, res_id = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                                                                                'hr_employee_state',
                                                                                'open_hr_employee_termination')
        dict_act_window = self.pool.get('ir.actions.act_window').read(cr, uid, res_id, [])
        dict_act_window['domain'] = [('id', '=', term_id)]
        return dict_act_window
