# -*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (c) 2015 Clear ICT Solutions <info@clearict.com>.
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
from openerp.service.locking import RecordRLock
from openerp.tools.translate import _


class attendance_weekly(orm.Model):

    _inherit = 'hr.attendance.weekly'

    def write(self, cr, uid, ids, vals, context=None):

        if isinstance(ids, (long, int)):
            ids = [ids]

        locks = []
        try:
            for _id in ids:
                lock = RecordRLock(cr.dbname, self._name, _id)
                # Non-blocking lock. Fail if it's already locked by another
                if lock.acquire(blocking=False):
                    locks.append(lock)
                else:
                    _o = self.browse(cr, uid, _id, context=context)
                    raise orm.except_orm(
                        _('Access Temporarily Denied'),
                        _('Access temporarily locked to %s %s weekly '
                          'attendance. Please try again later.'
                          % (_o.department_id.name, _o.week_start))
                    )

            res = super(attendance_weekly, self).write(cr, uid, ids, vals,
                                                       context=context)
        finally:
            for _l in locks:
                _l.release()

        return res
