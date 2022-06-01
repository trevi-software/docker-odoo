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

class hr_no_change(orm.Model):
    
    _name = 'log.change.employee.no'
    _description = 'Employee Number Change Log'
    
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', readonly=True),
        'date': fields.date('Change Date', readonly=True),
        'prev_value': fields.char('Changed Value', readonly=True),
        'user_id': fields.many2one('res.users', 'Responsible', readonly=True),
    }
    
    _defaults = {
        'date': datetime.now().strftime(OE_DFORMAT),
    }
    
    def name_get(self, cr, uid, ids, context=None):
        
        res = dict.fromkeys(ids, False)
        for rec in self.browse(cr, uid, ids, context=context):
            res[rec.id] = rec.employee_id.name
        return res
    
    def create(self, cr, uid, vals, context=None):
        
        vals.update({'user_id': uid})
        return super(hr_no_change, self).create(cr, uid, vals, context=context)
