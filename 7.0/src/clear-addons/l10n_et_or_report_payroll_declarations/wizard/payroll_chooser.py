#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014 Michael Telahun Makonnen <mmakonnen@gmail.com>.
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

class payroll_chooser(orm.TransientModel):
    
    _name = 'hr.payroll.chooser.declaration'
    _description = 'Payroll Chooser for Declarations'
    
    def _declaration_list(self, cr, uid, context=None):
        
        res = [
            ('fit', _('Federal Income Tax Withholding')),
            ('pension', _('Pension Contribution')),
        ]
        return res
    
    _columns = {
        'register_id': fields.many2one('hr.payroll.register', 'Payroll Register', required=True),
        'declaration_type': fields.selection(_declaration_list, 'Declaration Type',
                                             required=True),
        'payroll_type': fields.selection([('orig', 'Original'), ('amend', 'Amended')],
                                         'Payroll Type', required=True),
        'tax_period': fields.char('Tax Period', size=64, required=True),
        'month': fields.char('Month', size=64, required=True),
        'year': fields.char('Year', size=64, required=True),
    }
    
    def _get_register_id(self, cr, uid, context=None):
        
        if context == None:
            context = {}
        
        register_id = context.get('active_id', False)
        if not register_id:
            register_id = context.get('active_ids', False) and context['active_ids'][0] or False
        return register_id
    
    _defaults = {
        'register_id': _get_register_id,
        'payroll_type': 'amend',
    }
    
    def get_report_name(self, cr, uid, datas, context=None):
        
        report_name = False
        if datas['form'].get('declaration_type', '') == 'pension':
            report_name = 'hr_payroll_pension_or_report'
        elif datas['form'].get('declaration_type', '') == 'fit':
            report_name = 'hr_payroll_fit_or_report'
        
        return report_name
    
    def print_report(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        datas = {'form': self.read(cr, uid, ids, context=context)[0],
                 'model': 'hr.payroll.register'}
        datas['ids'] = [datas['form']['register_id'][0]]
        
        report_name = self.get_report_name(cr, uid, datas, context=context)
        return {
            'type': 'ir.actions.report.xml',
            'report_name': report_name,
            'datas': datas,
        }
