#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

from datetime import datetime
from pytz import timezone, utc

from openerp import netsvc
from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools.translate import _

class hr_payslip(orm.Model):

    _inherit = 'hr.payslip'

    _columns = {
        'amended_payslip_id': fields.many2one('hr.payslip', 'Amended Payslip'),
        'original_payslip_run_id': fields.many2one('hr.payslip.run', 'Original Pay Slip Batch'),
    }

class hr_postclose_amendment(orm.Model):

    _name = 'hr.payroll.postclose.amendment'
    _description = 'Post Payroll Period Closing Payslip Amendment'

    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True, readonly=True,
                                       states={'draft': [('readonly', False)]}),
        'user_id': fields.many2one('res.users', 'Responsible', readonly=True),
        'date': fields.date('Date', required=True, readonly=True),
        'pp_id': fields.many2one('hr.payroll.period', 'Payroll Period', readonly=True,
                                 states={'draft': [('readonly', False)]}, required=True),
        'next_pp_id': fields.many2one('hr.payroll.period', 'Destination Payroll Period',
                                      required=False, readonly=False, states={'done': [('readonly', True)]}),
        'old_payslip_id': fields.many2one('hr.payslip', 'Original Payslip', readonly=True,
                                          states={'draft': [('readonly', False)]}),
        'new_payslip_id': fields.many2one('hr.payslip', 'Amended Payslip', readonly=True,
                                          states={'draft': [('readonly', False)]}),
        'payslip_amendment_ids': fields.many2many('hr.payslip.amendment', 'payroll_and_payslip_amendments_rel',
                                                  'payslip_amendment_id', 'payroll_amendment_id',
                                                  string='Payslip Amendments',
                                                  readonly=True, states={'draft': [('readonly', False)]}),
        'memo': fields.text('Notes'),
        'state': fields.selection([('draft', 'New'), ('open', 'In Progress'), ('done', 'Done')],
                                  'State', readonly=True),
    }

    def name_get(self, cr, uid, ids, context=None):

        if isinstance(ids, (int, long)):
            ids = [ids]

        res = []
        datas = self.read(cr, uid, ids, ['employee_id', 'pp_id'], context=context)
        for d in datas:
            res.append((d['id'], d['employee_id'][1] +' ['+ d['pp_id'][1] +']'))
        return res

    def _get_old_payslip(self, cr, uid, context=None):

        if context == None:
            context = {}

        if context.get('active_id', False):
            return context['active_id']
        elif context.get('active_ids', False):
            return context['active_ids'][0]

        return False

    def _get_employee(self, cr, uid, context=None):

        res = False
        ps_id = self._get_old_payslip(cr, uid, context=context)
        if ps_id:
            data = self.pool.get('hr.payslip').read(cr, uid, ps_id, ['employee_id'], context=context)
            if data.get('employee_id', False):
                res = data['employee_id'][0]
        return res

    def _ps2pp(self, cr, uid, ps_id, context=None):

        res = False
        if ps_id:
            ps_obj = self.pool.get('hr.payslip')
            ps = ps_obj.browse(cr, uid, ps_id, context=context)
            pp_obj = self.pool.get('hr.payroll.period')
            pp_ids = pp_obj.search(cr, uid, [('register_id', '=', ps.payslip_run_id.register_id.id)])
            if len(pp_ids) > 0:
                res = pp_ids[0]
        return res

    def _get_period(self, cr, uid, context=None):

        payslip_id = self._get_old_payslip(cr, uid, context=context)
        return self._ps2pp(cr, uid, payslip_id, context=context)

    _defaults = {
        'date': datetime.now().strftime(OE_DFORMAT),
        'user_id': lambda s, cr, uid, ctx: uid,
        'old_payslip_id': _get_old_payslip,
        'employee_id': _get_employee,
        'pp_id': _get_period,
        'state': 'draft',
    }

    def onchange_employee(self, cr, uid, ids, employee_id, context=None):

        res = {'domain': {'old_payslip_id': False}}
        if employee_id:
            res['domain']['old_payslip_id'] = [('employee_id', '=', employee_id)]
        return res

    def onchange_payslip(self, cr, uid, ids, ps_id, context=None):

        res = {'value': {'pp_id': self._ps2pp(cr, uid, ps_id, context=context)}}
        return res

    def unlink(self, cr, uid, ids, context=None):

        if isinstance(ids, (long, int)):
            ids = [ids]

        ps_ids = []
        psam_ids = []
        datas = self.read(cr, uid, ids, ['new_payslip_id', 'payslip_amendment_ids'])
        for d in datas:
            if d.get('new_payslip_id', False):
                ps_ids.append(d['new_payslip_id'][0])
            if d.get('payslip_amendment_ids', False):
                psam_ids += d['payslip_amendment_ids']

        self.pool.get('hr.payslip.amendment').unlink(cr, uid, psam_ids, context=context)
        self.pool.get('hr.payslip').unlink(cr, uid, ps_ids, context=context)

        return super(hr_postclose_amendment, self).unlink(cr, uid, ids, context=context)

    def state_open(self, cr, uid, ids, context=None):

        self.write(cr, uid, ids, {'state': 'open'}, context=context)
        return True

    def state_done(self, cr, uid, ids, context=None):

        wkf = netsvc.LocalService('workflow')
        for pca in self.browse(cr, uid, ids, context=context):
            self.relock_period(cr, uid, pca.id, context=context)
            for psa in pca.payslip_amendment_ids:
                wkf.trg_validate(uid, 'hr.payslip.amendment', psa.id, 'validate', cr)
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        return True

    def unlock_period(self, cr, uid, ids, context=None):

        if isinstance(ids, (long, int)):
            ids = [ids]

        me = self.browse(cr, uid, ids[0], context=context)
        self.pool.get('hr.payroll.period').unlock_period(cr, uid, [me.pp_id], [me.employee_id.id],
                                                         context=context)

        return

    def relock_period(self, cr, uid, ids, context=None):

        if isinstance(ids, (long, int)):
            ids = [ids]

        me = self.browse(cr, uid, ids[0], context=context)
        self.pool.get('hr.payroll.period').lock_period(cr, uid, [me.pp_id], [me.employee_id.id],
                                                       context=context)

        return

    def _get_confirmed_amendments(self, cr, uid, period_id, context=None):

        psa_ids = self.pool.get('hr.payslip.amendment').search(cr, uid,
                                                               [('pay_period_id', '=', period_id),
                                                                ('state', 'in', ['validate'])],
                                                               context=context)
        return psa_ids

    def create_amended_payslip(self, cr, uid, ids, context=None):

        if isinstance(ids, (long, int)):
            ids = [ids]

        pp_obj = self.pool.get('hr.payroll.period')
        me = self.browse(cr, uid, ids[0], context=context)

        # DateTime in db is stored as naive UTC. Convert it to explicit UTC and then convert
        # that into the time zone of the pay period schedule.
        #
        local_tz = timezone(me.pp_id.schedule_id.tz)
        utcDtStart, utcDtEnd = pp_obj.get_utc_times(cr, uid, me.pp_id, context=context)
        loclDTStart = utcDtStart.astimezone(local_tz)
        loclDTEnd = utcDtEnd.astimezone(local_tz)

        # Get Pay Slip Amendments, Employee ID, and the amount of the amendment
        #
        psa_codes = []
        ps_obj = self.pool.get('hr.payslip')
        psa_obj = self.pool.get('hr.payslip.amendment')
        psa_ids = psa_obj.search(cr, uid, [('pay_period_id', '=', me.pp_id.id),
                                           ('employee_id', '=', me.employee_id.id),
                                           ('state', 'in', ['validate'])],
                                 context=context)
        for psa in psa_obj.browse(cr, uid, psa_ids, context=context):
            psa_codes.append((psa.employee_id.id, psa.input_id.code, psa.amount))

        # Get the pay slip run that this amendment belongs to
        old_payslip_run_id = me.old_payslip_id and me.old_payslip_id.payslip_run_id.id or False
        if not old_payslip_run_id:
            for run in me.pp_id.register_id.run_ids:
                for dept in run.department_ids:
                    if dept.id == me.employee_id.department_id.id:
                        old_payslip_run_id = run.id
                        break
        if not old_payslip_run_id:
            raise orm.except_orm(_("Run-time Error"),
                                 _("The employee's department is not in the payroll register!"))

        # Create new payslip
        #
        slip_id = pp_obj.create_payslip(cr, uid, me.employee_id.id, loclDTStart.date(), loclDTEnd.date(),
                                        psa_codes, run_id=False, context=context)
        newslip_data = ps_obj.read(cr, uid, slip_id, ['name'], context=context)
        ps_obj.write(cr, uid, [slip_id], {'name': _('[Amended] ') + newslip_data['name'],
                                          'original_payslip_run_id': old_payslip_run_id},
                     context=context)

        # Delete the previous amended payslip
        if me.new_payslip_id:
            ps_obj.unlink(cr, uid, [me.new_payslip_id.id], context=context)

        # Compute pay slip, link to old payslip and to this amendment
        #
        ps_obj.compute_sheet(cr, uid, [slip_id], context=context)
        if me.old_payslip_id:
            ps_obj.write(cr, uid, me.old_payslip_id.id, {'amended_payslip_id': slip_id}, context=context)
        self.write(cr, uid, ids[0], {'new_payslip_id': slip_id}, context=context)

        # Create Pay Slip Amendment
        #
        return self.create_payslip_amendments(cr, uid, ids, context=context)

    def create_payslip_amendments(self, cr, uid, ids, context=None):

        if isinstance(ids, (long, int)):
            ids = [ids]

        psa_obj = self.pool.get('hr.payslip.amendment')
        me = self.browse(cr, uid, ids[0], context=context)

        # Get differences between old and new pay slips
        #
        diff = self.get_net_difference(cr, uid, me.id, context=context)
        allowance_amount = 0
        deduction_amount = 0
        tmp_allowances = diff['new']['allowances'] - diff['old']['allowances']
        tmp_deductions = diff['new']['deductions'] - diff['old']['deductions']
        tmp_net = diff['new']['net'] - diff['old']['net']
        if tmp_allowances > 0:
            allowance_amount += tmp_allowances
        elif tmp_allowances < 0:
            deduction_amount += abs(tmp_allowances)
        if tmp_deductions > 0:
            deduction_amount += tmp_deductions
        elif tmp_deductions < 0:
            allowance_amount += abs(tmp_deductions)

        # Get rule inputs
        #
        res_model, res_id = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                                                                                'hr_payroll_amendment',
                                                                                'salary_rule_input_adjust_earnings')
        data = self.pool.get('hr.rule.input').read(cr, uid, res_id, [])
        allow_input_id = data.get('id', False)

        res_model, res_id = self.pool.get('ir.model.data').get_object_reference(cr, uid,
                                                                                'hr_payroll_amendment',
                                                                                'salary_rule_input_adjust_deductions')
        data = self.pool.get('hr.rule.input').read(cr, uid, res_id, [])
        deduct_input_id = data.get('id', False)

        psa_ids = []
        if allowance_amount > 0:
            psa_allow_vals = {
                'name': 'Post-Close Pay Slip Amendment',
                'employee_id': me.employee_id.id,
                'amount': allowance_amount,
                'input_id': allow_input_id,
                'pay_period_id': (me.next_pp_id) and me.next_pp_id.id or False,
            }
            psa_ids.append(psa_obj.create(cr, uid, psa_allow_vals, context=context))
        if deduction_amount > 0:
            psa_deduct_vals = {
                'name': 'Post-Close Pay Slip Amendment',
                'employee_id': me.employee_id.id,
                'amount': deduction_amount,
                'input_id': deduct_input_id,
                'pay_period_id': (me.next_pp_id) and me.next_pp_id.id or False,
            }
            psa_ids.append(psa_obj.create(cr, uid, psa_deduct_vals, context=context))

        memo = me.memo and me.memo or ''
        memo = memo + '\n----------\n'
        memo = memo + 'Earnings and Deductions:\n%s' % diff
        memo = memo + ('\nallowance amount(%s) = new(%s) - old(%s)' %(tmp_allowances, diff['new']['allowances'], diff['old']['allowances']))
        memo = memo + ('\ndeduction amount(%s) = new(%s) - old(%s)' %(tmp_deductions, diff['new']['deductions'], diff['old']['deductions']))
        memo = memo + ('\nNET amount(%s) = new(%s) - old(%s)' %(tmp_net, diff['new']['net'], diff['old']['net']))
        self.write(cr, uid, me.id, {'payslip_amendment_ids': [(2, psa.id) for psa in me.payslip_amendment_ids]},
                   context=context)
        self.write(cr, uid, me.id, {'memo': memo,
                                    'payslip_amendment_ids': [(4, psa_id) for psa_id in psa_ids]},
                   context=context)

        return True

    def get_net_difference(self, cr, uid, my_id, context=None):

        me = self.browse(cr, uid, my_id, context=context)
        old_details = self.get_details_by_rule_category(cr, uid, me.old_payslip_id.details_by_salary_rule_category)
        new_details = self.get_details_by_rule_category(cr, uid, me.new_payslip_id.details_by_salary_rule_category)

        # For allowances: include changes in basic wage AND OT AND Allowances
        # For deductions: include ONLY deductions THAT ARE NOT taxes
        diff = {
            'old': {
                'allowances': old_details['workwage'] + old_details['ot'] + old_details['allowances'],
                'deductions': old_details['deductions'],
                'net': old_details['net'],
                'fit': old_details['fit'],
            },
            'new': {
                'allowances': new_details['workwage'] + new_details['ot'] + new_details['allowances'],
                'deductions': new_details['deductions'],
                'net': new_details['net'],
                'fit': new_details['fit'],
            }
        }

        return diff

    # Most of this function (except at the end) is copied verbatim from
    # the Pay Slip Details Report
    #
    def get_details_by_rule_category(self, cr, uid, obj):
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
            'allowances': 0,
            'taxable_gross': 0,
            'gross': 0,
            'fit': 0,
            'lu': 0,
            'ee_pension': 0,
            'deductions': 0,
            'deductions_total': 0,
            'net': 0,
            'er_contributions': 0,
        }
        if not obj:
            return regline

        # Arrange the Pay Slip Lines by category
        #
        for id in range(len(obj)):
            ids.append(obj[id].id)
        if ids:
            cr.execute('''SELECT pl.id, pl.category_id FROM hr_payslip_line as pl \
                LEFT JOIN hr_salary_rule_category AS rc on (pl.category_id = rc.id) \
                WHERE pl.id in %s \
                GROUP BY rc.parent_id, pl.sequence, pl.id, pl.category_id \
                ORDER BY pl.sequence, rc.parent_id''',(tuple(ids),))
            for x in cr.fetchall():
                result.setdefault(x[1], [])
                result[x[1]].append(x[0])
            for key, value in result.iteritems():
                rule_categories = rule_cate_obj.browse(cr, uid, [key])
                parents = get_recursive_parent(rule_categories)
                category_total = 0
                for line in payslip_line.browse(cr, uid, value):
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
                for line in payslip_line.browse(cr, uid, value):
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
                elif r['code'] == 'OT' and r['level'] == 0:
                    regline['ot'] += r['total']
                elif r['code'] == 'ALW' and r['level'] == 0:
                    regline['allowances'] += r['total']
                elif r['code'] == 'TXBL' and r['level'] == 0:
                    regline['taxable_gross'] += r['total']
                elif r['code'] == 'GROSS' and r['level'] == 0:
                    regline['gross'] += r['total']
                elif r['code'] == 'FITCALC' and r['level'] == 0:
                    regline['fit'] += r['total']
                elif r['code'] == 'DED' and r['level'] == 0:
                    regline['deductions'] += r['total']
                elif r['code'] == 'DEDTOTAL':
                    regline['deductions_total'] += r['total']
                elif r['code'] == 'NET' and r['level'] == 0:
                    regline['net'] += r['total']

        return regline

class hr_attendance(orm.Model):

    _inherit = 'hr.attendance'

    def is_locked(self, cr, uid, employee_id, utcdt_str, context=None):

        pca_obj = self.pool.get('hr.payroll.postclose.amendment')

        is_locked = super(hr_attendance, self).is_locked(cr, uid, employee_id, utcdt_str, context=None)
        if is_locked:
            pp_obj = self.pool.get('hr.payroll.period')
            pp_ids = pp_obj.search(cr, uid, [('state', 'in', ['payment','closed']),
                                             '&', ('date_start', '<=', utcdt_str),
                                                  ('date_end', '>=', utcdt_str),
                                            ], context=context)
            pca_ids = pca_obj.search(cr, uid, [('pp_id', 'in', pp_ids),
                                               ('employee_id', '=', employee_id),
                                               ('state', '=', 'draft')],
                                     context=context)
            if len(pca_ids) > 0:
                is_locked = False

        return is_locked
