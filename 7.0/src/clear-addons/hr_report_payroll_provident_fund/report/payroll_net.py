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

import time
from datetime import datetime

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from report import report_sxw

RULE_CODES = ['PROVFEE']
ER_RULE_CODES = ['PROVFER']

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)

        self.localcontext.update({
            'time': time,
            'get_no': self.get_no,
            'get_amount':self.get_amount,
            'get_tot_amount':self.get_tot_amount,
            'get_er_amount':self.get_er_amount,
            'get_tot_er_amount':self.get_tot_er_amount,
            'get_full_amount':self.get_full_amount,
            'get_tot_full_amount':self.get_tot_full_amount,
            'get_payslip_runs': self.get_payslip_runs,
            'get_details_by_payslip': self.get_details_by_payslip,
            'fmt_float': self.fmt_float,
        })
        self.no = 0
        self.amount = 0.0
        self.er_amount = 0.0
        self.full_amount = 0.0
        self.saved_run_id = -1

        # Running Total for all departments
        self.tot_amount = 0.0
        self.tot_er_amount = 0.0
        self.tot_full_amount = 0.0

    def _reset_values(self, run_id):
        
        self.no = 0
        self.amount = 0.0
        self.er_amount = 0.0
        self.full_amount = 0.0
        self.saved_run_id = run_id

    def fmt_float(self, f, d):
        
        return (("%."+str(d)+"f") % f)
    
    def is_selected(self, slip):
        
        # Do not include employees not having wages garnished
        #
        has_entry = False
        for line in slip.line_ids:
            if line.salary_rule_id.code in RULE_CODES and line.amount > 0.009:
                has_entry = True
                break
        return has_entry
            
    def get_payslip_runs(self, runs):
        
        payslip_runs = []
        for r in runs:
            
            has_entries = False
            for slip in r.slip_ids:
                
                # Do not include employees not having wages garnished
                #
                if self.is_selected(slip):
                    has_entries = True
                    break
            
            if has_entries:
                payslip_runs.append(r)
        
        return payslip_runs
    
    def get_details_by_payslip(self, payslips):
        
        res = []
        for slip in payslips:
            
            # Reset Subtotals if this is a new department
            #
            if self.saved_run_id == -1:
                self.saved_run_id = slip.payslip_run_id.id
            elif self.saved_run_id != slip.payslip_run_id.id:
                self._reset_values(slip.payslip_run_id.id)
            
            # Do not include employees not having wages garnished
            #
            if not self.is_selected(slip):
                continue
                
            tmp = self.get_details_by_rule_category(slip.details_by_salary_rule_category)
            tmp['name'] = slip.employee_id.name
            #tmp['id_no'] = slip.employee_id.f_employee_no
            tmp['id_no'] = slip.employee_id.legacy_no
            if tmp['amount'] > 0:
                tmp['amount'] = self.fmt_float(tmp['amount'], 2)
                tmp['er_amount'] = self.fmt_float(tmp['er_amount'], 2)
                tmp['full_amount'] = self.fmt_float(tmp['full_amount'], 2)
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
            'amount': 0,
            'er_amount': 0,
            'full_amount': 0,
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
                if r['code'] in RULE_CODES:
                    regline['amount'] += r['total']
                    regline['full_amount'] += r['total']
                elif r['code'] in ER_RULE_CODES:
                    regline['er_amount'] += r['total']
                    regline['full_amount'] += r['total']

            # Increase running totals
            #
            self.amount += regline['amount']
            self.tot_amount += regline['amount']
            self.er_amount += regline['er_amount']
            self.tot_er_amount += regline['er_amount']
            self.full_amount += regline['full_amount']
            self.tot_full_amount += regline['full_amount']
        
        return regline

    def get_amount(self):
        return self.fmt_float(self.amount, 2)

    def get_tot_amount(self):
        return self.fmt_float(self.tot_amount, 2)

    def get_er_amount(self):
        return self.fmt_float(self.er_amount, 2)

    def get_tot_er_amount(self):
        return self.fmt_float(self.tot_er_amount, 2)

    def get_full_amount(self):
        return self.fmt_float(self.full_amount, 2)

    def get_tot_full_amount(self):
        return self.fmt_float(self.tot_full_amount, 2)

    def get_no(self):
        self.no += 1
        return self.no
