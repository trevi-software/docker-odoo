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
        
        # Remove contracts
        slip_obj = self.pool['hr.payslip']
        slip_ids = slip_obj.search(cr, uid, [('employee_id', '=', employee.id)], context=context)
        if len(slip_ids) > 0:
            slip_obj.unlink(cr, uid, slip_ids, context=context)
            my_res = {'payslips': True}
        
        res = super(delete_wizard, self).remove_hook(cr, uid, wizard, employee, context=context)
        if my_res:
            res.update(my_res)
        
        return res
