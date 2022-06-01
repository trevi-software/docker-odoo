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
from pytz import timezone, utc

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT

class hr_payslip(orm.Model):
    
    _inherit = 'hr.payslip'
    
    def get_attendances_from_payslip(self, cr, uid, ids, context=None):
        
        h_obj = self.pool.get('hr.attendance')
        h_ids = []
        for slip in self.browse(cr, uid, ids, context=context):
            local_tz = (slip.payslip_run_id and slip.payslip_run_id.register_id) and timezone(slip.payslip_run_id.register_id.period_id.schedule_id.tz) or utc
            dtFrom = datetime.strptime(slip.date_from + ' 0:00:00', OE_DTFORMAT)
            dtFrom = local_tz.localize(dtFrom, is_dst=False)
            dtTo = datetime.strptime(slip.date_to + ' 23:59:59', OE_DTFORMAT)
            dtTo = local_tz.localize(dtTo, is_dst=False)
            utcdtFrom = dtFrom.astimezone(utc)
            utcdtTo = dtTo.astimezone(utc)
                
            h_ids = h_obj.search(cr, uid, [('employee_id', '=', slip.employee_id.id),
                                           ('name', '<=', utcdtTo.strftime(OE_DTFORMAT)),
                                           ('name', '>=', utcdtFrom.strftime(OE_DTFORMAT))],
                                 context=context)
        
        irmod_obj = self.pool.get('ir.model.data')
        res_model, res_id = irmod_obj.get_object_reference(cr, uid, 'hr_attendance',
                                                           'open_view_attendance')
        act_window_obj = self.pool.get('ir.actions.act_window')
        dict_act_window = act_window_obj.read(cr, uid, res_id, [])
        dict_act_window.update({'context': {'group_by': 'day'},
                                'domain': [('id', 'in', h_ids)]})
        return dict_act_window
    
    def get_holidays_from_payslip(self, cr, uid, ids, context=None):
        
        h_obj = self.pool.get('hr.holidays')
        h_ids = []
        for slip in self.browse(cr, uid, ids, context=context):
            local_tz = (slip.payslip_run_id and slip.payslip_run_id.register_id) and timezone(slip.payslip_run_id.register_id.period_id.schedule_id.tz) or utc
            dtFrom = datetime.strptime(slip.date_from + ' 0:00:00', OE_DTFORMAT)
            dtFrom = local_tz.localize(dtFrom, is_dst=False)
            dtTo = datetime.strptime(slip.date_to + ' 23:59:59', OE_DTFORMAT)
            dtTo = local_tz.localize(dtTo, is_dst=False)
            utcdtFrom = dtFrom.astimezone(utc)
            utcdtTo = dtTo.astimezone(utc)
                
            h_ids = h_obj.search(cr, uid, [('employee_id', '=', slip.employee_id.id),
                                           ('type', '=', 'remove'),
                                           ('date_from', '<=', utcdtTo.strftime(OE_DTFORMAT)),
                                           ('date_to', '>=', utcdtFrom.strftime(OE_DTFORMAT))],
                                 order='employee_id,date_from', context=context)
        
        irmod_obj = self.pool.get('ir.model.data')
        res_model, res_id = irmod_obj.get_object_reference(cr, uid, 'hr_payslip_link',
                                                           'view_requested_holidays')
        act_window_obj = self.pool.get('ir.actions.act_window')
        dict_act_window = act_window_obj.read(cr, uid, res_id, [])
        dict_act_window.update({'domain': [('type','=','remove'), ('id', 'in', h_ids)]})
        return dict_act_window
