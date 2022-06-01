#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

import time

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT

import netsvc
from openerp.addons.hr_equipment_issue.hr_equipment import ISSUE_LINE_STATE_SELECTION_ISSUE
from openerp.addons.hr_equipment_issue.hr_equipment import ISSUE_LINE_STATE_SELECTION_RETURN

class equipment_return(orm.TransientModel):
    
    _name = 'hr.equipment.return'
    _description = 'Equipment Return'
    
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'return_date': fields.date('Return Date', required=True),
        'line_id': fields.many2one('hr.equipment.issue.line', 'Issued Equipment', required=True),
        'return_user_id': fields.many2one('res.users', 'Recorded by', required=True),
        'status': fields.selection(ISSUE_LINE_STATE_SELECTION_RETURN, 'State', required=True),
        'note': fields.text('Notes'),
    }
    
    def _get_ee(self, cr, uid, context=None):
        
        if context == None:
            context = {}
        
        res = False
        if context.get('active_id', False):
            res = context['active_id']
        elif context.get('active_ids', False):
            res = context['active_ids'][0]
        
        return res
    
    _defaults = {
        'return_user_id': lambda s, cr, uid, ctx: uid,
        'employee_id': _get_ee,
        'return_date': time.strftime(OE_DFORMAT)
    }
    
    def onchange_employee(self, cr, uid, ids, employee_id, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        res = {'domain': dict.fromkeys(ids, False)}
        if not employee_id:
            return res
        
        res['domain']['line_id'] = [('employee_id', '=', employee_id), ('status', '=', 'issue')]
        
        return res
        
    def record(self, cr, uid, ids, context=None):
        
        line_obj = self.pool.get('hr.equipment.issue.line')
        data = self.read(cr, uid, ids[0], [], context=context)
        
        vals = {
            'return_date': data['return_date'],
            'status': data['status'],
            'return_user_id': data['return_user_id'][0],
        }
        if data.get('note', False):
            orig_data = line_obj.read(cr, uid, data['line_id'][0], ['note'], context=context)
            orig_note = False
            if orig_data.get('note', False):
                orig_note = orig_data['note']
            if orig_note:
                vals.update({'note': orig_note +'\n\n'+ data['return_date'] +'\n'+ data['note']})
            else:
                vals.update({'note': ''+ data['return_date'] +':\n'+ data['note']})
        
        line_obj.write(cr, uid, data['line_id'][0], vals, context=context)
        
        # Trigger evaluation of issue sheet
        #
        line = line_obj.browse(cr, uid, data['line_id'][0], context=context)
        wkf = netsvc.LocalService('workflow')
        wkf.trg_validate(uid, 'hr.equipment.issue', line.issue_id.id, 'signal_return', cr)
        
        return {'type': 'ir.actions.act_window_close'}
