# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP, 
#    Copyright (C) 2010 SYLEAM Info Services (<http://www.Syleam.fr/>) Damien CRIER
#
#    This file is a part of jasper_server
#
#    jasper_server is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    jasper_server is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


from osv import osv
from osv import fields

class jasper_document_extension(osv.osv):
    _name = 'jasper.document.extension'
    _description = 'Jasper Document Extension'

    _columns = {
            'name' : fields.char('Name', size=128, translate=True),
            'jasper_code' : fields.char('Code', size=32, required=True),
            'extension' : fields.char('Extension', size=10, required=True),
    }

jasper_document_extension()


class jasper_document(osv.osv):
    _name = 'jasper.document'
    _description = 'Jasper Document'

    _columns = {
            'name' : fields.char('Name', size=128, required=True), # button name
            'model' : fields.many2one('ir.model', 'Object Model', required=True), #object model in ir.model
            'jasper_file' : fields.char('Jasper file', size=128, required=True), # jasper filename
            'group_ids': fields.many2many('res.groups', 'jasper_wizard_group_rel', 'document_id', 'group-id', 'Groups', ),
            'action' : fields.many2one('ir.actions.act_window', 'Actions'),
    }

jasper_document()



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
