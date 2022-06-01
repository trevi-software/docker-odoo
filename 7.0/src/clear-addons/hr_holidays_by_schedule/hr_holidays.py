#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
#    Copyright (c) 2005-2006 Axelor SARL. (http://www.axelor.com)
#    and 2004-2010 Tiny SPRL (<http://tiny.be>).
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

from openerp.osv import fields, osv

class hr_holidays(osv.osv):
    
    _name = 'hr.holidays'
    _inherit = 'hr.holidays'

    def onchange_employee(self, cr, uid, ids, employee_id):
        return super(hr_holidays, self).onchange_employee(cr, uid, ids, employee_id)
    
    def onchange_date_from(self, cr, uid, ids, no_days, date_from, employee_id, hs_id, context=None):
        return self.onchange_bynumber(cr, uid, ids, no_days, date_from, employee_id, hs_id, context=context)

    def onchange_date_to(self, cr, uid, ids, no_days, date_from, date_to, employee_id, hs_id, context=None):
        return self.onchange_enddate(cr, uid, ids, employee_id, date_from, date_to, hs_id, no_days)
