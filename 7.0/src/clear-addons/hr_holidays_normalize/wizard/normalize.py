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

from datetime import datetime, timedelta

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT

class hr_holidays_normalize(orm.TransientModel):
    
    _name = 'hr.holidays.wizard.normalize'
    _description = 'Normalize Leaves Wizard'
    
    _columns = {
        'date_start': fields.date('Start', required=True),
        'date_end': fields.date('End', required=True),
        'start_time': fields.char('Alternate UTC Start Time'),
        'end_time': fields.char('Alternate UTC End Time'),
        'leave_ids': fields.many2many('hr.holidays', 'hr_holidays_normalize_wizard_rel',
                                     'wizard_id', 'leave_id', 'Leaves', readonly=True),
    }
    
    _defaults = {
        'start_time': '04:00:00',
        'end_time': '13:00:00',
    }
    
    def button_get_leaves(self, cr, uid, ids, context=None):
        
        lv_obj = self.pool.get('hr.holidays')
        
        lv_ids = []
        wizard = self.browse(cr, uid, ids[0], context=context)
        dPeriodStart = datetime.strptime(wizard.date_start, OE_DFORMAT)
        dPeriodEnd = datetime.strptime(wizard.date_end, OE_DFORMAT)
        dToday = dPeriodStart
        while dToday <= dPeriodEnd:
            str_today = dToday.strftime(OE_DFORMAT)
            str_utc_start = str_today +' '+ wizard.start_time
            str_utc_end_midnight = str_today + ' 23:59:59'
            lv_ids += lv_obj.search(cr, uid, ['&',
                                                  ('date_from', '>', str_utc_start),
                                                  ('date_from', '<=', str_utc_end_midnight),
                                              ('type', '=', 'remove'),
                                              ('state', 'in', ['validate', 'validate1'])],
                                    context=context)
            
            dToday = dToday + timedelta(days= +1)
        
        if len(lv_ids) > 0:
            self.write(cr, uid, ids[0], {'leave_ids': [(6, 0, lv_ids)]}, context=context)
        
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.holidays.wizard.normalize',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }
    
    def normalize(self, cr, uid, ids, context=None):
        
        lv_obj = self.pool.get('hr.holidays')
        wizard = self.browse(cr, uid, ids[0], context=context)
        for leave in wizard.leave_ids:
            dToday = datetime.strptime(leave.date_from, OE_DTFORMAT).date()
            str_today = dToday.strftime(OE_DFORMAT)
            str_utc_start = str_today +' '+ wizard.start_time
            assert str_utc_start < leave.date_from, "Calculated leave start is after current start time"
            lv_obj.write(cr, uid, [leave.id], {'date_from': str_utc_start}, context=context)
        
        return {'type': 'ir.actions.act_window_close'}
