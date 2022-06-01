#-*- coding:utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyrigth (C) 2013 Michael Telahun Makonnen <mmakonnen@gmail.com>
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    d$
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

from report import report_sxw

class Parser(report_sxw.rml_parse):
    def __init__(self, cr, uid, name, context):
        super(Parser, self).__init__(cr, uid, name, context)
        self.localcontext.update({
            'percent': self.percent,
            'wage': self.wage,
            'total_curr': self.total_curr,
            'total_new': self.total_new,
            'total_diff': self.total_diff,
            'total_diff_percent': self.total_diff_percent,
        })
    
    def total_curr(self, run):
        
        res = 0
        for incr in run.increment_ids:
            res += incr.current_wage
        return self.wage(res)
    
    def total_new(self, run):
        
        res = 0
        for incr in run.increment_ids:
            res += incr.wage
        return self.wage(res)
    
    def total_diff(self, run):
        
        res = 0
        for incr in run.increment_ids:
            res += incr.wage_difference
        return self.wage(res)
    
    def total_diff_percent(self, run):
        
        res = 0
        count = 0
        for incr in run.increment_ids:
            res += incr.wage_difference_percent
            count += 1
        return self.wage(res / count)
    
    def percent(self, p):
        
        return self.wage(p)
    
    def wage(self, w):
        
        return "%.2f" % w
