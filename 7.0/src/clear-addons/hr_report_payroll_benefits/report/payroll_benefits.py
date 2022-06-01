#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013,2014 Michael Telahun Makonnen <mmakonnen@gmail.com>
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
            'fmt_float': self.fmt_float,
            'get_total': self.get_total,
            'get_tot_total': self.get_tot_total,
            'get_premium': self.get_premium,
            'get_tot_premium': self.get_tot_premium,
            'get_paid': self.get_paid,
            'get_tot_paid': self.get_tot_paid,
            'get_unposted': self.get_unposted,
            'get_tot_unposted': self.get_tot_unposted,
            'get_remaining': self.get_remaining,
            'get_tot_remaining': self.get_tot_remaining,
            'get_details_by_payslip': self.get_details_by_payslip,
        })
        
        self.no = 0
        self.saved_run_id = -1
        self.benefit_ids = []
        
        self.total = 0
        self.premium = 0
        self.paid = 0
        self.unposted = 0
        self.remaining = 0

        self.tot_total = 0
        self.tot_premium = 0
        self.tot_paid = 0
        self.tot_unposted = 0
        self.tot_remaining = 0
    
    def set_context(self, objects, data, ids, report_type=None):
        if data.get('form', False) and data['form'].get('benefit_ids', False):
            self.benefit_ids += data['form']['benefit_ids']
        else:
            # Get only loan type benefits
            adv_obj = self.pool.get('hr.benefit.advantage')
            adv_ids = adv_obj.search(self.cr, self.uid, [('type', '=', 'loan')])
            if len(adv_ids) > 0:
                adv_datas = adv_obj.read(self.cr, self.uid, adv_ids, ['benefit_id'])
                self.benefit_ids += [d['benefit_id'][0] for d in adv_datas]
        
        return super(Parser, self).set_context(objects, data, ids, report_type=report_type)

    def _reset_values(self, run_id):
        
        self.no = 0
        self.saved_run_id = run_id
        
        self.total = 0
        self.paid = 0
        self.unposted = 0
        self.remaining = 0

    def fmt_float(self, f):
        
        return "%.2f" % f
    
    def get_details_by_payslip(self, payslips):
        
        res = []
        for slip in payslips:
            if self.saved_run_id == -1:
                self.saved_run_id = slip.payslip_run_id.id
            elif self.saved_run_id != slip.payslip_run_id.id:
                self._reset_values(slip.payslip_run_id.id)
                
            tmp = self.get_benefit_details(slip)
            if len(tmp) > 0:
                res.append(tmp)
        return res
    
    def get_benefit_details(self, slip):
        
        ben_obj = self.pool.get('hr.benefit')
        
        pols = []
        for pol in slip.employee_id.benefit_policy_ids:
            if pol.benefit_id.has_premium and pol.benefit_id.show_on_payroll_report:
                if pol.start_date <= slip.date_to \
                  and (not pol.end_date or pol.end_date >= slip.date_from):
                    pols.append(pol)
        
        if len(pols) == 0:
            return []
        
        res = {
            'id_no': slip.employee_id.f_employee_no,
            'name': slip.employee_id.name,
            'benefits': [],
        }
        
        pol_obj = self.pool.get('hr.benefit.policy')
        for pol in pols:
            
            dFrom = datetime.strptime(slip.date_from, OE_DFORMAT).date()
            dTo = datetime.strptime(slip.date_to, OE_DFORMAT).date()
            premium = ben_obj.get_latest_premium(self.cr, self.uid, pol.benefit_id, dTo)
            curr_prem = pol_obj.calculate_premium(self.cr, self.uid, pol, dFrom, dTo, 12)

            ppaid = 0
            upaid = 0
            for payment in pol.premium_payment_ids:
                if payment.state not in ['draft', 'cancel']:
                    ppaid += payment.amount
                elif payment.state in ['draft']:
                    upaid += payment.amount
            
            ben = {
                'benefit': pol.benefit_id.name,
                'policy': pol.name,
                'total_amount': pol.premium_total,
                'premium': curr_prem,
                'installments': pol.premium_installments,
                'paid_posted': ppaid,
                'paid_unposted': upaid,
                'remaining': pol.premium_total - ppaid,
            }
            res['benefits'] += [ben]
            
            # Update Sub-totals and Totals
            self.total += ben['total_amount']
            self.tot_total += ben['total_amount']
            self.premium += curr_prem
            self.tot_premium += curr_prem
            self.paid += ppaid
            self.tot_paid += ppaid
            self.unposted += upaid
            self.tot_unposted += upaid
            self.remaining += ben['remaining']
            self.tot_remaining += ben['remaining']
        
        return res
    
    def get_total(self):
        return self.total
    
    def get_tot_total(self):
        return self.tot_total
    
    def get_premium(self):
        return self.premium
    
    def get_tot_premium(self):
        return self.tot_premium
    
    def get_paid(self):
        return self.paid
    
    def get_tot_paid(self):
        return self.tot_paid

    def get_unposted(self):
        return self.unposted

    def get_tot_unposted(self):
        return self.tot_unposted

    def get_remaining(self):
        return self.remaining

    def get_tot_remaining(self):
        return self.tot_remaining

    def get_no(self):
        self.no += 1
        return self.no
