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
    
    _inherit = 'log.delete.employee.wizard'
    
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
        
        my_res = False
        class_string = 'hr.attendance.weekly.ot'
        class_employee_rel_field = 'employee_id'
        delete_field_string = 'weekly_attendance'
        
        # Remove Weekly OT
        obj = self.pool[class_string]
        obj_ids = obj.search(cr, uid, [(class_employee_rel_field, '=', employee.id)], context=context)
        if len(obj_ids) > 0:
            obj.unlink(cr, uid, obj_ids, context=context)
            my_res = {delete_field_string: True}
        
        # Remove Weekly Absence (Partial Attendance)
        class_string = 'hr.attendance.weekly.partial'
        obj = self.pool[class_string]
        obj_ids = obj.search(cr, uid, [(class_employee_rel_field, '=', employee.id)], context=context)
        if len(obj_ids) > 0:
            obj.unlink(cr, uid, obj_ids, context=context)
            my_res = {delete_field_string: True}
        
        res = super(delete_wizard, self).remove_hook(cr, uid, wizard, employee, context=context)
        if my_res:
            res.update(my_res)
        
        return res
