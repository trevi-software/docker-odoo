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

{
    'name': 'Payroll Direct Deposit in Payroll Period',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Integrate Direct Deposits into Payroll Period
=============================================
    """,
    'author':'Clear ICT Solutions <info@clearict.com>',
    'website':'http://clearict.com',
    'depends': [
        'hr_payroll_direct_deposit',
        'hr_payroll_period',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'payroll_period_end_view.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
