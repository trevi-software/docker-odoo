# -*- coding: utf-8 -*-
##############################################################################
#    
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>.
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
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

import logging
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

#-------------------------------------------------------------
# Amharic
#-------------------------------------------------------------

to_19 = ( u'ዜሮ',  u'አንድ',   u'ሁለት',  u'ሦስት', u'አራት',   u'አምስት',   u'ስድስት',
            u'ሰባት', u'ስምንት', u'ዘጠኝ', u'አስር',   u'አስራአንድ', u'አስራሁለት', u'አስራሦስት',
            u'አስራአራት', u'አስራአምስት', u'አስራስድስት', u'አስራሰባት', u'አስራስምንት', u'አስራዘጠኝ' )
tens  = ( u'ሃያ', u'ሠላሳ', u'አርባ', u'ሃምሳ', u'ሲልሳ', u'ሰባ', u'ሰማንያ ', u'ዘጠና')
denom = ( u'',
            u'ሺህ', u'ሚልየን', u'ቢልየን', u'ትሪልየን', u'ኳድሪልየን',
            u'ክዊንቲልየን',  u'ሴክስቲልየን', u'ሴፕቲልየን', u'ኦክቲልየን', u'ኖንቲልየን',
            u'ዴሲልየን', u'አንደሲልየን', u'ዱዎዴሲልየን', u'ትሬዴሲልየን', u'ኩዋትሮዴሲልየን',
            u'ሴክስዴሲልየን', u'ሴፕቴንደሲልየን', u'ኦክቶደሲልየን', u'ኖቬምደሲልየን', u'ቪጊንቲልየን' )

def _convert_nn(val):
    """convert a value < 100 to English.
    """
    if val < 20:
        return to_19[val]
    for (dcap, dval) in ((k, 20 + (10 * v)) for (v, k) in enumerate(tens)):
        if dval + 10 > val:
            if val % 10:
                return dcap + u'-' + to_19[val % 10]
            return dcap

def _convert_nnn(val):
    """
        convert a value < 1000 to amharic, special cased because it is the level that kicks 
        off the < 100 special case.  The rest are more general.  This also allows you to
        get strings in the form of 'forty-five hundred' if called directly.
    """
    word = u''
    (mod, rem) = (val % 100, val // 100)
    if rem > 0:
        word = to_19[rem] + u' መቶ'
        if mod > 0:
            word += u' '
    if mod > 0:
        word += _convert_nn(mod)
    return word

def amharic_number(val):
    if val < 100:
        return _convert_nn(val)
    if val < 1000:
        return _convert_nnn(val)
    for (didx, dval) in ((v - 1, 1000 ** v) for v in range(len(denom))):
        if dval > val:
            mod = 1000 ** didx
            l = val // mod
            r = val - (l * mod)
            ret = _convert_nnn(l) + u' ' + denom[didx]
            if r > 0:
                ret = ret + u', ' + amharic_number(r)
            return ret

def amount_to_text(number, currency=u'ብር'):
    number = '%.2f' % number
    units_name = currency
    list = str(number).split('.')
    start_word = amharic_number(int(list[0]))
    end_word = amharic_number(int(list[1]))
    cents_number = int(list[1])
    cents_name = (cents_number > 1) and u'ሳንቲም' or u'ሳንቲም'

    return u' '.join(filter(None, [start_word, units_name, (start_word or units_name) and (end_word or cents_name) and u'ከ', end_word, cents_name]))


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
