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
            'get_details_by_payslip': self.get_details_by_payslip,
            'add_count': self.add_count,
            'get_count': self.get_count,
        })
        
        self._count = 0

    def add_count(self):
        
        self._count += 1
        return
    
    def get_count(self):
        
        return self._count
    
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
        
    def get_details_by_payslip(self, payslips):
        
        accrual_obj = self.pool.get('hr.accrual')
        
        res = []
        for slip in payslips:
            tmp, contract_ids = self.get_details_by_rule_category(slip.details_by_salary_rule_category)
            
            tmp['name'] = slip.employee_id.name
            tmp['id_no'] = slip.employee_id.f_employee_no
            tmp['dept'] = slip.employee_id.department_id.complete_name
            tmp['date_from'] = slip.date_from
            tmp['date_to'] = slip.date_to
            
            worked_days_details = self.get_worked_days_details(slip.worked_days_line_ids)
            tmp.update(worked_days_details)
            
            dToday = datetime.strptime(slip.date_from, OE_DATEFORMAT).date()
            accruals = self.get_payslip_accruals(contract_ids, dToday)
            if len(accruals) > 0:
                for accrual_id, code in accruals:
                    balance = accrual_obj.get_balance(self.cr, self.uid, [accrual_id],
                                                             slip.employee_id.id, slip.date_to)
                    tmp[str(code)] = balance
            
            res.append(tmp)
        
        return res
    
    def get_worked_days_details(self, worked_day_lines):
        
        res = {
            'NFRA': 0,
            'WARNW': 0,
            'AWOL': 0,
        }
        for line in worked_day_lines:
            if line.code not in ['NFRA', 'WARNW', 'AWOL']:
                continue
            else:
                res[line.code] += line.number_of_hours
        res['AWOL'] = (res['AWOL'] > 0.009) and "%.2f" % (float(res['AWOL']) / 8.0) or '-'
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
            'special_hours': 0,
            'special_hours_qty': 0,
            'ot': 0,
            'ot_qty': 0,
            'transportation': 0,
            'perf': 0,
            'bunch': 0,
            'bunch_qty': 0,
            'allowances': 0,
            'taxable_gross': 0,
            'gross': 0,
            'fit': 0,
            'ee_pension': 0,
            'lu': 0,
            'benefits': 0,
            'penalty': 0,
            'deductions': 0,
            'deductions_total': 0,
            'net': 0,
            'er_contributions': 0,
            'LVANNUAL': 0,
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
                if r['code'] == 'CALCBASIC':
                    regline['salary'] += r['total']
                elif r['code'] == 'WORKHOL' or r['code'] == 'WORKRST':
                    regline['special_hours'] += r['total']
                    regline['special_hours_qty'] += r['quantity']
                elif r['code'] == 'OT':
                    regline['ot'] += r['total']
                    regline['ot_qty'] += r['quantity']
                elif r['code'] == 'TRA' or r['code'] == 'TRVA':
                    regline['transportation'] += r['total']
                elif r['code'] == 'PI' or r['code'] == 'EAB1':
                    regline['perf'] += r['total']
                elif r['code'] == 'BUNCH' or r['code'] == 'BUNCH2':
                    regline['bunch'] += r['total']
                    regline['bunch_qty'] += r['quantity']
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
                elif r['code'] == 'LU':
                    regline['lu'] += r['total']
                elif r['code'] == 'PD':
                    regline['penalty'] += r['total']
                elif r['code'] in ['ADV', 'BIKE']:
                    regline['benefits'] += r['total']
                elif r['code'] == 'DED':
                    regline['deductions'] += r['total']
                elif r['code'] == 'DEDTOTAL' and r['level'] == 0:
                    regline['deductions_total'] = r['total']
                elif r['code'] == 'NET' and r['level'] == 0:
                    regline['net'] += r['total']
                elif r['code'] == 'ER':
                    regline['er_contributions'] += r['total']
                elif r['code'] == 'LVANNUAL':
                    regline['LVANNUAL'] += r['total']
            
            # Make adjustments to subtract from the parent category's total the
            # amount of individual rules that we show separately on the sheet.
            #
            regline['ot'] -= regline['special_hours']
            regline['ot_qty'] -= regline['special_hours_qty']
            regline['allowances'] -= regline['transportation']
            regline['allowances'] -= regline['perf']
            regline['allowances'] -= regline['bunch']
            regline['deductions'] -= regline['ee_pension']
            regline['deductions'] -= regline['lu']
            regline['deductions'] -= regline['penalty']
            regline['deductions'] -= regline['benefits']
        
        # Format correctly
        #
        regline['salary'] = "%.2f" % regline['salary']
        regline['special_hours'] = (regline['special_hours'] > 0.009) and "%.2f" % regline['special_hours'] or '-'
        regline['special_hours_qty'] = (regline['special_hours_qty'] > 0.009) and "%.2f" % regline['special_hours_qty'] or '-'
        regline['ot'] = (regline['ot'] > 0.009) and "%.2f" % regline['ot'] or '-'
        regline['ot_qty'] = (regline['ot_qty'] > 0.009) and "%.2f" % regline['ot_qty'] or '-'
        regline['transportation'] = (regline['transportation'] > 0.009) and "%.2f" % regline['transportation'] or '-'
        regline['perf'] = (regline['perf'] > 0.009) and "%.2f" % regline['perf'] or '-'
        regline['bunch'] = (regline['bunch'] > 0.009) and "%.2f" % regline['bunch'] or '-'
        regline['bunch_qty'] = (regline['bunch_qty'] > 0.009) and "%.2f" % regline['bunch_qty'] or '-'
        regline['allowances'] = (regline['allowances'] > 0.009) and "%.2f" % regline['allowances'] or '-'
        regline['taxable_gross'] = (regline['taxable_gross'] > 0.009) and "%.2f" % regline['taxable_gross'] or '-'
        regline['gross'] = (regline['gross'] > 0.009) and "%.2f" % regline['gross'] or '-'
        regline['fit'] = (regline['fit'] > 0.009) and "%.2f" % regline['fit'] or '-'
        regline['ee_pension'] = (regline['ee_pension'] > 0.009) and "%.2f" % regline['ee_pension'] or '-'
        regline['lu'] = (regline['lu'] > 0.009) and "%.2f" % regline['lu'] or '-'
        regline['benefits'] = (regline['benefits'] > 0.009) and "%.2f" % regline['benefits'] or '-'
        regline['penalty'] = (regline['penalty'] > 0.009) and "%.2f" % regline['penalty'] or '-'
        regline['deductions'] = (regline['deductions'] > 0.009) and "%.2f" % regline['deductions'] or '-'
        regline['deductions_total'] = (regline['deductions_total'] > 0.009) and "%.2f" % regline['deductions_total'] or '-'
        regline['net'] = (regline['net'] > 0.009) and "%.2f" % regline['net'] or '-'
        regline['er_contributions'] = (regline['er_contributions'] > 0.009) and "%.2f" % regline['er_contributions'] or '-'
        regline['LVANNUAL'] = (regline['LVANNUAL'] > 0.009) and "%.2f" % float(regline['LVANNUAL']) or '-'

        return regline, contract_ids

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
