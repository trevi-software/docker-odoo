#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Clear ICT Solutions <http://clearict.com>.
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

class hr_employee_modify(orm.TransientModel):
    
    _name = 'hr.employee.idmodify.wizard'
    _description = 'Employee ID Modification Wizard'
    
    _columns = {
        'do_copy2unique': fields.boolean('Copy ID into Unique ID'),
        'do_legacy': fields.boolean('Copy from Legacy ID'),
        'do_regen': fields.boolean('Re-generate ID'),
        'employee_ids': fields.many2many('hr.employee',
                                         'hr_employee_idmodify_wizard_rel',
                                         'wizard_id', 'employee_id', 'Employees'),
    }
    
    def do_modify(self, cr, uid, ids, context=None):
        
        ee_obj = self.pool.get('hr.employee')
        wizard = self.browse(cr, uid, ids[0], context=context)
        
        for ee in wizard.employee_ids:
            
            vals = {}
            
            if wizard.do_copy2unique and ee.employee_no:
                vals.update({'employee_no_rand': ee.employee_no})
            
            if wizard.do_legacy and ee.legacy_no:
                vals.update({'employee_no': ee.legacy_no})
            
            if wizard.do_regen:
                
                # Multi-company support
                #
                ctx_copy = {}
                if context:
                    ctx_copy = context.copy()
                if ee.company_id.id:    
                    ctx_copy.update({'force_company': ee.company_id.id})
                
                eid = ee_obj.generate_employee_id(cr, uid,
                                                  {'name': ee.name,
                                                   'company_id': ee.company_id.id},
                                                  context=ctx_copy)
                vals.update({'employee_no': eid})
            
            ee_obj.write(cr, uid, ee.id, vals, context=context)
        
        return {'type': 'ir.actions.act_window_close'}
