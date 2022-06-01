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

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from pytz import timezone, utc

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT

import logging
_l = logging.getLogger(__name__)

class processing_employees(orm.TransientModel):
    
    _name = 'hr.payroll.processing.weekly.employees'
    _description = 'HR Payroll Processing Wizard Modified Employees'
    
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', readonly=True),
        'weekly_id': fields.many2one('hr.attendance.weekly', 'Week', readonly=True),
        'processing_id': fields.many2one('hr.payroll.processing', readonly=True),
    }
    
    _rec_name = 'employee_id'

class processing_wizard(orm.TransientModel):
    
    _name = 'hr.payroll.processing'
    _description = 'HR Payroll Processing Wizard'
    
    def _get_states_selection(self, cr, uid, context=None):
        
        return [
                ('apprvcn', 'Contracts'),
                ('apprvlv', 'Leaves'),
                ('apprvwg', 'Wage Adjustments'),
                ('doweekly', 'Weekly Attendances'),
                ('perfbns', 'Performance Bonus'),
                ('apprvpsa', 'Amendments'),
                ('holidays', 'Holidays'),
               ]
    
    _columns = {
        'state': fields.selection(_get_states_selection, 'State', readonly=True),
        'payroll_period_id': fields.many2one('hr.payroll.period', 'Payroll Period', readonly=True),
        
        # Contracts in Draft State
        'contract_ids': fields.many2many('hr.contract', 'hr_payroll_processing_contracts_rel',
                                         'wizard_id', 'contract_id', 'Contracts to Approve',
                                         readonly=True),
        
        # Leaves in Draft State
        'leave_ids': fields.many2many('hr.holidays', 'hr_payroll_processing_leaves_rel',
                                      'wizard_id', 'leave_id', 'Leaves to Approve',
                                      readonly=True),
        
        # Wage Adjustments in progress
        'wageadj_ids': fields.many2many('hr.contract.wage.increment', 'hr_payroll_processing_wageadj_rel',
                                        'wizard_id', 'wageadj_id', 'Wages to Approve',
                                        readonly=True),
        
        # Weekly Attendance to hr.attendance conversion
        'weekly_ids': fields.many2many('hr.attendance.weekly', 'hr_payroll_processing_weekly_rel',
                                        'wizard_id', 'weekly_id', 'Weekly Attendances',
                                        readonly=True),
        'weekly_modified_ids': fields.one2many('hr.payroll.processing.weekly.employees',
                                               'processing_id', 'Modified Employees from Weekly Attendances',
                                               readonly=True),
        
        # Pay Slip Amendments
        'conf_psa_ids': fields.many2many('hr.payslip.amendment', 'hr_payroll_processing_psa1_rel',
                                         'wizard_id', 'amendment_id', 'Confirmed Amendments', readonly=True),
        'draft_psa_ids': fields.many2many('hr.payslip.amendment', 'hr_payroll_processing_psa2_rel',
                                          'wizard_id', 'amendment_id', 'Draft Amendments',
                                          readonly=False),
        
        # Public Holidays
        'public_holiday_ids': fields.many2many('hr.holidays.public.line', 'hr_payroll_processing_hol_rel',
                                               'wizard_id', 'holiday_id', 'Public Holidays', readonly=True),
        
        # Performance Bonus
        'nobonus_department_ids': fields.many2many('hr.department', 'hr_payroll_processing_bnsdpt_rel',
                                                   'wizard_id', 'department_id', 'No Performance Bonus Departments'),
        'bonus_sheet_ids': fields.many2many('hr.bonus.sheet', 'hr_payroll_processing_bns_rel',
                                            'wizard_id', 'bonus_sheet_id', 'Performance Bonus', readonly=True),
        'draft_bonus_sheet_ids': fields.many2many('hr.bonus.sheet', 'hr_payroll_processing_bns2_rel',
                                                  'wizard_id', 'bonus_sheet_id', 'Draft Performance Bonus'),
    }
    
    def _get_pp(self, cr, uid, context=None):
        
        res = False
        if context != None:
            res = context.get('active_id', False)
        
        return res
    
    def _get_contracts(self, cr, uid, context=None):
        
        res = []
        c_obj = self.pool.get('hr.contract')
        pp_id = self._get_pp(cr, uid, context=context)
        if pp_id:
            pp = self.pool.get('hr.payroll.period').browse(cr, uid, pp_id, context=context)
            res = c_obj.search(cr, uid, [('date_start', '<=', pp.date_end),
                                         ('state', '=', 'draft'),
                                          '|', ('date_end', '=', False),
                                               ('date_end', '>=', pp.date_start)],
                               context=context)
        return res
    
    _defaults = {
        'state': 'apprvcn',
        'payroll_period_id': _get_pp,
        'contract_ids': _get_contracts,
    }
    
    def _populate_leaves(self, cr, uid, ids, context=None):
        
        res = []
        lv_obj = self.pool.get('hr.holidays')
        pp_id = self._get_pp(cr, uid, context=context)
        if pp_id:
            pp = self.pool.get('hr.payroll.period').browse(cr, uid, pp_id, context=context)
            res = lv_obj.search(cr, uid, [('date_from', '<=', pp.date_end),
                                          ('date_to', '>=', pp.date_start),
                                          ('state', 'not in', ['cancel', 'refuse', 'validate'])],
                                context=context)
        if len(res) > 0:
            self.write(cr, uid, ids, {'leave_ids': [(6, 0, res)]}, context=context)
        
        return
    
    def _populate_wageadj(self, cr, uid, ids, context=None):
        
        res = []
        wi_obj = self.pool.get('hr.contract.wage.increment')
        pp_id = self._get_pp(cr, uid, context=context)
        if pp_id:
            pp = self.pool.get('hr.payroll.period').browse(cr, uid, pp_id, context=context)
            res = wi_obj.search(cr, uid, [('effective_date', '<=', pp.date_end),
                                          ('state', 'not in', ['approve', 'decline'])],
                                context=context)
        if len(res) > 0:
            self.write(cr, uid, ids, {'wageadj_ids': [(6, 0, res)]}, context=context)
        
        return
    
    def _populate_weekly(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]

        res = []
        w_obj = self.pool.get('hr.attendance.weekly')
        pp_id = self._get_pp(cr, uid, context=context)
        if pp_id:
            pp = self.pool.get('hr.payroll.period').browse(cr, uid, pp_id, context=context)
            company_id = pp.company_id and pp.company_id.id or False
            if not company_id:
                user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
                company_id = user.company_id.id
            department_ids = self.pool.get('hr.department').search(cr, uid,
                                                                   [('company_id', '=', company_id)],
                                                                   context=context)
            
            local_tz = timezone(pp.schedule_id.tz)
            utcdtStart = utc.localize(datetime.strptime(pp.date_start, OE_DTFORMAT), is_dst=False)
            dtStart = utcdtStart.astimezone(local_tz)
            utcdtEnd = utc.localize(datetime.strptime(pp.date_end, OE_DTFORMAT), is_dst=False)
            dtEnd = utcdtEnd.astimezone(local_tz)
            dStart = dtStart.date()
            dEnd = dtEnd.date()
            for dept_id in department_ids:
                
                dTemp = dStart
                while dTemp.weekday() != 0:
                    dTemp += timedelta(days= -1)
                while dTemp <= dEnd:
                    tmp_ids = w_obj.search(cr, uid, [('department_id', '=', dept_id),
                                                     ('week_start', '=', dTemp.strftime(OE_DFORMAT))],
                                          context=context)
                    if len(tmp_ids) == 0:
                        tmp_id = w_obj.create(cr, uid, {'department_id': dept_id,
                                                        'week_start': dTemp.strftime(OE_DFORMAT)},
                                              context=context)
                        # Do not create a record if the department does not have any employees
                        #
                        ee_ids = w_obj.get_employees(cr, uid,
                                                     w_obj.browse(cr, uid, tmp_id, context=context),
                                                     context=context)
                        if len(ee_ids) == 0:
                            w_obj.unlink(cr, uid, tmp_id, context=context)
                        else:
                            res.append(tmp_id)
                    else:
                        if w_obj.is_attendance_dirty(cr, uid, tmp_ids[0], context=context):
                            res.append(tmp_ids[0])
                    
                    dTemp += timedelta(days= +7)

        # Remove stale records
        mod_obj = self.pool.get('hr.payroll.processing.weekly.employees')
        old_mod_ids = mod_obj.search(cr, uid, [('processing_id', '=', ids[0])],
                                     context=context)
        mod_obj.unlink(cr, uid, old_mod_ids, context=context)
        self.write(cr, uid, ids, {'weekly_ids': [(6, 0, [])]}, context=context)

        if len(res) > 0:
            self.write(cr, uid, ids, {'weekly_ids': [(6, 0, res)]}, context=context)
            
            # Append modified weekly employee records
            for weekly in w_obj.browse(cr, uid, res, context=context):
                dirty_ee_ids = w_obj.get_attendance_dirty_employees(cr, uid, weekly.id,
                                                                    context=context)
                
                for ee_id in dirty_ee_ids:
                    mod_id = mod_obj.create(cr, uid,
                                            {
                                             'employee_id': ee_id,
                                             'weekly_id': weekly.id,
                                             'processing_id': ids[0]},
                                            context=context)
        
        return
    
    def _populate_psa(self, cr, uid, ids, context=None):
        
        pp_id = self._get_pp(cr, uid, context=context)
        if pp_id:
            draft_psa_ids = self._get_draft_amendments(cr, uid, context=context)
            confirmed_psa_ids = self._get_confirmed_amendments(cr, uid, context=context)
            self.write(cr, uid, ids, {'draft_psa_ids': [(4)]}, context=context)
            self.write(cr, uid, ids, {'conf_psa_ids': [(4)]}, context=context)
            if len(draft_psa_ids) > 0:
                self.write(cr, uid, ids, {'draft_psa_ids': [(6, 0, draft_psa_ids)]}, context=context)
            if len(confirmed_psa_ids) > 0:
                self.write(cr, uid, ids, {'conf_psa_ids': [(6, 0, confirmed_psa_ids)]}, context=context)
        
        return
    
    def _get_confirmed_amendments(self, cr, uid, context=None):
        
        psa_ids = []
        pp_id = self._get_pp(cr, uid, context=context)
        if pp_id:
            psa_ids = self.pool.get('hr.payslip.amendment').search(cr, uid, [('pay_period_id', '=', pp_id),
                                                                             ('state', 'in', ['validate']),
                                                                            ],
                                                                   context=context)
        return psa_ids
    
    def _get_draft_amendments(self, cr, uid, context=None):
        
        psa_ids = []
        pp_id = self._get_pp(cr, uid, context=context)
        if pp_id:
            psa_ids = self.pool.get('hr.payslip.amendment').search(cr, uid, [('pay_period_id', '=', pp_id),
                                                                             ('state', 'in', ['draft']),
                                                                            ],
                                                                   context=context)
        return psa_ids
    
    def _populate_perfbonus(self, cr, uid, ids, context=None):
        
        pp_id = self._get_pp(cr, uid, context=context)
        self.write(cr, uid, ids, {'nobonus_department_ids': [(5)]}, context=context)
        self.write(cr, uid, ids, {'draft_bonus_sheet_ids': [(5)]}, context=context)
        self.write(cr, uid, ids, {'bonus_sheet_ids': [(5)]}, context=context)
        if pp_id:
            pp = self.pool.get('hr.payroll.period').browse(cr, uid, pp_id, context=context)
            company_id = pp.company_id and pp.company_id.id or False
            if not company_id:
                user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
                company_id = user.company_id.id
            department_ids = self.pool.get('hr.department').search(cr, uid,
                                                                   [('company_id', '=', company_id)],
                                                                   context=context)
            
            draft_ids = self.pool.get('hr.bonus.sheet').search(cr, uid,
                                                               [('date_start', '>=', pp.date_start),
                                                                ('date_start', '<=', pp.date_end),
                                                                ('state', '=', 'draft')],
                                                               context=context)
            confirmed_ids = self.pool.get('hr.bonus.sheet').search(cr, uid,
                                                               [('date_start', '>=', pp.date_start),
                                                                ('date_start', '<=', pp.date_end),
                                                                ('state', '=', 'approve')],
                                                               context=context)
            if len(draft_ids) > 0:
                self.write(cr, uid, ids, {'draft_bonus_sheet_ids': [(6, 0, draft_ids)]}, context=context)
            if len(confirmed_ids) > 0:
                self.write(cr, uid, ids, {'bonus_sheet_ids': [(6, 0, confirmed_ids)]}, context=context)
            for sheet in self.pool.get('hr.bonus.sheet').browse(cr, uid, draft_ids + confirmed_ids, context=context):
                if sheet.department_id.id in department_ids:
                    department_ids.remove(sheet.department_id.id)
            if len(department_ids) > 0:
                self.write(cr, uid, ids, {'nobonus_department_ids': [(6, 0, department_ids)]}, context=context)
        
        return
    
    def _populate_holidays(self, cr, uid, ids, context=None):
        
        holiday_ids = []
        pp_id = self._get_pp(cr, uid, context=context)
        if pp_id:
            pp = self.pool.get('hr.payroll.period').browse(cr, uid, pp_id, context=context)
            
            # XXX - Someone interested in DST should fix this.
            #
            local_tz = timezone(pp.schedule_id.tz)
            utcdtStart = utc.localize(datetime.strptime(pp.date_start, OE_DTFORMAT), is_dst=False)
            dtStart = utcdtStart.astimezone(local_tz)
            utcdtEnd = utc.localize(datetime.strptime(pp.date_end, OE_DTFORMAT), is_dst=False)
            dtEnd = utcdtEnd.astimezone(local_tz)
            start = dtStart.strftime(OE_DFORMAT)
            end = dtEnd.strftime(OE_DFORMAT)
            holiday_ids = self.pool.get('hr.holidays.public.line').search(cr, uid,
                                                                          ['&', ('date', '>=', start),
                                                                                ('date', '<=', end)],
                                                                          context=context)
        
            self.write(cr, uid, ids, {'public_holiday_ids': [(6, 0, holiday_ids)]}, context=context)
        else:
            self.write(cr, uid, ids, {'public_holiday_ids': [(5)]}, context=context)
        
        return
    
    def do_weekly_attendance(self, cr, uid, ids, context=None):
        
        wizard = self.browse(cr, uid, ids[0], context=context)
        for wm in wizard.weekly_modified_ids:
            self.create_adjustments(cr, uid, wm.weekly_id.id, wm.employee_id.id,
                                    only_weeks_list=None, do_sched=True, do_reset_rest=True, context=context)
        
        weekly_ids = [w.id for w in wizard.weekly_ids]
        self.pool.get('hr.attendance.weekly').write(cr, uid, weekly_ids,
                                                    {'init_time': datetime.now().strftime(OE_DTFORMAT)},
                                                    context=context)
        
        self.state_doweekly(cr, uid, ids, context=context)
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.payroll.processing',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context,
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
            
    def create_adjustments(self, cr, uid, weekly_id, employee_id, only_weeks_list=None,
                           do_sched=False, do_reset_rest=False, context=None):
        
        sched_obj = self.pool.get('hr.schedule')
        att_obj = self.pool.get('hr.attendance')
        watt_obj = self.pool.get('hr.attendance.weekly')
        
        if context is None:
            context = {}
        
        weekly_id_list = [weekly_id]
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
                                                     check_attendance=False,
                                                     context=context)
            watt_obj.add_punches(cr, uid, week.id, weekly_lines, context=context)
        
        return
    
    def state_back(self, cr, uid, ids, context=None):
        
        wizard = self.browse(cr, uid, ids[0], context=context)
        if wizard.state == 'holidays':
            self.state_psa(cr, uid, ids, context=context)
        elif wizard.state == 'apprvpsa':
            self.state_perfbonus(cr, uid, ids, context=context)
        elif wizard.state == 'perfbns':
            self.state_doweekly(cr, uid, ids, context=context)
        elif wizard.state == 'doweekly':
            self.state_wageadj(cr, uid, ids, context=context)
        elif wizard.state == 'apprvwg':
            self.state_leaves(cr, uid, ids, context=context)
        elif wizard.state == 'apprvlv':
            self.state_contracts(cr, uid, ids, context=context)
        
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.payroll.processing',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }
    
    def state_next(self, cr, uid, ids, context=None):
        
        wizard = self.browse(cr, uid, ids[0], context=context)
        if wizard.state == 'apprvcn':
            self.state_leaves(cr, uid, ids, context=context)
        elif wizard.state == 'apprvlv':
            self.state_wageadj(cr, uid, ids, context=context)
        elif wizard.state == 'apprvwg':
            self.state_doweekly(cr, uid, ids, context=context)
        elif wizard.state == 'doweekly':
            self.state_perfbonus(cr, uid, ids, context=context)
        elif wizard.state == 'perfbns':
            self.state_psa(cr, uid, ids, context=context)
        elif wizard.state == 'apprvpsa':
            self.state_holidays(cr, uid, ids, context=context)
        
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.payroll.processing',
            'res_id': ids[0],
            'type': 'ir.actions.act_window',
            'target': 'new',
            'nodestroy': True,
            'context': context,
        }
    
    def generate_payslips(self, cr, uid, ids, context=None):
        
        assert(len(ids) > 0, 'No wizard ids')
        ppend_obj = self.pool.get('hr.payroll.period.end.1')
        ppend_obj.create_payroll_register(cr, uid, ids, context=context)
        wizard = self.browse(cr, uid, ids[0], context=context)
        assert(wizard.payroll_period_id, 'No payroll period in wizard')

        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.payroll.period',
            'res_id': wizard.payroll_period_id.id,
            'type': 'ir.actions.act_window',
            'target': 'current',
            'nodestroy': True,
            'context': context,
        }
    
    def state_contracts(self, cr, uid, ids, context=None):
        
        self.write(cr, uid, ids, {'state': 'apprvcn'}, context=context)
    
    def state_leaves(self, cr, uid, ids, context=None):
        
        self._populate_leaves(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'state': 'apprvlv'}, context=context)
    
    def state_wageadj(self, cr, uid, ids, context=None):
        
        self._populate_wageadj(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'state': 'apprvwg'}, context=context)
    
    def state_doweekly(self, cr, uid, ids, context=None):
        
        self._populate_weekly(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'state': 'doweekly'}, context=context)
    
    def state_perfbonus(self, cr, uid, ids, context=None):
        
        self._populate_perfbonus(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'state': 'perfbns'}, context=context)
    
    def state_psa(self, cr, uid, ids, context=None):
        
        self._populate_psa(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'state': 'apprvpsa'}, context=context)
    
    def state_holidays(self, cr, uid, ids, context=None):
        
        self._populate_holidays(cr, uid, ids, context=context)
        self.write(cr, uid, ids, {'state': 'holidays'}, context=context)
