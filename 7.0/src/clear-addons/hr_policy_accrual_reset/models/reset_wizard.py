#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Clear ICT Solutions <info@clearict.com>.
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

from datetime import datetime, timedelta

from openerp import netsvc
from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.float_utils import float_compare
from openerp.tools.translate import _

class reset_wizard(orm.TransientModel):
    
    _name = 'hr.policy.accrual.reset.wizard'
    _description = 'Accruals Reset and Re-calculate Wizard'
    
    _columns = {
        'delete': fields.boolean('Delete Permanently'),
        'employee_ids': fields.many2many('hr.employee', 'hr_policy_accrual_reset_wizard_employee_rel',
                                         'wizard_id', 'employee_id', 'Employees'),
        'accrual_policy_id': fields.many2one('hr.policy.accrual', 'Accrual Policy', required=True),
        'accrual_policy_line_id': fields.many2one('hr.policy.line.accrual', 'Accrual Policy Line',
                                                  required=True),
    }
    
    _defaults = {
        'delete': True,
    }
    
    def onchange_accrual_policy(self, cr, uid, ids, policy_id, context=None):
        
        res = {'domain': {'accrual_policy_line_id': False}}
        if policy_id:
            line_obj = self.pool['hr.policy.line.accrual']
            line_ids = line_obj.search(cr, uid, [('policy_id', '=', policy_id)])
            if len(line_ids) > 0:
                res['domain']['accrual_policy_line_id'] = [('id', 'in', line_ids)]
        
        return res
    
    def _find_free_lv_date(self, cr, uid, employee_id, lvdate, context=None):
        
        lv_obj = self.pool['hr.holidays']
        dTemp = datetime.strptime(lvdate, OE_DFORMAT)
        dGuard = datetime.strptime('1970-01-01', OE_DFORMAT)
        while dTemp >= dGuard:
            # Decrease search date immediately because the passed in date is
            # the employment date. We don't want a leave on employee's first day of work :-P
            # We want the leave to be for employment so that it doesn't affect attendance, etc.
            #
            dTemp += timedelta(days= -1)
            lv_ids = lv_obj.search(cr, uid, [('employee_id', '=', employee_id),
                                             ('date_from', '<=', dTemp.strftime(OE_DFORMAT)),
                                             ('date_to', '>=', dTemp.strftime(OE_DFORMAT))],
                                   context=context)
            if len(lv_ids) == 0:
                break
        
        return dTemp.strftime(OE_DFORMAT)
    
    def do_recalc(self, cr, uid, ids, context=None):
        
        ee_obj = self.pool['hr.employee']
        lv_obj = self.pool['hr.holidays']
        acrpol_obj = self.pool['hr.policy.accrual']
        acrline_obj = self.pool['hr.accrual.line']
        dToday = datetime.now().date()
        user_name = self.pool['res.users'].browse(cr, uid, uid, context=context).name
        wizard = self.browse(cr, uid, ids[0], context=context)
        
        if not wizard.employee_ids or len(wizard.employee_ids) == 0:
            raise orm.except_orm(_('Missing Information'), _('You must select at least one employee!'))
        
        for ee in wizard.employee_ids:
            
            dEmployment = ee_obj.get_initial_employment_date(cr, uid, [ee.id], context=context)[ee.id]
            if not dEmployment:
                raise orm.except_orm(_('Incomplete Data'),
                                     _('Unable to determine employment date for %s. Does this employee have a valid contract?' %(ee.name)))
            employment_date = dEmployment.strftime(OE_DFORMAT)
            
            # Remove all accrual records and any associated leave allocations of
            # the selected accrual policy line for this employee.
            #
            acrline_ids = acrline_obj.search(cr, uid,
                                             [('employee_id', '=', ee.id),
                                              ('accrual_id', '=', wizard.accrual_policy_line_id.accrual_id.id)],
                                             context=context)
            if len(acrline_ids) > 0:
                acrline_obj.unlink(cr, uid, acrline_ids, context=context)
            if wizard.accrual_policy_line_id.accrual_id.holiday_status_id:
                lvalloc_ids = lv_obj.search(cr, uid, [('employee_id', '=', ee.id),
                                                      ('type', '=', 'add'),
                                                      ('state', 'in', ['validate', 'validate1'])],
                                            order='id desc', context=context)
                # XXX - Refuse all allocations. As of yet we don't have a mechanism to
                #       refuse only those created for a certain date.
                #
                if len(lvalloc_ids) > 0:
                    wkf = netsvc.LocalService('workflow')
                    for lv in lv_obj.browse(cr, uid, lvalloc_ids, context=context):
                        new_note = (lv.notes and lv.notes or '') + _('\n%s - Refused because of Allocation Reset starting from %s by %s' %(dToday.strftime(OE_DFORMAT), employment_date, user_name))
                        lv_obj.write(cr, uid, [lv.id], {'notes': new_note}, context=context)
                        wkf.trg_validate(uid, 'hr.holidays', lv.id, 'refuse', cr)
                        
                        # Write appropriate state value to guarantee that it is
                        # changed. I've encountered some examples in production
                        # when the workflow change didn't work.
                        #
                        lv_obj.write(cr, uid, lvalloc_ids, {'state': 'refuse'},
                                     context=context)
                    if wizard.delete:
                        for lv in lv_obj.browse(cr, uid, lvalloc_ids, context=context):
                            wkf.trg_validate(uid, 'hr.holidays', lv.id, 'reset', cr)
                            lv_obj.write(cr, uid, lvalloc_ids, {'state': 'draft'},
                                         context=context)
                        lv_obj.unlink(cr, uid, lvalloc_ids, context=context)
            
            # Get employee's initial employment date and begin calculating the
            # accrual from that date.
            #
            acrpol_obj.do_accrual_by_period(cr, uid, wizard.accrual_policy_line_id, ee,
                                            dEmployment + timedelta(days=27), dToday,
                                            descr=_('Allocation Reset starting from %s, by %s' %(employment_date, user_name)),
                                            context=context)
            
        return {'type': 'ir.actions.act_window_close'}
