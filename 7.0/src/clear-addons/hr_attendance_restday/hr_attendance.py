#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

#from openerp.addons.hr_schedule.wizard.restday import _change_restday
from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools.float_utils import float_is_zero
from openerp.tools.translate import _

SELECT_RESTDAYS = [
    ('mon', 'Monday'),
    ('tue', 'Tuesday'),
    ('wed', 'Wednesday'),
    ('thu', 'Thursday'),
    ('fri', 'Friday'),
    ('sat', 'Saturday'),
    ('sun', 'Sunday'),
]

class hr_weekly_ot(orm.Model):
    
    _inherit = 'hr.attendance.weekly.ot'
    
    _columns = {
        'off1': fields.selection(SELECT_RESTDAYS, 'Off1'),
        'off2': fields.selection(SELECT_RESTDAYS, 'Off2'),
    }
    
    def onchange_employee(self, cr, uid, ids, employee_id, weekly_id, context=None):
        
        sched_obj = self.pool.get('hr.schedule')
        
        res = {'value': {'off1': False, 'off2': False}}
        weekly = self.pool.get('hr.attendance.weekly').browse(cr, uid, weekly_id, context=context)
        sched_ids = sched_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                               ('date_start', '<=', weekly.week_start),
                                               ('date_end', '>', weekly.week_start)],
                                     context=context)
        restdays = []
        if len(sched_ids) > 0:
            restdays = sched_obj.get_rest_days_by_id(cr, uid, sched_ids[0], weekly.week_start,
                                                     context=context)
        
        restconv = {0: 'mon',
                    1: 'tue',
                    2: 'wed',
                    3: 'thu',
                    4: 'fri',
                    5: 'sat',
                    6: 'sun'}
        if len(restdays) > 1:
            res['value']['off2'] = restconv[restdays[1]]
        if len(restdays) > 0:
            res['value']['off1'] = restconv[restdays[0]]
        
        return res
    
    def _create_detail(self, cr, uid, schedule, actual_dayofweek, template_dayofweek,
                       week_start, context=None):
        
        # First, see if there's a schedule for the actual dayofweek. If so, use it.
        #
        if schedule.used_template_id:
            template = schedule.used_template_id
        else:
            template = schedule.template_id
        
        for worktime in template.worktime_ids:
            if worktime.dayofweek == actual_dayofweek:
                template_dayofweek = actual_dayofweek
        
        prevutcdtStart = False
        prevDayofWeek = False
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        local_tz = timezone(user.tz)
        dSchedStart = datetime.strptime(schedule.date_start, OE_DFORMAT).date()
        dWeekStart = schedule.date_start < week_start and datetime.strptime(week_start, OE_DFORMAT).date() or dSchedStart

        # Get the work times for the template day of week. It's possible that
        # there isn't one. In that case start from Monday (0) and use the first
        # available day of week until you reach Sunday(6), at which point we exit
        # the loop
        #
        _temp_dayofweek = 0
        template_worktime_ids = []
        while len(template_worktime_ids) == 0 and _temp_dayofweek < 7:
            for worktime in template.worktime_ids:
                
                if worktime.dayofweek != template_dayofweek:
                    continue
                else:
                    template_worktime_ids.append(worktime)
            
            if len(template_worktime_ids) == 0:
                template_dayofweek = str(_temp_dayofweek)
            _temp_dayofweek += 1

        for worktime in template_worktime_ids:
            
            if worktime.dayofweek != template_dayofweek:
                continue
            
            hour, sep, minute = worktime.hour_from.partition(':')
            toHour, toSep, toMin = worktime.hour_to.partition(':')
            if len(sep) == 0 or len(toSep) == 0:
                raise orm.except_orm(_('Invalid Time Format'), _('The time should be entered as HH:MM'))
            
            # XXX - Someone affected by DST should fix this
            #
            dtStart = datetime.strptime(dWeekStart.strftime('%Y-%m-%d') +' '+ hour +':'+ minute +':00', '%Y-%m-%d %H:%M:%S')
            locldtStart = local_tz.localize(dtStart, is_dst=False)
            utcdtStart = locldtStart.astimezone(utc)
            if actual_dayofweek != '0':
                utcdtStart = utcdtStart + relativedelta(days= +int(actual_dayofweek))
            dDay = utcdtStart.astimezone(local_tz).date()
            
            # If this worktime is a continuation (i.e - after lunch) set the start
            # time based on the difference from the previous record
            #
            if prevDayofWeek and prevDayofWeek == actual_dayofweek:
                prevHour = prevutcdtStart.strftime('%H')
                prevMin = prevutcdtStart.strftime('%M')
                curHour = utcdtStart.strftime('%H')
                curMin = utcdtStart.strftime('%M')
                delta_seconds = (datetime.strptime(curHour+':'+curMin, '%H:%M') - datetime.strptime(prevHour+':'+prevMin, '%H:%M')).seconds
                utcdtStart = prevutcdtStart + timedelta(seconds= +delta_seconds)
                dDay = prevutcdtStart.astimezone(local_tz).date()
            
            delta_seconds = (datetime.strptime(toHour+':'+toMin, '%H:%M') - datetime.strptime(hour+':'+minute, '%H:%M')).seconds
            utcdtEnd = utcdtStart + timedelta(seconds= +delta_seconds)
            
            val = {
                'name': schedule.name,
                'dayofweek': actual_dayofweek,
                'day': dDay,
                'date_start': utcdtStart.strftime('%Y-%m-%d %H:%M:%S'),
                'date_end': utcdtEnd.strftime('%Y-%m-%d %H:%M:%S'),
                'schedule_id': schedule.id,
            }
            self.pool.get('hr.schedule').write(cr, uid, schedule.id, {'detail_ids': [(0, 0, val)]},
                                               context=context)
            
            prevDayofWeek = worktime.dayofweek
            prevutcdtStart = utcdtStart
    
    def _create_schedule(self, cr, uid, ot, week_start, context=None):
        
        # Remove the current schedule and add a new one in its place according to
        # the new template. If the week that the change starts in is not at the
        # beginning of a schedule create two new schedules to accomodate the
        # truncated old one and the partial new one.
        #
        
        sched_obj = self.pool.get('hr.schedule')

        dWeekStart = datetime.strptime(week_start, '%Y-%m-%d').date()
        start_day = dWeekStart.strftime('%Y-%m-%d')
        vals1 = {
            'name': ot.employee_id.name +': '+ week_start +' Wk '+ str(dWeekStart.isocalendar()[1]),
            'employee_id': ot.employee_id.id,
            'template_id': ot.employee_id.contract_id.schedule_template_id.id,
            'date_start': start_day,
            'date_end': (dWeekStart + relativedelta(days =+6)).strftime(OE_DFORMAT),
        }
        
        res = sched_obj.create(cr, uid, vals1, context=context)
        
        return res
    
    def _change_restday(self, cr, uid, ot, daysofweek, force=False, context=None):
        
        sched_obj = self.pool.get('hr.schedule')
        sched_detail_obj = self.pool.get('hr.schedule.detail')
        week_start = ot.weekly_id.week_start
        
        schedule_ids = sched_obj.search(cr, uid, [('employee_id', '=', ot.employee_id.id),
                                                 ('date_start', '<=', week_start),
                                                 ('date_end', '>=', week_start)],
                                       context=context)
        
        # If there is no schedule create one
        if len(schedule_ids) == 0:
            schedule_ids.append(self._create_schedule(cr, uid, ot, week_start, context=context))
        
        sched = sched_obj.browse(cr, uid, schedule_ids[0], context=context)
        
        if len(sched.detail_ids) > 0:
            dtFirstDay = datetime.strptime(sched.detail_ids[0].date_start, OE_DTFORMAT)
            while dtFirstDay.weekday() > 0 or dtFirstDay.strftime(OE_DFORMAT) > week_start:
                dtFirstDay = dtFirstDay + timedelta(days= -1)
            date_start = dtFirstDay.strftime(OE_DFORMAT) < week_start and week_start +' '+ dtFirstDay.strftime('%H:%M:%S') or dtFirstDay.strftime(OE_DTFORMAT)
            dtNextWeek = datetime.strptime(date_start, OE_DTFORMAT) + relativedelta(weeks= +1)
        else:
            dtFirstDay = datetime.strptime(week_start, OE_DFORMAT)

        # First, get the current rest days
        rest_days = sched_obj.get_rest_days_by_id(cr, uid, sched.id, dtFirstDay.strftime(OE_DFORMAT),
                                                  context=context)
        
        # Check if there are any changes
        no_change = True
        for d in daysofweek:
            if d not in rest_days:
                no_change = False
                break
        for r in rest_days:
            if r not in daysofweek:
                no_change = False
                break
        if no_change and not force:
            return
        
        # Enter the new rest day(s)
        #
        sched_obj = self.pool.get('hr.schedule')
        nrest_days = daysofweek
        dSchedStart = datetime.strptime(sched.date_start, OE_DFORMAT).date()
        dWeekStart = sched.date_start < week_start and datetime.strptime(week_start, OE_DFORMAT).date() or dSchedStart
        if dWeekStart == dSchedStart:
            sched_obj.add_restdays(cr, uid, sched.id, sched.template_id, 'restday_ids1', rest_days=nrest_days, context=context)
        elif dWeekStart == dSchedStart + relativedelta(days= +7):
            sched_obj.add_restdays(cr, uid, sched.id, sched.template_id, 'restday_ids2', rest_days=nrest_days, context=context)
        elif dWeekStart == dSchedStart + relativedelta(days= +14):
            sched_obj.add_restdays(cr, uid, sched.id, sched.template_id, 'restday_ids3', rest_days=nrest_days, context=context)
        elif dWeekStart == dSchedStart + relativedelta(days= +21):
            sched_obj.add_restdays(cr, uid, sched.id, sched.template_id, 'restday_ids4', rest_days=nrest_days, context=context)
        elif dWeekStart == dSchedStart + relativedelta(days= +28):
            sched_obj.add_restdays(cr, uid, sched.id, sched.template_id, 'restday_ids5', rest_days=nrest_days, context=context)

        # Next, add a schedule detail for the rest day using the
        # template for the new (temp) rest day
        #
        for rest_day in rest_days:
            create_detail = True
            if rest_day not in daysofweek:
                for dtl in sched.detail_ids:
                    if dtl.dayofweek == str(rest_day):
                        create_detail = False
                        break
            elif rest_day in daysofweek:
                create_detail = False
            if create_detail:
                    self._create_detail(cr, uid, sched, str(rest_day), str(daysofweek[0]), week_start,
                                        context=context)
        
        # Last, remove the schedule detail for the new rest day
        for dtl in sched.detail_ids:
            if dtl.date_start < week_start or datetime.strptime(dtl.date_start, OE_DTFORMAT) >= dtNextWeek:
                continue
            if int(dtl.dayofweek) in daysofweek:
                sched_detail_obj.unlink(cr, uid, dtl.id, context=context)
        
        return
    
    def process_attendance(self, cr, uid, ot_id, context=None):

        lookup = {
            'mon': 0,
            'tue': 1,
            'wed': 2,
            'thu': 3,
            'fri': 4,
            'sat': 5,
            'sun': 6,
        }
        ot = self.browse(cr, uid, ot_id, context=context)
        
        restdays = []
        if ot.off1:
            restdays.append(lookup[ot.off1])
        if ot.off2:
            restdays.append(lookup[ot.off2])
        
        if len(restdays) > 0:
            self._change_restday(cr, uid, ot, restdays, context=context)
        
        return
    
    def write(self, cr, uid, ids, vals, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        res = super(hr_weekly_ot, self).write(cr, uid, ids, vals, context=context)
        
        for i in ids:
            self.process_attendance(cr, uid, i, context=context)

        return res

class weekly_attendance(orm.Model):
    
    _inherit = 'hr.attendance.weekly'
    
    def button_update_employees(self, cr, uid, ids, context=None):
        
        ot_obj = self.pool.get('hr.attendance.weekly.ot')
        res = super(weekly_attendance, self).button_update_employees(cr, uid, ids, context=context)
        weekly = self.browse(cr, uid, ids[0], context=context)
        for ot in weekly.ot_ids:
            res_onchange = ot_obj.onchange_employee(cr, uid, [], ot.employee_id.id, weekly.id,
                                                    context=context)
            vals = {'off1': res_onchange['value']['off1'],
                    'off2': res_onchange['value']['off2']}
            ot_obj.write(cr, uid, ot.id, vals, context=context)
        
        return res
