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

from openerp.addons.hr_attendance_batch_entry import local_cr
from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools.float_utils import float_is_zero, float_compare
from openerp.tools.translate import _

import logging
_l = logging.getLogger(__name__)

class attendance_punch_wizard(orm.TransientModel):
    
    _name = 'hr.attendance.autocorrect'
    _description = 'Weekly Attendance Auto-correct'
    
    _columns = {
        'department_ids': fields.many2many('hr.department',
                                           'hr_attendance_autocorrect_department_rel',
                                           'wizard_id', 'department_id', 'Departments'),
        'date_start': fields.date('Start', required=True),
        'date_end': fields.date('End', required=True),
        
        # Correct new employees schedule/attendance
        'new_employee_ids': fields.many2many('hr.employee',
                                             'hr_attendance_autocorrect_newee_rel',
                                             'wizard_id', 'employee_id', 'New Employees',
                                             readonly=False),
        'new_sched_tpl_id': fields.many2one('hr.schedule.template', 'Schedule Template',
                                               required=True),
        
        # Correct rest day ot
        'rstot_employee_ids': fields.many2many('hr.employee',
                                               'hr_attendance_autocorrect_rstotee_rel',
                                               'wizard_id', 'employee_id', 'Rst OT Employees',
                                               readonly=True),
        
        # Correct wrong absent employees
        'awol_employee_ids': fields.many2many('hr.employee',
                                              'hr_attendance_autocorrect_awolee_rel',
                                              'wizard_id', 'employee_id', 'Absent Employees',
                                              readonly=True),
    }
    
    def onchange_week_start(self, cr, uid, ids, newdate, context=None):
        
        return {'value': {'week_start': self.check_week_date(newdate)}}
    
    def onchange_week_end(self, cr, uid, ids, newdate, context=None):
        
        return {'value': {'week_end': self.check_week_date(newdate)}}
    
    def check_week_date(self, newdate):
        '''Returns newdate if it falls on a Monday; False otherwise.'''
        
        res = False
        if newdate:
            d = datetime.strptime(newdate, "%Y-%m-%d")
            if d.weekday() == 0:
                res = newdate
        return res
    
    def get_employee_first_contract_date(self, cr, uid, employee_id, start, end, context=None):
    
        c_obj = self.pool.get('hr.contract')
        
        c_ids = c_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                       ('date_start', '<=', end)])
        first_contract_date = None
        for contract in c_obj.browse(cr, uid, c_ids, context=context):
            if first_contract_date == None and contract.date_start < end:
                first_contract_date = contract.date_start
            elif first_contract_date != None and contract.date_start < first_contract_date:
                first_contract_date = contract.date_start
        
        if first_contract_date == None:
            first_contract_date = end
        elif first_contract_date < start:
            first_contract_date = start
        
        return first_contract_date
    
    def get_new_hires(self, cr, uid, ids, context=None):
    
        c_obj = self.pool.get('hr.contract')
        
        wizard = self.browse(cr, uid, ids[0], context=context)
        c_ids = c_obj.search(cr, uid, [('date_start', '>=', wizard.date_start),
                                       ('date_start', '<=', wizard.date_end)])
        ee_ids = []
        if len(c_ids) > 0:
            c_datas = c_obj.read(cr, uid, c_ids, ['employee_id'])
            ee_ids += [c['employee_id'][0] for c in c_datas if c['employee_id'][0] not in ee_ids]
            
            ee_ids = list(set(ee_ids))
            # Check to see this isn't a transfer or wage incr. or something
            # or if it is in the departments list (if it's not empty)
            ee_obj = self.pool.get('hr.employee')
            wizard_dept_ids = [dept.id for dept in wizard.department_ids]
            import logging
            _ll = logging.getLogger(__name__)
            _ll.warning('ee_ids: %s', ee_ids)
            for ee in ee_obj.browse(cr, uid, ee_ids):
                for c in ee.contract_ids:
                    if c.date_start < wizard.date_start:
                        ee_ids.remove(ee.id)
                        break
            
                if len(wizard_dept_ids) > 0 and ee.department_id.id not in wizard_dept_ids:
                    if ee.id in ee_ids:
                        ee_ids.remove(ee.id)


        if len(ee_ids) > 0:
            self.write(cr, uid, ids[0], {'new_employee_ids': [(6, 0, ee_ids)]}, context=context)
        
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.attendance.autocorrect',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }
    
    def _remove_add_schedule(self, cr, uid, schedule_id, week_start, tpl_id, context=None):
        
        # Remove the current schedule and add a new one in its place according to
        # the new template. If the week that the change starts in is not at the
        # beginning of a schedule create two new schedules to accomodate the
        # truncated old one and the partial new one.
        #
        
        sched_obj = self.pool.get('hr.schedule')
        sched = sched_obj.browse(cr, uid, schedule_id, context=context)
        
        # Don't try and change it if it's not Sunday (usual default)
        if sched.restday_ids1 and sched.restday_ids1[0].sequence != 6:
            return

        vals2 = False
        vals1 = {
            'name': sched.name,
            'employee_id': sched.employee_id.id,
            'template_id': tpl_id,
            'date_start': sched.date_start,
            'date_end': sched.date_end,
        }
        
        # Break up sched if it's greater than one week
        if week_start > sched.date_start:
            # The week we want to change is not the first week
            dWeekStart = datetime.strptime(week_start, '%Y-%m-%d').date()
            start_day = dWeekStart.strftime('%Y-%m-%d')
            vals1['template_id'] = sched.template_id.id
            vals1['date_end'] = (dWeekStart + relativedelta(days= -1)).strftime(OE_DFORMAT)
            vals2 = {
                'name': sched.employee_id.name +': '+ start_day +' Wk '+ str(dWeekStart.isocalendar()[1]),
                'employee_id': sched.employee_id.id,
                'template_id': tpl_id,
                'date_start': start_day,
                'date_end': sched.date_end,
            }
        else:
            dNewWeekStart = (datetime.strptime(week_start, OE_DFORMAT).date() + relativedelta(days= +7))
            start_day = dNewWeekStart.strftime(OE_DFORMAT)
            if sched.date_end > dNewWeekStart.strftime(OE_DFORMAT):
                # The week we want to change *IS* the first week
                vals1['date_end'] = (dNewWeekStart + relativedelta(days= -1)).strftime(OE_DFORMAT)
                vals2 = {
                    'name': sched.employee_id.name +': '+ start_day +' Wk '+ str(dNewWeekStart.isocalendar()[1]),
                    'employee_id': sched.employee_id.id,
                    'template_id': sched.template_id.id,
                    'date_start': dNewWeekStart.strftime(OE_DFORMAT),
                    'date_end': sched.date_end,
                }
                
        
        sched_obj.unlink(cr, uid, schedule_id, context=context)
        _l.warning('vals1: %s', vals1)
        sched_obj.create(cr, uid, vals1, context=context)
        if vals2:
            _l.warning('vals2: %s', vals2)
            sched_obj.create(cr, uid, vals2, context=context)
    
    def _change_by_template(self, cr, uid, employee_ids, week_start, new_template_id, context=None):
        
        sched_obj = self.pool.get('hr.schedule')
        
        for employee_id in employee_ids:
            schedule_ids = sched_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                                     ('date_start', '<=', week_start),
                                                     ('date_end', '>=', week_start)],
                                           context=context)
            
            # Remove the current schedule and add a new one in its place according to
            # the new template
            #
            if len(schedule_ids) > 0:
                self._remove_add_schedule(cr, uid, schedule_ids[0], week_start, new_template_id,
                                          context=context)
        
        return
    
    def correct_new_hires(self, cr, uid, ids, context=None):
        
        wizard = self.browse(cr, uid, ids[0], context=context)
        sched_obj = self.pool.get('hr.schedule')
        for ee in wizard.new_employee_ids:
            
            _l.warning('Autocorrect New Employee: %s', ee.name)

            # Figure out the start of the week of the contract
            contract_date = self.get_employee_first_contract_date(cr, uid, ee.id,
                                                                  wizard.date_start,
                                                                  wizard.date_end,
                                                                  context=context)
            _l.warning('    contract: %s', contract_date)
            contract_week_start = self.get_week_start(contract_date)
            _l.warning('    contract_week: %s', contract_week_start)
            
            # Try to get schedule for start of week of the contract. If there is already
            # one delete it. Create a new schedule with the template selected by the user.
            #
            sched_ids = sched_obj.search(cr, uid, [('employee_id', '=', ee.id),
                                                   ('date_start', '<=', contract_date),
                                                   ('date_end', '>=', contract_date)])
            if len(sched_ids) > 0:
                _l.warning('    change schedule')
                self._change_by_template(cr, uid, [ee.id], contract_week_start,
                                         wizard.new_sched_tpl_id.id, context=context)
            else:
                _l.warning('    create new schedule')
                dCStartWeek = datetime.strptime(contract_week_start, OE_DFORMAT).date()
                dCEndWeek = dCStartWeek + timedelta(days= +6)
                sched_vals = {
                    'name': ee.name +': '+ dCStartWeek.strftime(OE_DFORMAT) +' Wk '+ str(dCStartWeek.isocalendar()[1]),
                    'employee_id': ee.id,
                    'template_id': wizard.new_sched_tpl_id.id,
                    'date_start': dCStartWeek.strftime(OE_DFORMAT),
                    'date_end': dCEndWeek.strftime(OE_DFORMAT),
                }
                sched_obj.create(cr, uid, sched_vals, context=context)
            
            # Re-create attendances
            self.create_adjustments(cr, uid, wizard, ee.id, only_weeks_list=[contract_week_start],
                                    do_sched=False, do_reset_rest=False, context=context)
        
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.attendance.autocorrect',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }
        
    def _employees_by_dept(self, cr, uid, wizard, dept_id, context=None):
        
        e_obj = self.pool.get('hr.employee')
        att_obj = self.pool.get('hr.attendance')
        
        # Get all employees associated with this department. This
        # includes current and past employees of the department.
        #
        domain = ['|', ('active', '=', True), ('active', '=', False)]
        e_ids = e_obj.search(cr, uid,
                             domain + [('contract_id', '!=', False),
                              '|', ('department_id', '=', dept_id),
                                   ('saved_department_id', '=', dept_id)],
                             context=context)
        
        # Remove employees who don't have any attendance in this period
        for eid in e_ids:
            att_ids = att_obj.search(cr, uid, [('employee_id', '=', eid),
                                               ('name', '>=', wizard.date_start),
                                               ('name', '<=', wizard.date_end)],
                                     context=context)
            if len(att_ids) == 0:
                e_ids.remove(eid)
        
        return e_ids
    
    def _get_employee_data(self, cr, uid, wizard, department_id, ee_ids):
        
        payslip_obj = self.pool.get('hr.payslip')
        ee_obj = self.pool.get('hr.employee')
        
        res = dict.fromkeys(ee_ids)
        dtStart = datetime.strptime(wizard.date_start, OE_DFORMAT).date()
        dtEnd = datetime.strptime(wizard.date_end, OE_DFORMAT).date()
        for ee in ee_obj.browse(cr, uid, ee_ids):
            datas = []
            for c in ee.contract_ids:
                dtCStart = False
                dtCEnd = False
                if c.date_start: dtCStart = datetime.strptime(c.date_start, OE_DFORMAT).date()
                if c.date_end: dtCEnd = datetime.strptime(c.date_end, OE_DFORMAT).date()
                if (dtCStart and dtCStart <= dtEnd) and ((dtCEnd and dtCEnd >= dtStart) or not dtCEnd):
                    datas.append({'contract_id': c.id,
                                  'date_start': dtCStart > dtStart and dtCStart.strftime(OE_DFORMAT) or dtStart.strftime(OE_DFORMAT),
                                  'date_end': (dtCEnd and dtCEnd < dtEnd) and dtCEnd.strftime(OE_DFORMAT) or dtEnd.strftime(OE_DFORMAT)})
            wd_lines = []
            for d in datas:
                wd_lines += payslip_obj.get_worked_day_lines(cr, uid, [d['contract_id']],
                                                             d['date_start'], d['date_end'])
                            
            res.update({ee.id: wd_lines})
        
        return res
    
    def _get_restday_ot(self, employee_id, data):
        
        total = 0
        for line in data[employee_id]:
            if line['code'] in ['WORKRST', 'WORKOTR']:
                total += line['number_of_hours']
        return total
    
    def get_restday_ot_employees(self, cr, uid, ids, context=None):
        
        ot_ee_ids = []
        wizard = self.browse(cr, uid, ids[0], context=context)
        for dept in wizard.department_ids:
            ee_ids = self._employees_by_dept(cr, uid, wizard, dept.id, context=context)
            wd_data = self._get_employee_data(cr, uid, wizard, dept.id, ee_ids)
            for eid in ee_ids:
                if not float_is_zero(float(self._get_restday_ot(eid, wd_data)), precision_digits=2):
                    ot_ee_ids.append(eid)
        
        if len(ot_ee_ids) > 0:
            self.write(cr, uid, ids[0], {'rstot_employee_ids': [(6, 0, ot_ee_ids)]}, context=context)
        else:
            self.write(cr, uid, ids[0], {'rstot_employee_ids': [(5)]}, context=context)
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.attendance.autocorrect',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }
    
    def correct_restday_ot(self, cr, uid, ids, context=None):
        
        wizard = self.browse(cr, uid, ids[0], context=context)
        for ee in wizard.rstot_employee_ids:
        
            # Re-create attendances
            self.create_adjustments(cr, uid, wizard, ee.id, only_weeks_list=None,
                                    do_sched=True, do_reset_rest=True, context=context)
        
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.attendance.autocorrect',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }
    
    def _get_awol(self, employee_id, data):
        
        total = 0
        for line in data[employee_id]:
            if line['code'] in ['AWOL']:
                total += line['number_of_hours']
        return total
    
    def _get_weekly_absent_by_employee(self, cr, uid, wizard, employee_id, context=None):
        
        partial_obj = self.pool.get('hr.attendance.weekly.partial')
        
        total = 0.0
        partial_ids = partial_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                                   ('date', '>=', wizard.date_start),
                                                   ('date', '<=', wizard.date_end)],
                                         context=context)
        for partial in partial_obj.browse(cr, uid, partial_ids, context=context):
            worked_hrs = partial.s1hours + partial.s2hours
            total += (8.0 - worked_hrs)
        
        return total
    
    def get_wrong_absent_employees(self, cr, uid, ids, context=None):
        
        awol_ee_ids = []
        wizard = self.browse(cr, uid, ids[0], context=context)
        for dept in wizard.department_ids:
            ee_ids = self._employees_by_dept(cr, uid, wizard, dept.id, context=context)
            wd_data = self._get_employee_data(cr, uid, wizard, dept.id, ee_ids)
            for eid in ee_ids:
                awol_hrs = self._get_awol(eid, wd_data)
                if not float_is_zero(float(awol_hrs), precision_digits=2):
                    wabsent_hrs = self._get_weekly_absent_by_employee(cr, uid, wizard, eid,
                                                                      context=context)
                    if float_compare(awol_hrs, wabsent_hrs, precision_digits=0) > 0:
                        _l.warning('float_compare: %s - %s = %s', awol_hrs, wabsent_hrs, awol_hrs - wabsent_hrs)
                        awol_ee_ids.append(eid)
        
        if len(awol_ee_ids) > 0:
            self.write(cr, uid, ids[0], {'awol_employee_ids': [(6, 0, awol_ee_ids)]}, context=context)
        else:
            self.write(cr, uid, ids[0], {'awol_employee_ids': [(5)]}, context=context)
        
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.attendance.autocorrect',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }
    
    def correct_wrong_absent(self, cr, uid, ids, context=None):
        
        wizard = self.browse(cr, uid, ids[0], context=context)
        for ee in wizard.awol_employee_ids:
        
            # Re-create attendances
            self.create_adjustments(cr, uid, wizard, ee.id, only_weeks_list=None,
                                    do_sched=True, do_reset_rest=True, context=context)
        
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.attendance.autocorrect',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }
    
    def get_week_start(self, d_str):
        
        d = datetime.strptime(d_str, OE_DFORMAT)
        while d.weekday() != 0:
            d += timedelta(days= -1)
        return d.strftime(OE_DFORMAT)
    
    def _get_departments_by_date(self, cr, uid, wizard, ee, context=None):
        
        # Figure out the start of the week of the contract
        contract_date = self.get_employee_first_contract_date(cr, uid, ee.id,
                                                              wizard.date_start,
                                                              wizard.date_end,
                                                              context=context)
        
        res =  [{
            'department_id': ee.department_id and ee.department_id.id or ee.saved_department_id.id,
            'week_start': self.get_week_start(contract_date),
            'week_end': self.get_week_start(wizard.date_end)
        }]
        return res
        
    def get_weekly_ids(self, cr, uid, wizard, employee_id, context=None):
        
        ee_obj = self.pool.get('hr.employee')
        weekly_obj = self.pool.get('hr.attendance.weekly')

        weekly_ids = []        
        ee = ee_obj.browse(cr, uid, employee_id, context=context)
        wdatas = self._get_departments_by_date(cr, uid, wizard, ee, context=context)
        for wd in wdatas:
            weekly_ids += weekly_obj.search(cr, uid, [('department_id', '=', wd['department_id']),
                                                     '&', ('week_start', '>=', wd['week_start']),
                                                          ('week_start', '<=', wd['week_end'])],
                                           context=context)
        
        return weekly_ids
    
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
    
    def get_all_dates(self, cr, uid, weeks, context=None):
        
        res = []
        for week in weeks:
            dStart = datetime.strptime(week.week_start, OE_DFORMAT).date()
            dEnd = dStart + relativedelta(weeks= +1, days= -1)
            while dStart <= dEnd:
                res.append(dStart)
                dStart = dStart + timedelta(days= +1)
        
        return res
    
    def generate_schedules(self, cr, uid, employee_id, date_start, context=None):
        
        sched_obj = self.pool.get('hr.schedule')
        
        dStart = datetime.strptime(date_start, OE_DFORMAT).date()
        dEnd = dStart + relativedelta(weeks= +1, days= -1)
        
        sched_ids = []
        employee = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
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
            
    def create_adjustments(self, cr, uid, wizard, employee_id, only_weeks_list=None,
                           do_sched=False, do_reset_rest=False, context=None):
        
        sched_obj = self.pool.get('hr.schedule')
        att_obj = self.pool.get('hr.attendance')
        watt_obj = self.pool.get('hr.attendance.weekly')
        
        if context is None:
            context = {}
        
        weekly_id_list = self.get_weekly_ids(cr, uid, wizard, employee_id, context)
        allweeks = watt_obj.browse(cr, uid, weekly_id_list, context=context)
        week_start_list = []
        for w in allweeks:
            if only_weeks_list != None and w.week_start not in only_weeks_list:
                continue
            elif w.week_start not in week_start_list:
                week_start_list.append(w.week_start)
        week_start_list = self.sort_days(week_start_list)
        weeklies = []
        for _w in allweeks:
            if _w.week_start in week_start_list:
                weeklies.append(_w)
        
        # Because of various interactions within the software, the
        # following steps have to be done in exactly the following order.
        #
        
        # 1. Regenerate schedule for the weeks of the selected weekly attendances
        if do_sched:
            sched_ids = []
            new_sched_ids = []
            for week_start in week_start_list:
                _sched_ids = sched_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                                        ('date_start', '<=', week_start),
                                                        ('date_end', '>=', week_start)],
                                              context=context)
                for _si in _sched_ids:
                    if _si not in sched_ids:
                        sched_ids.append(_si)
            updated_week_start_list = self.get_week_start_list(cr, uid, sched_ids,
                                                               context=context)
            updated_week_start_list = self.sort_days(updated_week_start_list)
            if len(sched_ids) > 0:
                sched_obj.unlink(cr, uid, sched_ids, context=context)
            for week_start in updated_week_start_list:
                new_sched_ids += self.generate_schedules(cr, uid, employee_id, week_start,
                                                        context=context)
        
        # 2. Reset the rest-days of the schedule according to weekly attendance
        if do_reset_rest:
            employee_ot_list = []
            for week in weeklies:
                employee_ot_list += [ot for ot in week.ot_ids if ot.employee_id.id == employee_id]
            for ot in employee_ot_list:
                self.change_schedule_restday(cr, uid, ot, context=context)
        
        # 3. Remove attendances for the days of the selected weekly attendances
        list_of_dates = self.get_all_dates(cr, uid, weeklies, context=context)
        list_of_days = [d.strftime(OE_DFORMAT) for d in list_of_dates]
        att_ids = att_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                           '|', ('day', 'in', list_of_days),
                                                ('weekly_att_id', 'in', weekly_id_list)])
        if len(att_ids) > 0:
            att_obj.unlink(cr, uid, att_ids, context=context)
        
        # 4. Generate attendances for the days of the selected weekly attendances
        test_att_ids = att_obj.search(cr, uid, [('employee_id', '=', employee_id), ('day', 'in', list_of_days)], context=context)
        assert len(test_att_ids) == 0, "Attendance exists where it shouldn't!"
        for week in weeklies:
            weekly_lines = watt_obj.get_weekly_lines(cr, uid, week.id,
                                                     select_employee_id=employee_id,
                                                     context=context)
            watt_obj.add_punches(cr, uid, week.id, weekly_lines, context=context)
            watt_obj.write(cr, uid, week.id,
                           {'init_time': datetime.now().strftime(OE_DTFORMAT)},
                           context=context)
        
        return
            
