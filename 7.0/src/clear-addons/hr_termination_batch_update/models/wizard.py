# -*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Clear ICT Solutions <http://clearict.com>.
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

from openerp import netsvc
from openerp.osv import fields, orm


class hr_contract(orm.TransientModel):

    _name = 'hr.employee.termination.update.wizard'
    _description = 'De-activate employees in batches'

    _columns = {
        'termination_ids': fields.many2many(
            'hr.employee.termination',
            'hr_employee_termination_update_wizard_rel',
            'wizard_id', 'termination_id', 'Separation Records',
            domain="[('state', '=', 'confirm')]"),
    }

    def change_state(self, cr, uid, ids, context=None):

        wizard = self.browse(cr, uid, ids[0], context=context)
        wkf = netsvc.LocalService('workflow')
        for termination in wizard.termination_ids:
            if termination.state == 'confirm':
                wkf.trg_validate(uid, 'hr.employee.termination',
                                 termination.id, 'signal_done', cr)

        return {'type': 'ir.actions.act_window_close'}
