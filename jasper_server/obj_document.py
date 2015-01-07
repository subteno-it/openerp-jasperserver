# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP,
#    Copyright (C) 2010-2011 SYLEAM Info Services (<http://www.Syleam.fr/>)
#                            Damien CRIER
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


from openerp.osv import osv
from openerp.osv import orm
from openerp.osv import fields
from openerp.tools.sql import drop_view_if_exists
from openerp.tools.translate import _
from openerp.addons.jasper_server.common import KNOWN_PARAMETERS
from StringIO import StringIO
from lxml import etree
import base64
import jasperlib
import logging

_logger = logging.getLogger(__name__)

JRXML_NS = {
    'root': 'http://jasperreports.sourceforge.net/jasperreports',
}


class jasper_document_extension(orm.Model):
    _name = 'jasper.document.extension'
    _description = 'Jasper Document Extension'

    _columns = {
        'name': fields.char('Name', size=128, translate=True),
        'jasper_code': fields.char('Code', size=32, required=True),
        'extension': fields.char('Extension', size=10, required=True),
    }


class jasper_document(orm.Model):
    _name = 'jasper.document'
    _description = 'Jasper Document'
    _order = 'sequence'

    def _get_formats(self, cr, uid, context=None):
        """
        Return the list of all types of document that can be
        generate by JasperServer
        """
        if not context:
            context = {}
        extension_obj = self.pool.get('jasper.document.extension')
        ext_ids = extension_obj.search(cr, uid, [], context=context)
        extensions = extension_obj.read(cr, uid, ext_ids, context=context)
        ext = [(extension['jasper_code'],
                extension['name'] + " (*." + extension['extension'] + ")")
               for extension in extensions]
        return ext

    _columns = {
        'name': fields.char('Name', size=128, translate=True, required=True,
                            placeholder="InvoiceJ"),  # button name
        'enabled': fields.boolean('Active',
                                  help="Indicates if this document is active or not"),  # noqa
        'model_id': fields.many2one('ir.model', 'Object Model', required=True),
        'server_id': fields.many2one('jasper.server', 'Server',
                                     help='Select specific JasperServer'),
        'jasper_file': fields.char('Jasper file', size=128),  # jasper filename
        'group_ids': fields.many2many('res.groups', 'jasper_wizard_group_rel',
                                      'document_id', 'group_id', 'Groups', ),
        'depth': fields.integer('Depth', required=True),
        'format_choice': fields.selection([('mono', 'Single Format'),
                                           ('multi', 'Multi Format')],
                                          'Format Choice', required=True),
        'format': fields.selection(_get_formats, 'Formats'),
        'report_unit': fields.char('Report Unit', size=128,
                                   help='Enter the name for report unit in Jasper Server'),  # noqa
        'mode': fields.selection([('sql', 'SQL'), ('xml', 'XML'),
                                  ('multi', 'Multiple Report')], 'Mode',
                                 required=True),
        'before': fields.text('Before',
                              help='This field must be filled with a valid SQL request and will be executed BEFORE the report edition',),  # noqa
        'after': fields.text('After',
                             help='This field must be filled with a valid SQL request and will be executed AFTER the report edition',),  # noqa
        'attachment': fields.char('Save As Attachment Prefix', size=255,
                                  help='This is the filename of the attachment used to store the printing result. Keep empty to not save the printed reports. You can use a python expression with the object and time variables.'),  # noqa
        'attachment_use': fields.boolean('Reload from Attachment',
                                         help='If you check this, then the second time the user prints with same attachment name, it returns the previous report.'),  # noqa
        'param_ids': fields.one2many('jasper.document.parameter',
                                     'document_id', 'Parameters', ),
        'ctx': fields.char('Context', size=128,
                           help="Enter condition with context does match to see the print action\neg: context.get('foo') == 'bar'"),  # noqa
        'sql_view': fields.text('SQL View',
                                help='Insert your SQL view, if the report is base on it'),  # noqa
        'sql_name': fields.char('Name of view', size=128, ),
        'child_ids': fields.many2many('jasper.document',
                                      'jasper_document_multi_rel',
                                      'source_id',
                                      'destin_id',
                                      'Child report',
                                      help='Select reports to launch when this report is called'),  # noqa
        'sequence': fields.integer('Sequence',
                                   help='The sequence is used when launch a multple report, to select the order to launch'),  # noqa
        'only_one': fields.boolean('Launch one time for all ids',
                                   help='Launch the report only one time on multiple id'),  # noqa
        'duplicate': fields.char('Duplicate', size=256,
                                 help="Indicate the number of duplicate copie, use o as object to evaluate\neg: o.partner_id.copy\nor\n'1'", ),  # noqa
        'lang': fields.char('Lang', size=256,
                            help="Indicate the lang to use for this report, use o as object to evaluate\neg: o.partner_id.lang\nor\n'fr_FR'\ndefault use user's lang"),  # noqa
        'report_id': fields.many2one('ir.actions.report.xml', 'Report link',
                                     readonly=True, help='Link to the report in ir.actions.report.xml'),  # noqa
        'check_sel': fields.selection([('none', 'None'),
                                       ('simple', 'Simple'),
                                       ('func', 'Function')],
                                      'Checking type',
                                      help='if None, no check\nif Simple, define on Check Simple the condition\n if function, the object have check_print function'),  # noqa
        'check_simple': fields.char('Check Simple', size=256,
                                    help="This code inside this field must return True to send report execution\neg o.state in ('draft', 'open')"),  # noqa
        'message_simple': fields.char('Return message', size=256,
                                      translate=True,
                                      help="Error message when check simple doesn't valid"),  # noqa
        'label_ids': fields.one2many('jasper.document.label', 'document_id',
                                     'Labels'),
        'pdf_begin': fields.char('PDF at begin', size=128,
                                 help='Name of the PDF file store as attachment to add at the first page (page number not recompute)'),  # noqa
        'pdf_ended': fields.char('PDF at end', size=128,
                                 help='Name of the PDF file store as attachment to add at the last page (page number not recompute)'),  # noqa
    }

    _defaults = {
        'format_choice': 'mono',
        'mode': 'sql',
        'attachment': False,
        'depth': 0,
        'sequence': 100,
        'format': 'PDF',
        'duplicate': "'1'",
        'lang': False,
        'report_id': False,
        'check_sel': 'none',
        'check_simple': False,
        'message_simple': False,
    }

    def make_action(self, cr, uid, id, context=None):
        """
        Create an entry in ir_actions_report_xml
        and ir.values
        """
        act_report_obj = self.pool.get('ir.actions.report.xml')

        doc = self.browse(cr, uid, id, context=context)
        if doc.report_id:
            _logger.info('Update "%s" service' % doc.name)
            args = {
                'name': doc.name,
                'report_name': 'jasper.report_%d' % (doc.id,),
                'model': doc.model_id.model,
                'groups_id': [(6, 0, [x.id for x in doc.group_ids])],
                'header': False,
                'multi': False,
            }
            act_report_obj.write(cr, uid, [doc.report_id.id], args,
                                 context=context)
        else:
            _logger.info('Create "%s" service' % doc.name)
            args = {
                'name': doc.name,
                'report_name': 'jasper.report_%d' % (doc.id,),
                'model': doc.model_id.model,
                'report_type': 'jasper',
                'groups_id': [(6, 0, [x.id for x in doc.group_ids])],
                'header': False,
                'multi': False,
            }
            report_id = act_report_obj.create(cr, uid, args, context=context)
            cr.execute("""UPDATE jasper_document SET report_id=%s
                           WHERE id=%s""", (report_id, id))
            value = 'ir.actions.report.xml,' + str(report_id)
            self.pool.get('ir.model.data').ir_set(cr, uid, 'action',
                                                  'client_print_multi',
                                                  doc.name,
                                                  [doc.model_id.model],
                                                  value,
                                                  replace=False,
                                                  isobject=True)

    def action_values(self, cr, uid, report_id, context=None):
        """
        Search ids for reports
        """
        args = [
            ('key', '=', 'action'),
            ('key2', '=', 'client_print_multi'),
            ('value', '=', 'ir.actions.report.xml,%d' % report_id),
            # ('object', '=', True),
        ]
        return self.pool.get('ir.values').search(cr, uid, args,
                                                 context=context)

    def get_action_report(self, cr, uid, module, name, datas=None,
                          context=None):
        """
        Give the XML ID dans retrieve the report action

        :param module: name fo the module where the XMLID is reference
        :type module: str
        :param name: name of the XMLID (afte rthe dot)
        :type name: str
        :return: return an ir.actions.report.xml
        :rtype: dict
        """
        if context is None:
            context = {}

        if datas is None:
            datas = {}

        mod_obj = self.pool.get('ir.model.data')
        result = mod_obj.get_object_reference(cr, uid, module, name)
        id = result and result[1] or False
        service = 'jasper.report_%d' % (id,)
        _logger.debug('get_action_report -> ' + service)

        return {
            'type': 'ir.actions.report.xml',
            'report_name': service,
            'datas': datas,
            'context': context,
        }

    def create_values(self, cr, uid, id, context=None):
        doc = self.browse(cr, uid, id, context=context)
        if not self.action_values(cr, uid, doc.report_id.id, context=context):
            value = 'ir.actions.report.xml,%d' % doc.report_id.id
            _logger.debug('create_values -> ' + value)
            self.pool.get('ir.model.data').ir_set(cr, uid, 'action',
                                                  'client_print_multi',
                                                  doc.name,
                                                  [doc.model_id.model],
                                                  value,
                                                  replace=False,
                                                  isobject=True)
        return True

    def unlink_values(self, cr, uid, id, context=None):
        """
        Only remove link in ir.values, not the report
        """
        doc = self.browse(cr, uid, id, context=context)
        self.pool.get('ir.values').unlink(cr, uid,
                                          self.action_values(cr, uid,
                                                             doc.report_id.id,
                                                             context=context))
        _logger.debug('unlink_values')
        return True

    def create(self, cr, uid, vals, context=None):
        """
        Dynamicaly declare the wizard for this document
        """
        if context is None:
            context = {}

        doc_id = super(jasper_document, self).create(cr, uid, vals,
                                                     context=context)
        self.make_action(cr, uid, doc_id, context=context)

        # Check if view and create it in the database
        if vals.get('sql_name') and vals.get('sql_view'):
            drop_view_if_exists(cr, vals.get('sql_name'))
            sql_query = 'CREATE OR REPLACE VIEW %s AS\n%s' % (vals['sql_name'],
                                                              vals['sql_view'])
            cr.execute(sql_query)
        return doc_id

    def write(self, cr, uid, ids, vals, context=None):
        """
        If the description change, we must update the action
        """
        if context is None:
            context = {}

        if vals.get('sql_name') or vals.get('sql_view'):
            sql_name = vals.get('sql_name',
                                self.browse(cr, uid, ids[0]).sql_name)
            sql_view = vals.get('sql_view',
                                self.browse(cr, uid, ids[0]).sql_view)
            drop_view_if_exists(cr, sql_name)
            sql_query = 'CREATE OR REPLACE VIEW %s AS\n%s' % (sql_name,
                                                              sql_view)
            cr.execute(sql_query, (ids,))

        res = super(jasper_document, self).write(cr, uid, ids, vals,
                                                 context=context)

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
        default['name'] = doc.name + _(' (copy)')
        return super(jasper_document, self).copy(cr, uid, id, default,
                                                 context=context)

    def unlink(self, cr, uid, ids, context=None):
        """
        When remove jasper_document, we must remove data to
        ir.actions.report.xml and ir.values
        """
        if context is None:
            context = {}

        for doc in self.browse(cr, uid, ids, context=context):
            if doc.report_id:
                self.unlink_values(cr, uid, doc.id, context)
                self.pool['ir.actions.report.xml'].unlink(cr, uid,
                                                          [doc.report_id.id],
                                                          context=context)

        return super(jasper_document, self).unlink(cr, uid, ids,
                                                   context=context)

    def check_report(self, cr, uid, ids, context=None):
        # TODO, use jasperlib to check if report exists
        curr = self.browse(cr, uid, ids[0], context=context)
        js_server = self.pool.get('jasper.server')
        if curr.server_id:
            jss = js_server.browse(cr, uid, curr.server_id.id, context=context)
        else:
            js_server_ids = js_server.search(cr, uid, [('enable', '=', True)],
                                             context=context)
            if not js_server_ids:
                raise osv.except_osv(_('Error'),
                                     _('No JasperServer configuration found !'))  # noqa

            jss = js_server.browse(cr, uid, js_server_ids[0], context=context)

        def compose_path(basename):
            return jss['prefix'] and \
                '/' + jss['prefix'] + '/instances/%s/%s' or basename

        try:
            js = jasperlib.Jasper(jss.host, jss.port, jss.user, jss['pass'])
            js.auth()
            uri = compose_path('/openerp/bases/%s/%s') % (cr.dbname,
                                                          curr.report_unit)
            envelop = js.run_report(uri=uri, output='PDF', params={})
            js.send(jasperlib.SoapEnv('runReport', envelop).output())
        except jasperlib.ServerNotFound:
            raise osv.except_osv(
                _('Error'),
                _('Error, server not found %s %d') % (js.host, js.port))
        except jasperlib.AuthError:
            raise osv.except_osv(
                _('Error'),
                _('Error, Authentification failed for %s/%s') % (js.user,
                                                                 js.pwd))
        except jasperlib.ServerError, e:
            raise osv.except_osv(_('Error'), str(e).decode('utf-8'))

        return True

    def parse_jrxml(self, cr, uid, ids, content, context=None):
        """
        Parse JRXML file to retrieve I18N parameters and OERP parameters
        are not standard
        """
        label_obj = self.pool['jasper.document.label']
        param_obj = self.pool['jasper.document.parameter']
        att_obj = self.pool['ir.attachment']

        fp = StringIO(content)
        tree = etree.parse(fp)
        param = tree.xpath('//root:parameter/@name', namespaces=JRXML_NS)
        for label in param:
            val = tree.xpath('//root:parameter[@name="' + label + '"]//root:defaultValueExpression', namespaces=JRXML_NS)[0].text  # noqa
            _logger.debug('%s -> %s' % (label, val))

            if label.startswith('I18N_'):
                lab = label.replace('I18N_', '')
                label_ids = label_obj.search(cr, uid, [('name', '=', lab)],
                                             context=context)
                if label_ids:
                    continue
                label_obj.create(cr, uid, {
                    'document_id': ids[0],
                    'name': lab,
                    'value': val.replace('"', ''),
                }, context=context)
            if label.startswith('OERP_') and label not in KNOWN_PARAMETERS:
                lab = label.replace('OERP_', '')
                param_ids = param_obj.search(cr, uid, [('name', '=', lab)],
                                             context=context)
                if param_ids:
                    continue
                param_obj.create(cr, uid, {
                    'document_id': ids[0],
                    'name': lab,
                    'code': val.replace('"', ''),
                    'enabled': True,
                }, context=context)

        # Now we save JRXML as attachment
        # We retrieve the name of the report with the attribute name from the
        # jasperReport element
        filename = '%s.jrxml' % tree.xpath('//root:jasperReport/@name',
                                           namespaces=JRXML_NS)[0]

        att_ids = att_obj.search(
            cr, uid, [('name', '=', filename),
                      ('res_model', '=', 'jasper.document'),
                      ('res_id', '=', ids[0])], context=context)
        if att_ids:
            att_obj.unlink(cr, uid, att_ids, context=context)

        ctx = context.copy()
        ctx['type'] = 'binary'
        ctx['default_type'] = 'binary'
        att_obj.create(cr, uid, {'name': filename,
                                 'datas': base64.encodestring(content),
                                 'datas_fname': filename,
                                 'file_type': 'text/xml',
                                 'res_model': 'jasper.document',
                                 'res_id': ids[0]}, context=ctx)

        fp.close()
        return True


class jasper_document_parameter(orm.Model):
    _name = 'jasper.document.parameter'
    _description = 'Add parameter to send to jasper server'

    _columns = {
        'name': fields.char('Name', size=32, help='Name of the jasper parameter, the prefix must be OERP_', required=True),  # noqa
        'code': fields.char('Code', size=256, help='Enter the code to retrieve data', required=True),  # noqa
        'enabled': fields.boolean('Enabled'),
        'document_id': fields.many2one('jasper.document', 'Document',
                                       required=True),
    }

    _defaults = {
        'enabled': True,
    }


class jasper_document_label(orm.Model):
    _name = 'jasper.document.label'
    _description = 'Manage label in document, for different language'

    _columns = {
        'name': fields.char('Parameter', size=64, required=True,
                            help='Name of the parameter send to JasperServer, prefix with I18N_\neg: test become I18N_TEST as parameter'),  # noqa
        'value': fields.char('Value', size=256, required=True, translate=True,
                             help='Name of the label, this field must be translate in all languages available in the database'),  # noqa
        'document_id': fields.many2one('jasper.document', 'Document',
                                       required=True),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
