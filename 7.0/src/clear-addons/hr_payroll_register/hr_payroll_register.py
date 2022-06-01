#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

from datetime import datetime

from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.tools.float_utils import float_compare
from openerp.tools.translate import _
from osv import fields, osv

class hr_payroll_run(osv.osv):
    
    _name = 'hr.payslip.run'
    _inherit = 'hr.payslip.run'
    
    _columns = {
        'register_id': fields.many2one('hr.payroll.register', 'Register'),
        'department_ids': fields.many2many('hr.department', 'hr_payroll_register_department_rel',
                                           'register_id', 'department_id', 'Department'),
    }

class hr_payroll_register(osv.osv):
    
    _name = 'hr.payroll.register'

    def _get_change(self, cr, uid, ids, field_name, args, context=None):

        res = dict.fromkeys(ids, 0.0)
        for reg in self.browse(cr, uid, ids, context=context):
            for den in reg.denomination_ids:
                res[reg.id] += (den.denomination * den.denomination_qty)
        return res
    
    _columns = {
        'name': fields.char('Description', size=256),
        'state': fields.selection([
                                   ('draft', 'Draft'),
                                   ('close', 'Close'),
                                  ], 'Status', select=True, readonly=True),
        'date_start': fields.datetime('Date From', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'date_end': fields.datetime('Date To', required=True, readonly=True, states={'draft': [('readonly', False)]}),
        'run_ids': fields.one2many('hr.payslip.run', 'register_id', readonly=True, states={'draft': [('readonly', False)]}),
        'company_id': fields.many2one('res.company', 'Company'),
        'denomination_ids': fields.one2many(
            'hr.payroll.register.denominations', 'register_id',
            string='Denomination Quantitiess', readonly=True),
        'exact_change': fields.function(
            _get_change, type='float', string='Net Amount',
            digits_compute=dp.get_precision('Account'), readonly=True),
    }
    
    _sql_constraints = [('unique_name', 'UNIQUE(name)', _('Payroll Register description must be unique.'))]
    
    def _get_default_name(self, cr, uid, context=None):
        
        nMonth = datetime.now().strftime('%B')
        year = datetime.now().year
        name = _('Payroll for the Month of %s %s' %(nMonth, year))
        return name
    
    def _get_company(self, cr, uid, context=None):
        
        users_pool = self.pool.get('res.users')
        return users_pool.browse(cr, uid,
                                 users_pool.search(cr, uid, [('id','=',uid)], context=context),
                                 context=context)[0].company_id.id
    
    _defaults = {
        'name': _get_default_name,
        'state': 'draft',
        'company_id': _get_company,
    }
    
    def action_delete_runs(self, cr, uid, ids, context=None):
        
        pool = self.pool.get('hr.payslip.run')
        ids = pool.search(cr, uid, [('register_id', 'in', ids)], context=context)
        pool.unlink(cr, uid, ids, context=context)
        return True
    
    def get_net_payslip_lines_domain(self, run_ids):
        
        return [('slip_id.payslip_run_id', 'in', run_ids),
                ('salary_rule_id.code', '=', 'NET')]
    
    def get_net_payslip_lines(self, cr, uid, run_ids, context=None):
        
        net_lines = []
        slip_line_obj = self.pool.get('hr.payslip.line')
        slip_line_ids = slip_line_obj.search(cr, uid,
                                             self.get_net_payslip_lines_domain(run_ids),
                                             context=context)
        for line in slip_line_obj.browse(cr, uid, slip_line_ids, context=context):
            net_lines.append(line.total)
        
        return net_lines
    
    def set_denominations(self, cr, uid, ids, context=None):
        
        reg_id = ids[0]
        res = dict.fromkeys(ids, False)
        data = self.read(cr, uid, reg_id, ['run_ids'], context=context)
        if not data['run_ids'] or len(data['run_ids']) == 0:
            return
        
        # Remove current denomination count
        den_obj = self.pool.get('hr.payroll.register.denominations')
        den_ids = den_obj.search(cr, uid, [('register_id', '=', reg_id)],
                                 context=context)
        den_obj.unlink(cr, uid, den_ids, context=context)
        
        # Get list of all 'NET' payslip lines
        #
        net_lines = self.get_net_payslip_lines(cr, uid, data['run_ids'], context=context)
        if len(net_lines) == 0:
            return
        
        # Get denominations for payroll currency
        # Arrange in order from largest value to smallest.
        #
        denominations = []
        smallest_note = 1
        currency_obj = self.pool.get('res.currency')
        currency_id = currency_obj.search(cr, uid, [('name', '=', 'ETB')], context=context)[0]
        currency = currency_obj.browse(cr, uid, currency_id, context=context)
        for denom in currency.denomination_ids:
            if float_compare(denom.ratio, 1.00, precision_digits=2) == 0:
                smallest_note = denom.value

            if len(denominations) == 0:
                denominations.append(denom.value)
                continue
            
            idx = 0
            last_idx = len(denominations) - 1
            for preexist_val in denominations:
                if denom.value > preexist_val:
                    denominations.insert(idx, denom.value)
                    break
                elif idx == last_idx:
                    denominations.append(denom.value)
                    break
                idx += 1
        
        denom_qty_list = dict.fromkeys(denominations, 0)
        cents_factor = float(smallest_note) / denominations[-1]
        for net in net_lines:
            cents, notes = math.modf(net)
            
            notes = int(notes)
            # XXX - rounding to 4 decimal places should work for most currencies... I hope
            cents = int(round(cents,4) * cents_factor)
            for denom in denominations:
                if notes >= denom:
                    denom_qty_list[denom] += int(notes / denom)
                    notes = (notes > 0) and (notes % denom) or 0
                
                if notes == 0 and cents >= (denom * cents_factor):
                    cooked_denom = int(denom * cents_factor)
                    if cents >= cooked_denom:
                        denom_qty_list[denom] += (cents / cooked_denom)
                    elif denom == denominations[-1]:
                        denom_qty_list[denom] += (cents / cents_factor)
                        cents = 0
                    cents = cents % denom
        
        res[reg_id] = {'exact_change': 0.0, 'denomination_ids': []}
        for k, v in denom_qty_list.items():
            vals = {
                'register_id': reg_id,
                'denomination': k,
                'denomination_qty': v,
            }
            res[reg_id]['denomination_ids'].append(den_obj.create(cr, uid, vals, context=context))
            res[reg_id]['exact_change'] += (k * v)

        return

class hr_payroll_register_denominations(osv.Model):
    
    _name = 'hr.payroll.register.denominations' 
    _description = 'Exact denomination amounts for entire payroll register'
    
    _columns = {
        'register_id': fields.many2one('hr.payroll.register', 'Payroll Register', required=True,
                                       ondelete='cascade'),
        'denomination': fields.float('Denomination', digits_compute=dp.get_precision('Account'),
                                     required=True),
        'denomination_qty': fields.integer('Quantity'),
    }

    _order = 'denomination'
