# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Clear ICT Solutions <info@clearict.com>.
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

import logging
_logger = logging.getLogger(__name__)


class hr_payroll_period(orm.Model):

    _inherit = 'hr.payroll.period'

    _columns = {
        'noprocess_ids': fields.one2many('hr.payroll.noprocess',
                                         'payroll_period_id',
                                         'No Process List'),
    }

    def process_employee(self, cr, uid, ids, employee_id, context=None):
        """Hook method to allow subclasses to override creation of a pay slip
        for an employee."""

        if isinstance(ids, (long, int)):
            ids = [ids]

        for period in self.browse(cr, uid, ids, context=context):
            for noproc in period.noprocess_ids:
                if noproc.employee_id.id == employee_id:
                    _logger.warning("Skip payroll processing for: %s", noproc.employee_id.name)
                    return False

        return True


class hr_payroll_noprocess(orm.Model):

    _name = 'hr.payroll.noprocess'
    _description = 'Payroll No Process List'

    _columns = {
        'payroll_period_id': fields.many2one('hr.payroll.period',
                                             'Payroll Period', required=True),
        'employee_id': fields.many2one('hr.employee', 'Employee',
                                       required=True),
        'reason': fields.char('Reason'),
    }

    _sql_constraints = [('uniq_period_employee',
                         'UNIQUE(payroll_period_id,employee_id)',
                        _('Employee name is duplicated for the period.'))]
