# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

from openerp.osv import fields, orm
from openerp.tools.translate import _
from openerp.tools.float_utils import float_compare

from openerp.addons.decimal_precision import decimal_precision as dp


class hr_bonus_employees(orm.TransientModel):

    _name = 'hr.bonus.batch.employee.wizard'
    _description = 'Batch Employee Add'

    _columns = {
        'employee_ids': fields.many2many(
            'hr.employee', 'hr_bonus_employee_batch_rel',
            'bonus_id', 'employee_id', 'Employees'),
        'bonus_id': fields.many2one('hr.bonus', 'Bonus', required=True),
        'amount': fields.float(
            'Bonus Amount', digits_compute=dp.get_precision('Payroll'),
            required=True),
        'type': fields.selection(
            [('percent', 'Percentage'), ('fix', 'Fixed')], 'Type',
            required=True),
    }

    def _get_bonus(self, cr, uid, context=None):

        if context is not None:
            if context.get('active_id', False):
                return context['active_id']
        return False

    _defaults = {
        'bonus_id': _get_bonus,
    }

    def create_bonus_lines(self, cr, uid, ids, context=None):

        bonus_obj = self.pool.get('hr.bonus')
        line_obj = self.pool.get('hr.bonus.line')

        if context is None:
            context = {}

        wizard = self.browse(cr, uid, ids, context=context)[0]
        if not wizard.employee_ids or len(wizard.employee_ids) == 0:
            raise orm.except_orm(_("Warning !"),
                                 _("You must select at least one employee."))

        for ee in wizard.employee_ids:
            val = {
                'employee_id': ee.id,
                'type': wizard.type,
                'amount': wizard.amount,
                'sheet_id': wizard.bonus_id.id,
            }
            line_obj.create(cr, uid, val, context=context)
