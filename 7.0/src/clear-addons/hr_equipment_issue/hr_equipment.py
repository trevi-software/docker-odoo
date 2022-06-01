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

import time

from openerp.osv import fields, orm
from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as OE_DFORMAT
from openerp.tools.translate import _

# Status of hr.equipment.issue.line
#
ISSUE_LINE_STATE_SELECTION_ISSUE = [
    ('draft', 'Draft'),
    ('issue', 'Issued'),
]

ISSUE_LINE_STATE_SELECTION_RETURN = [
    ('returned1', 'Returned in Good Condition'),
    ('returned2', 'Returned Damaged'),
    ('lost', 'Lost'),
]

class equipment(orm.Model):
    
    _name = 'hr.equipment.type'
    _description = 'List of equipment that can be issued to an employee'
    
    _columns = {
        'name': fields.char('Description', size=256, required=True),
        'code': fields.char('Code', size=32),
        'note': fields.text('Notes'),
    }

class equipment_issue(orm.Model):
    
    _name = 'hr.equipment.issue'
    _description = 'Equipment Issue'
    
    _columns = {
        'name': fields.char('Reference', size=32, readonly=True),
        'employee_id': fields.many2one('hr.employee', 'Employee', required=True, readonly=True,
                                       states={'draft': [('readonly', False)]}),
        'date': fields.date('Issue Date', required=True, readonly=True,
                            states={'draft': [('readonly', False)]}),
        'user_id': fields.many2one('res.users', 'Recorded by', required=True, readonly=True,
                                    states={'draft': [('readonly', False)]}),
        'line_ids': fields.one2many('hr.equipment.issue.line', 'issue_id', 'Issued Equipment',
                                    readonly=True, states={'draft': [('readonly', False)]}),
        'note': fields.text('Notes'),
        'state': fields.selection([('draft', 'Draft'), ('issue', 'Issued'), ('done', 'Done')],
                                  'State', readonly=True),
    }
    
    _defaults = {
        'state': 'draft',
        'user_id': lambda s, cr, uid, ctx: uid,
        'date': time.strftime(OE_DFORMAT),
    }
    
    def create(self, cr, uid, vals, context=None):
        
        eid = super(equipment_issue, self).create(cr, uid, vals, context=context)
        if eid:
            ref = self.pool.get('ir.sequence').next_by_code(cr, uid, 'equipment_issue.ref',
                                                            context=context)
            self.pool.get('hr.equipment.issue').write(cr, uid, eid, {'name': ref}, context=context)
        return eid
    
    def state_issue(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        for issue in self.browse(cr, uid, ids, context=context):
            line_ids = [line.id for line in issue.line_ids]
            if len(line_ids) > 0:
                self.pool.get('hr.equipment.issue.line').write(cr, uid, line_ids,
                                                               {'status': 'issue'},
                                                               context=context)
        
        self.write(cr, uid, ids, {'state': 'issue'}, context=context)
        
        return
    
    def all_done(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        res = True
        for issue in self.browse(cr, uid, ids, context=context):
            for line in issue.line_ids:
                if line.status not in [k for k,v in ISSUE_LINE_STATE_SELECTION_RETURN]:
                    res = False
                    break
        return res
    
    def state_done(self, cr, uid, ids, context=None):
        
        self.write(cr, uid, ids, {'state': 'done'}, context=context)
        return
    
    def unlink(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        for issue in self.browse(cr, uid, ids, context=context):
            
            if issue.state != 'draft':
                raise orm.except_orm(_('Permission Denied'),
                                     _('You may not delete an issue that is not in a "draft" state.'))

        return super(equipment_issue, self).unlink(cr, uid, ids, context=context)
    
    def issue_line_get_ids(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        line_obj = self.pool.get('hr.equipment.issue.line')
        line_ids = line_obj.search(cr, uid, [('issue_id', 'in', ids)])
        
        return line_ids

class equipment_issue_line(orm.Model):
    
    _name = 'hr.equipment.issue.line'
    _description = 'Equipment Issue Line Item'
    
    _columns = {
        'issue_id': fields.many2one('hr.equipment.issue', 'Equipment Issue', ondelete='restrict',
                                    readonly=True),
        'employee_id': fields.related('issue_id', 'employee_id', type='many2one', readonly=True,
                                      relation='hr.employee', store=True, string='Employee'),
        'date': fields.related('issue_id', 'date', type='date', store=True, string="Issued Date",
                               readonly=True),
        'user_id': fields.related('issue_id', 'user_id', type='many2one', relation='res.users',
                                  store=True, readonly=True, string="Issue Recorded By"),
        'type_id': fields.many2one('hr.equipment.type', 'Equipment', required=True),
        'serial': fields.char('Serial No', size=64),
        'status': fields.selection(ISSUE_LINE_STATE_SELECTION_ISSUE + ISSUE_LINE_STATE_SELECTION_RETURN,
                                   'Status', readonly=True),
        'return_date': fields.date('Return Date', readonly=True),
        'return_user_id': fields.many2one('res.users', 'Return Recorded by', readonly=True),
        'note': fields.text('Notes'),
    }
    
    _defaults = {
        'status': 'draft',
    }
    
    def name_get(self, cr, uid, ids, context=None):
        
        res = []
        for line in self.browse(cr, uid, ids, context=context):
            res.append((line.id, line.date +' '+ line.type_id.name +' '+ (line.serial and line.serial or '')))
        return res
    
    def write(self, cr, uid, ids, vals, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        rd_fields = ['issue_id', 'employee_id', 'date', 'user_id', 'type_id', 'serial']
        keys = [k for k,v in vals.items()]
        for line in self.browse(cr, uid, ids, context=context):
            is_rd = False
            for f in rd_fields:
                if f in keys:
                    is_rd = True,
                    break
            if line.status == 'draft' or (line.status == 'issue' and is_rd):
                continue
            elif line.status in ['returned1', 'returned2', 'lost']:
                raise orm.except_orm(_('Permission Denied'),
                                     _('You may not modify an issue line that does not have a "draft" status.'))

        return super(equipment_issue_line, self).write(cr, uid, ids, vals, context=context)
    
    def unlink(self, cr, uid, ids, context=None):
        
        if isinstance(ids, (int, long)):
            ids = [ids]
        
        for line in self.browse(cr, uid, ids, context=context):
            
            if line.status != 'draft':
                raise orm.except_orm(_('Permission Denied'),
                                     _('You may not delete an issue line that does not have a "draft" status.'))

        return super(equipment_issue_line, self).unlink(cr, uid, ids, context=context)
