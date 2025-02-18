#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2011 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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
from dateutil.relativedelta import relativedelta

import netsvc
import openerp.addons.decimal_precision as dp
from osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT
from openerp.tools.float_utils import float_is_zero
from tools.translate import _

class wage_increment(osv.osv):
    
    _name = 'hr.contract.wage.increment'
    _description = 'HR Contract Wage Adjustment'
    
    def _calculate_difference(self, cr, uid, ids, field_name, args, context=None):
        
        res = dict.fromkeys(ids)
        for incr in self.browse(cr, uid, ids, context=context):
            divisor = float_is_zero(incr.contract_id.wage or 0, precision_digits=1) and 1.00 or incr.contract_id.wage
            if incr.wage >= incr.contract_id.wage:
                percent = ((incr.wage / divisor) - 1.0) * 100.0
            else:
                percent = (1.0 - (incr.wage / divisor)) * -100.0
            res[incr.id] = {
                            'wage_difference': incr.wage - incr.current_wage,
                            'wage_difference_percent': percent,
                           }
        
        return res
    
    def _get_department(self, cr, uid, ids, field_name, arg, context=None):
        
        res = dict.fromkeys(ids, False)
        for incr in self.browse(cr, uid, ids, context=context):
            res[incr.id] = incr.employee_id.department_id.id,
        
        return res
    
    _columns = {
                'effective_date': fields.date('Effective Date', required=True, readonly=True, states={'draft': [('readonly', False)]}),
                'wage': fields.float('New Wage', digits_compute=dp.get_precision('Payroll'), required=True, readonly=True, states={'draft': [('readonly', False)]}),
                'new_contract_id': fields.many2one('hr.contract', 'New Contract', readonly=True),
                'contract_id': fields.many2one('hr.contract', 'Contract', readonly=True, states={'draft': [('readonly', False)]}),
                'current_wage': fields.float('Wage', digits_compute=dp.get_precision('Account'),
                                             readonly=True),
                'wage_difference': fields.function(_calculate_difference, type='float', method=True,
                                                   string='Difference', multi='diff', readonly=True),
                'wage_difference_percent': fields.function(_calculate_difference, type='float', method=True,
                                                   string='Percentage', multi='diff', readonly=True),
                'employee_id': fields.related('contract_id', 'employee_id', relation='hr.employee',
                                              type='many2one', string='Employee', store=True,
                                              readonly=True),
                'job_id': fields.related('contract_id', 'job_id', relation='hr.job',
                                         type='many2one', string='Job', store=True, readonly=True),
                'department_id': fields.related('employee_id', 'department_id', relation='hr.department',
                                                 type='many2one', string='Department', store=True, readonly=True),
                'state': fields.selection([
                                           ('draft', 'Draft'),
                                           ('confirm', 'Confirmed'),
                                           ('approve', 'Approved'),
                                           ('decline', 'Declined')
                                          ], 'State', readonly=True),
                'run_id': fields.many2one('hr.contract.wage.increment.run', 'Batch Run',
                                          readonly=True, ondelete='cascade'),
                'remarks': fields.char('Remarks', size=256),
                'length_of_service': fields.related('employee_id', 'length_of_service', type='float',
                                                    store=True, string="Employed Months"),
    }
    
    def _get_contract_data(self, cr, uid, field_list, context=None):
        
        if context == None:
            context = {}
        
        contract_id = False
        employee_id = self._get_employee(cr, uid, context=context)
        if employee_id:
            ee_data = self.pool.get('hr.employee').read(cr, uid, employee_id, ['contract_id'], context=context)
            contract_id = ee_data.get('contract_id', False)[0]
        
        if not contract_id: return {}
        
        return self.pool.get('hr.contract').read(cr, uid, contract_id, field_list, context=context)
    
    def _get_contract_id(self, cr, uid, context=None):
        
        data = self._get_contract_data(cr, uid, ['id'], context)
        return data.get('id', False)
    
    def _get_wage(self, cr, uid, context=None):
        
        data = self._get_contract_data(cr, uid, ['wage'], context)
        return data.get('wage', False)
    
    def _get_employee(self, cr, uid, context=None):
        
        if context == None:
            context = {}
        employee_id = context.get('active_id', False)
        contract_id = context.get('active_contract_id', False)
        if contract_id and not employee_id:
            data = self.pool.get('hr.contract').read(cr, uid, contract_id, ['employee_id'],
                                                     context=context)
            employee_id = data['employee_id'][0]
        
        return employee_id
    
    def _get_effective_date(self, cr, uid, context=None):
        
        contract_id = self._get_contract_id(cr, uid, context=context)
        if not contract_id: return False
        
        contract = self.pool.get('hr.contract').browse(cr, uid, contract_id, context=context)
        if contract.pps_id:
            first_day = 1
            if contract.pps_id.type == 'monthly':
                first_day = contract.pps_id.mo_firstday
            dThisMonth = datetime.strptime(datetime.now().strftime('%Y-%m-' + first_day), DEFAULT_SERVER_DATE_FORMAT).date()
            dNextMonth = datetime.strptime((datetime.now() + relativedelta(months= +1)).strftime('%Y-%m-' + first_day), DEFAULT_SERVER_DATE_FORMAT).date()
            if dThisMonth < datetime.now().date():
                return dNextMonth.strftime(DEFAULT_SERVER_DATE_FORMAT)
            else:
                return dThisMonth.strftime(DEFAULT_SERVER_DATE_FORMAT)
        
        return False

    _defaults = {
        'employee_id': _get_employee,
        'contract_id': _get_contract_id,
        'current_wage': _get_wage,
        'effective_date': _get_effective_date,
        'state': 'draft',
    }
    
    _rec_name = 'effective_date'
    
    def _check_state(self, cr, uid, wage_incr, context=None):
        
        wage_incr_ids = self.search(cr, uid, [
                                              ('contract_id', '=', wage_incr.contract_id.id),
                                              ('state', 'in', ['draft', 'confirm', 'approved']),
                                              ('id', '!=', wage_incr.id),
                                             ],
                                    context=context)
        if len(wage_incr_ids) > 0:
            raise osv.except_osv(_('Warning'),
                                 _('There is already another wage adjustment in ' \
                                   'progress for this employee: %s.') % (wage_incr.employee_id.name))
        
        if wage_incr.contract_id.state in ['draft'] \
          or wage_incr.employee_id.state in ['pending_inactive', 'inactive']:
            raise osv.except_osv(_('Warning!'),
                                 _('The current state of either the contract or ' \
                                   'the employee does not permit a wage change: %s')  % (wage_incr.employee_id.name))
        
        if wage_incr.contract_id.date_end:
            dContractEnd = datetime.strptime(wage_incr.contract_id.date_end, DEFAULT_SERVER_DATE_FORMAT)
            dEffective = datetime.strptime(wage_incr.effective_date, DEFAULT_SERVER_DATE_FORMAT)
            if dEffective >= dContractEnd:
                raise osv.except_osv(_('Warning!'),
                                     _('The contract end date is on or before ' \
                                       'the effective date of the adjustment: %s') %(wage_incr.employee_id.name))
        
        return True
    
    def action_wage_increment(self, cr, uid, ids, context=None):
        
        hr_obj = self.pool.get('hr.contract')

        if isinstance(ids, (int, long)):
            ids = [ids]
        
        # Copy the contract and adjust start/end dates and wage accordingly.
        #
        for wi in self.browse(cr, uid, ids, context=context):
            
            if wi.wage_difference > -0.01 and wi.wage_difference < 0.01:
                continue

            self._check_state(cr, uid, wi, context=context)
            
            later_contracts = self.get_later_contracts(cr, uid, wi.employee_id, wi.effective_date,
                                                       context=context)

            # If the date of the adjustment and the start of the current contract coincide,
            # just change the wage on the contract. Otherwise, create a new contract.
            #
            if wi.contract_id.date_start == wi.effective_date:
                hr_obj.write(cr, uid, wi.contract_id.id, {'wage': wi.wage}, context=context)
            else:
                default = {
                    'wage': wi.wage,
                    'date_start': wi.effective_date,
                    'name': False,
                    'state': False,
                    'message_ids': False,
                    'trial_date_start': False,
                    'trial_date_end': False,
                    'concurrent_contracts': True,
                }
                if wi.contract_id.state == 'done':
                    default.update({'job_id': wi.contract_id.end_job_id.id})
                
                data = hr_obj.copy_data(cr, uid, wi.contract_id.id, default=default, context=context)
                notes = data.get('notes', False)
                if not notes:
                    notes = ''
                notes = notes + '\nSupercedes (because of wage adjustment) previous contract: ' + wi.contract_id.name
                data['notes'] = notes
                
                c_id = hr_obj.create(cr, uid, data, context=context)
                if c_id:
                    if wi.contract_id.notes:
                        notes = wi.contract_id.notes
                    else:
                        notes = ''
                    notes = notes + '\nSuperceded (for wage adjustment) by contract: ' + wi.contract_id.name
                    vals = {'notes': notes,
                            'date_end': False}
                    wkf = netsvc.LocalService('workflow')
                    
                    # Get state of current contract
                    curr_contract_state = wi.contract_id.state
                    
                    # Terminate the current contract (and trigger appropriate state change)
                    dEnd = datetime.strptime(wi.effective_date, DEFAULT_SERVER_DATE_FORMAT).date() + relativedelta(days= -1)
                    vals['date_end'] = datetime.strftime(dEnd, DEFAULT_SERVER_DATE_FORMAT)
                    hr_obj.write(cr, uid, wi.contract_id.id, vals, context=context)
                    if wi.contract_id.state != 'done':
                        wkf.trg_validate(uid, 'hr.contract', wi.contract_id.id, 'signal_done', cr)
                    
                    # Set the new contract to the appropriate state
                    wkf.trg_validate(uid, 'hr.contract', c_id, 'signal_confirm', cr)
                    if curr_contract_state == 'done':
                        wkf.trg_validate(uid, 'hr.contract', c_id, 'signal_done', cr)
        
            # Change the wage on all later contracts
            #
            if len(later_contracts) > 0:
                hr_obj.write(cr, uid, later_contracts, {'wage': wi.wage}, context=context)
        
        return
    
    def create(self, cr, uid, vals, context=None):
        
        if context == None:
            context = {}
        
        contract_id = vals['contract_id']
        con_obj = self.pool.get('hr.contract')

        # Find the contract the effective date falls on
        data = con_obj.read(cr, uid, contract_id, ['name', 'date_start', 'employee_id'], context=context)
        contract_id = self.find_closest_contract(cr, uid, data['employee_id'][0],
                                                 vals['effective_date'], context=context)
        if contract_id != vals['contract_id']:
            data = con_obj.read(cr, uid, contract_id, ['name', 'date_start', 'employee_id'], context=context)
            vals['contract_id'] = contract_id
        
        # Check that the contract start date is before the effective date
        if vals['effective_date'] < data['date_start']:
            vals['effective_date'] = data['date_start']

        wage_incr_ids = self.search(cr, uid, [
                                              ('contract_id', '=', contract_id),
                                              ('state', 'in', ['draft', 'confirm', 'approved']),
                                             ],
                                    context=context)
        if len(wage_incr_ids) > 0:
            raise osv.except_osv(_('Warning'), _('There is already another wage adjustment in progress for this contract: %s.') % (data['name']))
        
        # Pass our copied context so that any default values that get updated can find
        # the relevant employee id.
        context_copy = context.copy()
        context_copy.update({'active_contract_id': contract_id})
        return super(wage_increment, self).create(cr, uid, vals, context=context_copy)
    
    def find_closest_contract(self, cr, uid, employee_id, effective_date, context=None):
        
        data = self.pool.get('hr.employee').read(cr, uid, employee_id, ['contract_ids'], context=context)
        
        last_date = False
        contract_id = False
        con_obj = self.pool.get('hr.contract')
        for contract in con_obj.browse(cr, uid, data['contract_ids'], context=context):
            if not last_date and contract.date_start <= effective_date:
                last_date = contract.date_start
                contract_id = contract.id
            elif contract.date_start <= effective_date and contract.date_start > last_date:
                last_date = contract.date_start
                contract_id = contract.id
        
        # If the employee's starts employment after the effective date
        if last_date == False:
            for contract in con_obj.browse(cr, uid, data['contract_ids'], context=context):
                if not last_date and contract.date_start > effective_date:
                    last_date = contract.date_start
                    contract_id = contract.id
                elif contract.date_start > effective_date and contract.date_start < last_date:
                    last_date = contract.date_start
                    contract_id = contract.id
        
        return contract_id
    
    def get_later_contracts(self, cr, uid, employee, effective_date, context=None):
        
        contract_ids = []
        for contract in employee.contract_ids:
            if contract.date_start > effective_date:
                contract_ids.append(contract.id)
        
        return contract_ids
    
    def do_signal_confirm(self, cr, uid, ids, context=None):
        
        # Update contract if the current one has gone stale
        for wi in self.browse(cr, uid, ids, context=context):
            contract_id = self.find_closest_contract(cr, uid, wi.employee_id.id,
                                                     wi.effective_date, context=context)
            if contract_id != wi.contract_id.id:
                self.write(cr, uid, wi.id, {'contract_id': contract_id}, context=context)

        for wi in self.browse(cr, uid, ids, context=context):
            self._check_state(cr, uid, wi, context=context)
            self.write(cr, uid, wi.id, {'state': 'confirm'}, context=context)
    
    def do_signal_approve(self, cr, uid, ids, context=None):
        
        # Update contract if the current one has gone stale
        for wi in self.browse(cr, uid, ids, context=context):
            contract_id = self.find_closest_contract(cr, uid, wi.employee_id.id,
                                                     wi.effective_date, context=context)
            if contract_id != wi.contract_id.id:
                self.write(cr, uid, wi.id, {'contract_id': contract_id}, context=context)

        for i in ids:
            self.action_wage_increment(cr, uid, [i], context=context)
            self.write(cr, uid, i, {'state': 'approve'}, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        
        for incr in self.browse(cr, uid, ids, context=context):
            if incr.state in ['approve']:
                raise osv.except_osv(_('The record cannot be deleted!'), _('You may not delete a record that is in a %s state:\nEmployee: %s') %(incr.state, incr.employee_id.name))
        
        return super(wage_increment, self).unlink(cr, uid, ids, context=context)

class wage_increment_run(osv.osv):

    _name = 'hr.contract.wage.increment.run'
    _description = 'Wage Increment Batches'
    
    _inherit = ['ir.needaction_mixin']
    
    _columns = {
        'name': fields.char('Name', size=64, required=True, readonly=True,
                            states={'draft': [('readonly', False)]}),
        'effective_date': fields.date('Effective Date', required=True, readonly=True,
                                      states={'draft': [('readonly', False)]}),
        'type': fields.selection([
                                  ('fixed', 'Fixed Amount'),
                                  ('percent', 'Percentage'),
                                  ('final', 'Final Amount'),
                                  ('manual', 'Manual'),
                                 ], 'Type', required=True, readonly=True,
                                 states={'draft': [('readonly', False)]}),
        'adjustment_amount': fields.float('Adjustment Amount',
                                          digits_compute=dp.get_precision('Payroll'), required=True,
                                          readonly=True, states={'draft': [('readonly', False)]}),
        'increment_ids': fields.one2many('hr.contract.wage.increment', 'run_id', 'Adjustments',
                                         required=False, readonly=False,
                                         states={'confirm': [('readonly', False)],
                                                 'approve': [('readonly', True)],
                                                 'decline': [('readonly', True)]}),
        'state': fields.selection([
                                   ('draft', 'Draft'),
                                   ('confirm', 'Confirmed'),
                                   ('approve', 'Approved'),
                                   ('decline', 'Declined')
                                  ], 'State', readonly=True),
    }

    _defaults = {
        'state': 'draft',
    }
    
    def _needaction_domain_get(self, cr, uid, context=None):
        
        users_obj = self.pool.get('res.users')
        domain = []
        
        if users_obj.has_group(cr, uid, 'hr_security.group_hr_director'):
            domain = [('state', 'in', ['confirm'])]
            return domain
        
        return False
    
    def unlink(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        for run in self.browse(cr, uid, ids, context=context):
            if run.state in ['approve']:
                raise osv.except_osv(_('The adjustment run cannot be deleted!'), _('You may not delete a wage adjustment that is in the %s state.') %(run.state))
        
        return super(wage_increment_run, self).unlink(cr, uid, ids, context=context)
    
    def _state(self, cr, uid, ids, signal, state, context=None):
        
        wkf = netsvc.LocalService('workflow')
        for run in self.browse(cr, uid, ids, context=context):
            [wkf.trg_validate(uid, 'hr.contract.wage.increment', incr.id, signal, cr) for incr in run.increment_ids]
            self.write(cr, uid, run.id, {'state': state}, context=context)
        
        return True
    
    def state_confirm(self, cr, uid, ids, context=None):
        
        return self._state(cr, uid, ids, 'signal_confirm', 'confirm', context)
    
    def state_approve(self, cr, uid, ids, context=None):
        
        return self._state(cr, uid, ids, 'signal_approve', 'approve', context)
    
    def state_decline(self, cr, uid, ids, context=None):
        
        return self._state(cr, uid, ids, 'signal_decline', 'decline', context)

class hr_contract(osv.Model):
    
    _name = 'hr.contract'
    _inherit = 'hr.contract'
    
    def state_pending_done(self, cr, uid, ids, context=None):

        for i in ids:
            wi_ids = self.pool.get('hr.contract.wage.increment').search(cr, uid, [
                                                                                  ('contract_id', '=', i),
                                                                                  ('state', 'in', ['draft', 'confirm']),
                                                                                 ],
                                                                        context=context)
        if len(wi_ids) > 0:
            data = self.pool.get('hr.contract').read(cr, uid, i, ['name'],
                                                     context=context)
            raise osv.except_osv(_('Error'),
                                 _('There is a wage adjustment in progress for this contract. Either delete the adjustment or delay the termination of contract %s.') % (data['name']))
        return super(hr_contract, self).state_pending_done(cr, uid, ids, context=context)
