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

from openerp.osv import fields,osv

class res_partner(osv.Model):
    
    _inherit = 'res.partner'
    
    _columns = {
        'ethiopic_name': fields.char('Ethiopic Name', size=1024, select=True),
        'tin': fields.char('TIN', size=10, select=True),
        'vat_no': fields.char('VAT No', size=10, select=True),
        'subcity': fields.char('Subcity (Woreda)', size=256, select=True),
        'kebele': fields.char('Kebele', size=8, select=True),
        'houseno': fields.char('House No', size=16, select=True),
        'et_subcity': fields.char('Subcity (Woreda)', size=256, select=True),
        'et_city': fields.char('City', size=256, select=True),
        'pobox': fields.char('P.O. Box', size=16),
    }

class res_company(osv.Model):
    
    _inherit = 'res.company'
    
    _columns = {
        'ethiopic_name': fields.related('partner_id', 'ethiopic_name', string='Ethiopic Name',
                                        size=1024, store=True, type='char'),
    }

class res_country_state(osv.Model):
    
    _inherit = 'res.country.state'
    
    _columns = {
        'ethiopic_name': fields.char('Ethiopic Name', size=256, select=True),
        'et_code': fields.char('Ethiopic Code', size=16, select=True),
    }
