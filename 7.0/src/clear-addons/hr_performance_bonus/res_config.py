# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Business Applications
#    Copyright (C) 2015 Clear ICT Solutions (<http://clearict.com>).
#    Copyright (C) 2004-2012 OpenERP S.A. (<http://openerp.com>).
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

from openerp.addons.decimal_precision import decimal_precision as dp
from openerp.osv import fields, osv

class bonus_config_settings(osv.TransientModel):
    
    _inherit = 'hr.config.settings'
    
    _columns = {
        'default_fixed_bonus_amount': fields.float('Bonus Amount for Fixed Points', digits_compute=dp.get_precision('Payroll')),
        'default_daily_bonus_amount': fields.float('Bonus Amount for Daily Points', digits_compute=dp.get_precision('Payroll')),
        'default_fixed_amt_bonus_amount': fields.float('Bonus Amount for Fixed Monetary Amount', digits_compute=dp.get_precision('Payroll')),
        'default_assistant_multiplier': fields.float('Multiplier for Assistants', digits_compute=dp.get_precision('Payroll')),
        'default_supervisor_multiplier': fields.float('Multiplier for Supervisors', digits_compute=dp.get_precision('Payroll')),
        'default_manager_multiplier': fields.float('Multiplier for Managers', digits_compute=dp.get_precision('Payroll')),
    }

    def get_default_parameters(self, cr, uid, fields, context=None):
        icp = self.pool['ir.config_parameter']
        fix_bns_amount = icp.get_param(cr, uid, 'hr.bonus.sheet.fixed_bonus_amount', default=0)
        daily_bns_amount = icp.get_param(cr, uid, 'hr.bonus.sheet.daily_bonus_amount', default=0)
        fix_amt_bns_amount = icp.get_param(cr, uid, 'hr.bonus.sheet.fixed_amt_bonus_amount', default=0)
        ass_multiply = icp.get_param(cr, uid, 'hr.bonus.sheet.assistant_multiplier', default=0)
        sup_multiply = icp.get_param(cr, uid, 'hr.bonus.sheet.supervisor_multiplier', default=0)
        mgr_multiply = icp.get_param(cr, uid, 'hr.bonus.sheet.manager_multiplier', default=0)
        return {
            'default_fixed_bonus_amount': float(fix_bns_amount),
            'default_daily_bonus_amount': float(daily_bns_amount),
            'default_fixed_amt_bonus_amount': float(fix_amt_bns_amount),
            'default_assistant_multiplier': float(ass_multiply),
            'default_supervisor_multiplier': float(sup_multiply),
            'default_manager_multiplier': float(mgr_multiply),
        }

    def set_default_parameters(self, cr, uid, ids, context=None):
        config = self.browse(cr, uid, ids[0], context)
        icp = self.pool['ir.config_parameter']
        icp.set_param(cr, uid, 'hr.bonus.sheet.fixed_bonus_amount', config.default_fixed_bonus_amount)
        icp.set_param(cr, uid, 'hr.bonus.sheet.daily_bonus_amount', config.default_daily_bonus_amount)
        icp.set_param(cr, uid, 'hr.bonus.sheet.fixed_amt_bonus_amount', config.default_fixed_amt_bonus_amount)
        icp.set_param(cr, uid, 'hr.bonus.sheet.assistant_multiplier', config.default_assistant_multiplier)
        icp.set_param(cr, uid, 'hr.bonus.sheet.supervisor_multiplier', config.default_supervisor_multiplier)
        icp.set_param(cr, uid, 'hr.bonus.sheet.manager_multiplier', config.default_manager_multiplier)


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
