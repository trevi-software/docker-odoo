#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013,2014 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

import math

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

from openerp import netsvc
from openerp.addons import decimal_precision as dp
from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.translate import _

class benefit(osv.Model):
    
    _name = 'hr.benefit'
    _description = 'Employee Benefit'
    
    _columns = {
        'name': fields.char('Name', size=256, required=True),
        'code': fields.char('Code', size=32, required=True),
        'has_premium': fields.boolean('Has Premium'),
        'premium_ids': fields.one2many('hr.benefit.premium', 'benefit_id', string="Premiums"),
        'has_advantage': fields.boolean('Has Advantage'),
        'advantage_ids': fields.one2many('hr.benefit.advantage', 'benefit_id', string="Advantages"),
        'link2payroll': fields.boolean('Link to Payroll'),
        'min_employed_days': fields.integer('Minimum Employed Days'),
        'active': fields.boolean('Active'),
        'multi_policy': fields.boolean('Multiple Policies/Employee'),
    }

    _defaults = {
        'active': True,
        'min_employed_days': 0,
    }
    
    def name_get(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        res = []
        data = self.read(cr, uid, ids, ['name', 'code'], context=context)
        for d in data:
            res.append((d['id'], d['name'] +' ['+ d['code'] +']'))
        
        return res
    
    def _get_latest(self, cr, uid, benefit, dToday, ptype, context=None):
        '''Return an advantage with an effective date before dToday but greater than all others'''
        
        if not benefit or not dToday:
            return None
        
        res = None
        line_ids = None
        if ptype == 'advantage':
            line_ids = benefit.advantage_ids
        elif ptype == 'premium':
            line_ids = benefit.premium_ids
        
        for line in line_ids:
            dLine = datetime.strptime(line.effective_date, OE_DFORMAT).date()
            if dLine <= dToday:
                if res == None:
                    res = line
                elif dLine > datetime.strptime(res.effective_date, OE_DFORMAT).date():
                    res = line
        
        return res
    
    def get_latest_advantage(self, cr, uid, benefit, dToday, context=None):
        '''Return an advantage with an effective date before dToday but greater than all others'''
        
        if not benefit or not dToday:
            return None
        
        return self._get_latest(cr, uid, benefit, dToday, 'advantage', context=context)
    
    def get_latest_premium(self, cr, uid, benefit, dToday, context=None):
        '''Return a premium with an effective date before dToday but greater than all others'''
        
        if not benefit or not dToday:
            return None
        
        return self._get_latest(cr, uid, benefit, dToday, 'premium', context=context)

class benefit_premium(osv.Model):
    
    _name = 'hr.benefit.premium'
    _description = 'Employee Benefit Premium Policy Line'
    
    def _get_installments(self, cr, uid, ids, field_name, args, context=None):
        
        res = dict.fromkeys(ids, 0)
        for prm in self.browse(cr, uid, ids, context=context):
            res[prm.id] = (prm.amount > 0 and prm.total_amount > 0) and int(math.ceil(float(prm.total_amount) / float(prm.amount))) or 0
        return res
    
    _columns = {
        'benefit_id': fields.many2one('hr.benefit', 'Benefit'),
        'effective_date': fields.date('Effective Date', required=True),
        'type': fields.selection([
                                  ('monthly', 'Monthly'),
                                  ('annual', 'Annual'),
                                 ], 'Premium Type', required=True),
        'amount': fields.float('Premium Amount', digits_compute=dp.get_precision('Account')),
        'total_amount': fields.float('Total', digits_compute=dp.get_precision('Account')),
        'no_of_installments': fields.function(_get_installments, type='integer', method=True, string="No. of Installments",
                                        store={
                                            'hr.benefit.premium': (lambda s, c,u,ids,ctx: ids, ['amount', 'total_amount'], 10),
                                        }),
        'active': fields.boolean('Active'),
    }
    
    _rec_name = 'effective_date'
    
    _order = 'benefit_id,effective_date desc'
    
    _sql_constraints = [(
                         'unique_date_benefit_id',
                         'UNIQUE(effective_date,benefit_id)',
                         _('Effective dates must be unique per premium in a benefit!')
                        )]
    
    _defaults = {
        'active': True,
        'no_of_installments': 0,
    }

class benefit_advantage(osv.Model):
    
    _name = 'hr.benefit.advantage'
    _description = 'Employee Benefit Policy Advantage Line'
    
    _columns = {
        'benefit_id': fields.many2one('hr.benefit', 'Benefit'),
        'effective_date': fields.date('Effective Date', required=True),
        'min_employed_days': fields.integer('Minimum Employed Days',
                                            help="Number of days of employment before employee is eligible for this advantage."),
        'type': fields.selection([
                                  ('allowance', 'Allowance'),
                                  ('reimburse', 'Expense Re-imbursement'),
                                  ('loan', 'Loan'),
                                 ], 'Advantage Type', required=True),
        'allowance_amount': fields.float('Default Amount', digits_compute=dp.get_precision('Account'),
                                         help="If the allowance is not calculated in the salary rule this is the amount of the allowance"),
        'reim_nolimit': fields.boolean('No Limit'),
        'reim_limit_amount': fields.float('Limit Amount',  digits_compute=dp.get_precision('Account')),
        'reim_limit_period': fields.selection([
                                               ('monthly', 'Monthly'),
                                               ('annual', 'Annual'),
                                              ], 'Limit Period'),
        'reim_period_month_day': fields.selection([
             ('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5'),('6', '6'),('7', '7'),
             ('8', '8'),('9', '9'),('10', '10'),('11', '11'),('12', '12'),('13', '13'),('14', '14'),
             ('15', '15'),('16', '16'),('17', '17'),('18', '18'),('19', '19'),('20', '20'),('21', '21'),
             ('22', '22'),('23', '23'),('24', '24'),('25', '25'),('26', '26'),('27', '27'),('28', '28'),
             ('29', '29'),('30', '30'),('31', '31'),
            ],
            'First Day of Cycle'),
        'reim_period_annual_month': fields.selection([('1', 'January'), ('2', 'February'),
                                                    ('3', 'March'), ('4', 'April'),
                                                    ('5', 'May'), ('6', 'June'),
                                                    ('7', 'July'), ('8', 'August'),
                                                    ('9', 'September'), ('10', 'October'),
                                                    ('11', 'November'), ('12', 'December'),
                                                   ],
                                                   'Month'),
        'reim_period_annual_day': fields.selection([
             ('1', '1'),('2', '2'),('3', '3'),('4', '4'),('5', '5'),('6', '6'),('7', '7'),
             ('8', '8'),('9', '9'),('10', '10'),('11', '11'),('12', '12'),('13', '13'),('14', '14'),
             ('15', '15'),('16', '16'),('17', '17'),('18', '18'),('19', '19'),('20', '20'),('21', '21'),
             ('22', '22'),('23', '23'),('24', '24'),('25', '25'),('26', '26'),('27', '27'),('28', '28'),
             ('29', '29'),('30', '30'),('31', '31'),
            ],
            'Day of Month'),
        'loan_amount': fields.float('Loan Amount', digits_compute=dp.get_precision('Payroll'),
                                    help="The amount advanced to the employee"),
        'category_ids': fields.many2many('hr.employee.category', 'benefit_advantage_category_rel',
                                         'advantage_id', 'category_id', 'Employee Categories'),
        'job_ids': fields.many2many('hr.job', 'benefit_advantage_job_rel', 'advantage_id', 'job_id',
                                    'Included Job Positions',
                                    help="Applies only to these job positions"),
        'invert_categories': fields.boolean('Exclude Categories',
                                            help="If this is checked invert the sense of the "   \
                                            "match for the categories list. Exclude employees "  \
                                            "in the selected categories."),
        'invert_jobs': fields.boolean('Exclude Jobs',
                                      help="If this is checked invert the sense of the "   \
                                      "match for the jobs list. Exclude employees in "     \
                                      "the selected jobs."),
        'active': fields.boolean('Active'),
    }
    
    _rec_name = 'effective_date'
    
    _order = 'benefit_id,effective_date desc'
    
    _sql_constraints = [(
                         'unique_date_benefit_id',
                         'UNIQUE(effective_date,benefit_id)',
                        _('Effective date must be unique per advantage in a benefit!')
                       )]
    
    _defaults = {
        'active': True,
    }
    
    def _get_claims_in_period(self, cr, uid, employee_id, benefit_id, day, period, pm_day=None,
                              pa_month=None, pa_day=None, context=None):
        
        d = datetime.strptime(day, OE_DFORMAT)
        if period == 'monthly':
            diff = d.day - int(pm_day)
            if diff == 0:
                dStart = d
            elif diff > 0:
                dStart = d + timedelta(days= -(diff))
            else:
                dStart = d + relativedelta(months= -1, days= diff)
            dNextStart = dStart + relativedelta(months= +1)
        elif period == 'annual':
            day_diff = d.day - int(pa_day)
            month_diff = d.month - int(pa_month)
            if month_diff == 0:
                dStart = d
            elif month_diff > 0:
                dStart = d + relativedelta(months= -(month_diff))
            else:
                # month_diff is negative, but: -(-) = +
                dStart = d + relativedelta(months= -(month_diff))
            if day_diff > 0:
                dStart = dStart + timedelta(days= -(day_diff))
            elif day_diff < 0:
                dStart = dStart + relativedelta(months= -1, days= day_diff)
            dNextStart = dStart + relativedelta(years= +1)
        else:
            return 0.00

        claim_obj = self.pool.get('hr.benefit.claim')
        claim_ids = claim_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                               ('benefit_policy_id.benefit_id', '=', benefit_id),
                                               ('benefit_policy_id.start_date', '<', dNextStart.strftime(OE_DFORMAT)),
                                               '|', ('benefit_policy_id.end_date', '=', None),
                                                    ('benefit_policy_id.end_date', '>=', dStart.strftime(OE_DFORMAT)),
                                               ('date', '>=', dStart.strftime(OE_DFORMAT)),
                                               ('date', '<', dNextStart.strftime(OE_DFORMAT)),
                                               ('state', '=', 'approve')],
                                     context=context)
        res = 0.00
        if len(claim_ids) > 0:
            cr.execute("SELECT SUM(amount_approved) FROM hr_benefit_claim " \
                           "WHERE id in %s", (tuple(claim_ids),))
            res = cr.fetchall()[0][0]
        return res
    
    def get_reimburse_remaining(self, cr, uid, ids, employee_id, day, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        res = dict.fromkeys(ids, 0.00)
        fields = ['benefit_id', 'type', 'reim_nolimit', 'reim_limit_amount', 'reim_limit_period',
                  'reim_period_month_day', 'reim_period_annual_month', 'reim_period_annual_day']
        data = self.read(cr, uid, ids, fields, context=context)
        for d in data:
            if d.get('type', False) and d['type'] != 'reimburse':
                continue
            elif d.get('reim_nolimit', False):
                res[d['id']] = None
            elif d.get('reim_limit_period', False):
                limit = d.get('reim_limit_amount')
                claims = self._get_claims_in_period(cr, uid, employee_id, d['benefit_id'][0], day,
                                                    d['reim_limit_period'],
                                                    d['reim_period_month_day'],
                                                    d['reim_period_annual_month'],
                                                    d['reim_period_annual_day'], context=context)
                unclaimed = limit - claims
                res[d['id']] = (unclaimed < 0.01) and 0.00 or unclaimed
        
        return res

class benefit_policy(osv.Model):
    
    _name = 'hr.benefit.policy'
    _description = 'Benefit Enrollment'
    
    def _get_installments(self, cr, uid, ids, field_name, args, context=None):
        
        res = dict.fromkeys(ids, 0)
        for pol in self.browse(cr, uid, ids, context=context):
            res[pol.id] = (pol.premium_amount > 0 and pol.premium_total > 0) and int(math.ceil(float(pol.premium_total) / float(pol.premium_amount))) or 0
        return res
    
    def _get_ids_from_ee(self, cr, uid, employee_ids, context=None):
        
        obj = self.pool.get('hr.employee')
        datas = obj.read(cr, uid, employee_ids, ['department_id'], context=context)
        dept_ids = [d['department_id'][0] for d in datas]
        return dept_ids
    
    _columns = {
        'name': fields.char('Reference', size=32, readonly=True),
        'benefit_id': fields.many2one('hr.benefit', 'Benefit', required=True, readonly=True,
                                      states={'draft': [('readonly', False)]}),
        'benefit_code': fields.char('Benefit Code', size=32, readonly=True,
                                    states={'draft': [('readonly', False)]}),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True, readonly=True,
                                       states={'draft': [('readonly', False)]}),
        'department_id': fields.related('employee_id', 'department_id', type='many2one',
                                        obj='hr.department', string='Department',
                                        store={'hr_employee': (_get_ids_from_ee, ['department_id'], 10)}),
        'start_date': fields.date('Date of Enrollment', required=True, readonly=True,
                                  states={'draft': [('readonly', False)]}),
        'end_date': fields.date('Termination Date'),
        'active': fields.boolean('Active'),
        'advantage_override': fields.boolean('Change Advantage Amount', help="Check this field if the amount of the advantage should be changed in the policy."),
        'premium_override': fields.boolean('Change Premium Amount', help="Check this field if the amount of the premium should be changed in the policy."),
        'advantage_amount': fields.float('Advantage Amount', digits_compute=dp.get_precision('Account')),
        'premium_amount': fields.float('Premium Amount', digits_compute=dp.get_precision('Account')),
        'premium_total': fields.float('Premium Total', digits_compute=dp.get_precision('Account')),
        'premium_payment_ids': fields.one2many('hr.benefit.premium.payment', 'policy_id',
                                               'Premium Payments', readonly=True),
        'premium_installments': fields.function(_get_installments, type='integer', method=True, string="No. of Installments",
                                                store={
                                                       'hr.benefit.policy': (lambda s, c,u,ids,ctx: ids, ['premium_amount', 'premium_total'], 10),
                                                }),
        'note': fields.text('Remarks'),
        'state': fields.selection([('draft', 'Draft'),
                                   ('open', 'Open'),
                                   ('done', 'Done')],
                                  'State', readonly=True),
    }
    
    _defaults = {
        'active': True,
        'state': 'draft',
    }
    
    def name_get(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        res = []
        data = self.read(cr, uid, ids, ['name', 'benefit_id'], context=context)
        for d in data:
            res.append((d['id'], (d['name'] and d['name'] or '') +' '+ d['benefit_id'][1]))
        
        return res
    
    def onchange_benefit(self, cr, uid, ids, benefit_id, start_date, context=None):
        
        res = {'value': {
                 'benefit_code': False,
                 'advantage_amount': 0,
                 'premium_amount': 0,
                 'premium_total': 0,
              }
        }
        if not benefit_id or not start_date:
            return res
        
        benefit_obj = self.pool.get('hr.benefit')
        benefit = benefit_obj.browse(cr, uid, benefit_id, context=context)

        if benefit.code:
            res['value']['benefit_code'] = benefit.code
        
        dToday = datetime.strptime(start_date, OE_DFORMAT).date()
        adv = benefit_obj.get_latest_advantage(cr, uid, benefit, dToday, context=context)
        prm = benefit_obj.get_latest_premium(cr, uid, benefit, dToday, context=context)
        if adv != None:
            if adv.type == 'allowance':
                res['value']['advantage_amount'] = adv.allowance_amount
        if prm != None:
            res['value']['premium_amount'] = prm.amount
            res['value']['premium_total'] = prm.total_amount
        
        return res
    
    def onchange_start(self, cr, uid, ids, start_date, benefit_id, premium_total, context=None):
        
        res = {}
        if not start_date:
            return res
        
        if benefit_id:
            res = self.onchange_benefit(cr, uid, ids, benefit_id, start_date, context=context)

        if premium_total:
            res.update(self.onchange_premium_total(cr, uid, start_date, premium_total, context=context))
        else:
            res.update({'end_date': False})

        return res
    
    def onchange_premium_total(self, cr, uid, ids, start_date, premium_amount, premium_total, context=None):
        
        res = {'value': {'end_date': False, 'premium_installments': 0}}
        if not start_date or not premium_amount or premium_amount < 0:
            return res
        
        installments = int(math.ceil(float(premium_total) / float(premium_amount)))
        dStart = datetime.strptime(start_date, OE_DFORMAT).date()
        dEnd = dStart + relativedelta(months= +installments)
        res['value']['end_date'] = dEnd.strftime(OE_DFORMAT)
        res['value']['premium_installments'] = installments
        return res
    
    def _fail_elegibility(self, cr, uid, benefit_id, employee_id, context=None):
        
        res = False
        benefit = self.pool.get('hr.benefit').browse(cr, uid, benefit_id, context=context)
        
        # Check if employee has worked more than minimum number of days for benefit
        #
        if benefit.min_employed_days > 0:
            ee_obj = self.pool.get('hr.employee')
            dToday = datetime.today().date()
            srvc_months, dHire = ee_obj.get_months_service_to_date(cr, uid, [employee_id], dToday=dToday,
                                                                   context=context)[employee_id]
            srvc_months = int(srvc_months)
            
            employed_days = 0
            dCount = dHire
            while dCount < dToday:
                employed_days += 1
                dCount += timedelta(days= +1)
            if benefit.min_employed_days > employed_days:
                res = True
        
        return res
    
    def create(self, cr, uid, vals, context=None):
        
        # Check if the employee is already enrolled
        #
        benefit = self.pool.get('hr.benefit').browse(cr, uid, vals['benefit_id'], context=context)
        if not benefit.multi_policy:
            domain = [('employee_id', '=', vals['employee_id']),
                      ('benefit_id', '=', vals['benefit_id']),
            ]
            if vals['start_date'] and not vals.get('end_date', False):
                domain = domain + ['|', ('end_date', '=', False),
                                        ('end_date', '>=', vals['start_date'])]
            elif vals['start_date'] and vals['end_date']:
                domain = domain + [('start_date', '<=', vals['end_date']),
                                   '|', ('end_date', '=', False),
                                        ('end_date', '>=', vals['start_date'])]
            
            policy_ids = self.search(cr, uid, domain, context=context)
            if len(policy_ids) > 0:
                pol_data = self.read(cr, uid, policy_ids[0], ['name'], context=context)
                raise osv.except_osv(_('Error'),
                                     _('The employee is already enrolled in this benefit program.\nPolicy: %s') % (pol_data['name']))
        
        # Check if elegibility requirements have been met
        if self._fail_elegibility(cr, uid, vals['benefit_id'], vals['employee_id'], context=context):
            raise osv.except_osv(_('Elegibility Requirements Unmet'),
                                 _('The employee does not meet elegibility requirements for this benefit.'))
        
        ben_id = super(benefit_policy, self).create(cr, uid, vals, context)
        if ben_id:
            ref = self.pool.get('ir.sequence').next_by_code(cr, uid, 'benefit.policy.ref', context=context)
            if not ref:
                raise osv.except_osv(_('Critical Error'), _('Unable to obtain a benefit policy number!'))
            self.pool.get('hr.benefit.policy').write(cr, uid, ben_id, {'name': ref}, context=context)
        return ben_id
    
    def unlink(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        for pol in self.browse(cr, uid, ids, context=context):
            if pol.state != 'draft' and not (context and context.get('force_delete', False)):
                raise osv.except_osv(_('Invalid State'),
                                     _('You may not delete a policy that is not in a "draft" state.' \
                                       '\nPolicy No: %s' %(pol.name)))
        
        return super(benefit_policy, self).unlink(cr, uid, ids, context=context)
    
    def state_open(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        self.write(cr, uid, ids, {'state': 'open'}, context=context)
        return True
    
    def state_done(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        return True
    
    def end_policy(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        if len(ids) == 0:
            return False
        
        context.update({'end_benefit_policy_id': ids[0]})
        return {
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'hr.benefit.policy.end',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': context
        }
    
    def calculate_advantage(self, cr, uid, policy, dS, dE, annual_pay_periods, context=None):
        
        adv_amount = 0
        adv = self.pool.get('hr.benefit').get_latest_advantage(cr, uid, policy.benefit_id, dE,
                                                               context=context)
        if policy.advantage_override:
            adv_amount = policy.advantage_amount
        elif adv:
            if adv.type == 'allowance':
                adv_amount = adv.allowance_amount
            elif adv.type == 'loan':
                adv_amount = adv.loan_amount
        return adv_amount
    
    def _get_paid_amount(self, policy):
        
        res = 0
        for payment in policy.premium_payment_ids:
            if payment.state not in ['draft', 'cancel']:
                res += payment.amount
        return res
    
    def calculate_premium(self, cr, uid, policy, dS, dE, annual_pay_periods, refund=False, context=None):
        
        prm_amount = 0
        prm = self.pool.get('hr.benefit').get_latest_premium(cr, uid, policy.benefit_id, dE,
                                                             context=context)
        paid = self._get_paid_amount(policy)
        if policy.premium_override:
            # If this is a refund just use the premium amount specified in the policy.
            # Otherwise, try and calculate the amount of the remaining payments.
            #
            # XXX - In the case where we're refunding the last payment and it was
            #       less than the normal premium payment this will return the wrong
            #       answer. Not sure what to do about that. Maybe just return amount
            #       of the last payment ?
            #
            is_installments = (policy.premium_installments > 0)
            total = policy.premium_amount * (is_installments and float(policy.premium_installments) or 1.0)
            prm_amount = policy.premium_amount
            if not refund:
                prm_amount = (total - paid) > prm_amount and prm_amount or (total - paid)
                if prm_amount < 0: prm_amount = 0
        elif prm:
            is_installments = (prm.no_of_installments > 0)
            total = prm.amount * (is_installments and float(prm.no_of_installments) or 1.0)
            if not refund:
                if prm.type == 'annual':
                    prm_amount = prm.amount / float(annual_pay_periods)
                else:
                    prm_amount = prm.amount / float(annual_pay_periods / 12)
                if (total - paid) < prm_amount:
                    prm_amount = (total - paid) > 0 and (total - paid) or 0
        return prm_amount

class benefit_claim(osv.Model):
    
    _name = 'hr.benefit.claim'
    
    _columns = {
        'date': fields.date('Date', required=True, readonly=True, states={'draft': [('readonly', False)]},
                            help="The date the claim was made"),
        'benefit_policy_id': fields.many2one('hr.benefit.policy', 'Policy', required=True,
                                             readonly=True, states={'draft': [('readonly', False)]}),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True, readonly=True,
                                       states={'draft': [('readonly', False)]}),
        'amount_requested': fields.float('Requested Amount', digits_compute=dp.get_precision('Account'),
                                         required=True, readonly=True,
                                         states={'draft': [('readonly', False)]}),
        'amount_approved': fields.float('Approved Amount', digits_compute=dp.get_precision('Account'),
                                        readonly=True),
        'state': fields.selection([('draft', 'Draft'),
                                   ('approve', 'Approved'),
                                   ('decline', 'Declined')], 'State', readonly=True),
    }
    
    _rec_name = 'date'
    
    _defaults = {
        'date': datetime.now().strftime(OE_DFORMAT),
        'state': 'draft',
    }
    
    def name_get(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        res = []
        data = self.read(cr, uid, ids, ['date', 'benefit_policy_id'], context=context)
        for d in data:
            res.append((d['id'], d['benefit_policy_id'][1] +' '+ d['date']))
        
        return res

    def onchange_employee(self, cr, uid, ids, employee_id, context=None):
        
        res = {'domain': {'benefit_policy_id': False}}
        if not employee_id:
            return res
        
        res['domain']['benefit_policy_id'] = [
                                              ('employee_id', '=', employee_id),
                                              ('benefit_id.has_advantage', '=', True),
                                             ]
        return res
    
    def _get_approved_amount(self, cr, uid, employee_id, req, policy_id, date_str, context=None):
        
        benefit_obj = self.pool.get('hr.benefit')
        adv_obj = self.pool.get('hr.benefit.advantage')
        approved = 0.00
        if employee_id and policy_id and req and date_str:
            benefit_id = self.pool.get('hr.benefit.policy').read(cr, uid, policy_id, ['benefit_id'],
                                                             context=context)['benefit_id'][0]
            
            benefit = benefit_obj.browse(cr, uid, benefit_id, context=context)
            d = datetime.strptime(date_str, OE_DFORMAT).date()
            adv_line = benefit_obj.get_latest_advantage(cr, uid, benefit, d, context=context)
            if adv_line:
                remaining = adv_obj.get_reimburse_remaining(cr, uid, adv_line.id, employee_id,
                                                                 date_str)
                if remaining[adv_line.id] == None:
                    # No limit
                    approved = req
                elif remaining[adv_line.id] < 0.01:
                    # Over Limit
                    approved = 0.00
                else:
                    approved = (remaining[adv_line.id] - req) < 0.01 and remaining[adv_line.id] or req
            
        return approved
    
    def create(self, cr, uid, vals, context=None):
        
        approved = self._get_approved_amount(cr, uid, vals.get('employee_id', False),
                                             vals.get('amount_requested', False),
                                             vals.get('benefit_policy_id', False),
                                             vals['date'], context)
        vals.update({'amount_approved': approved})
            
        return super(benefit_claim, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid, ids, vals, context=None):
        
        fields = ['date', 'employee_id', 'amount_requested', 'benefit_policy_id']
        do_calc = False
        for k in vals.iterkeys():
            if k in fields:
                do_calc = True
                break
        
        if not do_calc:
            return super(benefit_claim, self).write(cr, uid, ids, vals, context=context)
        
        # Set values to be used in approval amount calculation
        if 'date' in vals:
            date_str = vals['date']
        else:
            date_str = False
        if 'employee_id' in vals:
            employee_id = vals['employee_id']
        else:
            employee_id = False
        if 'amount_requested' in vals:
            req = vals['amount_requested']
        else:
            req = False
        if 'benefit_policy_id' in vals:
            policy_id = vals['benefit_policy_id']
        else:
            policy_id = False
        
        for claim in self.browse(cr, uid, ids, context=context):
            if not date_str:
                date_str = claim.date
            if not employee_id:
                employee_id = claim.employee_id.id
            if not req:
                req = claim.amount_requested
            if not policy_id:
                policy_id = claim.benefit_policy_id.id
            approved = self._get_approved_amount(cr, uid, employee_id, req, policy_id,
                                                 date_str, context)
            vals.update({'amount_approved': approved})
            res = super(benefit_claim, self).write(cr, uid, claim.id, vals, context=context)
        
        return res
    
    def unlink(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        data = self.read(cr, uid, ids, ['state'], context=context)
        for d in data:
            if d['state'] in ['approve', 'decline'] and not (context and context.get('force_delete', False)):
                raise osv.except_osv(_('Error'),
                                    _('You may not a delete a claim that is not in a "Draft" state'))
        return super(benefit_claim, self).unlink(cr, uid, ids, context=context)
    
    def set_to_draft(self, cr, uid, ids, context=None):
        self.write(cr, uid, ids, {
            'state': 'draft',
        })
        wf_service = netsvc.LocalService("workflow")
        for i in ids:
            wf_service.trg_delete(uid, 'hr.benefit.claim', i, cr)
            wf_service.trg_create(uid, 'hr.benefit.claim', i, cr)
        return True
    
    def claim_approve(self, cr, uid, ids, context=None):
        
        self.write(cr, uid, ids, {'state': 'approve'}, context=context)
        return True
    
    def claim_decline(self, cr, uid, ids, context=None):
        
        self.write(cr, uid, ids, {'state': 'decline'}, context=context)
        return True

class premium_payment(osv.Model):
    
    _name = 'hr.benefit.premium.payment'
    
    _columns = {
        'date': fields.date('Date', required=True),
        'policy_id': fields.many2one('hr.benefit.policy', 'Policy', required=True,
                                     readonly=True, states={'draft': [('readonly', False)]}),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True, readonly=True,
                                       states={'draft': [('readonly', False)]}),
        'amount': fields.float('Amount', digits_compute=dp.get_precision('Account'), required=True,
                               readonly=True, states={'draft': [('readonly', False)]}),
        'payslip_id': fields.many2one('hr.payslip', 'Payslip', ondelete='cascade'),
        'state': fields.selection([('draft', 'Draft'),
                                   ('pending', 'Pending'),
                                   ('cancel', 'Cancelled'),
                                   ('done', 'Done')], 'State', readonly=True),
    }

    _rec_name = 'date'

    _defaults = {
        'date': datetime.now().strftime(OE_DFORMAT),
        'state': 'draft',
    }

    def name_get(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        res = []
        data = self.read(cr, uid, ids, ['date', 'policy_id'], context=context)
        for d in data:
            res.append((d['id'], d['policy_id'][1] +' '+ d['date']))
        
        return res

    def onchange_employee(self, cr, uid, ids, employee_id, context=None):
        
        res = {'domain': {'policy_id': False}}
        if not employee_id:
            return res
        
        res['domain']['policy_id'] = [
                                      ('employee_id', '=', employee_id),
                                      ('benefit_id.has_premium', '=', True),
                                     ]
        return res

    def unlink(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        for payment in self.browse(cr, uid, ids, context=context):
            if payment.state != 'draft' and not (context and context.get('force_delete', False)):
                raise osv.except_osv(_('Permission Denied'),
                                     _('You may not delete a premium payment that is past the "draft" stage.' \
                                       '\nPolicy: %s\nPayment Date: %s') %(payment.policy_id.name, payment.date))

        return super(premium_payment, self).unlink(cr, uid, ids, context=context)
    
    def state_pending(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        return self.write(cr, uid, ids, {'state': 'pending'}, context=context)

    def state_done(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        return self.write(cr, uid, ids, {'state': 'done'}, context=context)

    def state_cancel(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        return self.write(cr, uid, ids, {'state': 'cancel'}, context=context)

class hr_employee(osv.Model):
    
    _inherit = 'hr.employee'
    
    _columns = {
        'benefit_policy_ids': fields.one2many('hr.benefit.policy', 'employee_id', string='Benefits')
    }

class hr_payslip(osv.Model):
    
    _inherit = 'hr.payslip'
    
    _columns = {
        'premium_payment_ids': fields.one2many('hr.benefit.premium.payment', 'payslip_id',
                                               'Benefit Premium Payments'),
    }
    
    def get_benefits_dict(self, cr, uid, contract, payslip, context=None):
        
        res = super(hr_payslip, self).get_benefits_dict(cr, uid, contract, payslip, context=context)

        if not payslip:
            return res
        
        policy_obj = self.pool.get('hr.benefit.policy')
        benefit_obj = self.pool.get('hr.benefit')

        # Create records for all active benefits
        benefit_ids = benefit_obj.search(cr, uid, [('link2payroll', '=', True), ('active', '=', True)],
                                         context=context)
        bdata = benefit_obj.read(cr, uid, benefit_ids, ['code'], context=context)
        for bd in bdata:
            res.update({
                bd['code']: {
                   'qty': 0,
                   'ppf': 0,
                   'advantage_amount': 0,
                   'premium_amount': 0,
               }
            })

        # Search policies for this employee that are linked to payroll
        policy_ids = policy_obj.search(cr, uid, [('employee_id', '=', contract.employee_id.id),
                                                 ('benefit_id.link2payroll', '=', True),
                                                 ('start_date', '<=', payslip.date_to),
                                                 '|', ('end_date', '=', False),
                                                      ('end_date', '>=', payslip.date_from),
                                                ], context=context)
        
        # One dict per benefit
        #
        dSlipStart = datetime.strptime(payslip.date_from, OE_DFORMAT).date()
        dSlipEnd = datetime.strptime(payslip.date_to, OE_DFORMAT).date()
        d = dSlipStart
        deltaSlip = 0
        while d < dSlipEnd:
            deltaSlip += 1
            d += timedelta(days= +1)
        
        for policy in policy_obj.browse(cr, uid, policy_ids, context=context):
            
            # Calculate partial period factor relative to the policy
            dPolStart = datetime.strptime(policy.start_date, OE_DFORMAT).date()
            dPolEnd = dSlipEnd
            if policy.end_date != False:
                dPolEnd = datetime.strptime(policy.end_date, OE_DFORMAT).date()
            dS = (dPolStart > dSlipStart) and dPolStart or dSlipStart
            dE = (dPolEnd < dSlipEnd) and dPolEnd or dSlipEnd
            
            if (dPolEnd <= dSlipStart) or (dPolStart >= dSlipEnd):
                continue
            
            d = dS
            deltaPol = 0
            while d < dE:
                deltaPol += 1
                d += timedelta(days= +1)
            
            # Calculate advantage
            #
            adv_amount = policy_obj.calculate_advantage(cr, uid, policy, dS, dE,
                                                        contract.pps_id.annual_pay_periods,
                                                        context=context)

            # Calculate premium
            #
            prm_amount = policy_obj.calculate_premium(cr, uid, policy, dS, dE,
                                                      contract.pps_id.annual_pay_periods,
                                                      refund=payslip.credit_note and True or False,
                                                      context=context)

            res[policy.benefit_id.code]['qty'] += 1
            res[policy.benefit_id.code]['ppf'] += float(deltaPol) / float(deltaSlip)
            res[policy.benefit_id.code]['advantage_amount'] += adv_amount
            res[policy.benefit_id.code]['premium_amount'] += prm_amount

        return res

    def record_benefit_premium_payments(self, cr, uid, payslip, benefits, context=None):
        
        policy_obj = self.pool.get('hr.benefit.policy')
        premium_obj = self.pool.get('hr.benefit.premium.payment')
        for k, v in benefits.items():
            pol_ids = policy_obj.search(cr, uid, [('employee_id', '=', payslip.employee_id.id),
                                                  ('benefit_id', '=', v['id'])],
                                        context=context)
            if len(pol_ids) == 0:
                osv.except_osv(_('Error creating benefit premium payment records!'),
                               _('Unable to find a valid benefit policy:\nEmployee: %s\nBenefit: %s') %(payslip.employee_id.name, k))
            
            premium_obj.create(cr, uid, {'payslip_id': payslip.id,
                                         'date': payslip.date_to,
                                         'employee_id': payslip.employee_id.id,
                                         'policy_id': pol_ids[0],
                                         'amount': payslip.credit_note and -v['amount'] or v['amount'],
                                         },
                               context=context)
        return

    def remove_benefit_premium_payments(self, cr, uid, payslip_ids, context=None):
        
        if isinstance(payslip_ids, (int, long)):
            payslip_ids = [payslip_ids]
        
        pay_obj = self.pool.get('hr.benefit.premium.payment')
        pay_ids = pay_obj.search(cr, uid, [('payslip_id', 'in', payslip_ids)], context=context)
        if len(pay_ids) > 0:
            pay_obj.unlink(cr, uid, pay_ids, context=context)
        
        return

    def finalize_benefit_premium_payments(self, cr, uid, payslip_ids, context=None):
        
        if isinstance(payslip_ids, (int, long)):
            payslip_ids = [payslip_ids]
        
        wkf = netsvc.LocalService('workflow')
        pay_obj = self.pool.get('hr.benefit.premium.payment')
        pay_ids = pay_obj.search(cr, uid, [('payslip_id', 'in', payslip_ids)], context=context)
        for pay_id in pay_ids:
            wkf.trg_validate(uid, 'hr.benefit.premium.payment', pay_id, 'signal_pending', cr)
            wkf.trg_validate(uid, 'hr.benefit.premium.payment', pay_id, 'signal_done', cr)
        
        return

#    def refund_sheet(self, cr, uid, ids, context=None):
#        
#        if isinstance(ids, (int, long)):
#            ids = [ids]
#        
#        pay_obj = self.pool.get('hr.benefit.premium.payment')
#        wkf = netsvc.LocalService('workflow')
#        pay_ids = pay_obj.search(cr, uid, [('payslip_id', 'in', ids)], context=context)
#        for pay_id in pay_ids:
#            wkf.trg_validate(uid, 'hr.benefit.premium.payment', pay_id, 'signal_cancel', cr)
#        
#        res = super(hr_payslip, self).refund_sheet(cr, uid, ids, context=context)
#        
#        return res

class hr_salary_rule(osv.Model):
    
    _inherit = 'hr.salary.rule'
    
    _columns = {
        'benefit_id': fields.many2one('hr.benefit', 'Benefit'),
    }
