#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
#    Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)
#    and 2004-2010 Tiny SPRL (<http://tiny.be>).
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
from pytz import timezone, utc

from openerp import tools
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.float_utils import float_is_zero, float_compare
from openerp.tools.translate import _


class hr_holidays_status(osv.Model):
    
    _inherit = 'hr.holidays.status'
    
    _columns = {
        'ex_rest_days': fields.boolean('Exclude Rest Days',
                                       help="If enabled, the employee's day off is skipped in leave days calculation."),
        'ex_public_holidays': fields.boolean('Exclude Public Holidays',
                                             help="If enabled, public holidays are skipped in leave days calculation."),
    }

class hr_holidays(osv.osv):
    
    _name = 'hr.holidays'
    _inherit = ['hr.holidays', 'ir.needaction_mixin']

    _columns = {
        'real_days': fields.float('Total Days', digits=(16, 1)),
        'rest_days': fields.float('Rest Days', digits=(16, 1)),
        'public_holiday_days': fields.float('Public Holidays', digits=(16, 1)),
        'return_date': fields.char('Return Date', size=32),
    }

    def _employee_get(self, cr, uid, context=None):
        
        if context == None:
            context = {}
        
        # If the user didn't enter from "My Leaves" don't pre-populate Employee field
        if not context.get('search_default_my_leaves', False):
            return False
        
        ids = self.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
        if ids:
            return ids[0]
        return False

    def _days_get(self, cr, uid, context=None):
        
        if context == None:
            context = {}
        
        date_from = context.get('default_date_from')
        date_to = context.get('default_date_to')
        if date_from and date_to:
            delta = datetime.strptime(date_to, OE_DTFORMAT) - datetime.strptime(date_from, OE_DTFORMAT)
            return (delta.days and delta.days or 1)
        return False
    
    _defaults = {
        'employee_id': _employee_get,
        'number_of_days_temp': _days_get,
    }

    _order = 'date_from asc, type desc'
    
    def _needaction_domain_get(self, cr, uid, context=None):
        
        users_obj = self.pool.get('res.users')
        domain = []
        
        if users_obj.has_group(cr, uid, 'base.group_hr_manager'):
            domain = [('state', 'in', ['draft', 'confirm'])]
            return domain
        
        elif users_obj.has_group(cr, uid, 'hr_holidays_extension.group_hr_leave'):
            domain = [('state', 'in', ['confirm']), ('employee_id.user_id', '!=', uid)]
            return domain
        
        return False

    def onchange_bynumber(self, cr, uid, ids, no_days, date_from, employee_id, holiday_status_id, context=None):
        """
        Update the dates based on the number of days requested.
        """

        ee_obj = self.pool.get('hr.employee')
        holiday_obj = self.pool.get('hr.holidays.public')
        sched_tpl_obj = self.pool.get('hr.schedule.template')
        sched_detail_obj = self.pool.get('hr.schedule.detail')
        result = {'value': {}}

        if not no_days or (float_compare(no_days, 1.0, precision_rounding=0.01) == -1) or not date_from or not employee_id:
            return result
        
        user = self.pool.get('res.users').browse(cr, uid, uid)
        if user and user.tz:
            local_tz = timezone(user.tz)
        else:
            local_tz = timezone('Africa/Addis_Ababa')
        
        
        dt = datetime.strptime(date_from, OE_DTFORMAT)
        employee = ee_obj.browse(cr, uid, employee_id, context=context)
        if holiday_status_id:
            hs_data = self.pool.get('hr.holidays.status').read(cr, uid, holiday_status_id,
                                                               ['ex_rest_days', 'ex_public_holidays'],
                                                               context=context)
        else:
            hs_data = {}
        ex_rd = hs_data.get('ex_rest_days', False)
        ex_ph = hs_data.get('ex_public_holidays', False)
        
        # Get rest day and the schedule start time on the date the leave begins
        #
        rest_days = []
        times = tuple()
        if ex_rd:
            if employee.contract_id and employee.contract_id.schedule_template_id:
                rest_days = sched_tpl_obj.get_rest_days(cr, uid,
                                                        employee.contract_id.schedule_template_id.id,
                                                        context=context)
                times = sched_detail_obj.scheduled_begin_end_times(cr, uid, employee.id,
                                                                   employee.contract_id.id, dt,
                                                                   context=context)
        if len(times) > 0:
            utcdtStart = times[0][0]
        else:
            # If we can't find a schedule, just leave it as the user entered it.
            dtStart = local_tz.localize(dt, is_dst=False)
            utcdtStart = dtStart.astimezone(utc)
        
        count_days = no_days
        real_days = 1
        ph_days = 0
        r_days = 0
        next_dt = dt
        while float_compare(count_days, 1.0, precision_rounding=0.01) == 1:
            public_holiday = holiday_obj.is_public_holiday(cr, uid, next_dt.date(), context=context)
            public_holiday = (public_holiday and ex_ph)
            rest_day = (next_dt.weekday() in rest_days and ex_rd)
            next_dt += timedelta(days= +1)
            if public_holiday or rest_day:
                if public_holiday: ph_days += 1
                elif rest_day: r_days += 1
                real_days += 1
                continue
            else:
                count_days -= 1
                real_days += 1
        while (next_dt.weekday() in rest_days and ex_rd) or (holiday_obj.is_public_holiday(cr, uid, next_dt.date(), context=context) and ex_ph):
            if holiday_obj.is_public_holiday(cr, uid, next_dt.date(), context=context): ph_days += 1
            elif next_dt.weekday() in rest_days: r_days += 1
            next_dt += timedelta(days=1)
            real_days += 1

        # Set end time based on schedule
        #
        times = sched_detail_obj.scheduled_begin_end_times(cr, uid, employee.id,
                                                           employee.contract_id.id, next_dt,
                                                           context=context)
        if len(times) > 0:
            utcdtEnd = times[-1][1]
        else:
            dtEnd = local_tz.localize(datetime.strptime(next_dt.strftime(OE_DFORMAT) +' 23:59:59',  OE_DTFORMAT), is_dst=False)
            utcdtEnd = dtEnd.astimezone(utc)

        result['value'].update({'department_id': employee.department_id.id,
                                'date_from': utcdtStart.strftime(OE_DTFORMAT),
                                'date_to': utcdtEnd.strftime(OE_DTFORMAT),
                                'rest_days': r_days,
                                'public_holiday_days': ph_days,
                                'real_days': real_days})
        return result

    def onchange_enddate(self, cr, uid, ids, employee_id,
                         date_from, date_to, holiday_status_id, no_days, context=None):
        
        ee_obj = self.pool.get('hr.employee')
        holiday_obj = self.pool.get('hr.holidays.public')
        sched_tpl_obj = self.pool.get('hr.schedule.template')
        res = {'value': {'return_date': False}}

        if not employee_id or not date_to or (float_compare(no_days, 0.0, precision_rounding=0.01) == -1):
            return res

        if holiday_status_id:
            hs_data = self.pool.get('hr.holidays.status').read(cr, uid, holiday_status_id,
                                                               ['ex_rest_days', 'ex_public_holidays'],
                                                               context=context)
        else:
            hs_data = {}
        ex_rd = hs_data.get('ex_rest_days', False)
        ex_ph = hs_data.get('ex_public_holidays', False)

        rest_days = []
        if ex_rd:
            ee = ee_obj.browse(cr, uid, employee_id, context=context)
            if ee.contract_id and ee.contract_id.schedule_template_id:
                rest_days = sched_tpl_obj.get_rest_days(cr, uid,
                                                        ee.contract_id.schedule_template_id.id,
                                                        context=context)

        dt = datetime.strptime(date_to, OE_DTFORMAT)
        return_date = dt + timedelta(days= +1)
        while (return_date.weekday() in rest_days and ex_rd) or (holiday_obj.is_public_holiday(cr, uid, return_date.date(), context=context) and ex_ph):
            return_date += timedelta(days=1)
        res['value']['return_date'] = return_date.strftime('%B %d, %Y')
        
        # If the number of requested days is zero it means this is a partial day request.
        # Assume that a full day of work is 8 hours.
        #
        if float_compare(no_days, 1.0, precision_rounding=0.01) == -1:
            dtStart = datetime.strptime(date_from, OE_DTFORMAT)
            delta = dt - dtStart
            res['value'].update({'number_of_days_temp': float(delta.seconds) / (8.0 * 60.0 * 60.0)})
            res['value']['return_date'] = False
        return res

    def holidays_first_validate(self, cr, uid, ids, context=None):
        
        self._check_validate(cr, uid, ids, context=context)
        return super(hr_holidays, self).holidays_first_validate(cr, uid, ids, context=context)
    
    def holidays_validate(self, cr, uid, ids, context=None):
        
        self._check_validate(cr, uid, ids, context=context)
        return super(hr_holidays, self).holidays_validate(cr, uid, ids, context=context)
    
    def _check_validate(self, cr, uid, ids, context=None):
        
        users_obj = self.pool.get('res.users')
        
        if not users_obj.has_group(cr, uid, 'base.group_hr_manager'):
            for leave in self.browse(cr, uid, ids, context=context):
                if leave.employee_id.user_id.id == uid:
                    raise osv.except_osv(_('Warning!'), _('You cannot approve your own leave:\nHoliday Type: %s\nEmployee: %s') % (leave.holiday_status_id.name, leave.employee_id.name))
        return

class hr_attendance(osv.Model):
    
    _name = 'hr.attendance'
    _inherit = 'hr.attendance'
    
    def create(self, cr, uid, vals, context=None):
        
        retry_count = 1
        while retry_count >= 0:
            retry_count -= 1
            if vals.get('name', False):
                lv_ids = self.pool.get('hr.holidays').search(
                    cr, uid, [('employee_id', '=', vals['employee_id']),
                              ('type', '=', 'remove'),
                              ('date_from', '<=', vals['name']),
                              ('date_to', '>=', vals['name']),
                              ('state', 'in',
                               ['validate', 'validate1'])],
                    context=context)
                if len(lv_ids) > 0 and retry_count >= 0:
                    ee_data = self.pool.get('hr.employee').read(
                        cr, uid, vals['employee_id'], ['name'],
                        context=context)
                    self.create_adjustments(cr, uid,
                                            [vals['employee_id']],
                                            vals['name'], context=context)
                elif len(lv_ids) > 0:
                    raise osv.except_osv(_('Warning'),
                                         _('There is already one or more leaves recorded for the date you have chosen:\nEmployee: %s\nDate: %s' %(ee_data['name'], vals['name'])))
        
        return super(hr_attendance, self).create(cr, uid, vals, context=context)
    
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
            wot_obj._change_restday(cr, uid, ot, restdays, context=context)
        
        return
    
    def get_all_dates(self, cr, uid, weeks, context=None):
        
        res = []
        for week in weeks:
            dStart = datetime.strptime(week.week_start, OE_DFORMAT).date()
            dEnd = dStart + relativedelta(weeks= +1, days= -1)
            while dStart <= dEnd:
                res.append(dStart)
                dStart = dStart + timedelta(days= +1)
        
        return res
    
    def get_week_start_list(self, cr, uid, sched_ids, context=None):
        
        res = []
        for sched in self.pool.get('hr.schedule').browse(cr, uid, sched_ids, context=context):
            dStart = datetime.strptime(sched.date_start, OE_DFORMAT).date()
            dEnd = datetime.strptime(sched.date_end, OE_DFORMAT).date()
            while dStart <= dEnd:
                if dStart.weekday() == 0:
                    res.append(dStart.strftime(OE_DFORMAT))
                dStart += timedelta(days= +1)
        
        return res
            
    def create_adjustments(self, cr, uid, employee_ids, dt_str, context=None):
        
        ee_obj = self.pool.get('hr.employee')
        sched_obj = self.pool.get('hr.schedule')
        att_obj = self.pool.get('hr.attendance')
        watt_obj = self.pool.get('hr.attendance.weekly')
        
        if context is None:
            context = {}
        
        dt = datetime.strptime(dt_str, OE_DTFORMAT)
        while dt.weekday() != 0:
            dt = dt + timedelta(days= -1)
        weekly_obj = self.pool.get('hr.attendance.weekly')
        weekly_id_list = weekly_obj.search(cr, uid, [('week_start', '=', dt.strftime(OE_DFORMAT))],
                                                  context=context)
        weeklys = weekly_obj.browse(cr, uid, weekly_id_list, context=context)
        week_start_list = [dt.strftime(OE_DFORMAT)]
        
        for ee in ee_obj.browse(cr, uid, employee_ids, context=context):
            
            # Because of various interactions within the software, the
            # following steps have to be done in exactly the following order.
            #
            
            # 1. Regenerate schedule for the weeks of the selected weekly attendances
            sched_ids = []
            new_sched_ids = []
            for week_start in week_start_list:
                sched_ids += sched_obj.search(cr, uid, [('employee_id', '=', ee.id),
                                                        ('date_start', '<=', week_start),
                                                        ('date_end', '>=', week_start)],
                                              context=context)
            updated_week_start_list = self.get_week_start_list(cr, uid, sched_ids,
                                                               context=context)
            updated_week_start_list = self.sort_days(updated_week_start_list)
            if len(sched_ids) > 0:
                sched_obj.unlink(cr, uid, sched_ids, context=context)
            for week_start in updated_week_start_list:
                new_sched_ids += self.generate_schedules(cr, uid, ee, week_start,
                                                        context=context)
            
            # 2. Reset the rest-days of the schedule according to weekly attendance
            employee_ot_list = []
            for week in weeklys:
                employee_ot_list += [ot for ot in week.ot_ids if ot.employee_id.id == ee.id]
            for ot in employee_ot_list:
                self.change_schedule_restday(cr, uid, ot, context=context)
            
            # 3. Remove attendances for the days of the selected weekly attendances
            list_of_dates = self.get_all_dates(cr, uid, weeklys, context=context)
            list_of_days = [d.strftime(OE_DFORMAT) for d in list_of_dates]
            att_ids = att_obj.search(cr, uid, [('employee_id', '=', ee.id),
                                               '|', ('day', 'in', list_of_days),
                                                    ('weekly_att_id', 'in', weekly_id_list)])
            if len(att_ids) > 0:
                att_obj.unlink(cr, uid, att_ids, context=context)
            
            # 4. Generate attendances for the days of the selected weekly attendances
            for week in weeklys:
                weekly_lines = watt_obj.get_weekly_lines(cr, uid, week.id,
                                                         select_employee_id=ee.id,
                                                         context=context)
                watt_obj.add_punches(cr, uid, week.id, weekly_lines, context=context)
        
        return
