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

import pooler
import os
import time
import base64
import logging

from report.render import render
from httplib2 import Http, ServerNotFoundError, HttpLib2Error
from parser import ParseHTML, ParseXML, ParseDIME, ParseContent, WriteContent
from common import BODY_TEMPLATE, parameter
from report_exception import JasperException, AuthError, EvalError
from pyPdf import PdfFileWriter, PdfFileReader
from tools.translate import _

_logger = logging.getLogger('jasper_server')

##
# If cStringIO is available, we use it
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO


class external_pdf(render):
    def __init__(self, pdf):
        render.__init__(self)
        self.content = pdf
        self.output_type = 'pdf'

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
    _logger.debug(' %s' % message)


class Report(object):
    """
    compose the SOAP Query, launch the query and return the value
    """
    def __init__(self, name, cr, uid, ids, data, context):
        """Initialise the report"""
        self.name = name
        self.service = name.replace('report.jasper.', '')
        self.cr = cr
        self.uid = uid
        self.ids = ids
        self.data = data
        self.attrs = data.get('form', {})
        self.custom = data.get('jasper', {})
        self.model = data.get('model', False)
        self.pool = pooler.get_pool(cr.dbname)
        self.model_obj = self.pool.get(self.model)
        self.obj = None
        self.outputFormat = 'pdf'
        self.path = None
        # If no context, retrieve one on the current user
        self.context = context or self.pool.get('res.users').context_get(cr, uid, uid)

    def _jasper_execute(self, ex, current_document, js_conf, pdf_list, ids=None, context=None):
        """
        After retrieve datas to launch report, execute it and return the content
        """
        if context is None:
            context = self.context.copy()

        if ids is None:
            ids = []

        doc_obj = self.pool.get('jasper.document')
        js_obj = self.pool.get('jasper.server')
        cur_obj = self.model_obj.browse(self.cr, self.uid, ex, context=context)
        aname = False
        if self.attrs['attachment']:
            try:
                aname = eval(self.attrs['attachment'], {'object': cur_obj, 'time': time})
            except SyntaxError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Attachment Error'), _('Syntax error when evaluate attachment\n\nMessage: "%s"') % str(e))
            except NameError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Attachment Error'), _('Error when evaluate attachment\n\nMessage: "%s"') % str(e))
            except AttributeError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Attachment Error'), _('Attribute error when evaluate attachment\nVerify if specify field exists and valid\n\nMessage: "%s"') % str(e))
            except Exception, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Attachment Error'), _('Unknown error when evaluate attachment\nMessage: "%s"') % str(e))

        duplicate = 1
        if current_document.duplicate:
            try:
                duplicate = int(eval(current_document.duplicate, {'o': cur_obj}))
            except SyntaxError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Duplicate Error'), _('Syntax error when evaluate duplicate\n\nMessage: "%s"') % str(e))
            except NameError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Duplicate Error'), _('Error when evaluate duplicate\n\nMessage: "%s"') % str(e))
            except AttributeError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Duplicate Error'), _('Attribute error when evaluate duplicate\nVerify if specify field exists and valid\n\nMessage: "%s"') % str(e))
            except Exception, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Duplicate Error'), _('Unknown error when evaluate duplicate\nMessage: "%s"') % str(e))

        log_debug('Number of duplicate copy: %d' % int(duplicate))

        language = context.get('lang', 'en_US')
        if current_document.lang:
            try:
                language = eval(current_document.lang, {'o': cur_obj})
            except SyntaxError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Language Error'), _('Syntax error when evaluate language\n\nMessage: "%s"') % str(e))
            except NameError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Language Error'), _('Error when evaluate language\n\nMessage: "%s"') % str(e))
            except AttributeError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Language Error'), _('Attribute error when evaluate language\nVerify if specify field exists and valid\n\nMessage: "%s"') % str(e))
            except Exception, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Language Error'), _('Unknown error when evaluate language\nMessage: "%s"') % str(e))

        # Check if we can launch this reports
        # Test can be simple, or un a function
        if current_document.check_sel != 'none':
            try:
                if current_document.check_sel == 'simple' and not eval(current_document.check_simple, {'o': cur_obj}):
                    raise JasperException(_('Check Print Error'), current_document.message_simple)
                elif current_document.check_sel == 'func' and not hasattr(self.model_obj, 'check_print'):
                    raise JasperException(_('Check Print Error'), _('"check_print" function not found in "%s" object') % self.model)
                elif current_document.check_sel == 'func' and hasattr(self.model_obj, 'check_print') and \
                        not self.model_obj.check_print(self.cr, self.uid, cur_obj, context=context):
                    raise JasperException(_('Check Print Error'), _('Function "check_print" return an error'))

            except SyntaxError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Check Error'), _('Syntax error when check condition\n\nMessage: "%s"') % str(e))
            except NameError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Check Error'), _('Error when check condition\n\nMessage: "%s"') % str(e))
            except AttributeError, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Check Error'), _('Attribute error when check condition\nVerify if specify field exists and valid\n\nMessage: "%s"') % str(e))
            except JasperException, e:
                _logger.warning('Error %s' % str(e))
                raise JasperException(e.title, e.message)
            except Exception, e:
                _logger.warning('Error %s' % str(e))
                raise EvalError(_('Check Error'), _('Unknown error when check condition\nMessage: "%s"') % str(e))

        reload_ok = False
        if self.attrs['reload'] and aname:
            _logger.info('Printing must be reload from attachment if exists (%s)' % aname)
            aids = self.pool.get('ir.attachment').search(self.cr, self.uid,
                    [('name', '=', aname), ('res_model', '=', self.model), ('res_id', '=', ex)])
            if aids:
                reload_ok = True
                _logger.info('Attachment found, reload it!')
                brow_rec = self.pool.get('ir.attachment').browse(self.cr, self.uid, aids[0])
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
                'sql_query': self.attrs.get('query', "SELECT 'NO QUERY' as nothing"),
                'sql_query_where': self.attrs.get('query_where', '1 = 1'),
                'report_name': self.attrs.get('report_name', _('No report name')),
                'lang': language or 'en_US',
                'duplicate': duplicate,
            }

            # If XML we must compose it
            if self.attrs['params'][2] == 'xml':
                d_xml = js_obj.generator(self.cr, self.uid, self.model, self.ids[0],
                        self.attrs['params'][3], context=context)
                d_par['xml_data'] = d_xml

            # Retrieve the company information and send them in parameter
            # Is document have company field, to print correctly the document
            # Or take it to the user
            user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid, context=context)
            if hasattr(cur_obj, 'company_id'):
                cny = self.pool.get('res.company').browse(self.cr, self.uid, cur_obj.company_id.id, context=context)
            else:
                cny = user.company_id

            d_par['company_name'] = cny.name
            d_par['company_logo'] = cny.name.encode('ascii', 'ignore').replace(' ', '_')
            d_par['company_header1'] = cny.rml_header1 or ''
            d_par['company_footer1'] = cny.rml_footer1 or ''
            d_par['company_footer2'] = cny.rml_footer2 or ''
            d_par['company_website'] = cny.partner_id.website or ''
            d_par['company_currency'] = cny.currency_id.name or ''

            # Search the default address for the company.
            addr_id = self.pool.get('res.partner').address_get(self.cr, self.uid, [cny.partner_id.id], ['default'])['default']
            if not addr_id:
                raise JasperException(_('Error'), _('Main company have no address defined on the partner!'))
            addr = self.pool.get('res.partner.address').browse(self.cr, self.uid, addr_id, context=context)
            d_par['company_street'] = addr.street or ''
            d_par['company_street2'] = addr.street2 or ''
            d_par['company_zip'] = addr.zip or ''
            d_par['company_city'] = addr.city or ''
            d_par['company_country'] = addr.country_id.name or ''
            d_par['company_phone'] = addr.phone or ''
            d_par['company_fax'] = addr.fax or ''
            d_par['company_mail'] = addr.email or ''

            for p in current_document.param_ids:
                if p.code and  p.code.startswith('[['):
                    d_par[p.name.lower()] = eval(p.code.replace('[[', '').replace(']]', ''), {'o': cur_obj, 'c': cny, 't': time, 'u': user}) or ''
                else:
                    d_par[p.name] = p.code

            self.outputFormat = current_document.format.lower()
            special_dict = {
                'REPORT_LOCALE': language or 'en_US',
                'IS_JASPERSERVER': 'yes',
            }

            # we must retrieve label in the language document (not user's language)
            for l in doc_obj.browse(self.cr, self.uid, current_document.id, context={'lang': language}).label_ids:
                special_dict['I18N_' + l.name.upper()] = l.value

            # If report is launched since a wizard, we can retrieve some parameters
            for d in self.custom.keys():
                special_dict['CUSTOM_' + d.upper()] = self.custom[d]

            # If special value is available in context, we add them as parameters
            if context.get('jasper') and isinstance(context['jasper'], dict):
                for d in context['jasper'].keys():
                    special_dict['CONTEXT_' + d.upper()] = context['jasper'][d]

            par = parameter(self.attrs, d_par, special_dict)
            body_args = {
                'format': self.attrs['params'][0],
                'path': self.path or self.attrs['params'][1],
                'param': par,
                'database': '/openerp/databases/%s' % self.cr.dbname,
            }

            ###
            ## Execute the before query if it available
            ##
            if js_conf.get('before'):
                self.cr.execute(js_conf['before'], {'id': ex})

            body = BODY_TEMPLATE % body_args
            log_debug('****\n%s\n****' % body)

            headers = {'Content-type': 'text/xml', 'charset': 'UTF-8', 'SOAPAction': 'runReport'}
            h = Http()
            h.add_credentials(js_conf['user'], js_conf['pass'])
            try:
                uri = 'http://%s:%d%s' % (js_conf['host'], js_conf['port'], js_conf['repo'])
                resp, content = h.request(uri, "POST", body, headers)
            except ServerNotFoundError:
                raise JasperException(_('Error'), _('Server not found !'))
            except HttpLib2Error, e:
                raise JasperException(_('Error'), '%s' % str(e))
            except Exception, e:
                raise JasperException(_('Error'), '%s' % str(e))

            log_debug('HTTP -> RESPONSE:')
            log_debug('\n'.join(['%s: %s' % (x, resp[x]) for x in resp]))
            if resp.get('content-type').startswith('text/xml'):
                log_debug('CONTENT: %r' % content)
                raise JasperException(_('Error'), _('Code: %s\nMessage: %s') % ParseXML(content))
            elif resp.get('content-type').startswith('text/html'):
                log_debug('CONTENT: %r' % content)
                if ParseHTML(content).find('Bad credentials'):
                    raise AuthError(_('Authentification Error'), _('Invalid login or password'))
                else:
                    raise JasperException(_('Error'), '%s' % ParseHTML(content))
            elif resp.get('content-type') == 'application/dime':
                ParseDIME(content, pdf_list)
            else:
                raise JasperException(_('Unknown Error'), _('Content-type: %s\nMessage:%s') % (resp.get('content-type'), content))

            ###
            ## Store the content in ir.attachment if ask
            if aname:
                name = aname + '.' + self.outputFormat
                _logger.info('Save printing as attachment (%s)' % (name,))
                self.pool.get('ir.attachment').create(self.cr, self.uid, {
                            'name': aname,
                            'datas': base64.encodestring(ParseContent(content)),
                            'datas_fname': name,
                            'res_model': self.model,
                            'res_id': ex,
                            }, context=context)

            ###
            ## Execute the before query if it available
            ##
            if js_conf.get('after'):
                self.cr.execute(js_conf['after'], {'id': ex})

            ## Update the number of print on object
            fld = self.model_obj.fields_get(self.cr, self.uid)
            if 'number_of_print' in fld:
                self.model_obj.write(self.cr, self.uid, [cur_obj.id], {'number_of_print': (getattr(cur_obj, 'number_of_print', None) or 0) + 1}, context=context)

        return (content, duplicate)

    def execute(self):
        """Launch the report and return it"""
        context = self.context.copy()

        ids = self.ids
        js_obj = self.pool.get('jasper.server')
        doc_obj = self.pool.get('jasper.document')
        js_ids = js_obj.search(self.cr, self.uid, [('enable', '=', True)])
        if not len(js_ids):
            raise JasperException(_('Configuration Error'), _('No JasperServer configuration found!'))

        js = js_obj.read(self.cr, self.uid, js_ids, context=context)[0]
        log_debug('DATA:')
        log_debug('\n'.join(['%s: %s' % (x, self.data[x]) for x in self.data]))

        ##
        # For each IDS, launch a query, and return only one result
        #
        pdf_list = []
        doc_ids = doc_obj.search(self.cr, self.uid, [('service', '=', self.service)], context=context)
        if not doc_ids:
            raise JasperException(_('Configuration Error'), _("Service name doesn't match!"))

        doc = doc_obj.browse(self.cr, self.uid, doc_ids[0], context=context)
        self.attrs['attachment'] = doc.attachment
        self.attrs['reload'] = doc.attachment_use
        if not self.attrs.get('params'):
            uri = '/openerp/bases/%s/%s' % (self.cr.dbname, doc.report_unit)
            self.attrs['params'] = (doc.format, uri, doc.mode, doc.depth, {})
        one_check = {}
        one_check[doc.id] = False
        content = ''
        duplicate = 1
        for ex in ids:
            if doc.mode == 'multi':
                for d in doc.child_ids:
                    if d.only_one and one_check.get(d.id, False):
                        continue
                    self.path = '/openerp/bases/%s/%s' % (self.cr.dbname, d.report_unit)
                    (content, duplicate) = self._jasper_execute(ex, d, js, pdf_list, ids, context=context)
                    one_check[d.id] = True
            else:
                if doc.only_one and one_check.get(doc.id, False):
                    continue
                (content, duplicate) = self._jasper_execute(ex, doc, js, pdf_list, ids, context=context)
                one_check[doc.id] = True

        ## We use pyPdf to merge all PDF in unique file
        if len(pdf_list) > 1 or duplicate > 1:
            tmp_content = PdfFileWriter()
            for pdf in pdf_list:
                for x in range(0, duplicate):
                    fp = open(pdf, 'r')
                    tmp_pdf = PdfFileReader(fp)
                    for page in range(tmp_pdf.getNumPages()):
                        tmp_content.addPage(tmp_pdf.getPage(page))
                    c = StringIO()
                    tmp_content.write(c)
                    content = c.getvalue()
                    c.close()
                    fp.close()
                    del fp
                    del c
        elif len(pdf_list) == 1:
            fp = open(pdf_list[0], 'r')
            content = fp.read()
            fp.close()
            del fp

        for f in pdf_list:
            os.remove(f)

        self.obj = external_pdf(content)
        self.obj.set_output_type(self.outputFormat)
        return (self.obj.content, self.outputFormat)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
