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

{
    'name': 'Currency Denominations',
    'category': 'Finance',
    'author': 'Michael Telahun Makonnen',
    'website':'http://miketelahun.wordpress.com',
    'version': '1.0',
    'description': """
Currency Denominations
======================

An extensible method for denoting the denominations of individual currencies.
    """,
    'depends': [
        'base',
        'decimal_precision',
    ],
    'init_xml': [],
    'update_xml': [
        'security/ir.model.access.csv',
        'res_currency_view.xml',
     ],
    'test': [
    ],
    'demo_xml': [],
    'active': False,
    'installable': True,
}
