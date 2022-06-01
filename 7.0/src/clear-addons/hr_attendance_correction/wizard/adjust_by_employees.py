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

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.translate import _

class hr_payslip_employees(orm.TransientModel):

    _name ='hr.attendance.weekly.correction.wizard'
    _description = 'Re-generate attendance and schedule for selected employees'
    
    _columns = {
        'employee_ids': fields.many2many('hr.employee', 'hr_employee_attendance_correction_wizard_rel', 'wizard_id', 'employee_id', 'Employees'),
        'start': fields.date('Start date', required=True),
        'end': fields.date('End date', required=True),
        'recreate_sched': fields.boolean('Re-create Schedule'),
    }
    
    _defaults = {
        'recreate_sched': True,
    }

    def sort_days(self, days_list):
        
        res = []
        for day in days_list:
            if len(res) == 0:
                res.append(day)
            else:
                for dres in res:
                    if day < dres:
                        res.insert(res.index(dres), day)
                        break
                    elif dres == res[-1]:
                        res.append(day)
                        break
        
        return res
    
    def get_week_start(self, date_str):

        d = datetime.strptime(date_str, OE_DFORMAT)
        while d.weekday() != 0:
            d += timedelta(days=-1)
        return d

    def get_week_start_list(self, start_str, end_str):

        res = []
        dStart = datetime.strptime(start_str, OE_DFORMAT)
        while dStart.weekday() != 0:
            dStart += timedelta(days=-1)
        dEnd = datetime.strptime(end_str, OE_DFORMAT)
        while dEnd >= dStart:
            if dEnd.weekday() == 0:
                res.append(dEnd.strftime(OE_DFORMAT))
            dEnd += timedelta(days=-1)
        return list(reversed(res))

    def generate_schedules(self, cr, uid, employee, date_start, context=None):
        
        sched_obj = self.pool.get('hr.schedule')
        
        dStart = datetime.strptime(date_start, OE_DFORMAT).date()
        dEnd = dStart + relativedelta(weeks= +1, days= -1)
        
        sched_ids = []
        if not employee.contract_id or not employee.contract_id.schedule_template_id:
            return sched_ids
        
        dNextStart = dStart
        dNextEnd = dStart + relativedelta(weeks= +1, days= -1)
        while dNextStart < dEnd:
            
            # If there are overlapping schedules, don't create
            #
            overlap_sched_ids = sched_obj.search(cr, uid, [('employee_id', '=', employee.id),
                                                   ('date_start', '<=', dNextEnd.strftime('%Y-%m-%d')),
                                                   ('date_end', '>=', dNextStart.strftime('%Y-%m-%d'))],
                                         context=context)
            if len(overlap_sched_ids) > 0:
                dNextStart = dNextStart + relativedelta(weeks= +1)
                dNextEnd = dNextStart + relativedelta(weeks= +1, days= -1)
                continue
            
            sched = {
                'name': employee.name +': '+ dNextStart.strftime(OE_DFORMAT) +' Wk '+ str(dNextStart.isocalendar()[1]),
                'employee_id': employee.id,
                'template_id': employee.contract_id.schedule_template_id.id,
                'date_start': dNextStart.strftime(OE_DFORMAT),
                'date_end': dNextEnd.strftime(OE_DFORMAT),
            }
            sched_ids.append(sched_obj.create(cr, uid, sched, context=context))
            
            dNextStart = dNextStart + relativedelta(weeks= +1)
            dNextEnd = dNextStart + relativedelta(weeks= +1, days= -1)
        
        return sched_ids
    
    def change_schedule_restday(self, cr, uid, ot, context=None):
        
        wot_obj = self.pool.get('hr.attendance.weekly.ot')
        lookup = {
            'mon': 0,
            'tue': 1,
            'wed': 2,
            'thu': 3,
            'fri': 4,
            'sat': 5,
            'sun': 6,
        }
        
        restdays = []
        if ot.off1:
            restdays.append(lookup[ot.off1])
        if ot.off2:
            restdays.append(lookup[ot.off2])
        
        if len(restdays) > 0:
            wot_obj._change_restday(cr, uid, ot, restdays, force=True, context=context)
        
        return
    
    def get_all_dates(self, start_str, end_str):

        res = []
        dStart = datetime.strptime(start_str, OE_DFORMAT)
        dEnd = datetime.strptime(end_str, OE_DFORMAT)
        while dStart <= dEnd:
            res.append(dStart)
            dStart = dStart + timedelta(days=1)

        return res
    
    def get_week_start_list_from_sched(self, cr, uid, sched_ids, context=None):
        
        res = []
        for sched in self.pool.get('hr.schedule').browse(cr, uid, sched_ids, context=context):
            dStart = datetime.strptime(sched.date_start, OE_DFORMAT).date()
            dEnd = datetime.strptime(sched.date_end, OE_DFORMAT).date()
            while dStart <= dEnd:
                if dStart.weekday() == 0:
                    res.append(dStart.strftime(OE_DFORMAT))
                dStart += timedelta(days= +1)
        
        return res
            
    def create_adjustments(self, cr, uid, ids, context=None):
        
        sched_obj = self.pool.get('hr.schedule')
        att_obj = self.pool.get('hr.attendance')
        watt_obj = self.pool.get('hr.attendance.weekly')
        
        if context is None:
            context = {}
        
        wizard = self.browse(cr, uid, ids[0], context=context)
        if not wizard.employee_ids or len(wizard.employee_ids) == 0:
            raise orm.except_orm(_("Warning !"), _("You must select at least one employee to make attendance corrections."))

        week_start_list = self.get_week_start_list(wizard.start, wizard.end)
        for ee in wizard.employee_ids:

            weekly_id_list = []
            for ws in week_start_list:
                weekly_id_list += watt_obj.get_other_weeklies(
                                        cr, uid, ee.id, ws, context=context)

            # Because of various interactions within the software, the
            # following steps have to be done in exactly the following order.
            #

            # 1. Regenerate schedule for the weeks of the selected weekly attendances
            if wizard.recreate_sched:
                sched_ids = []
                new_sched_ids = []
                for week_start in week_start_list:
                    sched_ids += sched_obj.search(cr, uid, [('employee_id', '=', ee.id),
                                                            ('date_start', '<=', week_start),
                                                            ('date_end', '>=', week_start)],
                                                  context=context)
                updated_week_start_list = self.get_week_start_list_from_sched(
                                        cr, uid, sched_ids, context=context)
                updated_week_start_list = self.sort_days(updated_week_start_list)
                if len(sched_ids) > 0:
                    sched_obj.unlink(cr, uid, sched_ids, context=context)
                for week_start in updated_week_start_list:
                    new_sched_ids += self.generate_schedules(cr, uid, ee, week_start,
                                                            context=context)
            
            # 2. Reset the rest-days of the schedule according to weekly attendance
            employee_ot_list = []
            weeklies = watt_obj.browse(cr, uid, weekly_id_list,
                                       context=context)
            for week in weeklies:
                employee_ot_list += [ot for ot in week.ot_ids if ot.employee_id.id == ee.id]
            for ot in employee_ot_list:
                self.change_schedule_restday(cr, uid, ot, context=context)
            
            # 3. Remove attendances for the days of the selected weekly attendances
            list_of_dates = self.get_all_dates(wizard.start, wizard.end)
            list_of_days = [d.strftime(OE_DFORMAT) for d in list_of_dates]
            att_ids = att_obj.search(cr, uid, [('employee_id', '=', ee.id),
                                               '|', ('day', 'in', list_of_days),
                                                    ('weekly_att_id', 'in', weekly_id_list)])
            if len(att_ids) > 0:
                att_obj.unlink(cr, uid, att_ids, context=context)
            
            # 4. Generate attendances for the days of the selected weekly attendances
            test_att_ids = att_obj.search(cr, uid, [('employee_id', '=', ee.id), ('day', 'in', list_of_days)], context=context)
            assert len(test_att_ids) == 0, "Attendance exists where it shouldn't!"
            for week in weeklies:
                weekly_lines = watt_obj.get_weekly_lines(cr, uid, week.id,
                                                         select_employee_id=ee.id,
                                                         check_attendance=False,
                                                         context=context)
                watt_obj.add_punches(cr, uid, week.id, weekly_lines, context=context)
        
        return {'type': 'ir.actions.act_window_close'}
