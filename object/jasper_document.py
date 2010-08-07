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
from jasper_server.wizard.format_choice import format_choice
import netsvc
import pooler
logger = netsvc.Logger()

def registered_wizard(name):
    """ Register dynamicaly the wizard for each entry"""
    gname = 'wizard.%s' % name
    if netsvc.service_exist(gname):
        if isinstance(netsvc.SERVICES[gname], format_choice):
            return
        del netsvc.SERVICES[gname]
    format_choice(name)
    logger.notifyChannel('jasper_server', netsvc.LOG_INFO, 'Register the jasper service [%s]' % name)


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
        'service': fields.char('Service name', size=64, required=True, 
            help='Enter the service name register at start by OpenERP Server'),
        'enabled' : fields.boolean('Active', help="Indicates if this document is active or not"),
        'model_id' : fields.many2one('ir.model', 'Object Model', required=True), #object model in ir.model
        'jasper_file' : fields.char('Jasper file', size=128, required=True), # jasper filename
        'group_ids': fields.many2many('res.groups', 'jasper_wizard_group_rel', 'document_id', 'group_id', 'Groups', ),
        'depth' : fields.integer('Depth', required=True),
        'format_choice' : fields.selection([('mono', 'Single Format'),('multi','Multi Format')], 'Format Choice', required=True),
        'format' : fields.selection(_get_formats, 'Formats'),
        'report_unit': fields.char('Report Unit', size=128, help='Enter the name for report unit in Jasper Server', required=True),
        'mode': fields.selection([('sql','SQL'),('xml','XML')], 'Mode', required=True),
        'before': fields.text('Before', help='This field must be filled with a valid SQL request and will be executed BEFORE the report edition',),
        'after': fields.text('After', help='This field must be filled with a valid SQL request and will be executed AFTER the report edition',),
        'attachment': fields.char('Save As Attachment Prefix', size=128, help='This is the filename of the attachment used to store the printing result. Keep empty to not save the printed reports. You can use a python expression with the object and time variables.'),
        'attachment_use': fields.boolean('Reload from Attachment', help='If you check this, then the second time the user prints with same attachment name, it returns the previous report.'),
        'toolbar': fields.boolean('Hide in toolbar', help='Check this if you want to hide button in toolbar'),
    }

    _defaults = {
        'format_choice': lambda *a: 'mono',
        'mode': lambda *a: 'sql',
        'attachment': lambda *a: False,
        'toolbar': lambda *a: True,
    }

    def __init__(self, pool, cr):
        """
        Automaticaly registered service at server starts
        """
        try:
            cr_new = pooler.get_db(cr.dbname).cursor()
            cr_new.execute("""SELECT 'jasper.'||service AS wiz_name FROM jasper_document WHERE enabled=true""")
            for rec in cr_new.dictfetchall():
                registered_wizard(rec['wiz_name'])
            cr_new.commit()
            cr_new.close()
        except Exception:
            pass

        super(jasper_document, self).__init__(pool, cr)

    def make_action(self, cr, uid, id, context=None):
        """
        If action doesn't exists we must create it
        Automatic registration to be directly available
        """
        b = self.browse(cr, uid, id, context=context)
        wiz_name = 'jasper.%s' % b.service
        registered_wizard(wiz_name)

        #if netsvc.service_exist(wiz_name):
        #    if isinstance(netsvc.SERVICES[wiz_name], format_choice):
        #        del netsvc.SERVICES[wiz_name]
        #try:
        #    format_choice(wiz_name)
        #except AssertionError:
        #    pass
        #logger.notifyChannel('jasper_server', netsvc.LOG_INFO, 'Register the jasper service [%s]' % b.name)

    def create(self, cr, uid, vals, context=None):
        """
        Dynamicaly declare the wizard for this document
        """
        if context is None:
            context = {}
        doc_id = super(jasper_document, self).create(cr, uid, vals, context=context)
        self.make_action(cr, uid, doc_id, context=context)
        return doc_id


    def write(self, cr, uid, ids, vals, context=None):
        """
        If the description change, we must update the action
        """
        if context is None:
            context = {}
        if not context.get('action'):
            for id in ids:
                self.make_action(cr, uid, id, context=context)
        return super(jasper_document, self).write(cr, uid, ids, vals, context=context)

jasper_document()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
