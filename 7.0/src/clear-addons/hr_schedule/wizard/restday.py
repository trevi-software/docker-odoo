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
from pytz import timezone, utc

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.translate import _

class restday(osv.TransientModel):
    
    _name = 'hr.restday.wizard'
    _description = 'Schedule Template Change Wizard'
    
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', required=False),
        'st_new_id': fields.many2one('hr.schedule.template','New Template'),
        'permanent': fields.boolean('Make Permanent'),
        'temp_restday': fields.boolean('Temporary Rest Day Change', help="If selected, change the rest day to the specified day only for the selected schedule."),
        'dayofweek': fields.selection([('0','Monday'),('1','Tuesday'),('2','Wednesday'),('3','Thursday'),('4','Friday'),('5','Saturday'),('6','Sunday')], 'Rest Day', select=True),
        'temp_week_start': fields.date('Start of Week'),
        'week_start': fields.date('Start of Week'),
        'multi': fields.boolean('Choose more than one employee'),
        'employee_ids': fields.many2many('hr.employee', 'restday_wizard_employee_rel',
                                         'wizard_id', 'employee_id', 'Employees'),
    }
    
    _defaults = {
        'temp_restday': False,
    }
    
    def onchange_week(self, cr, uid, ids, newdate):
        
        res = {'value': {'week_start': newdate}}
        if newdate:
            d = datetime.strptime(newdate, "%Y-%m-%d")
            if d.weekday() != 0:
                res['value']['week_start'] = False
                return res
        return res
    
    def onchange_temp_week(self, cr, uid, ids, newdate):
        
        res = {'value': {'temp_week_start': newdate}}
        if newdate:
            d = datetime.strptime(newdate, "%Y-%m-%d")
            if d.weekday() != 0:
                res['value']['temp_week_start'] = False
                return res
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

        for worktime in template.worktime_ids:
            
            if worktime.dayofweek != template_dayofweek:
                continue
            
            hour, sep, minute = worktime.hour_from.partition(':')
            toHour, toSep, toMin = worktime.hour_to.partition(':')
            if len(sep) == 0 or len(toSep) == 0:
                raise osv.except_osv(_('Invalid Time Format'), _('The time should be entered as HH:MM'))
            
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
    
    def _change_restday(self, cr, uid, employee_ids, week_start, dayofweek, context=None):
        
        sched_obj = self.pool.get('hr.schedule')
        sched_detail_obj = self.pool.get('hr.schedule.detail')
        
        for employee_id in employee_ids:
            schedule_ids = sched_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                                     ('date_start', '<=', week_start),
                                                     ('date_end', '>=', week_start)],
                                           context=context)
            sched = sched_obj.browse(cr, uid, schedule_ids[0], context=context)
            dtFirstDay = datetime.strptime(sched.detail_ids[0].date_start, OE_DTFORMAT)
            date_start = dtFirstDay.strftime(OE_DFORMAT) < week_start and week_start +' '+ dtFirstDay.strftime('%H:%M:%S') or dtFirstDay.strftime(OE_DTFORMAT)
            dtNextWeek = datetime.strptime(date_start, OE_DTFORMAT) + relativedelta(weeks= +1)
            
            # First get the current rest days
            rest_days = sched_obj.get_rest_days_by_id(cr, uid, sched.id, dtFirstDay.strftime(OE_DFORMAT),
                                                      context=context)
            
            # Next, remove the schedule detail for the new rest day
            for dtl in sched.detail_ids:
                if dtl.date_start < week_start or datetime.strptime(dtl.date_start, OE_DTFORMAT) >= dtNextWeek:
                    continue
                if dtl.dayofweek == dayofweek:
                    sched_detail_obj.unlink(cr, uid, dtl.id, context=context)
    
            # Enter the new rest day(s)
            #
            sched_obj = self.pool.get('hr.schedule')
            nrest_days = [dayofweek] + rest_days[1:]
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
            
            # Last, add a schedule detail for the first rest day in the week using the
            # template for the new (temp) rest day
            #
            if len(rest_days) > 0:
                self._create_detail(cr, uid, sched, str(rest_days[0]), dayofweek, week_start,
                                    context=context)
        
        return
    
    def _remove_add_schedule(self, cr, uid, employee_id, schedule_id, week_start, tpl_id, context=None):
        
        # Remove the current schedule and add a new one in its place according to
        # the new template. If the week that the change starts in is not at the
        # beginning of a schedule create two new schedules to accommodate the
        # truncated old one and the partial new one.
        #
        
        sched_obj = self.pool.get('hr.schedule')
        ee = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
        if schedule_id:
            sched = sched_obj.browse(cr, uid, schedule_id, context=context)
            sched_name = sched.name
            date_start = sched.date_start
            date_end = sched.date_end
            sched_tpl_id = sched.template_id.id
        else:
            date_start = week_start
            dWeekStart = datetime.strptime(date_start, OE_DFORMAT)
            date_end = (dWeekStart + timedelta(days= +6)).strftime(OE_DFORMAT)
            sched_name = ee.name +': '+ dWeekStart.strftime(OE_DFORMAT) +' Wk '+ str(dWeekStart.isocalendar()[1])
            sched_tpl_id = tpl_id

        vals2 = False
        vals1 = {
            'name': sched_name,
            'employee_id': employee_id,
            'template_id': tpl_id,
            'date_start': date_start,
            'date_end': date_end,
        }
        
        if schedule_id:
            if week_start > date_start:
                dWeekStart = datetime.strptime(week_start, '%Y-%m-%d').date()
                start_day = dWeekStart.strftime('%Y-%m-%d')
                vals1['template_id'] = sched_tpl_id
                vals1['date_end'] = (dWeekStart + relativedelta(days= -1)).strftime('%Y-%m-%d')
                vals2 = {
                    'name': ee.name +': '+ start_day +' Wk '+ str(dWeekStart.isocalendar()[1]),
                    'employee_id': employee_id,
                    'template_id': tpl_id,
                    'date_start': start_day,
                    'date_end': date_end,
                }
            
            sched_obj.unlink(cr, uid, schedule_id, context=context)
        sched_obj.create(cr, uid, vals1, context=context)
        if vals2:
            sched_obj.create(cr, uid, vals2, context=context)
    
    def _change_by_template(self, cr, uid, employee_ids, week_start, new_template_id, doall, context=None):
        
        sched_obj = self.pool.get('hr.schedule')
        
        for employee_id in employee_ids:
            schedule_ids = sched_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                                     ('date_start', '<=', week_start),
                                                     ('date_end', '>=', week_start)],
                                           context=context)
            
            # Remove the current schedule, if it exists, and add a new one in its place according to
            # the new template
            #
            if len(schedule_ids) == 0:
                self._remove_add_schedule(cr, uid, employee_id, False, week_start, new_template_id,
                                          context=context)
            else:
                self._remove_add_schedule(cr, uid, employee_id, schedule_ids[0], week_start, new_template_id,
                                          context=context)
            
            # Also, change all subsequent schedules if so directed
            if doall:
                ids = sched_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                                 ('date_start', '>', week_start)],
                                       order='date_start asc', context=context)
                for sched in sched_obj.browse(cr, uid, ids, context=context):
                    self._remove_add_schedule(cr, uid, employee_id, sched.id, sched.date_start, new_template_id, context)
        
        return
    
    def change_restday(self, cr, uid, ids, context=None):
        
        employee_ids = []
        data = self.read(cr, uid, ids[0], [], context=context)
        if data.get('multi', False):
            employee_ids = data['employee_ids']
        else:
            employee_ids.append(data['employee_id'][0])
        
        # Change the rest day for only one schedule
        if data.get('temp_restday', False) and data.get('dayofweek', False) and data.get('temp_week_start', False):
            self._change_restday(cr, uid, employee_ids, data['temp_week_start'],
                                 data['dayofweek'], context=context)
        
        # Change entire week's schedule to the chosen schedule template
        if not data.get('temp_restday', False) and data.get('st_new_id', False) and data.get('week_start', False):
            
            if data.get('week_start', False):
                self._change_by_template(cr, uid, employee_ids, data['week_start'],
                                         data['st_new_id'][0], data.get('permanent', False),
                                         context=context)
            
            # If this change is permanent modify employee's contract to reflect the new template
            #
            if data.get('permanent', False):
                ee_obj = self.pool.get('hr.employee')
                for e_id in employee_ids:
                    ee = ee_obj.browse(cr, uid, e_id, context=context)
                    self.pool.get('hr.contract').write(cr, uid, ee.contract_id.id,
                                                       {'schedule_template_id': data['st_new_id'][0]},
                                                       context=context)
        
        return {
            'name': 'Change Schedule Template',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.restday.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
