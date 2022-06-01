#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyrigth (C) 2013,2014 Michael Telahun Makonnen <mmakonnen@gmail.com>
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

import locale
import time
from datetime import datetime

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.report import report_sxw

RULE_CODES = ['FITCALC']

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)

        self.localcontext.update({
            'time': time,
            'get_no': self.get_no,
            'get_no_display': self.get_no_display,
            'get_salary': self.get_salary,
            'get_tot_salary': self.get_tot_salary,
            'get_fit':self.get_fit,
            'get_tot_fit':self.get_tot_fit,
            'get_ot':self.get_ot,
            'get_tot_ot':self.get_tot_ot,
            'get_allowance':self.get_allowance,
            'get_tot_allowance':self.get_tot_allowance,
            'get_taxable':self.get_taxable,
            'get_tot_taxable':self.get_tot_taxable,
            'get_net':self.get_net,
            'get_tot_net':self.get_tot_net,
            'get_diff':self.get_diff,
            'get_tot_diff':self.get_tot_diff,
            'get_details_by_payslip': self.get_details_by_payslip,
            'fmt_float': self.fmt_float,
            'tax_period': self.get_tax_period,
            'tax_month': self.get_tax_month,
            'tax_year': self.get_tax_year,
        })
        self.tax_period = False
        self.tax_month = False
        self.tax_year = False
        self.payroll_type = False
        self.no = 0
        self.salary = 0.0
        self.fit = 0.0
        self.ot = 0.0
        self.allowance = 0.0
        self.net = 0.0
        self.diff = 0.0
        self.taxable = 0.0
        self.saved_run_id = -1

        # Running Total for all departments
        self.tot_salary = 0.0
        self.tot_fit = 0.0
        self.tot_ot = 0.0
        self.tot_allowance = 0.0
        self.tot_taxable = 0.0
        self.tot_net = 0.0
        self.tot_diff = 0.0
    
    def set_context(self, objects, data, ids, report_type=None):
        if data.get('form', False) and data['form'].get('tax_period', False):
            self.tax_period = data['form']['tax_period']
        
        if data.get('form', False) and data['form'].get('month'):
            self.tax_month = data['form']['month']
        
        if data.get('form', False) and data['form'].get('year'):
            self.tax_year = data['form']['year']
        
        if data.get('form', False) and data['form'].get('payroll_type'):
            self.payroll_type = data['form']['payroll_type']
        
        return super(Parser, self).set_context(objects, data, ids, report_type=report_type)

    def _reset_values(self, run_id):
        
        self.no = 0
        self.salary = 0.0
        self.fit = 0.0
        self.ot = 0.0
        self.allowance = 0.0
        self.taxable = 0.0
        self.net = 0.00
        self.diff = 0.00
        self.saved_run_id = run_id

    def fmt_float(self, f, d):
        locale.setlocale(locale.LC_ALL, '')
        strAmount = locale.format(("%."+str(d)+"f"), f, grouping=True)
        return strAmount
    
    def choose_payslip(self, slip):
        
        res = False
        if self.payroll_type == 'orig':
            res = slip
        elif self.payroll_type == 'amend':
            if slip.amended_payslip_id:
                res = slip.amended_payslip_id
            else:
                res = slip
        
        return res
    
    def get_details_by_payslip(self, payslips):
        
        res = []
        ee_obj = self.pool.get('hr.employee')
        for slip in payslips:
            
            _slip = self.choose_payslip(slip)
            tmp = self.get_details_by_rule_category(_slip.details_by_salary_rule_category)
            tmp['name'] = _slip.employee_id.name
            #tmp['id_no'] = slip.employee_id.employee_no
            tmp['id_no'] = _slip.employee_id.legacy_no
            if tmp['fit'] >= 0:
                _contracts = ee_obj.get_initial_employment_date(self.cr, self.uid,
                                                                [_slip.employee_id.id])
                if _contracts[_slip.employee_id.id]:
                    tmp['employment_date'] = _contracts[_slip.employee_id.id].strftime('%d-%b-%Y')
                else:
                    tmp['employment_date'] = ''
                res.append(tmp)
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

        # Choose only the categories (or rules) that we want to
        # show in the report.
        #
        regline = {
            'salary': 0,
            'fit': 0,
            'ot': 0,
            'allowance': 0,
            'taxable_gross': 0,
            'net': 0,
            'diff': 0,
        }
        
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
                for line in payslip_line.browse(self.cr, self.uid, value):
                    category_total += line.total
                level = 0
                for parent in parents:
                    res.append({
                        'rule_category': parent.name,
                        'name': parent.name,
                        'code': parent.code,
                        'level': level,
                        'total': category_total,
                    })
                    level += 1
                for line in payslip_line.browse(self.cr, self.uid, value):
                    res.append({
                        'rule_category': line.name,
                        'name': line.name,
                        'code': line.code,
                        'total': line.total,
                        'level': level
                    })
            
            for r in res:
                if r['code'] == 'CALCBASIC' and r['level'] != 0:
                    regline['salary'] += r['total']
                elif r['code'] in RULE_CODES and r['level'] == 0:
                    regline['fit'] += r['total']
                elif r['code'] == 'OT':
                    regline['ot'] += r['total']
                elif r['code'] == 'ALW':
                    regline['allowance'] += r['total']
                elif r['code'] == 'TXBL' and r['level'] == 0:
                    regline['taxable_gross'] += r['total']
                elif r['code'] == 'NET' and r['level'] == 0:
                    regline['net'] += r['total']

            regline['diff'] = regline['taxable_gross'] - regline['fit']
            
            # Increase running totals
            #
            if regline['fit'] >= 0:
                self.salary += regline['salary']
                self.tot_salary += regline['salary']
                self.fit += regline['fit']
                self.tot_fit += regline['fit']
                self.ot += regline['ot']
                self.tot_ot += regline['ot']
                self.allowance += regline['allowance']
                self.tot_allowance += regline['allowance']
                self.taxable += regline['taxable_gross']
                self.tot_taxable += regline['taxable_gross']
                self.net += regline['net']
                self.tot_net += regline['net']
                self.diff += regline['diff']
                self.tot_diff += regline['diff']
        
        return regline

    def get_salary(self):
        return self.fmt_float(self.salary, 2)

    def get_tot_salary(self):
        return self.fmt_float(self.tot_salary, 2)

    def get_fit(self):
        return self.fmt_float(self.fit, 2)

    def get_tot_fit(self):
        return self.fmt_float(self.tot_fit, 2)

    def get_ot(self):
        return self.fmt_float(self.ot, 2)

    def get_tot_ot(self):
        return self.fmt_float(self.tot_ot, 2)

    def get_allowance(self):
        return self.fmt_float(self.allowance, 2)

    def get_tot_allowance(self):
        return self.fmt_float(self.tot_allowance, 2)

    def get_taxable(self):
        return self.fmt_float(self.taxable, 2)

    def get_tot_taxable(self):
        return self.fmt_float(self.tot_taxable, 2)

    def get_net(self):
        return self.fmt_float(self.net, 2)

    def get_tot_net(self):
        return self.fmt_float(self.tot_net, 2)

    def get_diff(self):
        return self.fmt_float(self.dif, 2)

    def get_tot_diff(self):
        return self.fmt_float(self.tot_diff, 2)

    def get_no(self):
        self.no += 1
        return self.no

    def get_no_display(self):
        return self.no
    
    def get_tax_period(self):
        return self.tax_period
    
    def get_tax_month(self):
        return self.tax_month
    
    def get_tax_year(self):
        return self.tax_year
