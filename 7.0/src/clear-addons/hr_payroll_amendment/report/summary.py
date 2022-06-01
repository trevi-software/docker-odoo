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

from report import report_sxw

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)

        self.localcontext.update({
            'time': time,
            'get_no': self.get_no,
            'get_net':self.get_net,
            'get_payslip_runs': self.get_payslip_runs,
            'get_details_by_run': self.get_details_by_run,
            'get_net': self.get_net,
            'get_fit': self.get_fit,
            'get_earnings': self.get_earnings,
            'get_deductions': self.get_deductions,
            'get_tot_net': self.get_tot_net,
            'get_tot_fit': self.get_tot_fit,
            'get_tot_earnings': self.get_tot_earnings,
            'get_tot_deductions': self.get_tot_deductions,
            'fmt_float': self.fmt_float,
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
        })
        self.no = 0
        self.net = 0.0
        self.fit = 0.0
        self.earnings = 0.0
        self.deductions = 0.0
        self.note100 = 0.0
        self.note50 = 0.0
        self.note10 = 0.0
        self.note5 = 0.0
        self.note1 = 0.0
        self.saved_run_id = -1

        # Running Total for all departments
        self.tot_net = 0.0
        self.tot_fit = 0.0
        self.tot_earnings = 0.0
        self.tot_deductions = 0.0
        self.tot_note100 = 0.0
        self.tot_note50 = 0.0
        self.tot_note10 = 0.0
        self.tot_note5 = 0.0
        self.tot_note1 = 0.0

    def _reset_values(self, run_id):

        self.no = 0
        self.net = 0.0
        self.fit = 0.0
        self.earnings = 0.0
        self.deductions = 0.0
        self.note100 = 0.0
        self.note50 = 0.0
        self.note10 = 0.0
        self.note5 = 0.0
        self.note1 = 0.0
        self.saved_run_id = run_id

    def fmt_float(self, f, d):

        return (("%."+str(d)+"f") % f)

    def get_amendments(self, run):

        pa_obj = self.pool.get('hr.payroll.postclose.amendment')
        slip_ids = [s.id for s in run.slip_ids]
        pa_ids = pa_obj.search(self.cr, self.uid, [('old_payslip_id', 'in', slip_ids)])

        # Add amendments where there was no 'old' pay slip
        tmp_ids = pa_obj.search(self.cr, self.uid, [('old_payslip_id', '=', False),
                                                    ('new_payslip_id', '!=', False),
                                                    ('new_payslip_id.original_payslip_run_id', '=', run.id)])
        pa_ids += tmp_ids
        return pa_ids

    def get_payslip_runs(self, runs):

        payslip_runs = []
        for r in runs:

            pa_ids = self.get_amendments(r)
            if len(pa_ids) > 0:
                payslip_runs.append(r)

        return payslip_runs

    def get_details_by_run(self, run):

        pa_obj = self.pool.get('hr.payroll.postclose.amendment')
        pa_ids = self.get_amendments(run)
        self._reset_values(run.id)

        res = []
        for amendment in pa_obj.browse(self.cr, self.uid, pa_ids):

            diff = pa_obj.get_net_difference(self.cr, self.uid, amendment.id)
            allowance_amount = 0
            deduction_amount = 0
            tmp_allowances = diff['new']['allowances'] - diff['old']['allowances']
            tmp_deductions = diff['new']['deductions'] - diff['old']['deductions']
            tmp_net = diff['new']['net'] - diff['old']['net']
            tmp_fit = diff['new']['fit'] - diff['old']['fit']
            if tmp_fit < 0:
                tmp_fit = 0
            if tmp_allowances > 0:
                allowance_amount += tmp_allowances
            elif tmp_allowances < 0:
                deduction_amount += abs(tmp_allowances)
            if tmp_deductions > 0:
                deduction_amount += tmp_deductions
            elif tmp_deductions < 0:
                allowance_amount += abs(tmp_deductions)
            tmp = {
                'name': amendment.employee_id.name,
                'id_no': amendment.employee_id.legacy_no,
                'allowance': tmp_allowances,
                'deduction': tmp_deductions,
                'net': tmp_net,
                'fit': tmp_fit,
                'denominations': ['', '', '', '', ''],
            }

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

            self.earnings += tmp_allowances
            self.tot_earnings += tmp_allowances
            self.deductions += tmp_deductions
            self.tot_deductions += tmp_deductions
            self.fit += tmp_fit
            self.tot_fit += tmp_fit
            if tmp_net > 0:
                self.net += tmp_net
                self.tot_net += tmp_net

            res.append(tmp)

        return res

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

    def get_net(self):
        return self.fmt_float(self.net, 2)

    def get_tot_net(self):
        return self.fmt_float(self.tot_net, 2)

    def get_fit(self):
        return self.fmt_float(self.fit, 2)

    def get_tot_fit(self):
        return self.fmt_float(self.tot_fit, 2)

    def get_earnings(self):
        return self.fmt_float(self.earnings, 2)

    def get_tot_earnings(self):
        return self.fmt_float(self.tot_earnings, 2)

    def get_deductions(self):
        return self.fmt_float(self.deductions, 2)

    def get_tot_deductions(self):
        return self.fmt_float(self.tot_deductions, 2)

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
