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
from openerp.report import report_sxw

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)

        self.localcontext.update({
            'time': time,
            'get_no': self.get_no,
            'get_salary':self.get_salary,
            'get_workwage':self.get_workwage,
            'get_ot':self.get_ot,
            'get_transportation': self.get_transportation,
            'get_hous': self.get_hous,
            'get_pos': self.get_pos,
            'get_hard': self.get_hard,
            'get_perfbonus': self.get_perfbonus,
            'get_allowances': self.get_allowances,
            'get_allowance_total': self.get_allowance_total,
            'get_gross':self.get_gross,
            'get_taxable_gross': self.get_taxable_gross,
            'get_ded_fit': self.get_ded_fit,
            'get_ded_pf_ee': self.get_ded_pf_ee,
            'get_ded_provf_ee': self.get_ded_provf_ee,
            'get_ded_lu': self.get_ded_lu,
            'get_ded_loan': self.get_ded_loan,
            'get_ded_garnish': self.get_ded_garnish,
            'get_deduct': self.get_deduct,
            'get_total_deduct':self.get_total_deduct,
            'get_net':self.get_net,
            'get_er_contributions': self.get_er_contributions,
            'get_tot_pension': self.get_tot_pension,
            'get_er_provf': self.get_er_provf,
            'get_tot_salary':self.get_tot_salary,
            'get_tot_workwage':self.get_tot_workwage,
            'get_tot_ot':self.get_tot_ot,
            'get_tot_transportation': self.get_tot_transportation,
            'get_tot_hous': self.get_tot_hous,
            'get_tot_pos': self.get_tot_pos,
            'get_tot_hard': self.get_tot_hard,
            'get_tot_perfbonus': self.get_tot_perfbonus,
            'get_tot_allowances': self.get_tot_allowances,
            'get_tot_allowance_total': self.get_tot_allowance_total,
            'get_tot_gross':self.get_tot_gross,
            'get_tot_taxable_gross': self.get_tot_taxable_gross,
            'get_tot_ded_fit': self.get_tot_ded_fit,
            'get_tot_ded_pf_ee': self.get_tot_ded_pf_ee,
            'get_tot_ded_provf_ee': self.get_tot_ded_provf_ee,
            'get_tot_ded_lu': self.get_tot_ded_lu,
            'get_tot_ded_loan': self.get_tot_ded_loan,
            'get_tot_ded_garnish': self.get_tot_ded_garnish,
            'get_tot_deduct': self.get_tot_deduct,
            'get_tot_total_deduct':self.get_tot_total_deduct,
            'get_tot_net':self.get_tot_net,
            'get_tot_er_contributions': self.get_tot_er_contributions,
            'get_tot_tot_pension': self.get_tot_tot_pension,
            'get_tot_er_provf': self.get_tot_er_provf,
            'get_details_by_payslip': self.get_details_by_payslip,
            'fmt_float': self.fmt_float,
            'get_payslip_runs': self.get_payslip_runs,
        })
        self.no = 0
        self.salary = 0.0
        self.workwage = 0.0
        self.ot = 0.0
        self.transportation = 0.0
        self.hous_allow = 0.0
        self.pos_allow = 0.0
        self.hard_allow = 0.0
        self.perfbonus_allow = 0.0
        self.allowances = 0.0
        self.allowance_total = 0.0
        self.gross = 0.0
        self.taxable_gross = 0.0
        self.ded_fit = 0.0
        self.ded_pf_ee = 0.0
        self.ded_provf_ee = 0.0
        self.ded_lu = 0.0
        self.ded_loan = 0.0
        self.ded_garnish = 0.0
        self.deduct = 0.0
        self.total_deduct = 0.0
        self.net = 0.0
        self.er_contributions = 0.0
        self.tot_pension = 0.0
        self.er_provf = 0.0
        self.saved_run_id = -1

        # Running Total for all departments
        self.tot_salary = 0.0
        self.tot_workwage = 0.0
        self.tot_ot = 0.0
        self.tot_transportation = 0.0
        self.tot_hous_allow = 0.0
        self.tot_pos_allow = 0.0
        self.tot_hard_allow = 0.0
        self.tot_perfbonus_allow = 0.0
        self.tot_allowances = 0.0
        self.tot_allowance_total = 0.0
        self.tot_gross = 0.0
        self.tot_taxable_gross = 0.0
        self.tot_ded_fit = 0.0
        self.tot_ded_pf_ee = 0.0
        self.tot_ded_provf_ee = 0.0
        self.tot_ded_lu = 0.0
        self.tot_ded_loan = 0.0
        self.tot_ded_garnish = 0.0
        self.tot_deduct = 0.0
        self.tot_total_deduct = 0.0
        self.tot_net = 0.0
        self.tot_er_contributions = 0.0
        self.tot_tot_pension = 0.0
        self.tot_er_provf = 0.0

    def _reset_values(self, run_id):
        
        self.no = 0
        
        #self.tot_salary += self.salary
        self.salary = 0.0

        #self.tot_workwage += self.workwage
        self.workwage = 0.0

        #self.tot_ot += self.ot
        self.ot = 0.0
        
        #self.tot_transportation += self.transportation
        self.transportation = 0.0
        
        #self.tot_hous_allow += self.hous_allow
        self.hous_allow = 0.0
        
        #self.tot_pos_allow += self.pos_allow
        self.pos_allow = 0.0
        
        #self.tot_hard_allow += self.hard_allow
        self.hard_allow = 0.0

        self.perfbonus_allow = 0.0
        
        #self.tot_allowances += self.allowances
        self.allowances = 0.0
        
        self.allowance_total = 0.0

        #self.tot_gross += self.gross
        self.gross = 0.0
        
        #self.tot_taxable_gross += self.taxable_gross
        self.taxable_gross = 0.0
        
        #self.tot_ded_fit += self.ded_fit
        self.ded_fit = 0.0
        
        #self.tot_ded_pf_ee += self.ded_pf_ee
        self.ded_pf_ee = 0.0

        self.ded_provf_ee = 0.0
        
        #self.tot_ded_lu += self.ded_lu
        self.ded_lu = 0.0

        self.ded_loan = 0.0

        self.ded_garnish = 0.0
        
        #self.tot_deduct += self.deduct
        self.deduct = 0.0
        
        #self.tot_total_deduct += self.total_deduct
        self.total_deduct = 0.0
        
        #self.tot_net += self.net
        self.net = 0.0
        
        #self.tot_er_contributions += self.er_contributions
        self.er_contributions = 0.0

        self.tot_pension = 0.0

        self.er_provf = 0.0
        
        self.saved_run_id = run_id

    def fmt_float(self, f):
        
        return "%.2f" % f
    
    def get_payslip_runs(self, runs):
        
        payslip_runs = []
        for r in runs:
            _has_entry = False
            for slip in r.slip_ids:
                if slip.amended_payslip_id:
                    _has_entry = True
                    break
                
            if _has_entry:
                payslip_runs.append(r)
        
        return payslip_runs
    
    def get_details_by_payslip(self, payslips):
        
        res = []
        start_date = False
        end_date = False
        seen_slip_ids = []
        for slip in payslips:

            if not start_date or not end_date:
                start_date = slip.date_from
                end_date = slip.date_to

            if self.saved_run_id == -1:
                self.saved_run_id = slip.payslip_run_id.id
            elif self.saved_run_id != slip.payslip_run_id.id:
                self._reset_values(slip.payslip_run_id.id)
            
            this_slip = slip
            if slip.amended_payslip_id:
                this_slip = slip.amended_payslip_id
            tmp = self.get_details_by_rule_category(this_slip.details_by_salary_rule_category)
            tmp['name'] = slip.employee_id.name
            #tmp['id_no'] = slip.employee_id.employee_no
            tmp['id_no'] = slip.employee_id.legacy_no
            if slip.amended_payslip_id:
                res.append(tmp)
                seen_slip_ids.append(this_slip.id)

        # Get amended pay slips with no original (not in orig. payroll)
        amend_obj = self.pool.get('hr.payroll.postclose.amendment')
        if start_date and end_date:
            _ids = amend_obj.search(self.cr, self.uid,
                                    [('pp_id.date_start', '=', start_date),
                                     ('pp_id.date_end', '=', end_date)],
                                    )
            for amend in amend_obj.browse(self.cr, self.uid, _ids,
                                          context=self.context):
                if amend.new_payslip_id.id not in seen_slip_ids:
                    slip = amend.new_payslip_id
                    tmp = self.get_details_by_rule_category(
                        slip.details_by_salary_rule_category)
                    tmp['name'] = slip.employee_id.name
                    tmp['id_no'] = slip.employee_id.employee_no
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
            'name': '',
            'id_no': '',
            'salary': 0,
            'workwage': 0,
            'ot': 0,
            'transportation': 0,
            'hous_allow': 0,
            'pos_allow': 0,
            'hard_allow': 0,
            'perfbonus_allow': 0,
            'allowances': 0,
            'allowance_total': 0,
            'taxable_gross': 0,
            'gross': 0,
            'fit': 0,
            'lu': 0,
            'loan': 0,
            'garnish': 0,
            'ee_pension': 0,
            'ee_provident': 0,
            'deductions': 0,
            'deductions_total': 0,
            'net': 0,
            'er_contributions': 0,
            'pension_total': 0,
            'er_provf': 0,
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
                # Level 0 is the category
                if r['code'] == 'BASIC' and r['level'] != 0:
                    regline['salary'] += r['total']
                elif r['code'] == 'WORKWAGE':
                    regline['workwage'] += r['total']
                elif r['code'] == 'OT':
                    regline['ot'] += r['total']
                elif r['code'] == 'TRA' or r['code'] == 'TRVA' or r['code'] == 'TRANS03':
                    regline['transportation'] += r['total']
                elif r['code'] == 'HOUS'or r['code'] == 'PRES60' or r['code'] == 'PRES70' or r['code'] == 'PAADJ':
                    regline['hous_allow'] += r['total']
                elif r['code'] == 'POS':
                    regline['pos_allow'] += r['total']
                elif r['code'] == 'HARD30' or r['code'] == 'HARD50' or r['code'] == 'hardship200':
                    regline['hard_allow'] += r['total']
                elif r['code'] == 'BNS1' or r['code'] == 'BNS1GRADING' or r['code'] == 'GUARD100' or r['code'] == 'BONUS':
                    regline['perfbonus_allow'] += r['total']
                elif r['code'] == 'ALW':
                    regline['allowances'] += r['total']
                elif r['code'] == 'TXBL' and r['level'] == 0:
                    regline['taxable_gross'] += r['total']
                elif r['code'] == 'GROSS' and r['level'] == 0:
                    regline['gross'] += r['total']
                elif r['code'] == 'FITCALC' and r['level'] == 0:
                    regline['fit'] += r['total']
                elif r['code'] == 'PROVFEE':
                    regline['ee_provident'] += r['total']
                elif r['code'] == 'PENFEE':
                    regline['ee_pension'] += r['total']
                    regline['pension_total'] += r['total']
                elif r['code'] == 'LU' or r['code'] == 'LBRU':
                    regline['lu'] += r['total']
                elif r['code'] == 'LOAN' or r['code'] == 'LOAN2':
                    regline['loan'] += r['total']
                elif r['code'] == 'GARN' or r['code'] == 'GARN2':
                    regline['garnish'] += r['total']
                elif r['code'] == 'DED' and r['level'] == 0:
                    regline['deductions'] += r['total']
                elif r['code'] == 'DEDTOTAL' and r['level'] == 0:
                    regline['deductions_total'] += r['total']
                elif r['code'] == 'NET' and r['level'] == 0:
                    regline['net'] += r['total']
                elif r['code'] == 'PENFER':
                    regline['er_contributions'] += r['total']
                    regline['pension_total'] += r['total']
                elif r['code'] == 'PROVFER':
                    regline['er_provf'] += r['total']
            
            # Make adjustments to subtract from the parent category's total the
            # amount of individual rules that we show separately on the sheet.
            #
            regline['allowance_total'] = regline['allowances']
            regline['allowances'] -= regline['transportation']
            regline['allowances'] -= regline['hous_allow']
            regline['allowances'] -= regline['pos_allow']
            regline['allowances'] -= regline['hard_allow']
            regline['allowances'] -= regline['perfbonus_allow']
            regline['deductions'] -= regline['ee_pension']
            regline['deductions'] -= regline['ee_provident']
            regline['deductions'] -= regline['lu']
            regline['deductions'] -= regline['loan']
            regline['deductions'] -= regline['garnish']
            
            # Increase running totals
            #
            self.salary += regline['salary']
            self.workwage += regline['workwage']
            self.ot += regline['ot']
            self.transportation += regline['transportation']
            self.hous_allow += regline['hous_allow']
            self.pos_allow += regline['pos_allow']
            self.hard_allow += regline['hard_allow']
            self.perfbonus_allow += regline['perfbonus_allow']
            self.allowances += regline['allowances']
            self.allowance_total += regline['allowance_total']
            self.gross += regline['gross']
            self.taxable_gross += regline['taxable_gross']
            self.ded_fit += regline['fit']
            self.ded_pf_ee += regline['ee_pension']
            self.ded_provf_ee += regline['ee_provident']
            self.ded_lu += regline['lu']
            self.ded_loan += regline['loan']
            self.ded_garnish += regline['garnish']
            self.deduct += regline['deductions']
            self.total_deduct += regline['deductions_total']
            self.net += regline['net']
            self.er_contributions += regline['er_contributions']
            self.tot_pension += regline['pension_total']
            self.er_provf += regline['er_provf']

            self.tot_salary += regline['salary']
            self.tot_workwage += regline['workwage']
            self.tot_ot += regline['ot']
            self.tot_transportation += regline['transportation']
            self.tot_hous_allow += regline['hous_allow']
            self.tot_pos_allow += regline['pos_allow']
            self.tot_hard_allow += regline['hard_allow']
            self.tot_perfbonus_allow += regline['perfbonus_allow']
            self.tot_allowances += regline['allowances']
            self.tot_allowance_total += regline['allowance_total']
            self.tot_gross += regline['gross']
            self.tot_taxable_gross += regline['taxable_gross']
            self.tot_ded_fit += regline['fit']
            self.tot_ded_pf_ee += regline['ee_pension']
            self.tot_ded_provf_ee += regline['ee_provident']
            self.tot_ded_lu += regline['lu']
            self.tot_ded_loan += regline['loan']
            self.tot_ded_garnish += regline['garnish']
            self.tot_deduct += regline['deductions']
            self.tot_total_deduct += regline['deductions_total']
            self.tot_net += regline['net']
            self.tot_er_contributions += regline['er_contributions']
            self.tot_tot_pension += regline['pension_total']
            self.tot_er_provf += regline['er_provf']
        
        return regline
    
    def get_salary(self, obj):
        return self.salary
    
    def get_tot_salary(self, obj):
        return self.tot_salary
    
    def get_workwage(self, obj):
        return self.workwage
    
    def get_tot_workwage(self, obj):
        return self.tot_workwage

    def get_ot(self,obj):
        return self.ot

    def get_tot_ot(self,obj):
        return self.tot_ot

    def get_transportation(self,obj):
        return self.transportation

    def get_tot_transportation(self,obj):
        return self.tot_transportation

    def get_hous(self,obj):
        return self.hous_allow

    def get_tot_hous(self,obj):
        return self.tot_hous_allow

    def get_pos(self,obj):
        return self.pos_allow

    def get_tot_pos(self,obj):
        return self.tot_pos_allow

    def get_hard(self,obj):
        return self.hard_allow

    def get_tot_hard(self,obj):
        return self.tot_hard_allow

    def get_perfbonus(self,obj):
        return self.perfbonus_allow

    def get_tot_perfbonus(self,obj):
        return self.tot_perfbonus_allow

    def get_allowances(self,obj):
        return self.allowances

    def get_tot_allowances(self,obj):
        return self.tot_allowances

    def get_allowance_total(self,obj):
        return self.allowance_total

    def get_tot_allowance_total(self,obj):
        return self.tot_allowance_total

    def get_gross(self,obj):
        return self.gross

    def get_tot_gross(self,obj):
        return self.tot_gross

    def get_taxable_gross(self,obj):
        return self.taxable_gross

    def get_tot_taxable_gross(self,obj):
        return self.tot_taxable_gross

    def get_ded_fit(self, obj):
        return self.ded_fit

    def get_tot_ded_fit(self, obj):
        return self.tot_ded_fit
    
    def get_ded_pf_ee(self, obj):
        return self.ded_pf_ee
    
    def get_tot_ded_pf_ee(self, obj):
        return self.tot_ded_pf_ee
    
    def get_ded_provf_ee(self, obj):
        return self.ded_provf_ee
    
    def get_tot_ded_provf_ee(self, obj):
        return self.tot_ded_provf_ee
    
    def get_ded_lu(self, obj):
        return self.ded_lu
    
    def get_tot_ded_lu(self, obj):
        return self.tot_ded_lu
    
    def get_ded_loan(self, obj):
        return self.ded_loan
    
    def get_tot_ded_loan(self, obj):
        return self.tot_ded_loan
    
    def get_ded_garnish(self, obj):
        return self.ded_garnish
    
    def get_tot_ded_garnish(self, obj):
        return self.tot_ded_garnish
    
    def get_deduct(self,obj):
        return self.deduct
    
    def get_tot_deduct(self,obj):
        return self.tot_deduct

    def get_total_deduct(self,obj):
        return self.total_deduct

    def get_tot_total_deduct(self,obj):
        return self.tot_total_deduct

    def get_net(self,obj):
        return self.net

    def get_tot_net(self,obj):
        return self.tot_net

    def get_er_contributions(self, obj):
        return self.er_contributions

    def get_tot_er_contributions(self, obj):
        return self.tot_er_contributions

    def get_tot_pension(self, obj):
        return self.tot_pension

    def get_tot_tot_pension(self, obj):
        return self.tot_tot_pension

    def get_er_provf(self, obj):
        return self.er_provf

    def get_tot_er_provf(self, obj):
        return self.tot_er_provf

    def get_no(self):
        self.no += 1
        return self.no
