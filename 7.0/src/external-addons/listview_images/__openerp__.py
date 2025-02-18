# Copyright (C) 2013  Marcel van der Boom <marcel@hsdev.com>
#
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>
{
    'name': "Enable image-display in list view",
    'description': "Makes binary image fields display in list and tree views",
    'category': 'Web',
    'depends': ['web'],
    'js': ['static/src/js/view_list.js'],
    'installable': True,
    'active': False,
}
