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

class delete_wizard(orm.TransientModel):
    
    _name = 'log.delete.employee.wizard'
    _description = 'Employee Removal Wizard'
    
    _columns = {
        'employee_ids': fields.many2many('hr.employee', 'delete_employee_wizard_rel',
                                         'wizard_id', 'employee_id', string='Employees'),
    }
    
    # This is a convenience method that other classes from inheriting objects can
    # implement to remove records related to this employee. They must return a dict
    # with a key that is a field of log.delete.employee:
    #
    #    ... do something
    #    my_res = {'field_name': field_value}
    #    res = super(delete_wizard, self).remove_hook(cr, uid, wizard, employee, context=context)
    #    if my_res:
    #        res.update(my_res)
    #    return res
    #
    def remove_hook(self, cr, uid, wizard, employee, context=None):
        
        res = {}
        
        # Remove contracts
        c_obj = self.pool['hr.contract']
        c_ids = c_obj.search(cr, uid, [('employee_id', '=', employee.id)], context=context)
        if len(c_ids) > 0:
            c_obj.unlink(cr, uid, c_ids, context=context)
            res.update({'contracts': True})
        
        return res
    
    def do_change(self, cr, uid, ids, context=None):
        
        unlink_ids = []
        wizard = self.browse(cr, uid, ids[0], context=context)
        for employee in wizard.employee_ids:
            
            # Cache these values so that removal of objects doesn't change them
            ee_dept_name = employee.department_id and employee.department_id.complete_name or False,
            if ee_dept_name:
                ee_dept_name = ee_dept_name[0]
            ee_job_name = employee.job_id and employee.job_id.name or False
            
            # Remove related objects.
            update_vals = self.remove_hook(cr, uid, wizard, employee, context=context)
            
            # Log the removal. Update log record with returned values from
            # removal hook method.
            #
            removal_record = {
                'employee_name': employee.name,
                'employee_dob': employee.birthday,
                'employee_gender': employee.gender,
                'employee_identification': employee.identification_id,
                'department_name': ee_dept_name,
                'job_name': ee_job_name,
            }
            removal_record.update(update_vals)
            change_id = self.pool.get('log.delete.employee').create(cr, uid, removal_record,
                                                                    context=context)
            if not change_id:
                orm.except_orm(_('Error'),
                               _('Unable to log employee removal:\nEmployee Name: %s' %(employee.name)))
            
            unlink_ids.append(employee.id)
        
        # Remove the employee records
        #
        if len(unlink_ids) > 0:
            self.pool['hr.employee'].unlink(cr, uid, unlink_ids, context=context)
        
        return {'type': 'ir.actions.act_window_close'}
