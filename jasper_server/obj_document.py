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

from openerp import models, api, fields, exceptions
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


class jasper_document_extension(models.Model):
    _name = 'jasper.document.extension'
    _description = 'Jasper Document Extension'

    name = fields.Char(size=128, translate=True)
    jasper_code = fields.Char(string='Code', size=32, required=True)
    extension = fields.Char(size=10, required=True)


class jasper_document(models.Model):
    _name = 'jasper.document'
    _description = 'Jasper Document'
    _order = 'sequence'

    def _get_formats(self):
        """
        Return the list of all types of document that can be
        generate by JasperServer
        """
        extension_obj = self.env['jasper.document.extension']
        extensions = extension_obj.search([])
        return [(extension.jasper_code, '%s (*.%s)' % (extension.name, extension.extension)) for extension in extensions]

    name = fields.Char(size=128, translate=True, required=True, placeholder="InvoiceJ")
    enabled = fields.Boolean(string='Active', help="Indicates if this document is active or not")
    model_id = fields.Many2one('ir.model', string='Object Model', required=True),
    server_id = fields.Many2one('jasper.server', string='Server', help='Select specific JasperServer')
    jasper_file = fields.Char('Jasper file', size=128)
    group_ids = fields.Many2many('res.groups', 'jasper_wizard_group_rel', 'document_id', 'group_id', string='Groups')
    depth = fields.Integer(required=True, default=0)
    format_choice = fields.Selection([
        ('mono', 'Single Format'),
        ('multi', 'Multi Format')
    ], default='mono', required=True)
    format = fields.Selection(_get_formats, defaumt='PDF', string='Formats')
    report_unit = fields.Char(size=128, help='Enter the name for report unit in Jasper Server')
    mode = fields.Selection([
        ('sql', 'SQL'),
        ('xml', 'XML'),
        ('multi', 'Multiple Report'),
    ], default='sql', required=True)
    before = fields.Text(help='This field must be filled with a valid SQL request and will be executed BEFORE the report edition',)
    after = fields.Text(help='This field must be filled with a valid SQL request and will be executed AFTER the report edition',)
    attachment = fields.Char(
        string='Save As Attachment Prefix', size=255, default=False,
        help='This is the filename of the attachment used to store the printing result. Keep empty to not save the printed reports. You can use a python expression with the object and time variables.',
    )
    attachment_use = fields.Boolean(string='Reload from Attachment', help='If you check this, then the second time the user prints with same attachment name, it returns the previous report.')
    param_ids = fields.One2many('jasper.document.parameter', 'document_id', string='Parameters', )
    ctx = fields.Char(string='Context', size=128, help="Enter condition with context does match to see the print action\neg: context.get('foo') == 'bar'")
    sql_view = fields.Text(string='SQL View', help='Insert your SQL view, if the report is base on it')
    sql_name = fields.Char(string='Name of view', size=128)
    child_ids = fields.Many2many('jasper.document', 'jasper_document_multi_rel', 'source_id', 'destin_id', string='Child report', help='Select reports to launch when this report is called')
    sequence = fields.Integer(default=100, help='The sequence is used when launch a multple report, to select the order to launch')
    only_one = fields.Boolean(string='Launch one time for all ids', help='Launch the report only one time on multiple id')
    duplicate = fields.Char(size=256, default="'1'", help="Indicate the number of duplicate copie, use o as object to evaluate\neg: o.partner_id.copy\nor\n'1'")
    lang = fields.Char(size=256, default=False, help="Indicate the lang to use for this report, use o as object to evaluate\neg: o.partner_id.lang\nor\n'fr_FR'\ndefault use user's lang")
    report_id = fields.Many2one('ir.actions.report.xml', 'Report link', readonly=True, default=False, help='Link to the report in ir.actions.report.xml')
    check_sel = fields.Selection([
        ('none', 'None'),
        ('simple', 'Simple'),
        ('func', 'Function'),
    ], string='Checking type', default='none', help='if None, no check\nif Simple, define on Check Simple the condition\n if function, the object have check_print function')
    check_simple = fields.Char(size=256, help="This code inside this field must return True to send report execution\neg o.state in ('draft', 'open')")
    message_simple = fields.Char(string='Return message', size=256, translate=True, help="Error message when check simple doesn't valid")
    label_ids = fields.One2many('jasper.document.label', 'document_id', string='Labels')
    pdf_begin = fields.Char(string='PDF at begin', size=128, help='Name of the PDF file store as attachment to add at the first page (page number not recompute)')
    pdf_ended = fields.Char(string='PDF at end', size=128, help='Name of the PDF file store as attachment to add at the last page (page number not recompute)')

    def make_action(self):
        """
        Create an entry in ir_actions_report_xml
        and ir.values
        """
        act_report_obj = self.pool.get('ir.actions.report.xml')

        if self.report_id:
            _logger.info('Update "%s" service' % self.name)
            args = {
                'name': self.name,
                'report_name': 'jasper.report_%d' % (self.id,),
                'model': self.model_id.model,
                'groups_id': [(6, 0, [x.id for x in self.group_ids])],
                'header': False,
                'multi': False,
            }
            self.report_id.write(args)
        else:
            _logger.info('Create "%s" service' % self.name)
            args = {
                'name': self.name,
                'report_name': 'jasper.report_%d' % (self.id,),
                'model': self.model_id.model,
                'report_type': 'jasper',
                'groups_id': [(6, 0, [x.id for x in self.group_ids])],
                'header': False,
                'multi': False,
            }
            report_id = act_report_obj.create(args)
            self.env.cr.execute("""UPDATE jasper_document SET report_id=%s
                           WHERE id=%s""", (report_id, id))
            value = 'ir.actions.report.xml,' + str(report_id)
            self.pool.get('ir.model.data').ir_set('action',
                                                  'client_print_multi',
                                                  self.name,
                                                  [self.model_id.model],
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
        if not self.action_values(cr, uid, self.report_id.id, context=context):
            value = 'ir.actions.report.xml,%d' % self.report_id.id
            _logger.debug('create_values -> ' + value)
            self.pool.get('ir.model.data').ir_set(cr, uid, 'action',
                                                  'client_print_multi',
                                                  self.name,
                                                  [self.model_id.model],
                                                  value,
                                                  replace=False,
                                                  isobject=True)
        return True

    def unlink_values(self, cr, uid, id, context=None):
        """
        Only remove link in ir.values, not the report
        """
        self.pool.get('ir.values').unlink(cr, uid,
                                          self.action_values(cr, uid,
                                                             self.report_id.id,
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

        default['report_id'] = False
        default['name'] = self.name + _(' (copy)')
        return super(jasper_document, self).copy(cr, uid, id, default,
                                                 context=context)

    def unlink(self, cr, uid, ids, context=None):
        """
        When remove jasper_document, we must remove data to
        ir.actions.report.xml and ir.values
        """
        for doc in self:
            if doc.report_id:
                doc.unlink_values()
                doc.report_id.unlink()

        return super(jasper_document, self).unlink()

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
                raise exceptions.Warning(_('Error'),
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
            raise exceptions.Warning(
                _('Error'),
                _('Error, server not found %s %d') % (js.host, js.port))
        except jasperlib.AuthError:
            raise exceptions.Warning(
                _('Error'),
                _('Error, Authentification failed for %s/%s') % (js.user,
                                                                 js.pwd))
        except jasperlib.ServerError, e:
            raise exceptions.Warning(_('Error'), str(e).decode('utf-8'))

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


class jasper_document_parameter(models.Model):
    _name = 'jasper.document.parameter'
    _description = 'Add parameter to send to jasper server'

    name = fields.Char(size=32, help='Name of the jasper parameter, the prefix must be OERP_', required=True)
    code = fields.Char(size=256, help='Enter the code to retrieve data', required=True)
    enabled = fields.Boolean(default=True)
    document_id = fields.Many2one('jasper.document', string='Document', required=True)


class jasper_document_label(models.Model):
    _name = 'jasper.document.label'
    _description = 'Manage label in document, for different language'

    name = fields.Char(
        string='Parameter', size=64, required=True,
        help='Name of the parameter send to JasperServer, prefix with I18N_\neg: test become I18N_TEST as parameter',
    )
    value = fields.Char(
        size=256, required=True, translate=True,
        help='Name of the label, this field must be translate in all languages available in the database',
    )
    document_id = fields.Many2one('jasper.document', 'Document', required=True)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
