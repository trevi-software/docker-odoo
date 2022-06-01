# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Sucros Clear Information Technologies PLC
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

from openerp.osv import orm


class payroll_period(orm.Model):

    _inherit = 'hr.payslip.exception'

    def button_recalculate(self, cr, uid, ids, context=None):

        pp_obj = self.pool.get('hr.payroll.period')
        for ex in self.browse(cr, uid, ids, context=None):
            period = ex.slip_id.payslip_run_id.register_id.period_id
            pp_obj.rerun_payslip(
                            cr, uid, period.id, ex.slip_id.id, context=context)
