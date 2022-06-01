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

from datetime import datetime, timedelta

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT

class hr_payslip(orm.Model):
    
    _inherit = 'hr.payslip'
    
    def get_weekly_attendance_from_payslip(self, cr, uid, ids, context=None):
        
        w_obj = self.pool.get('hr.attendance.weekly')
        ot_obj = self.pool.get('hr.attendance.weekly.ot')
        p_obj = self.pool.get('hr.attendance.weekly.partial')
        w_ids = []
        ot_ids = []
        p_ids = []
        for slip in self.browse(cr, uid, ids, context=context):
            # Find the first monday in the period
            #
            dFrom = datetime.strptime(slip.date_from, OE_DFORMAT).date()
            while dFrom.weekday() != 0:
                dFrom = dFrom + timedelta(days= -1)
            
            ot_ids = ot_obj.search(cr, uid, [('employee_id', '=', slip.employee_id.id),
                                             ('weekly_id.week_start', '<=', slip.date_to),
                                             ('weekly_id.week_start', '>=', dFrom.strftime(OE_DFORMAT))],
                                   context=context)
            for ot in ot_obj.browse(cr, uid, ot_ids, context=context):
                if ot.weekly_id.id not in w_ids:
                    w_ids.append(ot.weekly_id.id)
            
            p_ids = p_obj.search(cr, uid, [('employee_id', '=', slip.employee_id.id),
                                            ('weekly_id.week_start', '<=', slip.date_to),
                                            ('weekly_id.week_start', '>=', dFrom.strftime(OE_DFORMAT))],
                                   context=context)
            for partial in p_obj.browse(cr, uid, p_ids, context=context):
                if partial.weekly_id.id not in w_ids:
                    w_ids.append(partial.weekly_id.id)
        
        irmod_obj = self.pool.get('ir.model.data')
        res_model, res_id = irmod_obj.get_object_reference(cr, uid, 'hr_attendance_batch_entry',
                                                           'open_weekly_attendance')
        act_window_obj = self.pool.get('ir.actions.act_window')
        dict_act_window = act_window_obj.read(cr, uid, res_id, [])
        dict_act_window.update({'context': {},
                                'domain': [('id', 'in', w_ids)]})
        return dict_act_window
