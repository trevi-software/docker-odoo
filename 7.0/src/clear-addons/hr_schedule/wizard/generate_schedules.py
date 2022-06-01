#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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
from dateutil.relativedelta import relativedelta

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT

class hr_schedule_generate(osv.TransientModel):
    
    _name = 'hr.schedule.generate'
    _description = 'Generate Schedules'
    _columns = {
        'date_start': fields.date('Start', required=True),
        'no_weeks': fields.integer('Number of weeks', required=True),
        'employee_ids': fields.many2many('hr.employee', 'hr_employee_schedule_rel',
                                         'generate_id', 'employee_id', 'Employees'),
    }
    
    _defaults = {
        'no_weeks': 2,
    }
    
    def onchange_start_date(self, cr, uid, ids, date_start, context=None):
        
        res = {
            'value': {
                'date_start': False,
            }
        }
        if date_start:
            dStart = datetime.strptime(date_start, '%Y-%m-%d').date()
            # The schedule must start on a Monday
            if dStart.weekday() == 0:
                res['value']['date_start'] = dStart.strftime('%Y-%m-%d')
        
        return res
    
    def generate_schedules(self, cr, uid, ids, context=None):
        
        sched_obj = self.pool.get('hr.schedule')
        ee_obj = self.pool.get('hr.employee')
        data = self.read(cr, uid, ids, context=context)[0]
        
        dStart = datetime.strptime(data['date_start'], '%Y-%m-%d').date()
        dEnd = dStart + relativedelta(weeks= +data['no_weeks'], days= -1)
        
        sched_ids = []
        if len(data['employee_ids']) > 0:
            for ee in ee_obj.browse(cr, uid, data['employee_ids'], context=context):
                if not ee.contract_id or not ee.contract_id.schedule_template_id:
                    continue
                
                dNextStart = dStart
                dNextEnd = dStart + relativedelta(weeks= +1, days= -1)
                import logging
                _l = logging.getLogger(__name__)
                while dNextStart < dEnd:
                    _l.warning('dNextStart: %s\ndNextEnd: %s', dNextStart, dNextEnd)
                    
                    # If there are overlapping schedules, don't create
                    #
                    overlap_sched_ids = sched_obj.search(cr, uid, [('employee_id', '=', ee.id),
                                                           ('date_start', '<=', dNextEnd.strftime('%Y-%m-%d')),
                                                           ('date_end', '>=', dNextStart.strftime('%Y-%m-%d'))],
                                                 context=context)
                    if len(overlap_sched_ids) > 0:
                        dNextStart = dNextStart + relativedelta(weeks= +1)
                        dNextEnd = dNextStart + relativedelta(weeks= +1, days= -1)
                        continue
                    
                    sched = {
                        'name': ee.name +': '+ dNextStart.strftime(OE_DFORMAT) +' Wk '+ str(dNextStart.isocalendar()[1]),
                        'employee_id': ee.id,
                        'template_id': ee.contract_id.schedule_template_id.id,
                        'date_start': dNextStart.strftime('%Y-%m-%d'),
                        'date_end': dNextEnd.strftime('%Y-%m-%d'),
                    }
                    sched_ids.append(sched_obj.create(cr, uid, sched, context=context))
                    
                    dNextStart = dNextStart + relativedelta(weeks= +1)
                    dNextEnd = dNextStart + relativedelta(weeks= +1, days= -1)
        
        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.schedule',
            'domain': [('id', 'in', sched_ids)],
            'type': 'ir.actions.act_window',
            'target': 'current',
            'nodestroy': True,
            'context': context,
        }
