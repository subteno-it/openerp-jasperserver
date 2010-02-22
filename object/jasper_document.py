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

    def _get_formats(self, cr, uid, context=None):
        """
        Return the list of all types of document that can be generate by JasperServer
        """
        if not context:
            context = {}
        extension_obj = self.pool.get('jasper.document.extension')
        ext_ids = extension_obj.search(cr, uid, [])
        extensions = self.pool.get('jasper.document.extension').read(cr, uid, ext_ids)
        extensions = [(extension['jasper_code'], extension['name']+" (*."+extension['extension']+")") for extension in extensions]
        return extensions

    # TODO: Add One2many with model list and depth for each, use for ban process
    # TODO: Add dynamic parameter to send to jasper report server
    # TODO: Implement thhe possibility to dynamicaly generate a wizard
    _columns = {
        'name' : fields.char('Name', size=128, required=True), # button name
        'enabled' : fields.boolean('Active', help="Indicates if this document is active or not"),
        'model' : fields.many2one('ir.model', 'Object Model', required=True), #object model in ir.model
        'jasper_file' : fields.char('Jasper file', size=128, required=True), # jasper filename
        'group_ids': fields.many2many('res.groups', 'jasper_wizard_group_rel', 'document_id', 'group_id', 'Groups', ),
        'action' : fields.many2one('ir.actions.act_window', 'Actions'),
        'depth' : fields.integer('Depth', required=True),
        'format_choice' : fields.selection([('mono', 'Single Format'),('multi','Multi Format')], 'Format Choice', required=True),
        'format' : fields.selection(_get_formats, 'Formats'),
    }

    def create(self, cr, uid, vals, context=None):
        """
        Dynamicaly declare the wizard for this document
        """
        if not context:
            context = {}

        return super(jasper_document, self).create(cr, uid, vals, context=context)


    def write(self, cr, uid, ids, vals, context=None):
        """

        """
        if not context:
            context = {}

        return super(jasper_document, self).write(cr, uid, ids, vals, context=context)


    def unlink(self, cr, uid, ids, context=None):
        """

        """
        if not context:
            context = {}

        return super(jasper_document, self).unlink(cr, uid, ids)


    def add_wizard(self, cr, uid):
        """

        """
        if not context:
            context = {}

        return True


    def update_wizard(self, cr, uid):
        """

        """
        if not context:
            context = {}

        return True


    def remove_wizard(self, cr, uid):
        """

        """
        if not context:
            context = {}

        return True

jasper_document()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
