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

from openerp.report import report_sxw
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools.translate import _

class Parser(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'get_no': self._get_no,
            'week_start': self._get_week_start,
            'week_no': self._get_week_no,
            'mday': self._get_mday,
            'is_on_leave': self.is_on_leave,
            'get_leave_string': self.get_leave_string,
        })
        
        self.no = 0
        self.department_id = 0
    
    def set_context(self, objects, data, ids, report_type=None):
        if data.get('form', False) and data['form'].get('week_start', False):
            self.week_start = data['form']['week_start']
        else:
            self.week_start = (datetime.now().date() + relativedelta(days= +(7 - datetime.now().date().weekday()))).strftime('%Y-%m-%d')
        
        if data.get('form', False) and data['form'].get('week_no'):
            self.week_no = data['form']['week_no']
        else:
            self.week_no = datetime.strptime(self.week_start, '%Y-%m-%d').isocalendar()[1]
        
        # Create schedules if necessary
        for dept in self.pool.get('hr.department').browse(self.cr, self.uid, data['form']['department_ids']):
            self.generate_schedules(self.cr, self.uid, self.week_start, dept.member_ids)
        
        return super(Parser, self).set_context(objects, data, ids, report_type=report_type)
    
    def generate_schedules(self, cr, uid, date_start, employees, context=None):
        
        sched_obj = self.pool.get('hr.schedule')
        
        dStart = datetime.strptime(date_start, OE_DFORMAT).date()
        dEnd = dStart + relativedelta(weeks= +1, days= -1)
        
        sched_ids = []
        if len(employees) > 0:
            for ee in employees:
                if not ee.contract_id or not ee.contract_id.schedule_template_id:
                    continue
                
                dNextStart = dStart
                dNextEnd = dStart + relativedelta(weeks= +1, days= -1)
                while dNextStart < dEnd:
                    
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
        
        return
    
    def _get_week_start(self):
        dt = datetime.strptime(self.week_start, '%Y-%m-%d')
        return dt.strftime('%B %d, %Y')
    
    def _get_week_no(self):
        return self.week_no
    
    def _get_no(self, d_id):
        if d_id != self.department_id:
            self.department_id = d_id
            self.no = 0
        self.no += 1
        return self.no
    
    def _get_mday(self, wday):
        dt = datetime.strptime(self.week_start, '%Y-%m-%d')
        dt = dt + relativedelta(days= +wday)
        return dt.strftime('%d')

    def _get_lv(self, ee_id, wday):
        
        lv_obj = self.pool.get('hr.holidays')
        code = None
        
        dt = datetime.strptime(self.week_start + ' 12:00:00', OE_DTFORMAT)
        dt = dt + relativedelta(days= +wday)
        
        lv_ids = lv_obj.search(self.cr, self.uid, [('employee_id', '=', ee_id),
                                                   ('type', '=', 'remove'),
                                                   ('state', '=', 'validate'),
                                                   ('date_from', '<=', dt.strftime(OE_DTFORMAT)),
                                                   ('date_to', '>=', dt.strftime(OE_DTFORMAT))])
        if len(lv_ids) > 0:
            lv = lv_obj.browse(self.cr, self.uid, lv_ids[0])
            code = lv.holiday_status_id.code
        
        return code
    
    def is_on_leave(self, ee_id, wday):
        
        res = False
        restdays = self.pool.get('hr.employee').get_restdays_by_week(self.cr, self.uid, ee_id.id,
                                                                 self.week_start)
        if self._get_lv(ee_id.id, wday) != None:
            res = True
        elif wday in restdays:
            res = True
        return res
    
    def get_leave_string(self, ee_id, wday):
        
        res = ''
        code = self._get_lv(ee_id.id, wday)

        if code == None:
            restdays = self.pool.get('hr.employee').get_restdays_by_week(self.cr, self.uid, ee_id.id,
                                                                     self.week_start)
            if wday in restdays:
                res = _('Off')
            return res
        
        if code == 'LVANNUAL':
            res = _('AL')
        elif code == 'LVMATERNITY':
            res = _('ML')
        elif code == 'LVPTO':
            res = _('PL')
        elif code == 'LVUTO':
            res = _('UL')

        return res
