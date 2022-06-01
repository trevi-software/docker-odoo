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

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OEDATE_FORMAT
from openerp.tools.translate import _

class hr_payslip(osv.Model):
    
    _name = 'hr.payslip'
    _inherit = 'hr.payslip'
    
    def get_worked_day_lines(self, cr, uid, contract_ids, date_from, date_to, context=None):
        
        res = super(hr_payslip, self).get_worked_day_lines(cr, uid, contract_ids, date_from, date_to,
                                                           context=context)
        if len(res) == 0:
            return res
        
        # Use the first contract ID available
        contract_id = res[0]['contract_id']
        employee_id = self.pool.get('hr.contract').read(cr, uid, contract_id, ['employee_id'],
                                                        context=context)['employee_id'][0]
        ee = self.pool.get('hr.employee').browse(cr, uid, employee_id, context=context)
        
        dFrom = datetime.strptime(date_from, OEDATE_FORMAT).date()
        dTo = datetime.strptime(date_to, OEDATE_FORMAT).date()
        
        # Gather the following data
        #    1. Number of infractions for not taking care of equipment or for
        #       disregarding rules & regulations
        #    2. Number of written warnings
        #    3. Number of times late for work
        #
        
        # 1. Number of infractions
        nfra = {
             'name': _("Infractions"),
             'sequence': 100,
             'code': 'NFRA',
             'number_of_days': 0.0,
             'number_of_hours': 0.0,
             'contract_id': contract_id,
        }
        for infraction in ee.infraction_ids:
            d = datetime.strptime(infraction.date, OEDATE_FORMAT).date()
            if d >= dFrom and d <= dTo and infraction.state not in ['draft']:
                nfra['number_of_days'] += 1
                nfra['number_of_hours'] += 1
        
        # 2. Number of written/verbal warnings
        warn = {
             'name': _("Written Warnings"),
             'sequence': 101,
             'code': 'WARNW',
             'number_of_days': 0.0,
             'number_of_hours': 0.0,
             'contract_id': contract_id,
        }
        warnv = {
             'name': _("Verbal Warnings"),
             'sequence': 101,
             'code': 'WARNV',
             'number_of_days': 0.0,
             'number_of_hours': 0.0,
             'contract_id': contract_id,
        }
        for action in ee.infraction_action_ids:
            if action.warning_id and action.warning_id.type == 'written' and action.infraction_id and action.infraction_id.state == 'action':
                d = datetime.strptime(action.warning_id.date, OEDATE_FORMAT).date()
                if d >= dFrom and d <= dTo:
                    warn['number_of_days'] += 1
                    warn['number_of_hours'] += 1
            elif action.warning_id and action.warning_id.type == 'verbal' and action.infraction_id and action.infraction_id.state == 'action':
                d = datetime.strptime(action.warning_id.date, OEDATE_FORMAT).date()
                if d >= dFrom and d <= dTo:
                    warnv['number_of_days'] += 1
                    warnv['number_of_hours'] += 1
        
        # 3. Number of times late for work
        tardy = {
             'name': _("Tardy"),
             'sequence': 102,
             'code': 'TARDY',
             'number_of_days': 0.0,
             'number_of_hours': 0.0,
             'contract_id': contract_id,
        }
        tardy_ids = self.pool.get('hr.schedule.alert').search(cr, uid,
                                                             [
                                                              ('employee_id', '=', employee_id),
                                                              ('rule_id.code', '=', 'TARDY'),
                                                              '&',
                                                                  ('name', '>=', date_from + ' 00:00:00'),
                                                                  ('name', '<=', date_to + ' 23:59:59'),
                                                             ])
        if tardy_ids > 0:
            tardy['number_of_days'] += len(tardy_ids)
            tardy['number_of_hours'] += tardy['number_of_days']
        
        # 4. Number of hours of unapproved over time
        #    First get the number of days/hours of OT worked, then subtract hours that have
        #    been approved.
        #
        unaotd_days = 0
        unaotd_hrs = 0
        unaotd_rate = 0
        unaotn_days = 0
        unaotn_hrs = 0
        unaotn_rate = 0
        unaotr_days = 0
        unaotr_hrs = 0
        unaotr_rate = 0
        unaoth_days = 0
        unaoth_hrs = 0
        unaoth_rate = 0
        for r in res:
            if r['code'] == 'WORKOTD' and r['contract_id'] == contract_id:
                unaotd_days += r['number_of_days']
                unaotd_hrs += r['number_of_hours']
                unaotd_rate = r['rate']
            elif r['code'] == 'WORKOTN' and r['contract_id'] == contract_id:
                unaotn_days += r['number_of_days']
                unaotn_hrs += r['number_of_hours']
                unaotn_rate = r['rate']
            elif r['code'] == 'WORKOTR' and r['contract_id'] == contract_id:
                unaotr_days += r['number_of_days']
                unaotr_hrs += r['number_of_hours']
                unaotr_rate = r['rate']
            elif r['code'] == 'WORKOTH' and r['contract_id'] == contract_id:
                unaoth_days += r['number_of_days']
                unaoth_hrs += r['number_of_hours']
                unaoth_rate = r['rate']
        
        unapproved_otd = {
            'name': _("Unapproved Daily OT"),
            'sequence': 103,
            'code': 'UNAOTD',
            'number_of_days': unaotd_days,
            'number_of_hours': unaotd_hrs,
            'rate': unaotd_rate,
            'contract_id': contract_id,
        }
        unapproved_otn = {
            'name': _("Unapproved Nightly OT"),
            'sequence': 104,
            'code': 'UNAOTN',
            'number_of_days': unaotn_days,
            'number_of_hours': unaotn_hrs,
            'rate': unaotn_rate,
            'contract_id': contract_id,
        }
        unapproved_otr = {
            'name': _("Unapproved Rest Day OT"),
            'sequence': 105,
            'code': 'UNAOTR',
            'number_of_days': unaotr_days,
            'number_of_hours': unaotr_hrs,
            'rate': unaotr_rate,
            'contract_id': contract_id,
        }
        unapproved_oth = {
            'name': _("Unapproved Holiday OT"),
            'sequence': 106,
            'code': 'UNAOTH',
            'number_of_days': unaoth_days,
            'number_of_hours': unaoth_hrs,
            'rate': unaoth_rate,
            'contract_id': contract_id,
        }
        
        # Initialize list of public holidays. We only need to calculate it once during
        # the lifetime of this object so attach it directly to it.
        # XXX - this is the same code in hr_payroll_extension/get_worked_day_lines()
        #
        try:
            public_holidays_list = self._mtm_public_holidays_list
        except AttributeError:
            self._mtm_public_holidays_list = self.holidays_list_init(cr, uid, dFrom, dTo,
                                                                     context=context)
            public_holidays_list = self._mtm_public_holidays_list
        
        sched_obj = self.pool.get('hr.schedule')
        schedot_obj = self.pool.get('hr.schedule.ot')
        week_from = (dFrom + timedelta(days= -6)).strftime(OEDATE_FORMAT)
        week_to = dTo.strftime(OEDATE_FORMAT)
        sched_ot_ids = schedot_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                                    ('week_start', '>=', week_from),
                                                    ('week_start', '<=', week_to)],
                                          context=context)
        for sched_ot in schedot_obj.browse(cr, uid, sched_ot_ids, context=context):
            if sched_ot.state not in ['approve']:
                continue
            
            dtWeekStart = datetime.strptime(sched_ot.week_start, OEDATE_FORMAT)
            rest_days = sched_obj.get_rest_days(cr, uid, employee_id, dtWeekStart, context=context)
            
            for i in range(0, 7):
                d = dtWeekStart.date() + timedelta(days= i)
                if d < dFrom:
                    continue
                
                hrs = 0
                if i == 0:
                    hrs = sched_ot.mon
                elif i == 1:
                    hrs = sched_ot.tue
                elif i == 2:
                    hrs = sched_ot.wed
                elif i == 3:
                    hrs = sched_ot.thu
                elif i == 4:
                    hrs = sched_ot.fri
                elif i == 5:
                    hrs = sched_ot.sat
                elif i == 6:
                    hrs = sched_ot.sun
                
                if self.holidays_list_contains(d, public_holidays_list) and hrs > 0.009:
                    unapproved_oth['number_of_days'] -= 1
                    unapproved_oth['number_of_hours'] -= hrs
                elif d.weekday() in rest_days and hrs > 0.009:
                    unapproved_otr['number_of_days'] -= 1
                    unapproved_otr['number_of_hours'] -= hrs
                elif hrs > 0.009:
                    unapproved_otd['number_of_days'] -= 1
                    unapproved_otd['number_of_hours'] -= hrs
        
        res += [nfra] + [warn] + [warnv] + [tardy] + [unapproved_otd]         \
               + [unapproved_otn] + [unapproved_otr] + [unapproved_oth]
        return res
