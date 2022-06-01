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

from openerp.osv import fields, orm

class cert_type(orm.Model):
    
    _name = 'hr.certification.type'
    _description = 'Certification Type'
    
    _columns = {
        'name': fields.char('Name', size=256, required=True),
    }

class cert(orm.Model):
    
    _name = 'hr.certification'
    _description = 'Certification'
    
    _columns = {
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True),
        'type_id': fields.many2one('hr.certification.type', 'Type', required=True),
        'first_issued': fields.date('First Issued', required=True),
        'active': fields.boolean('Active'),
        'renewal_ids': fields.one2many('hr.certification.renewal', 'certification_id', 'Renewals'),
        'state': fields.selection([('draft', 'Draft'),
                                   ('open', 'Open'),
                                   ('renew', 'Renewal'),
                                   ('expire', 'Expired'),
                                   ('done', 'Done')], 'State'),
    }
    
    _defaults = {
        'state': 'draft',
        'active': True,
    }

    def name_get(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (long, int)):
            ids = [ids]
        
        res = []
        for cert in self.browse(cr, uid, ids, context=context):
            name = cert.type_id.name +': '+ cert.employee_id.name
            res.append((cert.id, name))
        
        return res
    
    def state_open(self, cr, uid, ids, context=None):
        
        self.write(cr, uid, ids, {'state': 'open'}, context=context)
        return True
    
    def state_renew(self, cr, uid, ids, context=None):
        
        self.write(cr, uid, ids, {'state': 'renew'}, context=context)
        return True
    
    def state_expired(self, cr, uid, ids, context=None):
        
        self.write(cr, uid, ids, {'state': 'expired'}, context=context)
        return True
    
    def state_done(self, cr, uid, ids, context=None):
        
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        return True

class cert_renewal(orm.Model):
    
    _name = 'hr.certification.renewal'
    _description = 'Certification Renewal Record'
    
    _columns = {
        'certification_id': fields.many2one('hr.certification', 'Certification'),
        'renewal_date': fields.date('Renewed On', required=True),
        'expiry_date': fields.date('Expires On', required=True),
    }
    
    _rec_name = 'renewal_date'

class employee(orm.Model):
    
    _inherit = 'hr.employee'
    
    _columns = {
        'certification_ids': fields.one2many('hr.certification', 'employee_id', 'Certifications'),
    }
