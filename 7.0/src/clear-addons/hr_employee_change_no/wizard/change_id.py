#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Clear ICT Solutions <info@clearict.com>.
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

from openerp.osv import fields, orm
from openerp.tools.translate import _

class change_no_wizard(orm.TransientModel):
    
    _name = 'log.change.employee.no.wizard'
    _description = 'Employee Number Change Wizard'
    
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'prev_value': fields.char('Current Value', readonly=True),
        'new_value': fields.char('New Value', required=True),
    }
    
    def _get_prev(self, cr, uid, context=None):
        
        res = ''
        ee_id = context.get('active_id', False)
        if ee_id:
            ee = self.pool.get('hr.employee').browse(cr, uid, ee_id, context=context)
            res = ee.employee_no
        
        return res
    
    _defaults = {
        'employee_id': lambda s,c,u,ctx: ctx.get('active_id', False),
        'prev_value': _get_prev,
    }
    
    def onchange_employee_id(self, cr, uid, ids, employee_id, context=None):
        
        res = {'value': {'prev_value': False}}
        if employee_id:
            ee = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
            res['value']['prev_value'] = ee.employee_no
        return res
    
    def do_change(self, cr, uid, ids, context=None):
        
        wizard = self.browse(cr, uid, ids[0], context=context)
        change_id = self.pool.get('log.change.employee.no').create(cr, uid,
                                                       {'employee_id': wizard.employee_id.id,
                                                        'prev_value': str(wizard.employee_id.employee_no)},
                                                       context=context)
        if not change_id:
            orm.except_orm(_('Error'), _('Unable to log Number change!'))
        
        self.pool.get('hr.employee').write(cr, uid, wizard.employee_id.id,
                                           {'employee_no': wizard.new_value},
                                           context=context)
        
        return {'type': 'ir.actions.act_window_close'}
