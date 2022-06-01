#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyrigth (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
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
from datetime import datetime

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DATEFORMAT
from report import report_sxw

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)

        self.localcontext.update({
            'time': time,
            'get_payslip_runs': self.get_payslip_runs,
            'get_details_by_payslip': self.get_details_by_payslip,
            'add_count': self.add_count,
            'get_count': self.get_count,
            'get_dept_count': self.get_count_by_dept,
            'reset_dept_count': self.reset_dept_count,
        })

        self._count = 0
        self._dept_count = 0

    def add_count(self):

        self._count += 1
        self._dept_count += 1
        return

    def get_count(self):

        return self._count

    def get_count_by_dept(self):

        return self._dept_count

    def reset_dept_count(self):
        self._dept_count = 0
        return

    def get_annual_leave_days(self, employee):

        lv_status_obj = self.pool.get('hr.holidays.status')

        remaining = 0
        hol_status_ids = lv_status_obj.search(self.cr, self.uid, [('code', '=', 'LVANNUAL')])
        res = lv_status_obj.get_days(self.cr, self.uid, hol_status_ids, employee.id, False)
        for k,v in res.items():
            remaining = v['remaining_leaves']
            break

        return remaining

    def get_payslip_accruals(self, contract_ids, dToday):

        accrual_policy_obj = self.pool.get('hr.policy.accrual')
        contract_obj = self.pool.get('hr.contract')
        res = []

        for c in contract_obj.browse(self.cr, self.uid, contract_ids):
            policy = accrual_policy_obj.get_latest_policy(self.cr, self.uid, c.policy_group_id,
                                                          dToday)
            if policy == None:
                continue

            for accrual_policy_line in policy.line_ids:
                if accrual_policy_line.balance_on_payslip and accrual_policy_line.accrual_id.id not in res:
                    res.append((accrual_policy_line.accrual_id.id, accrual_policy_line.accrual_id.holiday_status_id.code))

        return res

    def get_payslip_runs(self, runs):

        payslip_runs = []
        for r in runs:

            pa_obj = self.pool.get('hr.payroll.postclose.amendment')
            tmp_ids = pa_obj.search(
                self.cr, self.uid,
                [('new_payslip_id', '!=', False),
                 ('new_payslip_id.original_payslip_run_id', '=', r.id)]
            )
            if len(tmp_ids) > 0:
                payslip_runs.append(r)

            # XXX - need this for backwards compatibility with implementations
            #       that generated amendments before original_payslip_run_id
            #       was introduced.
            #
            else:
                for slip in r.slip_ids:
                    if slip.amended_payslip_id:
                        payslip_runs.append(r)
                        break

        return payslip_runs

    def _get_rec(self, slip):

        tmp, contract_ids = self.get_details_by_rule_category(slip.details_by_salary_rule_category)

        if slip:
            tmp['name'] = slip.employee_id.name
            tmp['id_no'] = slip.employee_id.legacy_no
            tmp['dept'] = slip.employee_id.department_id.complete_name
            tmp['date_from'] = slip.date_from
            tmp['date_to'] = slip.date_to
            tmp['remaining_AL'] = self.get_annual_leave_days(slip.employee_id)
            tmp['remaining_AL'] = (tmp['remaining_AL'] > 0.009) and "%.2f" % float(tmp['remaining_AL']) or '0'
        else:
            tmp['name'] = ''
            tmp['id_no'] = ''
            tmp['dept'] = ''
            tmp['date_from'] = ''
            tmp['date_to'] = ''
            tmp['remaining_AL'] = '0'

        worked_days_details = self.get_worked_days_details(slip)
        tmp.update(worked_days_details)

        return tmp

    def get_details_by_payslip(self, run):

        pa_obj = self.pool.get('hr.payroll.postclose.amendment')
        accrual_obj = self.pool.get('hr.accrual')

        res = []
        tmp_ids = pa_obj.search(
            self.cr, self.uid,
            [('new_payslip_id', '!=', False),
             ('new_payslip_id.original_payslip_run_id', '=', run.id)]
        )
        for pa in pa_obj.browse(self.cr, self.uid, tmp_ids):
            tmp = self._get_rec(pa.old_payslip_id)
            tmp2 = self._get_rec(pa.new_payslip_id)
            res.append(tmp)
            res.append(tmp2)

        if len(tmp_ids) > 0:
            return res

        # XXX - need this for backwards compatibility with implementations
        #       that generated amendments before original_payslip_run_id
        #       was introduced.
        #
        for slip in run.slip_ids:
            if slip.amended_payslip_id:
                tmp = self._get_rec(slip)
                tmp2 = self._get_rec(slip.amended_payslip_id)
                res.append(tmp)
                res.append(tmp2)

        return res

    def get_worked_days_details(self, slip):

        res = {
            'LEAVES': 0,
            'WORK100': 0,
            'AWOL': 0,
            'MAX': 0,
        }
        if not slip:
            return res

        max_count = 0
        for line in slip.worked_days_line_ids:
            if line.code not in ['MAX', 'AWOL', 'WORK100', 'WORKHOL', 'LVANNUAL', 'LVBEREAVEMENT', 'LVCIVIC',
                                 'LVMATERNITY', 'LVMMEDICAL', 'LVSICK', 'LVSICK50',
                                 'LVSICK00', 'LVWEDDING', 'LVPTU', 'LVUTO', 'LVTRAIN']:
                continue
            elif line.code in ['LVANNUAL', 'LVBEREAVEMENT', 'LVCIVIC',
                               'LVMATERNITY', 'LVMMEDICAL', 'LVSICK', 'LVSICK50',
                               'LVSICK00', 'LVWEDDING', 'LVPTU', 'LVUTO', 'LVTRAIN']:
                res['LEAVES'] += line.number_of_hours
            elif line.code in  ['WORK100', 'WORKHOL']:
                res['WORK100'] += line.number_of_hours
            elif line.code == 'AWOL':
                res['AWOL'] += line.number_of_hours
            elif line.code == 'MAX':
                res['MAX'] += line.number_of_hours
                max_count += 1

        # XXX - In order to quiet down hysterical alarm over worked days
        #       not being exactly 26 days, replace worked days calculation with
        #       simple algorithm (even though not totally accurate). One
        #       special exception is made for new hires / terminations. We
        #       roughly try to distinguish those by MAX number of days and
        #       whether there are multiple contracts.
        dept_name = ''
        if slip.employee_id.department_id:
            dept_name = slip.employee_id.department_id.name
        elif slip.employee_id.saved_department_id:
            dept_name = slip.employee_id.saved_department_id.name
        if max_count > 1 or res['MAX'] > (22.0*8.0) or 'Pushcart' in dept_name:
            res['WORK100'] = (26*8) - res['LEAVES'] - res['AWOL']

        res['AWOL'] = (res['AWOL'] > 0.009) and "%.2f" % (float(res['AWOL']) / 8.0) or '-'
        res['LEAVES'] = (res['LEAVES'] > 0.009) and "%.2f" % (float(res['LEAVES']) / 8.0) or '-'
        res['WORK100'] = (res['WORK100'] > 0.009) and "%.2f" % (float(res['WORK100']) / 8.0) or '-'
        return res

    # Most of this function (except at the end) is copied verbatim from
    # the Pay Slip Details Report
    #
    def get_details_by_rule_category(self, obj):
        payslip_line = self.pool.get('hr.payslip.line')
        rule_cate_obj = self.pool.get('hr.salary.rule.category')

        def get_recursive_parent(rule_categories):
            if not rule_categories:
                return []
            if rule_categories[0].parent_id:
                rule_categories.insert(0, rule_categories[0].parent_id)
                get_recursive_parent(rule_categories)
            return rule_categories

        res = []
        result = {}
        ids = []
        contract_ids = []

        # Choose only the categories (or rules) that we want to
        # show in the report.
        #
        regline = {
            'salary': 0,
            'workwage': 0,
            'otday': 0,
            'otnight': 0,
            'otrest': 0,
            'otholiday': 0,
            'otday_qty': 0,
            'otnight_qty': 0,
            'otrest_qty': 0,
            'otholiday_qty': 0,
            'transportation': 0,
            'perf': 0,
            'hous': 0,
            'hard': 0,
            'pos': 0,
            'pres': 0,
            'allowances': 0,
            'taxable_gross': 0,
            'gross': 0,
            'fit': 0,
            'ee_pension': 0,
            'ee_provfee': 0,
            'lu': 0,
            'penalty': 0,
            'garnish': 0,
            'deductions': 0,
            'deductions_total': 0,
            'net': 0,
            'er_penfer': 0,
            'er_provfer': 0,
        }
        if not obj:
            return (regline, [])

        # Arrange the Pay Slip Lines by category
        #
        for id in range(len(obj)):
            ids.append(obj[id].id)
        if ids:
            self.cr.execute('''SELECT pl.id, pl.category_id FROM hr_payslip_line as pl \
                LEFT JOIN hr_salary_rule_category AS rc on (pl.category_id = rc.id) \
                WHERE pl.id in %s \
                GROUP BY rc.parent_id, pl.sequence, pl.id, pl.category_id \
                ORDER BY pl.sequence, rc.parent_id''',(tuple(ids),))
            for x in self.cr.fetchall():
                result.setdefault(x[1], [])
                result[x[1]].append(x[0])
            for key, value in result.iteritems():
                rule_categories = rule_cate_obj.browse(self.cr, self.uid, [key])
                parents = get_recursive_parent(rule_categories)
                category_total = 0
                category_qty_total = 0
                for line in payslip_line.browse(self.cr, self.uid, value):
                    category_total += line.total
                    category_qty_total += line.quantity
                level = 0
                for parent in parents:
                    res.append({
                        'rule_category': parent.name,
                        'name': parent.name,
                        'code': parent.code,
                        'level': level,
                        'total': category_total,
                        'quantity' : category_qty_total,
                    })
                    level += 1
                for line in payslip_line.browse(self.cr, self.uid, value):
                    res.append({
                        'rule_category': line.name,
                        'name': line.name,
                        'code': line.code,
                        'total': line.total,
                        'quantity': line.quantity,
                        'level': level
                    })

                    if line.contract_id.id not in contract_ids:
                        contract_ids.append(line.contract_id.id)

            for r in res:
                # Level 0 is the category
                if r['code'] in ['BASIC', 'CALCBASIC'] and r['level'] != 0:
                    regline['salary'] += r['total']
                elif r['code'] == 'BASIC' and r['level'] == 0:
                    regline['workwage'] += r['total']
                elif r['code'] in ['OTD', 'SPOT', 'OTH', 'OTR']:
                    regline['otday'] += r['total']
                    regline['otday_qty'] += r['quantity']
                elif r['code'] == 'OTN':
                    regline['otnight'] += r['total']
                    regline['otnight_qty'] += r['quantity']
                elif r['code'] == 'WORKRST':
                    regline['otrest'] += r['total']
                    regline['otrest_qty'] += r['quantity']
                elif r['code'] == 'WORKHOL':
                    regline['otholiday'] += r['total']
                    regline['otholiday_qty'] += r['quantity']
                elif r['code'] == 'TRA' or r['code'] == 'TRVA' or r['code'] == 'TRANS03':
                    regline['transportation'] += r['total']
                elif r['code'] == 'BNS1' or r['code'] == 'BNS1GRADING' or r['code'] == 'GUARD100' or r['code'] == 'BONUS':
                    regline['perf'] += r['total']
                elif r['code'] == 'HOUS':
                    regline['hous'] += r['total']
                elif r['code'] in ['PRES60', 'PRES70', 'PAADJ']:
                    regline['pres'] += r['total']
                elif r['code'] == 'HARD30' or r['code'] == 'HARD50' or r['code'] == 'hardship200':
                    regline['hard'] += r['total']
                elif r['code'] == 'POS':
                    regline['pos'] += r['total']
                elif r['code'] == 'ALW':
                    regline['allowances'] += r['total']
                elif r['code'] == 'TXBL':
                    regline['taxable_gross'] += r['total']
                elif r['code'] == 'GROSS' and r['level'] == 0:
                    regline['gross'] += r['total']
                elif r['code'] == 'FITCALC':
                    regline['fit'] += r['total']
                elif r['code'] == 'PENFEE':
                    regline['ee_pension'] += r['total']
                elif r['code'] == 'PROVFEE':
                    regline['ee_provfee'] += r['total']
                elif r['code'] == 'LU' or r['code'] == 'LBRU':
                    regline['lu'] += r['total']
                elif r['code'] == 'LOAN' or r['code'] == 'LOAN2':
                    regline['penalty'] += r['total']
                elif r['code'] in ['GARN', 'GARN2']:
                    regline['garnish'] += r['total']
                elif r['code'] == 'DED':
                    regline['deductions'] += r['total']
                elif r['code'] == 'DEDTOTAL' and r['level'] == 0:
                    regline['deductions_total'] = r['total']
                elif r['code'] == 'NET' and r['level'] == 0:
                    regline['net'] += r['total']
                elif r['code'] == 'PENFER':
                    regline['er_penfer'] += r['total']
                elif r['code'] == 'PROVFER':
                    regline['er_provfer'] += r['total']

            # Make adjustments to subtract from the parent category's total the
            # amount of individual rules that we show separately on the sheet.
            #
            regline['allowances'] -= regline['transportation']
            regline['allowances'] -= regline['perf']
            regline['allowances'] -= regline['hous']
            regline['allowances'] -= regline['hard']
            regline['allowances'] -= regline['pos']
            regline['allowances'] -= regline['pres']
            regline['deductions'] -= regline['ee_pension']
            regline['deductions'] -= regline['ee_provfee']
            regline['deductions'] -= regline['lu']
            regline['deductions'] -= regline['penalty']
            regline['deductions'] -= regline['garnish']

        # Format correctly
        #
        regline['salary'] = "%.2f" % regline['salary']
        regline['workwage'] = "%.2f" % regline['workwage']
        regline['otday'] = (regline['otday'] > 0.009) and "%.2f" % regline['otday'] or '-'
        regline['otday_qty'] = (regline['otday_qty'] > 0.009) and "%.2f" % regline['otday_qty'] or '-'
        regline['otnight'] = (regline['otnight'] > 0.009) and "%.2f" % regline['otnight'] or '-'
        regline['otnight_qty'] = (regline['otnight_qty'] > 0.009) and "%.2f" % regline['otnight_qty'] or '-'
        regline['otrest'] = (regline['otrest'] > 0.009) and "%.2f" % regline['otrest'] or '-'
        regline['otrest_qty'] = (regline['otrest_qty'] > 0.009) and "%.2f" % regline['otrest_qty'] or '-'
        regline['otholiday'] = (regline['otholiday'] > 0.009) and "%.2f" % regline['otholiday'] or '-'
        regline['otholiday_qty'] = (regline['otholiday_qty'] > 0.009) and "%.2f" % regline['otholiday_qty'] or '-'
        regline['transportation'] = (regline['transportation'] > 0.009) and "%.2f" % regline['transportation'] or '-'
        regline['perf'] = (regline['perf'] > 0.009) and "%.2f" % regline['perf'] or '-'
        regline['hous'] = (regline['hous'] > 0.009) and "%.2f" % regline['hous'] or '-'
        regline['hard'] = (regline['hard'] > 0.009) and "%.2f" % regline['hard'] or '-'
        regline['pos'] = (regline['pos'] > 0.009) and "%.2f" % regline['pos'] or '-'
        regline['pres'] = (regline['pres'] > 0.009) and "%.2f" % regline['pres'] or '-'
        regline['allowances'] = (regline['allowances'] > 0.009) and "%.2f" % regline['allowances'] or '-'
        regline['taxable_gross'] = (regline['taxable_gross'] > 0.009) and "%.2f" % regline['taxable_gross'] or '-'
        regline['gross'] = (regline['gross'] > 0.009) and "%.2f" % regline['gross'] or '-'
        regline['fit'] = (regline['fit'] > 0.009) and "%.2f" % regline['fit'] or '-'
        regline['ee_pension'] = (regline['ee_pension'] > 0.009) and "%.2f" % regline['ee_pension'] or '-'
        regline['ee_provfee'] = (regline['ee_provfee'] > 0.009) and "%.2f" % regline['ee_provfee'] or '-'
        regline['lu'] = (regline['lu'] > 0.009) and "%.2f" % regline['lu'] or '-'
        regline['garnish'] = (regline['garnish'] > 0.009) and "%.2f" % regline['garnish'] or '-'
        regline['penalty'] = (regline['penalty'] > 0.009) and "%.2f" % regline['penalty'] or '-'
        regline['deductions'] = (regline['deductions'] > 0.009) and "%.2f" % regline['deductions'] or '-'
        regline['deductions_total'] = (regline['deductions_total'] > 0.009) and "%.2f" % regline['deductions_total'] or '-'
        regline['net'] = (regline['net'] > 0.009) and "%.2f" % regline['net'] or '-'
        regline['er_penfer'] = (regline['er_penfer'] > 0.009) and "%.2f" % regline['er_penfer'] or '-'
        regline['er_provfer'] = (regline['er_provfer'] > 0.009) and "%.2f" % regline['er_provfer'] or '-'

        return regline, contract_ids

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
