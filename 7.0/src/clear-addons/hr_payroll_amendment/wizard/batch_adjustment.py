#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

from openerp.osv import fields, orm
from openerp.tools.translate import _
from openerp.tools.float_utils import float_compare

class hr_payslip_employees(orm.TransientModel):

    _name ='payroll.amendment.wizard'
    _description = 'Generate Payroll Amendments for selected employees'
    
    _columns = {
        'employee_ids': fields.many2many('hr.employee', 'hr_employee_payroll_amendment_rel',
                                         'pa_id', 'employee_id', 'Employees'),
        'payroll_register_id': fields.many2one('hr.payroll.register', 'Payroll Register',
                                               required=True),
        'next_pp_id': fields.many2one('hr.payroll.period', 'Destination Payroll Period'),
        'memo': fields.text('Notes'),
    }
    
    def create_adjustments(self, cr, uid, ids, context=None):
        
        pam_obj = self.pool.get('hr.payroll.postclose.amendment')
        psam_obj = self.pool.get('hr.payslip.amendment')
        ps_obj = self.pool.get('hr.payslip')
        
        if context is None:
            context = {}
        
        wizard = self.browse(cr, uid, ids, context=context)[0]
        if not wizard.employee_ids or len (wizard.employee_ids) == 0:
            raise orm.except_orm(_("Warning !"), _("You must select at least one employee to generate amendments."))
        
        res_ids = []
        for ee in wizard.employee_ids:
            
            # Find this employee's pay slip
            ps = False
            _break = False
            for run in wizard.payroll_register_id.run_ids:
                for payslip in run.slip_ids:
                    if payslip.employee_id.id == ee.id:
                        ps = payslip
                        _break = True
                        break
                if _break:
                    break
            
            if ps == False:
                #raise orm.except_orm(_("Warning !"), _("Unable to find pay slip for %s" % (ee.name)))
                continue
            
            res = {
                'employee_id': ee.id,
                'pp_id': wizard.payroll_register_id.period_id.id,
                'next_pp_id': wizard.next_pp_id.id,
                'old_payslip_id': ps.id,
                'memo': wizard.memo,
            }
            
            res_id = pam_obj.create(cr, uid, res, context=context)
            pam_obj.create_amended_payslip(cr, uid, [res_id], context=context)
            
            # Check if there is any difference and discard any that don't show one
            diff = pam_obj.get_net_difference(cr, uid, res_id, context=context)
            if float_compare(diff['new']['net'], diff['old']['net'], precision_digits=2) == 0:
                pam = pam_obj.browse(cr, uid, res_id, context=context)
                psam_obj.unlink(cr, uid, [pa.id for pa in pam.payslip_amendment_ids], context=context)
                ps_obj.unlink(cr, uid, [pam.new_payslip_id.id], context=context)
                pam_obj.unlink(cr, uid, [pam.id], context=context)
            else:
                res_ids.append(res_id)
        
        return {
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.payroll.postclose.amendment',
            'domain': [('id', 'in', res_ids)],
            'type': 'ir.actions.act_window',
            'target': 'current',
            'nodestroy': True,
            'context': context,
        }
