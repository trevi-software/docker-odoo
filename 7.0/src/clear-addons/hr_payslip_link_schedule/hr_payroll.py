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

class hr_payslip(orm.Model):
    
    _inherit = 'hr.payslip'
    
    def get_schedules_from_payslip(self, cr, uid, ids, context=None):
        
        h_obj = self.pool.get('hr.schedule')
        h_ids = []
        for slip in self.browse(cr, uid, ids, context=context):
                
            h_ids = h_obj.search(cr, uid, [('employee_id', '=', slip.employee_id.id),
                                           ('date_start', '<=', slip.date_to),
                                           ('date_end', '>=', slip.date_from)],
                                 order='employee_id,date_start',
                                 context=context)
        
        irmod_obj = self.pool.get('ir.model.data')
        res_model, res_id = irmod_obj.get_object_reference(cr, uid, 'hr_schedule',
                                                           'open_schedule_view')
        act_window_obj = self.pool.get('ir.actions.act_window')
        dict_act_window = act_window_obj.read(cr, uid, res_id, [])
        dict_act_window.update({'domain': [('id', 'in', h_ids)]})
        return dict_act_window
