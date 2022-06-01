#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2011,2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

import random
import string
from osv import fields,osv
from tools.translate import _

IDLEN = 8

class hr_employee(osv.osv):
    """Implement company wide unique identification number."""

    _name = 'hr.employee'
    _inherit = 'hr.employee'

    _columns = {
        'employee_no': fields.char('Employee ID', readonly=True),
        'employee_no_rand': fields.char('Unique ID', size=IDLEN, readonly=True),
        'employee_no': fields.char('Employee ID',
                       size=IDLEN,
                       readonly=True),
        # Formatted version of employee ID
        'f_employee_no': fields.char('Employee ID',
                                     size=IDLEN+2,
                                     readonly=True),
        'tin_no': fields.char('TIN No', size=10),
    }

    _sql_constraints = [
        ('employeeno_uniq', 'unique(employee_no)', 'The Employee Number must be unique accross the company(s).'),
        ('tinno_uniq', 'unique(tin_no)', 'There is already another employee with this TIN number.'),
    ]
    
    def _check_identification(self, cr, uid, ids, context=None):
        obj = self.browse(cr, uid, ids[0], context=context)
        if obj.identification_id or obj.tin_no:
            return True
        return False
    
#    _constraints = [
#        (_check_identification, 'At least one of the identification fields must be filled in.', ['identification_id', 'tin_no']),
#    ]

    def _generate_employeeno(self, cr, uid, arg):
        """Generate a random employee identifacation number. For easier integration with
        other systems (such as punch clocks, etc) that use an integer as an id the first
        digit will allways be non-zero."""

        eid = ''
        tries = 0
        max_tries = 50
        while tries < max_tries:
            rnd = random.SystemRandom()
            digit1 = ''.join(rnd.choice(['1','2','3','4','5','6','7','8','9']))
            digits = ''.join(rnd.choice(string.digits) for _ in range(IDLEN - 1))
            eid = digit1 + digits
            ids = self.search(cr, uid, [('employee_no', '=', eid)])
            if len(ids) == 0:
                break

            tries += 1

        if tries == max_tries:
            raise osv.except_osv(_('Error'), _('Unable to generate an Employee ID number that is unique.'))
        
        return eid

    def create(self, cr, uid, vals, context={}):

        eid = self._generate_employeeno(cr, uid, context)
        vals['employee_no'] = eid
        vals['f_employee_no'] = '%s-%s-%s' % (eid[:2], eid[2:4], eid[4:])
        return super(hr_employee, self).create(cr, uid, vals, context)
