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

{
    'name': 'Initial Annual Leave',
    'version': '1.0',
    'category': 'Generic Modules/Human Resources',
    'description': """
Transfer Annual Leave from Previous System
==========================================

This module adds a field to hr.employee for transfering/importing annual leave from a
previous system. The hr.employee record being imported must have field called:
    initial_annual_leave
and there should be a holiday status called:
    LVANNUAL
This holiday status should be associate with an accrual account.
    """,
    'author':'Michael Telahun Makonnen <mmakonnen@gmail.com>',
    'website':'http://miketelahun.wordpress.com',
    'depends': [
        'hr_accrual',
        'hr_holidays',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'wizard/al_view.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
