# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
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

import time
from datetime import datetime

from openerp.osv import fields, osv
from openerp.tools import DEFAULT_SERVER_DATETIME_FORMAT as OE_DTFORMAT
from openerp.tools.translate import _

class hr_action_reason(osv.osv):
    _name = "hr.action.reason"
    _description = "Action Reason"
    _columns = {
        'name': fields.char('Reason', size=64, required=True, help='Specifies the reason for Signing In/Signing Out.'),
        'action_type': fields.selection([('sign_in', 'Sign in'), ('sign_out', 'Sign out')], "Action Type"),
    }
    _defaults = {
        'action_type': 'sign_in',
    }

hr_action_reason()

def _employee_get(obj, cr, uid, context=None):
    ids = obj.pool.get('hr.employee').search(cr, uid, [('user_id', '=', uid)], context=context)
    return ids and ids[0] or False

class hr_attendance(osv.osv):
    _name = "hr.attendance"
    _description = "Attendance"

    def _day_compute(self, cr, uid, ids, fieldnames, args, context=None):
        res = dict.fromkeys(ids, '')
        for obj in self.browse(cr, uid, ids, context=context):
            res[obj.id] = time.strftime('%Y-%m-%d', time.strptime(obj.name, '%Y-%m-%d %H:%M:%S'))
        return res

    _columns = {
        'name': fields.datetime('Date', required=True, select=1),
        'action': fields.selection([('sign_in', 'Sign In'), ('sign_out', 'Sign Out'), ('action','Action')], 'Action', required=True),
        'action_desc': fields.many2one("hr.action.reason", "Action Reason", domain="[('action_type', '=', action)]", help='Specifies the reason for Signing In/Signing Out in case of extra hours.'),
        'employee_id': fields.many2one('hr.employee', "Employee", required=True, select=True),
        'day': fields.function(_day_compute, type='char', string='Day', store=True, select=1, size=32),
    }
    _defaults = {
        'name': lambda *a: time.strftime('%Y-%m-%d %H:%M:%S'), #please don't remove the lambda, if you remove it then the current time will not change
        'employee_id': _employee_get,
    }

    def _altern_si_so(self, cr, uid, ids, context=None):
        """ Alternance sign_in/sign_out check.
            Previous (if exists) must be of opposite action.
            Next (if exists) must be of opposite action.
        """
        import logging
        _log = logging.getLogger(__name__)
        for att in self.browse(cr, uid, ids, context=context):
            # search and browse for first previous and first next records
            prev_att_ids = self.search(cr, uid, [('employee_id', '=', att.employee_id.id), ('name', '<', att.name), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name DESC')
            next_add_ids = self.search(cr, uid, [('employee_id', '=', att.employee_id.id), ('name', '>', att.name), ('action', 'in', ('sign_in', 'sign_out'))], limit=1, order='name ASC')
            prev_atts = self.browse(cr, uid, prev_att_ids, context=context)
            next_atts = self.browse(cr, uid, next_add_ids, context=context)
            # check for alternance, return False if at least one condition is not satisfied
            if prev_atts and prev_atts[0].action == att.action: # previous exists and is same action
                _log.warning('%s att: %s', att.employee_id.name, att.name)
                _log.warning('Prev att: %s', prev_atts[0].name)
                return False
            if next_atts:
                att_day = datetime.strptime(att.name, OE_DTFORMAT)
                next_day = datetime.strptime(next_atts[0].name, OE_DTFORMAT)
                if att_day == next_day and next_atts[0].action == att.action: # next exists and is same action
                    _log.warning('%s att: %s', att.employee_id.name, att.name)
                    _log.warning('Next att: %s', next_atts[0].name)
                    return False
            if (not prev_atts) and (not next_atts) and att.action != 'sign_in': # first attendance must be sign_in
                return False
        return True

    _constraints = [(_altern_si_so, 'Error ! Sign in (resp. Sign out) must follow Sign out (resp. Sign in)', ['action'])]
    _order = 'name desc'

hr_attendance()

class hr_employee(osv.osv):
    _inherit = "hr.employee"
    _description = "Employee"

    def _state(self, cr, uid, ids, name, args, context=None):
        result = {}
        if not ids:
            return result
        for id in ids:
            result[id] = 'absent'
        cr.execute('SELECT hr_attendance.action, hr_attendance.employee_id \
                FROM ( \
                    SELECT MAX(name) AS name, employee_id \
                    FROM hr_attendance \
                    WHERE action in (\'sign_in\', \'sign_out\') \
                    GROUP BY employee_id \
                ) AS foo \
                LEFT JOIN hr_attendance \
                    ON (hr_attendance.employee_id = foo.employee_id \
                        AND hr_attendance.name = foo.name) \
                WHERE hr_attendance.employee_id IN %s',(tuple(ids),))
        for res in cr.fetchall():
            result[res[1]] = res[0] == 'sign_in' and 'present' or 'absent'
        return result
    
    def _last_sign(self, cr, uid, ids, name, args, context=None):
        result = {}
        if not ids:
            return result
        for id in ids:
            result[id] = False
            cr.execute("""select max(name) as name
                        from hr_attendance
                        where action in ('sign_in', 'sign_out') and employee_id = %s""",(id,))
            for res in cr.fetchall():
                result[id] = res[0]
        return result

    def _attendance_access(self, cr, uid, ids, name, args, context=None):
        # this function field use to hide attendance button to singin/singout from menu
        group = self.pool.get('ir.model.data').get_object(cr, uid, 'base', 'group_hr_attendance')
        visible = False
        if uid in [user.id for user in group.users]:
            visible = True
        return dict([(x, visible) for x in ids])

    _columns = {
       'state': fields.function(_state, type='selection', selection=[('absent', 'Absent'), ('present', 'Present')], string='Attendance'),
       'last_sign': fields.function(_last_sign, type='datetime', string='Last Sign'),
       'attendance_access': fields.function(_attendance_access, string='Attendance Access', type='boolean'),
    }

    def _action_check(self, cr, uid, emp_id, dt=False, context=None):
        cr.execute('SELECT MAX(name) FROM hr_attendance WHERE employee_id=%s', (emp_id,))
        res = cr.fetchone()
        return not (res and (res[0]>=(dt or time.strftime('%Y-%m-%d %H:%M:%S'))))

    def attendance_action_change(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        action_date = context.get('action_date', False)
        action = context.get('action', False)
        hr_attendance = self.pool.get('hr.attendance')
        warning_sign = {'sign_in': _('Sign In'), 'sign_out': _('Sign Out')}
        for employee in self.browse(cr, uid, ids, context=context):
            if not action:
                if employee.state == 'present': action = 'sign_out'
                if employee.state == 'absent': action = 'sign_in'

            if not self._action_check(cr, uid, employee.id, action_date, context):
                raise osv.except_osv(_('Warning'), _('You tried to %s with a date anterior to another event !\nTry to contact the HR Manager to correct attendances.')%(warning_sign[action],))

            vals = {'action': action, 'employee_id': employee.id}
            if action_date:
                vals['name'] = action_date
            hr_attendance.create(cr, uid, vals, context=context)
        return True

hr_employee()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
