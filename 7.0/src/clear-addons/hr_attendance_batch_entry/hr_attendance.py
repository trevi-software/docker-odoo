#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2011,2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

import time
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone, utc

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools.translate import _

import logging
_l = logging.getLogger(__name__)

class hr_attendance_weekly(osv.osv):
    
    _name = 'hr.attendance.weekly'
    _description = 'Weekly Attendance'
    
    _columns = {
                'att_ids': fields.one2many('hr.attendance', 'weekly_att_id', 'Daily Attendance Records', readonly=True),
                'department_id': fields.many2one('hr.department', 'Department', required=True),
                'week_start': fields.date('Start of Week', required=True),
                'partial_ids': fields.one2many('hr.attendance.weekly.partial', 'weekly_id', 'Partial Attendance'),
                'ot_ids': fields.one2many('hr.attendance.weekly.ot', 'weekly_id', 'Over-Time'),
                'init_time': fields.datetime('Attendance Creation Time'),
    }
    
    _rec_name = 'week_start'
    
    _order = 'week_start desc, department_id'
    
    _sql_constraints = [
                ('week_dept_uniq', 'UNIQUE(week_start, department_id)', 'Duplicate record!'),
    ]
    
    def onchange_department(self, cr, uid, ids, department_id, context=None):
        
        res = {}
        self.action_delete_hours(cr, uid, ids, context=context)
        return res
    
    def onchange_week_start(self, cr, uid, ids, newdate, context=None):
        
        res = {'value': {'week_start': newdate}}
        if newdate:
            d = datetime.strptime(newdate, "%Y-%m-%d")
            if d.weekday() != 0:
                res['value']['week_start'] = False
                return res
        self.action_delete_hours(cr, uid, ids, context=context)
        return res
    
    def button_delete_hours(self, cr, uid, ids, context=None):
        
        return self.action_delete_hours(cr, uid, ids, context=None)
    
    def action_delete_hours(self, cr, uid, ids, employee_ids=None, context=None):
        
        att_obj = self.pool.get('hr.attendance')
        
        domain = [('weekly_att_id', 'in', ids)]
        if employee_ids != None:
            domain = domain + [('employee_id.id', 'in', employee_ids)]
        
        att_ids = att_obj.search(cr, uid, domain, context=context)
        att_obj.unlink(cr, uid, att_ids, context=context)
        return True
    
    def is_attendance_dirty(self, cr, uid, my_id, context=None):
        
        ot_obj = self.pool.get('hr.attendance.weekly.ot')
        partial_obj = self.pool.get('hr.attendance.weekly.partial')
        weekly = self.browse(cr, uid, my_id, context=context)
        
        # Weekly attendance considered dirty in one of six cases:
        #    1. No hr.attendance records have been created
        #    2. One of the attached OT records were modified or
        #       created after the weekly attendance was last updated.
        #    3. One of the attached Partial attendance records were
        #       modified after the weekly attendance was last updated.
        #    4. One of the attached Special OT (if installed) records were
        #       modified after the weekly attendance was last update.
        #    5. A leave was created or updated during the week of the
        #       weekly attendance but after the last time it was updated.
        #    6. A schedule was created or updated during the week of the
        #       weekly attendance but after the last time it was updated.
        #
        if weekly.att_ids == 0 and not weekly.init_time:
            return True
        elif len(weekly.att_ids) > 0:
            
            dtInit = datetime.strptime(weekly.init_time, OE_DTFORMAT)
            for ot in weekly.ot_ids:
                perms = ot_obj.perm_read(cr, uid, [ot.id], context=context)
                dtCreate = datetime.strptime(perms[0].get('create_date', False), '%Y-%m-%d %H:%M:%S.%f')
                dtUpdate = datetime.strptime(perms[0].get('write_date', False), '%Y-%m-%d %H:%M:%S.%f')
                if dtCreate >= dtInit or dtUpdate >= dtInit:
                    return True
            for partial in weekly.partial_ids:
                perms = partial_obj.perm_read(cr, uid, [partial.id], context=context)
                dtCreate = datetime.strptime(perms[0].get('create_date', False), '%Y-%m-%d %H:%M:%S.%f')
                dtUpdate = datetime.strptime(perms[0].get('write_date', False), '%Y-%m-%d %H:%M:%S.%f')
                if dtCreate >= dtInit or dtUpdate >= dtInit:
                    return True
            
            spot_obj = False
            try:
                spot_obj = self.pool.get('hr.attendance.weekly.specialot')
            except:
                pass
            
            if spot_obj:
                spot_obj = self.pool.get('hr.attendance.weekly.specialot')
                for spot in weekly.specialot_ids:
                    perms = spot_obj.perm_read(cr, uid, [spot.id], context=context)
                    dtCreate = datetime.strptime(perms[0].get('create_date', False), '%Y-%m-%d %H:%M:%S.%f')
                    dtUpdate = datetime.strptime(perms[0].get('write_date', False), '%Y-%m-%d %H:%M:%S.%f')
                    if dtCreate >= dtInit or dtUpdate >= dtInit:
                        return True
        dirty_lv_ee_ids = self._get_employees_with_dirty_leaves(cr, uid, weekly, context=context)
        if len(dirty_lv_ee_ids) > 0:
            return True
        dirty_sched_ee_ids = self._get_employees_with_dirty_schedules(cr, uid, weekly, context=context)
        if len(dirty_sched_ee_ids) > 0:
            return True
        
        return False

    def _get_employees_with_duplicate_attendance(
                                        self, cr, uid, weekly, context=None):

        ee_ids = self.get_employees(cr, uid, weekly, context=context)
        res = []

        if len(ee_ids) == 0:
            return res

        dtStart = datetime.strptime(
                                weekly.week_start + ' 00:00:00', OE_DTFORMAT)
        dtNext = dtStart + timedelta(days=7)

        # Find duplicate attendances within the weekly attendance's time-frame
        cr.execute("""SELECT employee_id,name,COUNT(*)
            FROM hr_attendance
            WHERE employee_id IN %s
            AND day >= %s
            AND day < %s
            GROUP BY employee_id, name
            HAVING COUNT(*) > 1
            """, (tuple(ee_ids), dtStart.strftime(OE_DTFORMAT),
                  dtNext.strftime(OE_DTFORMAT)))
        for _d in cr.fetchall():
            if _d[0] not in res:
                res.append(_d[0])

        return res

    def _get_employees_with_dirty_leaves(self, cr, uid, weekly, context=None):
        
        ee_ids = self.get_employees(cr, uid, weekly, context=context)
        res = []

        if len(ee_ids) == 0:
            return res

        # XXX - arbitrary constant!!!!
        #       Maybe hr.attendance.weekly should have a time zone field?
        #
        local_tz = timezone('Africa/Addis_Ababa')
        dtStart = datetime.strptime(weekly.week_start + ' 00:00:00', OE_DTFORMAT)
        utcdtStart = (local_tz.localize(dtStart, is_dst=False)).astimezone(utc)
        utcdtNextStart = utcdtStart + timedelta(days=7)

        # XXX Hack to prevent false positives when comparing timestamp
        #     with datetime that doesn't have millisec. part.
        init_time = weekly.init_time + '.999999'

        # Find leaves created or modified within the weekly attendance's time-frame
        cr.execute("""SELECT id,employee_id
            FROM hr_holidays
            WHERE employee_id IN %s
            AND type = %s
            AND date_to >= %s
            AND date_from < %s
            AND (create_date > %s
                 OR write_date > %s)
            """, (tuple(ee_ids), 'remove', utcdtStart.strftime(OE_DTFORMAT),
                  utcdtNextStart.strftime(OE_DTFORMAT), init_time, init_time))
        for _d in cr.fetchall():
            if _d[1] not in res:
                res.append(_d[1])
        
        return res

    def _get_employees_with_dirty_schedules(self, cr, uid, weekly, context=None):

        ee_ids = self.get_employees(cr, uid, weekly, context=context)
        res = []

        if len(ee_ids) == 0:
            return res

        # XXX Hack to prevent false positives when comparing timestamp
        #     with datetime that doesn't have millisec. part.
        init_time = weekly.init_time + '.999999'

        # Note any employees without a schedule for the week
        #
        sched_ids = []
        with_sched_ee_ids = []
        cr.execute("""SELECT id,employee_id
            FROM hr_schedule
            WHERE employee_id IN %s
            AND date_end >= %s
            AND date_start <= %s
            """, (tuple(ee_ids), weekly.week_start, weekly.week_start))
        for _d in cr.fetchall():
            sched_ids.append(_d[0])
            if _d[1] not in with_sched_ee_ids:
                with_sched_ee_ids.append(_d[1])
        if len(with_sched_ee_ids) != len(ee_ids):
            for eid in ee_ids:
                if eid not in with_sched_ee_ids:
                    res.append(eid)

        if len(sched_ids) == 0:
            return res

        # Find schedules created or modified within the weekly attendance's time-frame.
        #
        cr.execute("""SELECT id,employee_id
            FROM hr_schedule
            WHERE id IN %s
            AND (create_date > %s
                 OR write_date > %s)
            """, (tuple(sched_ids), init_time, init_time))
        for _d in cr.fetchall():
            if _d[1] not in res:
                res.append(_d[1])

        # For the remaining employee ids search for schedule details
        # created/modified within weekly attendance's time-frame.
        #
        mod_ee_ids = [eid for eid in ee_ids if eid not in res]
        if len(mod_ee_ids) > 0:
            cr.execute("""SELECT id,employee_id
                FROM hr_schedule_detail
                WHERE schedule_id IN %s
                AND employee_id IN %s
                AND (create_date > %s
                     OR write_date > %s)
                """, (tuple(sched_ids), tuple(mod_ee_ids), init_time,
                      init_time))
            for _d in cr.fetchall():
                if _d[1] not in res:
                    res.append(_d[1])

        return res
    
    def get_attendance_dirty_employees(self, cr, uid, my_id, context=None):
        
        res = []
        weekly = self.browse(cr, uid, my_id, context=context)
        ee_ids = self.get_employees(cr, uid, weekly, context=context)
        ot_obj = self.pool.get('hr.attendance.weekly.ot')
        partial_obj = self.pool.get('hr.attendance.weekly.partial')
        
        # Weekly attendance considered dirty in one of six cases:
        #    1. No hr.attendance records have been created
        #    2. One of the attached OT records were modified or
        #       created after the weekly attendance was last updated.
        #    3. One of the attached Partial attendance records were
        #       modified after the weekly attendance was last update.
        #    4. One of the attached Special OT (if installed) records were
        #       modified after the weekly attendance was last update.
        #    5. A leave was created or updated during the week of the
        #       weekly attendance but after the last time it was updated.
        #    6. A schedule was created or updated during the week of the
        #       weekly attendance but after the last time it was updated.
        #    7. Multiple sign-in / sign-out per day
        #
        if not weekly.att_ids or len(weekly.att_ids) == 0 or not weekly.init_time:
            res += ee_ids
            
        elif len(weekly.att_ids) > 0:
            
            problem_ee_ids = []
            
            dtInit = datetime.strptime(weekly.init_time, OE_DTFORMAT)
            for ot in weekly.ot_ids:
                perms = ot_obj.perm_read(cr, uid, [ot.id], context=context)
                dtCreate = datetime.strptime(perms[0].get('create_date', False), '%Y-%m-%d %H:%M:%S.%f')
                dtUpdate = datetime.strptime(perms[0].get('write_date', False), '%Y-%m-%d %H:%M:%S.%f')
                if dtCreate >= dtInit or dtUpdate >= dtInit:
                    problem_ee_ids.append(ot.employee_id.id)
            for partial in weekly.partial_ids:
                perms = partial_obj.perm_read(cr, uid, [partial.id], context=context)
                dtCreate = datetime.strptime(perms[0].get('create_date', False), '%Y-%m-%d %H:%M:%S.%f')
                dtUpdate = datetime.strptime(perms[0].get('write_date', False), '%Y-%m-%d %H:%M:%S.%f')
                if dtCreate >= dtInit or dtUpdate >= dtInit:
                    if partial.employee_id.id not in problem_ee_ids:
                        problem_ee_ids.append(partial.employee_id.id)
            
            spot_obj = False
            try:
                spot_obj = self.pool.get('hr.attendance.weekly.specialot')
            except:
                pass
            
            if spot_obj:
                spot_obj = self.pool.get('hr.attendance.weekly.specialot')
                for spot in weekly.specialot_ids:
                    perms = spot_obj.perm_read(cr, uid, [spot.id], context=context)
                    dtCreate = datetime.strptime(perms[0].get('create_date', False), '%Y-%m-%d %H:%M:%S.%f')
                    dtUpdate = datetime.strptime(perms[0].get('write_date', False), '%Y-%m-%d %H:%M:%S.%f')
                    if dtCreate >= dtInit or dtUpdate >= dtInit:
                        if spot.employee_id.id not in problem_ee_ids:
                            problem_ee_ids.append(spot.employee_id.id)
            
            dirty_lv_ee_ids = self._get_employees_with_dirty_leaves(cr, uid, weekly, context=context)
            if len(dirty_lv_ee_ids) > 0:
                for e_id in dirty_lv_ee_ids:
                    if e_id not in problem_ee_ids:
                        problem_ee_ids.append(e_id)
            
            dirty_sched_ee_ids = self._get_employees_with_dirty_schedules(cr, uid, weekly, context=context)
            if len(dirty_sched_ee_ids) > 0:
                for e_id in dirty_sched_ee_ids:
                    if e_id not in problem_ee_ids:
                        problem_ee_ids.append(e_id)
            
            dupl_ee_ids = self._get_employees_with_duplicate_attendance(
                                            cr, uid, weekly, context=context)
            if len(dupl_ee_ids) > 0:
                for e_id in dupl_ee_ids:
                    if e_id not in problem_ee_ids:
                        problem_ee_ids.append(e_id)

            if len(problem_ee_ids) > 0:
                for _id in problem_ee_ids:
                    if _id not in res:
                        res.append(_id)
        
        return res
        
    def get_other_weeklies(self, cr, uid, employee_id, week_start, context=None):

        res = []
        dWeekStart = datetime.strptime(week_start, OE_DFORMAT).date()
        dWeekEnd = dWeekStart + relativedelta(days=6)
        w_obj = self.pool.get('hr.attendance.weekly')
        c_obj = self.pool.get('hr.contract')
        c_ids = c_obj.search(
            cr, uid,
            [
             ('employee_id', '=', employee_id),
             ('date_start', '<=', dWeekEnd.strftime(OE_DFORMAT)),
            ], context=context
        )
        c_ids2 = c_obj.search(
            cr, uid,
            [
             ('id', 'in', c_ids),
              '|', ('date_end', '=', False),
                  ('date_end', '>=', dWeekStart.strftime(OE_DFORMAT)),
            ], context=context
        )
        c_ids = c_ids2
        if len(c_ids) > 0:
            dept_ids = []
            for c in c_obj.browse(cr, uid, c_ids, context=context):
                job = c.job_id
                if not job:
                    job = c.end_job_id
                if not job:
                    continue
                w_ids = w_obj.search(
                    cr, uid,
                    [
                     ('department_id', '=', job.department_id.id),
                     ('week_start', '=', week_start),
                    ], context=context)
                res += w_ids
                import logging
                _log = logging.getLogger(__name__)
                _log.warning('%s for %s on %s', c.employee_id.name, job.department_id.name, week_start)
        
        return res

    def get_employees(self, cr, uid, weekly, context=None):
        
        c_obj = self.pool.get('hr.contract')
        e_obj = self.pool.get('hr.employee')
        term_obj = self.pool.get('hr.employee.termination')
        attendance_obj = self.pool.get('hr.attendance')
        
        # Get all employees associated with this weekly attendance. This
        # includes current and past employees of the department
        #
        e_ids = e_obj.search(cr, uid,
                             [('contract_id', '!=', False),
                              '|', ('active', '=', True),
                                   ('active', '=', False),
                              '|', ('department_id', '=', weekly.department_id.id),
                                   ('saved_department_id', '=', weekly.department_id.id)],
                             context=context)
        att_domain = ['|', ('active', '=', True), ('active', '=', False)]
        att_ids = attendance_obj.search(cr, uid, [('weekly_att_id', '=', weekly.id)] + att_domain,
                                        order='name', context=context)
        e_att_ids = []
        have_att_ids = []
        if len(att_ids) > 0:
            att_data = attendance_obj.read(cr, uid, att_ids, ['employee_id'], context=context)
            for data in att_data:
                if data['employee_id'][0] not in e_ids:
                    e_att_ids.append(data['employee_id'][0])
                    have_att_ids.append(data['employee_id'][0])
            # Re-run it through search() to get correct ordering
            e_ids = e_obj.search(cr, uid, [('id', 'in', e_att_ids + e_ids)], context=context)

        # Remove terminated employees, unless they have an attendance record in this week
        term_ids = term_obj.search(cr, uid, [('employee_id', 'in', e_ids),
                                             ('employee_id.status', 'in', ['pending_inactive', 'inactive']),
                                             ('state', 'in', ['draft','confirm', 'done'])],
                                   context=context)
        if len(term_ids) > 0:
            term_data = term_obj.read(cr, uid, term_ids, ['name', 'employee_id'], context=context)
            for data in term_data:
                if data['name'] < weekly.week_start and data['employee_id'][0] in e_ids and data['employee_id'][0] not in have_att_ids:
                    e_ids.remove(data['employee_id'][0])

        # Remove employees who were hired after the last day of the week
        #
        invalid_ee_ids = []
        dWeekStart = datetime.strptime(weekly.week_start, OE_DFORMAT).date()
        dWeekEnd = dWeekStart + timedelta(days= +6)
        contract_obj = self.pool.get('hr.contract')
        contract_ids = contract_obj.search(cr, uid, [('employee_id', 'in', e_ids),
                                                     ('date_start', '>', dWeekEnd.strftime(OE_DFORMAT)),
                                                    ], context=context)
        datas = contract_obj.read(cr, uid, contract_ids, ['employee_id'], context=context)
        ee_contract_after_weekstart_ids = [data['employee_id'][0] for data in datas]
        has_contract_ids = self.pool.get('hr.contract').search(cr, uid, [('employee_id', 'in', e_ids),
                                                                     ('date_start', '<', dWeekEnd.strftime(OE_DFORMAT)),
                                                                     ('date_end', '>=', dWeekStart.strftime(OE_DFORMAT)),
                                                                    ], context=context)
        datas = contract_obj.read(cr, uid, has_contract_ids, ['employee_id'], context=context)
        ee_contract_before_weekend_ids = [data['employee_id'][0] for data in datas]
        for ee_id in ee_contract_after_weekstart_ids:
            if ee_id not in ee_contract_before_weekend_ids:
                invalid_ee_ids.append(ee_id)
        copy_e_ids = e_ids
        e_ids = []
        for e_id in copy_e_ids:
            if e_id not in invalid_ee_ids:
                e_ids.append(e_id)
        
        return e_ids
    
    def button_update_employees(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        weekly = self.browse(cr, uid, ids[0], context=context)
        ee_ids = self.get_employees(cr, uid, weekly, context)
        
        current_ids = [ot.employee_id.id for ot in weekly.ot_ids]
        new_ids = [eid for eid in ee_ids if eid not in current_ids]
        ot_recs = [(0, 0, {'employee_id': nid}) for nid in new_ids]
        self.write(cr, uid, weekly.id, {'ot_ids': ot_recs}, context=context)
        
        return True

    def l10n_get_midday_str(self):
        return '%Y-%m-%d 9:00:00'
    
    def l10n_get_shift_times(self):
        return ['07:00:00', '12:00:00', '13:00:00', '16:00:00']
    
    def l10n_get_amstart(self):
        return ('07', '00')
    
    def l10n_get_pmstart(self):
        return ('13', '00')
    
    def l10n_get_coldstore_name(self):
        return 'Coldroom'

    def _default_time_vals(self, cr, uid, eid, context=None):
        
        e = self.pool.get('hr.employee').browse(cr, uid, eid, context=context)
        if e.department_id and e.department_id.name.find(self.l10n_get_coldstore_name()) != -1:
            res = {'amhour': '21',
                   'ammin': '00',
                   'pmhour': '02',
                   'pmmin': '00',
            }
        else:
            amhour, ammin = self.l10n_get_amstart()
            pmhour, pmmin = self.l10n_get_pmstart()
            res = {'amhour': amhour,
                   'ammin': ammin,
                   'pmhour': pmhour,
                   'pmmin': pmmin
            }
        return res
    
    def generate_schedules(self, cr, uid, employee_ids, date_start, context=None):
        
        sched_obj = self.pool.get('hr.schedule')
        ee_obj = self.pool.get('hr.employee')
        
        dStart = datetime.strptime(date_start, OE_DFORMAT).date()
        dEnd = dStart + relativedelta(weeks= +1, days= -1)
        
        sched_ids = []
        for ee in ee_obj.browse(cr, uid, employee_ids, context=context):
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
                    'date_start': dNextStart.strftime(OE_DFORMAT),
                    'date_end': dNextEnd.strftime(OE_DFORMAT),
                }
                sched_ids.append(sched_obj.create(cr, uid, sched, context=context))
                
                dNextStart = dNextStart + relativedelta(weeks= +1)
                dNextEnd = dNextStart + relativedelta(weeks= +1, days= -1)
        
        return sched_ids
    
    def get_weekly_lines(self, cr, uid, weekly_id, select_employee_id=None, check_attendance=True, context=None):
        
        e_obj = self.pool.get('hr.employee')
        term_obj = self.pool.get('hr.employee.termination')
        # XXX - rename more appropriately: detail_obj
        sched_obj = self.pool.get('hr.schedule.detail')
        real_sched_obj = self.pool.get('hr.schedule')
        attendance_obj = self.pool.get('hr.attendance')
        wot_obj = self.pool.get('hr.attendance.weekly.ot')
        weekly = self.browse(cr, uid, weekly_id, context=context)
        res = []
        
        e_ids = []
        if select_employee_id == None:
            e_ids = self.get_employees(cr, uid, weekly, context=context)
        else:
            e_ids.append(select_employee_id)
        
        for eid in e_ids:
            vals = {
                    'employee_id': eid,
                    'department_id': weekly.department_id.id,
                    'in_times': [],
                    'out_times': [],
                    'dates': [],
            }
            
            # Sort out dates and times
            local_tz = timezone('Africa/Addis_Ababa')
            dtStart = datetime.strptime(weekly.week_start + ' 00:00:00', OE_DTFORMAT)
            utcdtStart = (local_tz.localize(dtStart, is_dst=False)).astimezone(utc)
            utcdtEnd = utcdtStart + timedelta(days=7)
            week_end = utcdtEnd.astimezone(local_tz).strftime(OE_DFORMAT)
            
            # Get schedules for this time period. If there aren't any create them.
            #
            real_sched_ids = real_sched_obj.search(cr, uid, [('employee_id', '=', eid),
                                                             ('date_start', '<', week_end),
                                                             ('date_end', '>=', weekly.week_start)],
                                                   context=context)
            if len(real_sched_ids) == 0:
                    real_sched_ids = self.generate_schedules(cr, uid, [eid],
                                                             weekly.week_start, context=context)
            
            # Get any attendance records that may already be associated with this timesheet,
            # and any records added outside of this weekly attendance.
            #
            sin = []
            sout = []
            dates = []
            att_domain = ['|', ('active', '=', True), ('active', '=', False)]

            att_ids = attendance_obj.search(cr, uid, [('weekly_att_id', '=', weekly_id),
                                                      ('employee_id', '=', eid)] + att_domain,
                                            order='name', context=context)
            att2_ids = []
            eedata = e_obj.read(cr, uid, eid, ['contract_id'], context=context)
            if check_attendance and eedata.get('contract_id', False):
                contract = self.pool.get('hr.contract').browse(cr, uid, eedata['contract_id'][0],
                                                               context=context)
                for i in range(0, 6):
                    att2_ids += attendance_obj.punch_ids_on_day(cr, uid, contract,
                                                                dtStart.date() + timedelta(days= +i),
                                                                context=context)
            for att2_id in att2_ids:
                if att2_id not in att_ids:
                    att_ids.append(att2_id)
            # Put attendance records in order of punch time
            if len(att_ids) > 0:
                att_ids = attendance_obj.search(cr, uid, [('id', 'in', att_ids)], order='name',
                                                context=context)
            if check_attendance and len(att_ids) > 0:
                for a in attendance_obj.browse(cr, uid, att_ids, context=context):
                    if a.action == 'sign_in':
                        sin.append(a.name)
                    elif a.action == 'sign_out':
                        sout.append(a.name)
                vals['in_times'] = sin
                vals['out_times'] = sout
            else:
                # Get default values from schedules. If there is no schedule create it
                #
                
                # XXX rename more appropriately: detail_ids
                sched_ids = sched_obj.search(cr, uid, [('schedule_id.employee_id', '=', eid),
                                                       ('day', '>=', weekly.week_start),
                                                       ('day', '<', week_end)],
                                             order='date_start', context=context)
                
                ee_data = e_obj.read(cr, uid, eid, ['status'], context=context)
                term_ids = term_obj.search(cr, uid, [('employee_id', '=', eid),
                                                     ('employee_id.status', 'in', ['pending_inactive', 'inactive']),
                                                     ('state', 'in', ['draft', 'confirm', 'done'])],
                                           context=context)
                if len(term_ids) > 0:
                    term_data = term_obj.read(cr, uid, term_ids[0], ['name'], context=context)
                else:
                    term_data = False

                wot_ids = wot_obj.search(cr, uid, [('employee_id', '=', eid),
                                                   ('weekly_id.week_start', '=', weekly.week_start)],
                                         context=context)

                worked_days = []
                week_days = [0, 1, 2, 3, 4, 5, 6]
                dTempSaved = False
                for s in sched_obj.browse(cr, uid, sched_ids, context=context):

                    # Break if the employee no longer works for us
                    dTerm = term_data and datetime.strptime(term_data['name'], OE_DFORMAT).date() or False
                    dToday = datetime.strptime(s.day, OE_DFORMAT).date()
                    if term_data and ee_data['status'] in ['pending_inactive', 'inactive'] and dTerm < dToday:
                        break

                    # Break if the employee no longer works in this department
                    contract_do_break = True
                    contracts = e_obj.get_contracts_on_day(cr, uid, eid, dToday, context=context)
                    for curr_contract in contracts:
                        if curr_contract and curr_contract.job_id:
                            if curr_contract.job_id.department_id.id == weekly.department_id.id:
                                contract_do_break = False
                                break
                        elif curr_contract and curr_contract.end_job_id:
                            if curr_contract.end_job_id.department_id.id == weekly.department_id.id:
                                contract_do_break = False
                                break
                    if contract_do_break:
                        continue

                    # If we have a partial record for this employee on this date, use it
                    #
                    ispartial = False
                    worked_days.append(int(s.dayofweek))
                    dTemp = datetime.strptime(s.date_start, OE_DTFORMAT).date()
                    for partial in weekly.partial_ids:
                        dPartial = datetime.strptime(partial.date, OE_DFORMAT).date()
                        if dPartial == dTemp and partial.employee_id.id == eid:
                            ispartial = True
                            dt_sched_start = datetime.strptime(s.date_start, OE_DTFORMAT)
                            if (dTempSaved is False or dTempSaved != dTemp):
                                if partial.s1hours > 0.01:
                                    dt_sched_end = dt_sched_start + timedelta(seconds= +int(partial.s1hours * 60.0 * 60.0))
                                    sin.append(dt_sched_start.strftime(OE_DTFORMAT))
                                    sout.append(dt_sched_end.strftime(OE_DTFORMAT))
                                    dates.append(dToday.strftime(OE_DFORMAT))
                            elif dTempSaved == dTemp:
                                if partial.s2hours > 0.01:
                                    dt_sched_end = dt_sched_start + timedelta(seconds= +int(partial.s2hours * 60.0 * 60.0))
                                    sin.append(dt_sched_start.strftime(OE_DTFORMAT))
                                    sout.append(dt_sched_end.strftime(OE_DTFORMAT))
                                    dates.append(dToday.strftime(OE_DFORMAT))
                            dTempSaved = dTemp
                            break
                    
                    # There is no partial record, use the date/times in the schedule
                    #
                    if not ispartial:
                        # Add OT hours to regular schedule
                        dt = datetime.strptime(s.date_start, OE_DTFORMAT)
                        dtE = datetime.strptime(s.date_end, OE_DTFORMAT)
                        date_start = s.date_start
                        date_end = s.date_end
                        otHours = 0.0
                        #for ot in weekly.ot_ids:
                        for ot in wot_obj.browse(cr, uid, wot_ids, context=context):
                            if ot.employee_id.id == s.schedule_id.employee_id.id:
                                if dt.weekday() == 0 and ot.mon > 0.01:
                                    otHours = ot.mon
                                elif dt.weekday() == 1 and ot.tue > 0.01:
                                    otHours = ot.tue
                                elif dt.weekday() == 2 and ot.wed > 0.01:
                                    otHours = ot.wed
                                elif dt.weekday() == 3 and ot.thu > 0.01:
                                    otHours = ot.thu
                                elif dt.weekday() == 4 and ot.fri > 0.01:
                                    otHours = ot.fri
                                elif dt.weekday() == 5 and ot.sat > 0.01:
                                    otHours = ot.sat
                                elif dt.weekday() == 6 and ot.sun > 0.01:
                                    otHours = ot.sun
                        if otHours > 0.01:
                            # Figure out if this is the last entry for the day, and if it
                            # is add the OT hours to it
                            detail_ids = sched_obj.search(cr, uid, [('schedule_id.employee_id', '=', eid),
                                                                    ('day', '=', s.day)],
                                                          order='date_start', context=context)
                            if len(detail_ids) > 0:
                                data = sched_obj.read(cr, uid, detail_ids[-1], ['date_start', 'date_end'],
                                                      context=context)
                                if data['date_start'] == s.date_start:
                                    dtE = datetime.strptime(data['date_end'], OE_DTFORMAT)
                                    dtE += timedelta(hours= otHours)
                                    date_end = dtE.strftime(OE_DTFORMAT)
                        
                        if not self.on_leave(cr, uid, eid, dt, context=context) and not self.on_leave(cr, uid, eid, dtE, context=context):
                            sin.append(date_start)
                            sout.append(date_end)
                            dates.append(dToday.strftime(OE_DFORMAT))
                
                if len(real_sched_ids) > 0:
                    # Add OT hours for any days not in the schedule
                    #
                    rest_days = [d for d in week_days if d not in worked_days]
                    for d in rest_days:
                        otHours = 0.0
                        #for ot in weekly.ot_ids:
                        for ot in wot_obj.browse(cr, uid, wot_ids, context=context):
                            if ot.employee_id.id == eid:
                                if d == 0 and ot.mon > 0.01:
                                    otHours = ot.mon
                                elif d == 1 and ot.tue > 0.01:
                                    otHours = ot.tue
                                elif d == 2 and ot.wed > 0.01:
                                    otHours = ot.wed
                                elif d == 3 and ot.thu > 0.01:
                                    otHours = ot.thu
                                elif d == 4 and ot.fri > 0.01:
                                    otHours = ot.fri
                                elif d == 5 and ot.sat > 0.01:
                                    otHours = ot.sat
                                elif d == 6 and ot.sun > 0.01:
                                    otHours = ot.sun
                        if otHours > 0.01:
                            employee = e_obj.browse(cr, uid, eid, context=context)
                            if employee.department_id and employee.department_id.name.find(self.l10n_get_coldstore_name()) != -1:
                                times = ['21:00:00', '01:00:00', '02:00:00', '06:00:00']
                            else:
                                times = self.l10n_get_shift_times()
                            dtWeek = datetime.strptime(weekly.week_start +' '+ times[0], OE_DTFORMAT)
                            dtAM = dtWeek + timedelta(days= d)
                            dToday = dtAM.date()
                            local_tz = timezone(employee.contract_id.pps_id.tz)
                            utcdtAM = (local_tz.localize(dtAM, is_dst=False)).astimezone(utc)
                            if otHours > 6.0:
                                utcdtAMend = utcdtAM + timedelta(hours= 5)
                                utcdtPM = utcdtAMend + timedelta(hours= +1)
                                utcdtPMend = utcdtPM + timedelta(hours= (otHours - 5))
                            else:
                                utcdtAMend = utcdtAM + timedelta(hours= otHours)
                                utcdtPM = False
                                utcdtPMend = False
                            if not self.on_leave(cr, uid, eid, utcdtAM, context=context) and not self.on_leave(cr, uid, eid, utcdtAMend, context=context):
                                sin.append(utcdtAM.strftime(OE_DTFORMAT))
                                sout.append(utcdtAMend.strftime(OE_DTFORMAT))
                                dates.append(dToday.strftime(OE_DFORMAT))
                            if utcdtPM and (not self.on_leave(cr, uid, eid, utcdtPM, context=context) and not self.on_leave(cr, uid, eid, utcdtPMend, context=context)):
                                sin.append(utcdtPM.strftime(OE_DTFORMAT))
                                sout.append(utcdtPMend.strftime(OE_DTFORMAT))
                                dates.append(dToday.strftime(OE_DFORMAT))
                    
                    vals['in_times'] = sin
                    vals['out_times'] = sout
                    vals['dates'] = dates
                else:
                    ee = self.pool.get('hr.employee').browse(cr, uid, vals['employee_id'], context=context)
                    raise osv.except_osv('Error', 'No schedule for employee %s' % (ee.name))
            
            res.append(vals)
        return res
    
    def on_leave(self, cr, uid, employee_id, utcdt, context=None):
        
        str_dt = utcdt.strftime(OE_DTFORMAT)
        leave_ids = self.pool.get('hr.holidays').search(cr, uid, [('employee_id', '=', employee_id),
                                                                  ('type', '=', 'remove'),
                                                                  ('date_from', '<=', str_dt),
                                                                  ('date_to', '>=', str_dt),
                                                                  ('state', 'in', ['validate', 'validate1'])],
                                                        context=context)
        return (len(leave_ids) > 0)
    
    def get_action_reason(self, cr, uid, reason, text, context=None):
        
        aid = self.pool.get('hr.action.reason').search(cr, uid, [
                                                                ('action_type', '=', reason),
                                                                ('name', 'ilike', text),
                                                               ],
                                                      context=context)
        if len(aid) == 0:
            return False
        return aid[0]

    def add_punches(self, cr, uid, weekly_id, weekly_lines, context=None):

        sinDesc = self.get_action_reason(cr, uid, 'sign_in', 'Batch Sign-in%', context=context)
        soutDesc = self.get_action_reason(cr, uid, 'sign_out', 'Batch Sign-out%', context=context)
        for line in weekly_lines:
            employee_id = line['employee_id']
            if len(line['in_times']) != len(line['out_times']):
                ee = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
                raise osv.except_osv('Error',
                                     'Punch times mismatch for %s', ee.name)

            for i in range(len(line['in_times'])):
                recIn = {
                       'name': line['in_times'][i],
                       'action': 'sign_in',
                       'action_desc': sinDesc,
                       'employee_id': employee_id,
                       'day': line['dates'][i],
                }
                recOut = {
                       'name': line['out_times'][i],
                       'action': 'sign_out',
                       'action_desc': soutDesc,
                       'employee_id': employee_id,
                       'day': line['dates'][i],
                }
                self.write(cr, uid, weekly_id, {'att_ids': [(0, 0, recIn)]}, context=context)
                self.write(cr, uid, weekly_id, {'att_ids': [(0, 0, recOut)]}, context=context)

        return
    
    def create_punches(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        for i in ids:
            if self.is_attendance_dirty(cr, uid, i, context=context):
                self.action_delete_hours(cr, uid, [i], context=context)
                week_vals = self.get_weekly_lines(cr, uid, i, context=context)
                self.add_punches(cr, uid, i, week_vals, context=context)
                self.write(cr, uid, i, {'init_time': datetime.now().strftime(OE_DTFORMAT)},
                           context=context)
    
        return True

class hr_weekly_absent(osv.Model):
    
    _name = 'hr.attendance.weekly.partial'
    _description = 'Weekly Attendance Employee absence records'
    
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'weekly_id': fields.many2one('hr.attendance.weekly', 'Weekly Attendance', required=True),
        'dayofweek': fields.selection([('0', 'Monday'),('1', 'Tuesday'),
                                       ('2', 'Wednesday'),('3', 'Thursday'),
                                       ('4', 'Friday'),('5', 'Saturday'),
                                       ('6', 'Sunday')],
                                      'Day of Week'),
        'date': fields.date('Date', required=True),
        's1hours': fields.float('First Shift', help="Hours worked in morning shift."),
        's2hours': fields.float('Second Shift', help="Hours worked in afternoon shift."),
    }
    
    def _get_weekly(self, cr, uid, context=None):
        
        if context == None:
            context = {}
        
        return context.get('weekly_id', False)
    
    _defaults = {
        'weekly_id': _get_weekly,
    }
    
    def onchange_dayofweek(self, cr, uid, ids, weekly_id, dayofweek, date_str, context=None):
        
        res = {'value': {'date': False}}
        if not dayofweek:
            return res
        
        weekly = self.pool.get('hr.attendance.weekly').browse(cr, uid, weekly_id, context=context)
        d = datetime.strptime(weekly.week_start, OE_DFORMAT)
        d = d + timedelta(days= +int(dayofweek))
        res['value']['date'] = d.strftime(OE_DFORMAT)
        
        return res

class hr_weekly_ot(osv.Model):
    
    _name = 'hr.attendance.weekly.ot'
    _description = 'Weekly Attendance OT Record'
    
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'weekly_id': fields.many2one('hr.attendance.weekly', 'Weekly Attendance', required=True),
        'mon': fields.float('Mon'),
        'tue': fields.float('Tue'),
        'wed': fields.float('Wed'),
        'thu': fields.float('Thu'),
        'fri': fields.float('Fri'),
        'sat': fields.float('Sat'),
        'sun': fields.float('Sun'),
    }
    
    def _get_weekly(self, cr, uid, context=None):
        
        if context == None:
            context = {}
        
        return context.get('weekly_id', False)
    
    _defaults = {
        'weekly_id': _get_weekly,
    }
    
    def get_action_reason(self, cr, uid, reason, text, context=None):
        
        aid = self.pool.get('hr.action.reason').search(cr, uid, [
                                                                ('action_type', '=', reason),
                                                                ('name', 'ilike', text),
                                                               ],
                                                      context=context)
        if len(aid) == 0:
            return False
        return aid[0]

class hr_attendance(osv.osv):
    
    _name = 'hr.attendance'
    _inherit = 'hr.attendance'
    
    _columns = {
        'weekly_att_id': fields.many2one('hr.attendance.weekly', 'Weekly Attendance'),
        'day': fields.char('Day', required=True, select=1, size=32),
    }

    def create(self, cr, uid, vals, context=None):

        if 'day' not in vals:
            vals.update({
                'day': time.strftime(
                            '%Y-%m-%d',
                            time.strptime(vals['name'], '%Y-%m-%d %H:%M:%S'))})
        return super(hr_attendance, self).create(cr, uid, vals, context=context)


class hr_employee(osv.Model):
    
    _name = 'hr.employee'
    _inherit = 'hr.employee'
    
    def _get_day_off(self, cr, uid, ids, field_name, arg, context=None):
        """Returns the index of the first rest day of the week. 0 is Monday"""
        
        sched_tpl_obj = self.pool.get('hr.schedule.template')
        
        res = dict.fromkeys(ids, '')
        for ee in self.browse(cr, uid, ids, context=context):
            if not ee.contract_id or not ee.contract_id.schedule_template_id:
                continue
            days = sched_tpl_obj.get_rest_days(cr, uid, ee.contract_id.schedule_template_id.id,
                                               context=context)
            if len(days) > 0:
                res[ee.id] = days[0]
        
        return res
    
    _columns = {
        'rest_day': fields.function(_get_day_off, type='integer', method=True, readonly=True,
                                   string="Day Off"),
    }
    
    def get_contracts_on_day(self, cr, uid, employee_id, dToday, context=None):

        ee = self.browse(cr, uid, employee_id, context=context)
        contracts = []
        for c in ee.contract_ids:
            dStart = datetime.strptime(c.date_start, OE_DFORMAT).date()
            dEnd = False
            if c.date_end:
                dEnd = datetime.strptime(c.date_end, OE_DFORMAT).date()
            if dToday >= dStart and (not dEnd or dToday <= dEnd):
                contracts.append(c)
        return contracts

    def get_restdays_by_week(self, cr, uid, employee_id, week_start, context=None):
        """Returns the indexes of the rest days of the week as a list. 0 is Monday"""
        
        sched_tpl_obj = self.pool.get('hr.schedule.template')
        sched_obj = self.pool.get('hr.schedule')
        
        res = []
        ee = self.browse(cr, uid, employee_id, context=context)
        
        # Is there a schedule? If so, use it
        sched_ids = sched_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                               ('date_start', '<=', week_start),
                                               ('date_end', '>=', week_start)],
                                     context=context)
        if len(sched_ids) > 0:
            sched = sched_obj.browse(cr, uid, sched_ids[0], context=context)
            dSchedStart = datetime.strptime(sched.date_start, OE_DFORMAT).date()
            dWeekStart = datetime.strptime(week_start, OE_DFORMAT).date()
            restdays = False
            if dWeekStart == dSchedStart:
                restdays = sched.restday_ids1
            elif dWeekStart == dSchedStart + relativedelta(weeks= +1):
                restdays = sched.restday_ids2
            elif dWeekStart == dSchedStart + relativedelta(weeks= +2):
                restdays = sched.restday_ids3
            elif dWeekStart == dSchedStart + relativedelta(weeks= +3):
                restdays = sched.restday_ids4
            elif dWeekStart == dSchedStart + relativedelta(weeks= +4):
                restdays = sched.restday_ids5
            if restdays:
                for day in restdays:
                    res.append(day.sequence)
        else:
            if ee.contract_id and ee.contract_id.schedule_template_id:
                days = sched_tpl_obj.get_rest_days(cr, uid, ee.contract_id.schedule_template_id.id,
                                                   context=context)
                if len(days) > 0:
                    res.append(days[0])
        
        return res
