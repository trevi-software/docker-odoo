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

from openerp.osv import fields, osv
from openerp.tools.translate import _

ET_MONTHS_SELECTION_AM = [
    u'መስከረም', u'ጥቅምት', u'ህዳር', u'ታህሳስ', u'ጥር',
    u'የካቲት', u'መጋቢት', u'ሚያዝያ', u'ግንቦት', u'ሰኔ',
    u'ሃምሌ', u'ነሐሴ', u'ጳጉሜ', 
]

ET_MONTHS_SELECTION = [
    ('1', _('Meskerem')),
    ('2', _('Tikimt')),
    ('3', _('Hedar')),
    ('4', _('Tahsas')),
    ('5', _('Tir')),
    ('6', _('Yekatit')),
    ('7', _('Megabit')),
    ('8', _('Miazia')),
    ('9', _('Genbot')),
    ('10', _('Senie')),
    ('11', _('Hamle')),
    ('12', _('Nehassie')),
    ('13', _('Pagume')),
]

ET_DAYOFMONTH_SELECTION = [
    ('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', '5'), 
    ('6', '6'), ('7', '7'), ('8', '8'), ('9', '9'), ('10', '10'), 
    ('11', '11'), ('12', '12'), ('13', '13'), ('14', '14'), ('15', '15'), 
    ('16', '16'), ('17', '17'), ('18', '18'), ('19', '19'), ('20', '20'), 
    ('21', '21'), ('22', '22'), ('23', '23'), ('24', '24'), ('25', '25'), 
    ('26', '26'), ('27', '27'), ('28', '28'), ('29', '29'), ('30', '30'), 
]
