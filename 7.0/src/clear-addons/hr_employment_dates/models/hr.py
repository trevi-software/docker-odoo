# -*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2016 Clear ICT Solutions <info@clearict.com>.
#    All Rights Reserved.
#    @author: Michael Telahun Makonnen <miket@clearict.com>
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

import logging
from openerp import SUPERUSER_ID
from openerp.osv import fields, orm

_logger = logging.getLogger(__name__)


class Employee(orm.Model):

    _inherit = 'hr.employee'

    def _get_employment_dates(self, cr, uid, ids, field_names, args,
                              context=None):

        res = dict.fromkeys(ids, False)
        for ee in self.browse(cr, uid, ids, context=context):
            contracts = self._get_contracts_list(ee)
            _start = False
            _end = False
            if len(contracts) > 0:
                _start = contracts[0].date_start
                _initial_date = contracts[0].\
                    employee_id.initial_employment_date
                if _initial_date and _initial_date < _start:
                    _start = contracts.employee_id.initial_employment_date
                _end = contracts[-1].date_end
            res[ee.id] = {
                'employment_start': _start,
                'employment_end': _end,
            }

        return res

    def _get_ids_from_contracts(self, cr, uid, ids, context=None):

        res = []
        for contract in self.pool.get('hr.contract').\
                browse(cr, uid, ids, context=context):
            if contract.employee_id.id not in res:
                res.append(contract.employee_id.id)

        return res

    _columns = {
        'employment_start': fields.function(
            _get_employment_dates, type='date', method=True, multi='empdate',
            string='Employment Start', select=1,
            store={
                'hr.contract': (_get_ids_from_contracts,
                                ['employee_id', 'date_start', 'date_end'], 10)
            },
        ),
        'employment_end': fields.function(
            _get_employment_dates, type='date', method=True, multi='empdate',
            string='Employment End', select=1,
            store={
                'hr.contract': (_get_ids_from_contracts,
                                ['employee_id', 'date_start', 'date_end'], 10)
            },
        ),
    }

    def _set_employment_dates(self, cr, uid, ids, context=None):

        res = self._get_employment_dates(cr, uid, ids, None, None,
                                         context=context)
        for _id in ids:
            if res[_id]['employment_start']:
                query = "UPDATE hr_employee                         \
                         SET employment_start=%s,employment_end=%s  \
                         WHERE id=%s"
                var_end = None
                if res[_id]['employment_end']:
                    var_end = res[_id]['employment_end']
                cr.execute(query, (res[_id]['employment_start'], var_end, _id))
        return True

    def init(self, cr):
        """Set start/end dates (if not set) at module installation"""
        cr.execute("SELECT id, employment_start \
                    FROM hr_employee            \
                    WHERE employment_start is NULL",)
        to_set = cr.fetchall()
        if to_set:
            _logger.info(
                'Setting Employment dates for %s employees', len(to_set)
            )
            _count = 0
            for employees in to_set:
                _count += 1
                if _count % 100 == 0:
                    _logger.info('Employment dates updated: %s', _count)
                self._set_employment_dates(cr, SUPERUSER_ID, [employees[0]])
        return True
