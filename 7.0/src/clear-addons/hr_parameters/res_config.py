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

from openerp.osv import fields, orm

class hr_config_settings(orm.Model):
    
    _inherit = 'hr.config.settings'
    
    _columns = {
        'hr_manager_id': fields.many2one('hr.employee', 'HR Manager'),
        'payroll_manager_id': fields.many2one('hr.employee', 'Payroll Manager'),
    }
    
    def get_default_hr_manager_id(self, cr, uid, fields, context=None):
        
        employee_id = False
        ids = self.search(cr, uid, [], order='id', context=context)
        if len(ids) > 0:
            config = self.browse(cr, uid, ids[-1], context=context)
            if config.hr_manager_id:
                employee_id = config.hr_manager_id.id
        return {'hr_manager_id': employee_id}
    
    def get_default_payroll_manager_id(self, cr, uid, fields, context=None):
        
        employee_id = False
        ids = self.search(cr, uid, [], order='id', context=context)
        if len(ids) > 0:
            config = self.browse(cr, uid, ids[-1], context=context)
            if config.payroll_manager_id:
                employee_id = config.payroll_manager_id.id
        return {'payroll_manager_id': employee_id}
