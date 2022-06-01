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

from datetime import datetime

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT

class log_delete_employee(orm.Model):
    
    _name = 'log.delete.employee'
    _description = 'Deleted Employee Records Log'
    
    _columns = {
        'employee_name': fields.char('Name', required=True),
        'employee_dob': fields.date('Date of Birth'),
        'employee_gender': fields.selection([('male', 'Male'), ('female', 'Female')], 'Gender'),
        'employee_identification': fields.char('Identification No.'),
        'department_name': fields.char('Department'),
        'job_name': fields.char('Job'),
        'date': fields.date('Change Date', readonly=True),
        'user_id': fields.many2one('res.users', 'Responsible', readonly=True),
        'contracts': fields.boolean('Contracts'),
        'attendances': fields.boolean('Attendances'),
        'schedules': fields.boolean('Schedules'),
        'leaves': fields.integer('Leaves'),
        'payslips': fields.integer('Pay Slips'),
        'benefits': fields.integer('Pay Slips'),
    }
    
    _rec_name = 'employee_name'
    
    _defaults = {
        'date': datetime.now().strftime(OE_DFORMAT),
    }
    
    def create(self, cr, uid, vals, context=None):
        
        vals.update({'user_id': uid})
        return super(log_delete_employee, self).create(cr, uid, vals, context=context)
