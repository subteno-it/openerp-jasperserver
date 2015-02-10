# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP,
#    Copyright (C) 2010-2011 SYLEAM Info Services (<http://www.syleam.fr/>)
#                  Christophe CHAUVET <christophe.chauvet@syleam.fr>
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

import os
import time
import base64
import logging

from openerp import pooler
from openerp.report.render import render
from openerp.tools.translate import _
# from httplib2 import Http, ServerNotFoundError, HttpLib2Error
from parser import WriteContent, ParseResponse
from .common import parameter_dict, merge_pdf
from report_exception import JasperException, EvalError
from pyPdf import PdfFileWriter, PdfFileReader
from openerp.addons.jasper_server import jasperlib as jslib

_logger = logging.getLogger('openerp.addons.jasper_server.report')

##
# If cStringIO is available, we use it
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO  # noqa


class external_pdf(render):
    def __init__(self, pdf, doc_format='pdf'):
        render.__init__(self)
        self.content = pdf
        self.output_type = doc_format

    def _render(self):
        return self.content

    def set_output_type(self, format):
        """
        Change the format of the file

        :param format: file format (eg: pdf)
        :type  format: str
        """
        self.output_type = format

    def get_output_type(self,):
        """
        Retrieve the format of the attachment
        """
        return self.output_type


def log_debug(message):
    if _logger.isEnabledFor(logging.DEBUG):
        _logger.debug(' %s' % message)


class Report(object):
    """
    compose the SOAP Query, launch the query and return the value
    """
    def __init__(self, name, cr, uid, ids, data, context):
        """Initialise the report"""
        self.name = name
        self.service = name.replace('report.jasper.report_', '')
        self.cr = cr
        self.uid = uid
        self.ids = ids
        self.data = data
        self.attrs = data.get('form', {})
        self.custom = data.get('jasper', {})
        self.model = data.get('model', False)
        self.pool = pooler.get_pool(cr.dbname)
        self.outputFormat = 'PDF'
        self.path = None

        # Reuse object pool
        self.model_obj = self.pool.get(self.model)
        self.doc_obj = self.pool.get('jasper.document')
        self.js_obj = self.pool.get('jasper.server')
        self.obj = None

        # If no context, retrieve one on the current user
        self.context = context or self.pool.get('res.users').context_get(
            cr, uid, uid)

    def add_attachment(self, res_id, aname, content, mimetype='binary',
                       context=None):
        """
        Add attachment for this report
        """
        name = aname + '.' + self.outputFormat.lower()
        ctx = context.copy()
        ctx['type'] = mimetype
        ctx['default_type'] = 'binary'

        return self.pool.get('ir.attachment').create(
            self.cr, self.uid, {'name': name,
                                'datas': base64.encodestring(content),
                                'datas_fname': name,
                                'file_type': mimetype,
                                'res_model': self.model,
                                'res_id': res_id}, context=ctx)

    def _eval_field(self, cur_obj, fieldcontent):
        """
        Evaluate the field
        """
        try:
            return eval(fieldcontent, {'object': cur_obj, 'time': time})
        except SyntaxError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Field Eval Error'),
                            _('Syntax error when evaluate field\n\nMessage: "%s"') % str(e))  # noqa
        except NameError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Field Eval Error'),
                            _('Error when evaluate field\n\nMessage: "%s"') % str(e))  # noqa
        except AttributeError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Field Eval Error'),
                            _('Attribute error when evaluate field\nVerify if specify field exists and valid\n\nMessage: "%s"') % str(e))  # noqa
        except Exception, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Field Eval Error'),
                            _('Unknown error when evaluate field\nMessage: "%s"') % str(e))  # noqa

    def _eval_attachment(self, cur_obj):
        """
        Launch eval on attachement field, and return the value
        """
        try:
            return eval(self.attrs['attachment'], {'object': cur_obj,
                                                   'time': time})
        except SyntaxError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Attachment Error'),
                            _('Syntax error when evaluate attachment\n\nMessage: "%s"') % str(e))  # noqa
        except NameError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Attachment Error'),
                            _('Error when evaluate attachment\n\nMessage: "%s"') % str(e))  # noqa
        except AttributeError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Attachment Error'),
                            _('Attribute error when evaluate attachment\nVerify if specify field exists and valid\n\nMessage: "%s"') % str(e))  # noqa
        except Exception, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Attachment Error'),
                            _('Unknown error when evaluate attachment\nMessage: "%s"') % str(e))  # noqa

    def _eval_duplicate(self, cur_obj, current_document):
        """
        Evaluate the duplicate field
        """
        try:
            return int(eval(current_document.duplicate, {'o': cur_obj}))
        except SyntaxError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Duplicate Error'),
                            _('Syntax error when evaluate duplicate\n\nMessage: "%s"') % str(e))  # noqa
        except NameError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Duplicate Error'),
                            _('Error when evaluate duplicate\n\nMessage: "%s"') % str(e))  # noqa
        except AttributeError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Duplicate Error'),
                            _('Attribute error when evaluate duplicate\nVerify if specify field exists and valid\n\nMessage: "%s"') % str(e))  # noqa
        except Exception, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Duplicate Error'),
                            _('Unknown error when evaluate duplicate\nMessage: "%s"') % str(e))  # noqa

    def _eval_lang(self, cur_obj, current_document, context=None):
        """
        Evaluate the lang field
        """
        if context is None:
            context = {}

        try:
            return eval(current_document.lang, {'o': cur_obj, 'ctx': context})
        except SyntaxError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Language Error'), _('Syntax error when evaluate language\n\nMessage: "%s"') % str(e))  # noqa
        except NameError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Language Error'), _('Error when evaluate language\n\nMessage: "%s"') % str(e))  # noqa
        except AttributeError, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Language Error'), _('Attribute error when evaluate language\nVerify if specify field exists and valid\n\nMessage: "%s"') % str(e))  # noqa
        except Exception, e:
            _logger.warning('Error %s' % str(e))
            raise EvalError(_('Language Error'), _('Unknown error when evaluate language\nMessage: "%s"') % str(e))  # noqa

    def _jasper_execute(self, ex, current_document, js_conf, pdf_list,
                        reload=False, ids=None, context=None):
        """
        After retrieve datas to launch report, execute it and
        return the content
        """
        # Issue 934068 with web client with model is missing from the context
        if not self.model:
            self.model = current_document.model_id.model
            self.model_obj = self.pool.get(self.model)

        if context is None:
            context = self.context.copy()

        if ids is None:
            ids = []

        cur_obj = self.model_obj.browse(self.cr, self.uid, ex, context=context)
        aname = False
        if self.attrs['attachment']:
            aname = self._eval_attachment(cur_obj)

        duplicate = 1
        if current_document.duplicate:
            duplicate = self._eval_duplicate(cur_obj, current_document)

        log_debug('Number of duplicate copy: %d' % int(duplicate))

        language = context.get('lang', 'en_US')
        if current_document.lang:
            language = self._eval_lang(
                cur_obj, current_document, context=context)

        # Check if we can launch this reports
        # Test can be simple, or un a function
        if current_document.check_sel != 'none':
            try:
                if current_document.check_sel == 'simple' and \
                   not eval(current_document.check_simple, {'o': cur_obj}):
                    raise JasperException(_('Check Print Error'), current_document.message_simple)  # noqa
                elif current_document.check_sel == 'func' and \
                        not hasattr(self.model_obj, 'check_print'):
                    raise JasperException(_('Check Print Error'), _('"check_print" function not found in "%s" object') % self.model)  # noqa
                elif current_document.check_sel == 'func' and \
                        hasattr(self.model_obj, 'check_print') and \
                        not self.model_obj.check_print(self.cr, self.uid,
                                                       cur_obj,
                                                       context=context):
                    raise JasperException(_('Check Print Error'), _('Function "check_print" return an error'))  # noqa

            except SyntaxError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Check Error'), _('Syntax error when check condition\n\nMessage: "%s"') % str(e))  # noqa
            except NameError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Check Error'), _('Error when check condition\n\nMessage: "%s"') % str(e))  # noqa
            except AttributeError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Check Error'), _('Attribute error when check condition\nVerify if specify field exists and valid\n\nMessage: "%s"') % str(e))  # noqa
            except JasperException, e:
                _logger.warning('Error %s' % str(e))
                raise JasperException(e.title, e.message)
            except Exception, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Check Error'), _('Unknown error when check condition\nMessage: "%s"') % str(e))  # noqa

        reload_ok = False
        if self.attrs['reload'] and aname:
            _logger.info('Printing must be reload from attachment if exists (%s)' % aname)  # noqa
            aids = self.pool.get('ir.attachment').search(
                self.cr, self.uid, [('name', '=', aname),
                                    ('res_model', '=', self.model),
                                    ('res_id', '=', ex)])
            if aids:
                reload_ok = True
                _logger.info('Attachment found, reload it!')
                brow_rec = self.pool.get('ir.attachment').browse(
                    self.cr, self.uid, aids[0])
                if brow_rec.datas:
                    d = base64.decodestring(brow_rec.datas)
                    WriteContent(d, pdf_list)
                    content = d
            else:
                _logger.info('Attachment not found')

        if not reload_ok:
            # Bug found in iReport >= 3.7.x (IN doesn't work in SQL Query)
            # We cannot use $X{IN, field, Collection}
            # use $P!{OERP_ACTIVE_IDS} indeed as
            # ids in ($P!{OERP_ACTIVE_IDS} (exclamation mark)
            d_par = {
                'active_id': ex,
                'active_ids': ','.join(str(i) for i in ids),
                'model': self.model,
                'sql_query': self.attrs.get('query', "SELECT 'NO QUERY' as nothing"),  # noqa
                'sql_query_where': self.attrs.get('query_where', '1 = 1'),
                'report_name': self.attrs.get('report_name', _('No report name')),  # noqa
                'lang': language or 'en_US',
                'duplicate': duplicate,
                'dbname': self.cr.dbname,
                'uid': self.uid,
            }

            # If XML we must compose it
            if self.attrs['params'][2] == 'xml':
                d_xml = self.js_obj.generator(self.cr, self.uid, self.model,
                                              self.ids[0],
                                              self.attrs['params'][3],
                                              context=context)
                d_par['xml_data'] = d_xml

            # Retrieve the company information and send them in parameter
            # Is document have company field, to print correctly the document
            # Or take it to the user
            user = self.pool.get('res.users').browse(self.cr, self.uid,
                                                     self.uid,
                                                     context=context)
            if hasattr(cur_obj, 'company_id') and cur_obj.company_id:
                cny = self.pool.get('res.company').browse(
                    self.cr, self.uid, cur_obj.company_id.id, context=context)
            else:
                cny = user.company_id

            d_par.update({
                'company_name': cny.name,
                'company_logo': cny.name.encode('ascii',
                                                'ignore').replace(' ', '_'),
                'company_header1': cny.rml_header1 or '',
                'company_footer1': cny.rml_footer or '',
                'company_footer2': '',
                'company_website': cny.partner_id.website or '',
                'company_currency': cny.currency_id.name or '',

                # Search the default address for the company.
                'company_street': cny.partner_id.street or '',
                'company_street2': cny.partner_id.street2 or '',
                'company_zip': cny.partner_id.zip or '',
                'company_city': cny.partner_id.city or '',
                'company_country': cny.partner_id.country_id.name or '',
                'company_phone': cny.partner_id.phone or '',
                'company_fax': cny.partner_id.fax or '',
                'company_mail': cny.partner_id.email or '',
            })

            for p in current_document.param_ids:
                if p.code and p.code.startswith('[['):
                    d_par[p.name.lower()] = eval(p.code.replace('[[', '').replace(']]', ''), {'o': cur_obj, 'c': cny, 't': time, 'u': user}) or ''  # noqa
                else:
                    d_par[p.name] = p.code

            self.outputFormat = current_document.format
            special_dict = {
                'REPORT_LOCALE': language or 'en_US',
                'IS_JASPERSERVER': 'yes',
            }

            # we must retrieve label in the language document
            # (not user's language)
            for l in self.doc_obj.browse(self.cr, self.uid,
                                         current_document.id,
                                         context={'lang': language}).label_ids:
                special_dict['I18N_' + l.name.upper()] = l.value or ''

            # If report is launched since a wizard,
            # we can retrieve some parameters
            for d in self.custom.keys():
                special_dict['CUSTOM_' + d.upper()] = self.custom[d]

            # If special value is available in context,
            # we add them as parameters
            if context.get('jasper') and isinstance(context['jasper'], dict):
                for d in context['jasper'].keys():
                    special_dict['CONTEXT_' + d.upper()] = context['jasper'][d]

            par = parameter_dict(self.attrs, d_par, special_dict)

            # Execute the before query if it available
            if js_conf.get('before'):
                self.cr.execute(js_conf['before'], {'id': ex})

            try:
                js = jslib.Jasper(js_conf['host'], js_conf['port'],
                                  js_conf['user'], js_conf['pass'])
                js.auth()
                envelop = js.run_report(uri=self.path or
                                        self.attrs['params'][1],
                                        output=self.outputFormat,
                                        params=par)
                response = js.send(jslib.SoapEnv('runReport',
                                                 envelop).output())
                content = response['data']
                mimetype = response['content-type']
                ParseResponse(response, pdf_list, self.outputFormat.lower())
            except jslib.ServerNotFound:
                raise JasperException(_('Error'), _('Server not found !'))
            except jslib.AuthError:
                raise JasperException(_('Error'), _('Autentification failed !'))  # noqa

            # Store the content in ir.attachment if ask
            if aname:
                self.add_attachment(ex, aname, content, mimetype=mimetype,
                                    context=self.context)

            # Execute the before query if it available
            if js_conf.get('after'):
                self.cr.execute(js_conf['after'], {'id': ex})

            # Update the number of print on object
            fld = self.model_obj.fields_get(self.cr, self.uid)
            if 'number_of_print' in fld:
                self.model_obj.write(
                    self.cr, self.uid, [cur_obj.id],
                    {'number_of_print': (getattr(cur_obj, 'number_of_print',
                                                 None) or 0) + 1},
                    context=context)

        return (content, duplicate)

    def execute(self):
        """Launch the report and return it"""
        context = self.context.copy()

        ids = self.ids
        log_debug('DATA:')
        log_debug('\n'.join(['%s: %s' % (x, self.data[x]) for x in self.data]))

        ##
        # For each IDS, launch a query, and return only one result
        #
        pdf_list = []
        doc_ids = self.doc_obj.search(self.cr, self.uid,
                                      [('id', '=', self.service)],
                                      context=context)
        if not doc_ids:
            raise JasperException(_('Configuration Error'),
                                  _("Service name doesn't match!"))

        doc = self.doc_obj.browse(self.cr, self.uid, doc_ids[0],
                                  context=context)
        self.outputFormat = doc.format
        log_debug('Format: %s' % doc.format)

        if doc.server_id:
            js_ids = [doc.server_id.id]
        else:
            js_ids = self.js_obj.search(self.cr, self.uid,
                                        [('enable', '=', True)])
            if not len(js_ids):
                raise JasperException(_('Configuration Error'),
                                      _('No JasperServer configuration found!'))  # noqa

        js = self.js_obj.read(self.cr, self.uid, js_ids[0], context=context)

        def compose_path(basename):
            return js['prefix'] and '/' + js['prefix'] + '/instances/%s/%s' or basename   # noqa

        self.attrs['attachment'] = doc.attachment
        self.attrs['reload'] = doc.attachment_use
        if not self.attrs.get('params'):
            uri = compose_path('/openerp/bases/%s/%s') % (self.cr.dbname,
                                                          doc.report_unit)
            self.attrs['params'] = (doc.format, uri, doc.mode, doc.depth, {})

        one_check = {}
        one_check[doc.id] = False
        content = ''
        duplicate = 1
        for ex in ids:
            if doc.mode == 'multi' and self.outputFormat == 'PDF':
                for d in doc.child_ids:
                    if d.only_one and one_check.get(d.id, False):
                        continue
                    self.path = compose_path('/openerp/bases/%s/%s') % (self.cr.dbname, d.report_unit)  # noqa
                    (content, duplicate) = self._jasper_execute(
                        ex, d, js, pdf_list, reload, ids, context=self.context)
                    one_check[d.id] = True
            else:
                if doc.only_one and one_check.get(doc.id, False):
                    continue
                (content, duplicate) = self._jasper_execute(
                    ex, doc, js, pdf_list, reload, ids, context=self.context)
                one_check[doc.id] = True

        # If format is not PDF, we return it directly
        # ONLY PDF CAN BE MERGE!
        if self.outputFormat != 'PDF':
            self.obj = external_pdf(content, self.outputFormat)
            return (self.obj.content, self.outputFormat)

        def find_pdf_attachment(pdfname, current_obj):
            """
            Evaluate the pdfname, and return it as a fiel object
            """
            if not pdfname:
                return None

            filename = self._eval_field(current_obj, pdfname)
            att_obj = self.pool.get('ir.attachment')
            aids = att_obj.search(self.cr, self.uid,
                                  [('name', '=', filename),
                                   ('res_model', '=', self.model_obj._name),
                                   ('res_id', '=', ex)])
            if not aids:
                return None

            att = att_obj.browse(self.cr, self.uid, aids[0], context=context)
            datas = StringIO()
            if att.datas:
                datas.write(base64.decodestring(att.datas))
                return datas
            return None

        # If We must add begin and end file in the current PDF
        cur_obj = self.model_obj.browse(self.cr, self.uid, ex, context=context)
        pdf_fo_begin = find_pdf_attachment(doc.pdf_begin, cur_obj)
        pdf_fo_ended = find_pdf_attachment(doc.pdf_ended, cur_obj)

        # We use pyPdf to merge all PDF in unique file
        c = StringIO()
        if len(pdf_list) > 1 or duplicate > 1:
            # content = ''
            tmp_content = PdfFileWriter()

            # We add all PDF file in a list of file pointer to close them
            # at the end of treatment
            tmp_pdf_list = []
            for curpdf in pdf_list:
                tmp_pdf_list.append(open(curpdf, 'r'))

            for fo_pdf in tmp_pdf_list:
                for x in range(0, duplicate):
                    fo_pdf.seek(0)
                    tmp_pdf = PdfFileReader(fo_pdf)
                    for page in range(tmp_pdf.getNumPages()):
                        tmp_content.addPage(tmp_pdf.getPage(page))
            else:
                tmp_content.write(c)
                # content = c.getvalue()

            # It seem there is a bug on PyPDF if we close the "fp" file,
            # we cannot call tmp_content.write(c) We received
            # an exception "ValueError: I/O operation on closed file"
            for fo_pdf in tmp_pdf_list:
                if not fo_pdf.closed:
                    fo_pdf.close()

        elif len(pdf_list) == 1:
            fp = open(pdf_list[0], 'r')
            c.write(fp.read())
            fp.close()

        # Remove all files on the disk
        for f in pdf_list:
            os.remove(f)

        # If covers, we merge PDF
        fo_merge = merge_pdf([pdf_fo_begin, c, pdf_fo_ended])
        content = fo_merge.getvalue()
        fo_merge.close()

        if not c.closed:
            c.close()

        self.obj = external_pdf(content, self.outputFormat)
        return (self.obj.content, self.outputFormat)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
