# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP,
#    Copyright (C) 2010-2011 SYLEAM Info Services (<http://www.Syleam.fr/>) Damien CRIER
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
from tools.sql import drop_view_if_exists
from tools.translate import _
from jasper_server.common import registered_report
import ir
import logging

_logger = logging.getLogger('jasper_server')


class jasper_document_extension(osv.osv):
    _name = 'jasper.document.extension'
    _description = 'Jasper Document Extension'

    _columns = {
        'name': fields.char('Name', size=128, translate=True),
        'jasper_code': fields.char('Code', size=32, required=True),
        'extension': fields.char('Extension', size=10, required=True),
    }

jasper_document_extension()


class jasper_document(osv.osv):
    _name = 'jasper.document'
    _description = 'Jasper Document'
    _order = 'sequence'

    def _get_formats(self, cr, uid, context=None):
        """
        Return the list of all types of document that can be generate by JasperServer
        """
        if not context:
            context = {}
        extension_obj = self.pool.get('jasper.document.extension')
        ext_ids = extension_obj.search(cr, uid, [])
        extensions = self.pool.get('jasper.document.extension').read(cr, uid, ext_ids)
        extensions = [(extension['jasper_code'], extension['name'] + " (*." + extension['extension'] + ")") for extension in extensions]
        return extensions

    # TODO: Add One2many with model list and depth for each, use for ban process
    # TODO: Implement thhe possibility to dynamicaly generate a wizard
    _columns = {
        'name': fields.char('Name', size=128, translate=True, required=True),  # button name
        'service': fields.char('Service name', size=64, required=True,
            help='Enter the service name register at start by OpenERP Server'),
        'enabled': fields.boolean('Active', help="Indicates if this document is active or not"),
        'model_id': fields.many2one('ir.model', 'Object Model', required=True),  # object model in ir.model
        'jasper_file': fields.char('Jasper file', size=128),  # jasper filename
        'group_ids': fields.many2many('res.groups', 'jasper_wizard_group_rel', 'document_id', 'group_id', 'Groups', ),
        'depth': fields.integer('Depth', required=True),
        'format_choice': fields.selection([('mono', 'Single Format'), ('multi', 'Multi Format')], 'Format Choice', required=True),
        'format': fields.selection(_get_formats, 'Formats'),
        'report_unit': fields.char('Report Unit', size=128, help='Enter the name for report unit in Jasper Server'),
        'mode': fields.selection([('sql', 'SQL'), ('xml', 'XML'), ('multi', 'Multiple Report')], 'Mode', required=True),
        'before': fields.text('Before', help='This field must be filled with a valid SQL request and will be executed BEFORE the report edition',),
        'after': fields.text('After', help='This field must be filled with a valid SQL request and will be executed AFTER the report edition',),
        'attachment': fields.char('Save As Attachment Prefix', size=255, help='This is the filename of the attachment used to store the printing result. Keep empty to not save the printed reports. You can use a python expression with the object and time variables.'),
        'attachment_use': fields.boolean('Reload from Attachment', help='If you check this, then the second time the user prints with same attachment name, it returns the previous report.'),
        'toolbar': fields.boolean('Hide in toolbar', help='Check this if you want to hide button in toolbar'),
        'param_ids': fields.one2many('jasper.document.parameter', 'document_id', 'Parameters', ),
        'ctx': fields.char('Context', size=128, help="Enter condition with context does match to see the print action\neg: context.get('foo') == 'bar'"),
        'sql_view': fields.text('SQL View', help='Insert your SQL view, if the report is base on it'),
        'sql_name': fields.char('Name of view', size=128, ),
        'child_ids': fields.many2many('jasper.document', 'jasper_document_multi_rel', 'source_id', 'destin_id', 'Child report', help='Select reports to launch when this report is called'),
        'sequence': fields.integer('Sequence', help='The sequence is used when launch a multple report, to select the order to launch'),
        'only_one': fields.boolean('Launch one time for all ids', help='Launch the report only one time on multiple id'),
        'duplicate': fields.char('Duplicate', size=256, help="Indicate the number of duplicate copie, use o as object to evaluate\neg: o.partner_id.copy\nor\n'1'", ),
        'lang': fields.char('Lang', size=256, help="Indicate the lang to use for this report, use o as object to evaluate\neg: o.partner_id.lang\nor\n'fr_FR'\ndefault use user's lang"),
        'report_id': fields.many2one('ir.actions.report.xml', 'Report link', readonly=True, help='Link to the report in ir.actions.report.xml'),
        'check_sel': fields.selection([('none', 'None'), ('simple', 'Simple'), ('func', 'Function')], 'Checking type',
                        help='if None, no check\nif Simple, define on Check Simple the condition\n if function, the object have check_print function'),
        'check_simple': fields.char('Check Simple', size=256, help="This code inside this field must return True to send report execution\neg o.state in ('draft', 'open')"),
        'message_simple': fields.char('Return message', size=256, translate=True, help="Error message when check simple doesn't valid"),
        'label_ids': fields.one2many('jasper.document.label', 'document_id', 'Labels'),
    }

    _defaults = {
        'format_choice': lambda *a: 'mono',
        'mode': lambda *a: 'sql',
        'attachment': lambda *a: False,
        'toolbar': lambda *a: True,
        'depth': lambda *a: 0,
        'sequence': lambda *a: 100,
        'format': lambda *a: 'PDF',
        'duplicate': lambda *a: "'1'",
        'lang': lambda *a: False,
        'report_id': lambda *a: False,
        'check_sel': lambda *a: 'none',
        'check_simple': lambda *a: False,
        'message_simple': lambda *a: False,
    }

    def __init__(self, pool, cr):
        """
        Automaticaly registered service at server starts
        """
        super(jasper_document, self).__init__(pool, cr)

    def make_action(self, cr, uid, id, context=None):
        """
        Create an entry in ir_actions_report_xml
        and ir.values
        """
        b = self.browse(cr, uid, id, context=context)
        act_report_obj = self.pool.get('ir.actions.report.xml')

        doc = self.browse(cr, uid, id, context=context)
        if doc.report_id:
            _logger.info('Update "%s" service' % doc.name)
            args = {
                'name': doc.name,
                'report_name': 'jasper.' + doc.service,
                'model': doc.model_id.model,
                'groups_id': [(6, 0, [x.id for x in doc.group_ids])],
                'header': False,
                'multi': doc.toolbar,
            }
            act_report_obj.write(cr, uid, [doc.report_id.id], args, context=context)
        else:
            _logger.info('Create "%s" service' % doc.name)
            args = {
                'name': doc.name,
                'report_name': 'jasper.' + doc.service,
                'model': doc.model_id.model,
                'report_type': 'jasper',
                'groups_id': [(6, 0, [x.id for x in doc.group_ids])],
                'header': False,
                'multi': doc.toolbar,
            }
            report_id = act_report_obj.create(cr, uid, args, context=context)
            cr.execute("""UPDATE jasper_document SET report_id=%s WHERE id=%s""", (report_id, id))
            value = 'ir.actions.report.xml,' + str(report_id)
            ir.ir_set(cr, uid, 'action', 'client_print_multi', doc.name, [doc.model_id.model], value, replace=False, isobject=True)
        registered_report('jasper.' + doc.service)

    def action_values(self, cr, uid, report_id, context=None):
        """
        Search ids for reports
        """
        args = [
            ('key2', '=', 'client_print_multi'),
            ('value', '=', 'ir.actions.report.xml,%d' % report_id),
            ('object', '=', True),
        ]
        return self.pool.get('ir.values').search(cr, uid, args, context=context)

    def create_values(self, cr, uid, id, context=None):
        doc = self.browse(cr, uid, id, context=context)
        if not self.action_values(cr, uid, doc.report_id.id, context=context):
            value = 'ir.actions.report.xml,%d' % doc.report_id.id
            ir.ir_set(cr, uid, 'action', 'client_print_multi', doc.name, [doc.model_id.model], value, replace=False, isobject=True)
        return True

    def unlink_values(self, cr, uid, id, context=None):
        """
        Only remove link in ir.values, not the report
        """
        doc = self.browse(cr, uid, id, context=context)
        for v in self.action_values(cr, uid, doc.report_id.id, context=context):
            ir.ir_del(cr, uid, v)
        return True

    def create(self, cr, uid, vals, context=None):
        """
        Dynamicaly declare the wizard for this document
        """
        if context is None:
            context = {}
        doc_id = super(jasper_document, self).create(cr, uid, vals, context=context)
        self.make_action(cr, uid, doc_id, context=context)

        # Check if view and create it in the database
        if vals.get('sql_name') and vals.get('sql_view'):
            drop_view_if_exists(cr, vals.get('sql_name'))
            sql_query = 'CREATE OR REPLACE VIEW %s AS\n%s' % (vals['sql_name'], vals['sql_view'])
            cr.execute(sql_query)
        return doc_id

    def write(self, cr, uid, ids, vals, context=None):
        """
        If the description change, we must update the action
        """
        if context is None:
            context = {}

        if vals.get('sql_name') or vals.get('sql_view'):
            sql_name = vals.get('sql_name', self.browse(cr, uid, ids[0]).sql_name)
            sql_view = vals.get('sql_view', self.browse(cr, uid, ids[0]).sql_view)
            drop_view_if_exists(cr, sql_name)
            sql_query = 'CREATE OR REPLACE VIEW %s AS\n%s' % (sql_name, sql_view)
            cr.execute(sql_query, (ids,))

        res = super(jasper_document, self).write(cr, uid, ids, vals, context=context)

        if not context.get('action'):
            for id in ids:
                self.make_action(cr, uid, id, context=context)

            if 'enabled' in vals:
                if vals['enabled']:
                    for id in ids:
                        self.create_values(cr, uid, id, context)
                else:
                    for id in ids:
                        self.unlink_values(cr, uid, id, context)
        return res

    def copy(self, cr, uid, id, default=None, context=None):
        """
        When we duplicate code, we must remove some field, before
        """
        if context is None:
            context = {}

        if default is None:
            default = {}

        doc = self.browse(cr, uid, id, context=context)

        default['report_id'] = False
        default['service'] = doc.service + '_copy'
        default['name'] = doc.name + _(' (copy)')
        return super(jasper_document, self).copy(cr, uid, id, default, context=context)

    def unlink(self, cr, uid, ids, context=None):
        """
        When remove jasper_document, we must remove data to ir.actions.report.xml and ir.values
        """
        if context is None:
            context = {}

        for doc in self.browse(cr, uid, ids, context=context):
            if doc.report_id:
                self.unlink_values(cr, uid, doc.id, context)
                self.pool.get('ir.actions.report.xml').unlink(cr, uid, [doc.report_id.id], context=context)

        return super(jasper_document, self).unlink(cr, uid, ids, context=context)

jasper_document()


class jasper_document_parameter(osv.osv):
    _name = 'jasper.document.parameter'
    _description = 'Add parameter to send to jasper server'

    _columns = {
        'name': fields.char('Name', size=32, help='Name of the jasper parameter, the prefix must be OERP_', required=True),
        'code': fields.char('Code', size=256, help='Enter the code to retrieve data', required=True),
        'enabled': fields.boolean('Enabled'),
        'document_id': fields.many2one('jasper.document', 'Document'),
    }

    _defaults = {
        'enabled': lambda *a: True,
    }

jasper_document_parameter()


class jasper_document_label(osv.osv):
    _name = 'jasper.document.label'
    _description = 'Manage label in document, for different language'

    _columns = {
        'name': fields.char('Parameter', size=64, help='Name of the parameter send to JasperServer, prefix with I18N_\neg: test become I18N_TEST as parameter', required=True),
        'value': fields.char('Value', size=256, help='Name of the label, this field must be translate in all languages available in the database', required=True, translate=True),
        'document_id': fields.many2one('jasper.document', 'Document'),
    }

jasper_document_label()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
