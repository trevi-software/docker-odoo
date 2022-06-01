# -*- coding:utf-8 -*-
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

from openerp.osv import fields, orm
from openerp.tools.float_utils import float_compare
from openerp.tools.translate import _


class change_contract_wizard(orm.TransientModel):

    _name = 'log.change.contract.wizard'
    _description = 'Employee Contract Change Wizard'

    _columns = {
        'contract_id': fields.many2one('hr.contract', 'Contract',
                                       required=True),
        'wage': fields.float('Current Wage', readonly=True),
        'new_wage': fields.float('New Wage', required=False),
        'start_date': fields.date('Current Start Date', readonly=True),
        'new_start_date': fields.date('New Start Date', required=False),
    }

    def _get_prev_wage(self, cr, uid, context=None):

        res = ''
        c_id = context.get('active_id', False)
        if c_id:
            c = self.pool.get('hr.contract').browse(cr, uid, c_id,
                                                    context=context)
            res = c.wage

        return res

    def _get_prev_start(self, cr, uid, context=None):

        res = ''
        c_id = context.get('active_id', False)
        if c_id:
            c = self.pool.get('hr.contract').browse(cr, uid, c_id,
                                                    context=context)
            res = c.date_start

        return res

    _defaults = {
        'contract_id': lambda s, c, u, ctx: ctx.get('active_id', False),
        'wage': _get_prev_wage,
        'new_wage': _get_prev_wage,
        'start_date': _get_prev_start,
        'new_start_date': _get_prev_start,
    }

    def onchange_contract_id(self, cr, uid, ids, contract_id, context=None):

        res = {'value': {'wage': False, 'new_wage': False, 'start_date': False,
                         'new_start_date': False}}
        if contract_id:
            c = self.pool.get('hr.contract').browse(cr, uid, contract_id,
                                                    context=context)
            res['value']['wage'] = c.wage
            res['value']['new_wage'] = c.wage
            res['value']['start_date'] = c.date_start
            res['value']['new_start_date'] = c.date_start
        return res

    def do_change(self, cr, uid, ids, context=None):

        wizard = self.browse(cr, uid, ids[0], context=context)
        vals = {'contract_id': wizard.contract_id.id}
        vals_write = {}
        if float_compare(wizard.new_wage, wizard.wage, precision_digits=2) != 0:
            vals.update({'wage': str(wizard.wage)})
            vals_write.update({'wage': wizard.new_wage})
        if wizard.new_start_date != wizard.start_date:
            vals.update({'date_start': wizard.start_date})
            vals_write.update({'date_start': wizard.new_start_date})

        ch_log_obj = self.pool.get('log.change.contract')
        change_id = ch_log_obj.create(cr, uid, vals, context=context)
        if not change_id:
            orm.except_orm(_('Error'), _('Unable to log contract change!'))

        self.pool.get('hr.contract').write(cr, uid, wizard.contract_id.id,
                                           vals_write, context=context)

        return {'type': 'ir.actions.act_window_close'}
