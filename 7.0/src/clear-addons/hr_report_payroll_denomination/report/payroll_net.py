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

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)

        self.localcontext.update({
            'time': time,
            'get_no': self.get_no,
            'get_net':self.get_net,
            'get_100':self.get_100,
            'get_50':self.get_50,
            'get_10':self.get_10,
            'get_5':self.get_5,
            'get_1':self.get_1,
            'get_tot_net':self.get_tot_net,
            'get_tot_100':self.get_tot_100,
            'get_tot_50':self.get_tot_50,
            'get_tot_10':self.get_tot_10,
            'get_tot_5':self.get_tot_5,
            'get_tot_1':self.get_tot_1,
            'get_payslip_runs': self.get_payslip_runs,
            'get_details_by_payslip': self.get_details_by_payslip,
            'fmt_float': self.fmt_float,
        })
        self.no = 0
        self.net = 0.0
        self.note100 = 0.0
        self.note50 = 0.0
        self.note10 = 0.0
        self.note5 = 0.0
        self.note1 = 0.0
        self.saved_run_id = -1

        # Running Total for all departments
        self.tot_net = 0.0
        self.tot_note100 = 0.0
        self.tot_note50 = 0.0
        self.tot_note10 = 0.0
        self.tot_note5 = 0.0
        self.tot_note1 = 0.0

    def _reset_values(self, run_id):
        
        self.no = 0
        self.net = 0.0
        self.note100 = 0.0
        self.note50 = 0.0
        self.note10 = 0.0
        self.note5 = 0.0
        self.note1 = 0.0
        self.saved_run_id = run_id

    def fmt_float(self, f, d):
        
        return (("%."+str(d)+"f") % f)
    
    def get_denominations(self, net):
        
        den = self.pool.get('res.currency').get_denominations_from_amount(self.cr,
                                                                          self.uid,
                                                                          'ETB', net)
        res = []
        res_sorted = []
        for d in den:
            if len(res_sorted) == 0:
                res_sorted.append(d)
                continue
            i = 0
            for rs in res_sorted:
                if d.get('name') < rs.get('name'):
                    res_sorted.insert(i, d)
                    break
                elif rs == res_sorted[-1]:
                    res_sorted.append(d)
                    break
                i += 1
        #res_sorted = res_sorted.reverse()
        i = -1
        while res_sorted[i]:
            res += [res_sorted[i].get('qty', 0)]
            i -= 1
            if res_sorted[i] == res_sorted[0]:
                break
        return res
    
    def get_payslip_runs(self, runs):
        
        dd_obj = self.pool.get('hr.payroll.directdeposit')
        payslip_runs = []
        for r in runs:
            
            has_entries = False
            for slip in r.slip_ids:
                
                # Get relevant direct deposit record
                #
                dd = None
                dToday = datetime.strptime(slip.date_to, OE_DFORMAT).date()
                if slip.employee_id.use_direct_deposit:
                    dd = dd_obj.get_latest(self.cr, self.uid, slip.employee_id.dd_ids, dToday)
                
                # Do not include employee who use Direct Deposit
                #
                if slip.employee_id.use_direct_deposit:
                    dToday = datetime.strptime(slip.date_to, OE_DFORMAT).date()
                    dd = dd_obj.get_latest(self.cr, self.uid, slip.employee_id.dd_ids, dToday)
                    if dd and dd.effective_date <= slip.date_to:
                        continue
                    else:
                        has_entries = True
                        break
                else:
                    has_entries = True
                    break
            
            if has_entries:
                payslip_runs.append(r)
        
        return payslip_runs
    
    def get_details_by_payslip(self, payslips):
        
        
        dd_obj = self.pool.get('hr.payroll.directdeposit')
        
        res = []
        for slip in payslips:
            
            # Reset subtotals if we're starting a new department
            #
            if self.saved_run_id == -1:
                self.saved_run_id = slip.payslip_run_id.id
            elif self.saved_run_id != slip.payslip_run_id.id:
                self._reset_values(slip.payslip_run_id.id)
            
            if slip.employee_id.use_direct_deposit:
                dToday = datetime.strptime(slip.date_to, OE_DFORMAT).date()
                dd = dd_obj.get_latest(self.cr, self.uid, slip.employee_id.dd_ids, dToday)
                if dd and dd.effective_date <= slip.date_to:
                    continue
                
            tmp = self.get_details_by_rule_category(slip.details_by_salary_rule_category)
            tmp['name'] = slip.employee_id.name
            #tmp['id_no'] = slip.employee_id.f_employee_no
            tmp['id_no'] = slip.employee_id.legacy_no
            if tmp['net'] > 0:
                tmp['denominations'] = self.get_denominations(tmp['net'])
                self.note100 += tmp['denominations'][0]
                self.note50 += tmp['denominations'][1]
                self.note10 += tmp['denominations'][2]
                self.note5 += tmp['denominations'][3]
                self.note1 += tmp['denominations'][4]
                self.tot_note100 += tmp['denominations'][0]
                self.tot_note50 += tmp['denominations'][1]
                self.tot_note10 += tmp['denominations'][2]
                self.tot_note5 += tmp['denominations'][3]
                self.tot_note1 += tmp['denominations'][4]
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
            'net': 0,
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
                if r['code'] == 'NET' and r['level'] == 0:
                    regline['net'] += r['total']

            # Increase running totals
            #
            self.net += regline['net']
            self.tot_net += regline['net']
        
        return regline

    def get_net(self):
        return self.fmt_float(self.net, 2)

    def get_tot_net(self):
        return self.fmt_float(self.tot_net, 2)

    def get_100(self):
        return self.fmt_float(self.note100, 0)

    def get_tot_100(self):
        return self.fmt_float(self.tot_note100, 0)

    def get_50(self):
        return self.fmt_float(self.note50, 0)

    def get_tot_50(self):
        return self.fmt_float(self.tot_note50, 0)

    def get_10(self):
        return self.fmt_float(self.note10, 0)

    def get_tot_10(self):
        return self.fmt_float(self.tot_note10, 0)

    def get_5(self):
        return self.fmt_float(self.note5, 0)

    def get_tot_5(self):
        return self.fmt_float(self.tot_note5, 0)

    def get_1(self):
        return self.fmt_float(self.note1, 0)

    def get_tot_1(self):
        return self.fmt_float(self.tot_note1, 0)

    def get_no(self):
        self.no += 1
        return self.no
