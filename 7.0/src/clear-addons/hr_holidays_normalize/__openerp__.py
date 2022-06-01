#-*- coding:utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Clear ICT Solutions <http://clearict.com>.
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
    'name': 'Normalize Holidays',
    'version': '1.0',
    'category': 'Human Resources',
    'description': """
Change start and end times of leaves
====================================
    """,
    'author':'Clear ICT Solutions <info@clearict.com>',
    'website':'http://clearict.com',
    'depends': [
        'hr_holidays',
        'hr_holidays_extension',
        'hr_schedule',
    ],
    'init_xml': [
    ],
    'update_xml': [
        'wizard/normalize.xml',
    ],
    'test': [
    ],
    'demo_xml': [
    ],
    'installable': True,
    'active': False,
}
