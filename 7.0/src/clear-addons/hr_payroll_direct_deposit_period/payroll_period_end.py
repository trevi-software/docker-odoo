# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Clear ICT Solutions <info@clearict.com>.
#    All Rights Reserved.
#
#    This program is free software: you can redistribute it and/or modify it
#    under the terms of the GNU Affero General Public License as published by
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

from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.osv import fields, osv


class payroll_period(osv.osv):

    _inherit = 'hr.payroll.period'

    _columns = {
        'direct_deposit_amount': fields.related(
            'register_id', 'direct_deposit_amount', type='float',
            readonly=True, string='Direct Deposit Net Amount'),
        'total_net_amount': fields.related(
            'register_id', 'total_net_amount', type='float',
            readonly=True, string='Total Net Amount'),
    }


class payroll_register(osv.osv):

    _inherit = 'hr.payroll.register'

    _columns = {
        'direct_deposit_amount': fields.float(
            'Direct Deposit Net Amount',
            digits_compute=dp.get_precision('Account'), readonly=True),
        'total_net_amount': fields.float(
            'Total Amount',
            digits_compute=dp.get_precision('Account'), readonly=True),
    }

    # Override base class method.
    # This now pulls up only cash payment pay slips.
    #
    def get_net_payslip_lines(self, cr, uid, run_ids, context=None):

        net_lines = []
        slip_line_obj = self.pool.get('hr.payslip.line')
        slip_line_ids = slip_line_obj.search(
            cr, uid, self.get_net_payslip_lines_domain(run_ids),
            context=context)
        for line in slip_line_obj.browse(
                                    cr, uid, slip_line_ids, context=context):
            if line.slip_id.employee_id.use_direct_deposit is False:
                net_lines.append(line.total)

        return net_lines

    def set_denominations(self, cr, uid, ids, context=None):

        super(payroll_register, self).set_denominations(
                                                cr, uid, ids, context=context)

        reg_id = ids[0]
        data = self.read(cr, uid, reg_id, ['run_ids'], context=context)
        if not data['run_ids'] or len(data['run_ids']) == 0:
            return

        dd_net = 0.0
        total_net = 0.0
        slip_line_obj = self.pool.get('hr.payslip.line')
        if data.get('run_ids', False):
            # Set direct deposit amount
            #
            slip_line_ids = slip_line_obj.search(
                cr, uid,
                self.get_net_payslip_lines_domain(data['run_ids']),
                context=context)
            for line in slip_line_obj.browse(
                                    cr, uid, slip_line_ids, context=context):
                if line.slip_id.employee_id.use_direct_deposit is True:
                    dd_net += line.total

            # Set total payroll amount
            #
            slip_line_ids = slip_line_obj.search(
                cr, uid,
                self.get_net_payslip_lines_domain(data['run_ids']),
                context=context)
            for line in slip_line_obj.browse(
                                    cr, uid, slip_line_ids, context=context):
                total_net += line.total

            self.write(cr, uid, [reg_id],
                       {'direct_deposit_amount': dd_net,
                        'total_net_amount': total_net},
                       context=context)

        return
