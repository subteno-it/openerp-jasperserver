# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP,
#    Copyright (C) 2010 SYLEAM Info Services (<http://www.syleam.fr/>)
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
#from lxml.etree import Element, tostring
#from netsvc import Logger, LOG_DEBUG
#from tempfile import mkstemp
#from subprocess import call
from parser import ParseHTML, ParseXML, ParseDIME, ParseContent, WriteContent
from common import BODY_TEMPLATE, parameter
#from tools.misc import ustr
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
        self.cr = cr
        self.uid = uid
        self.ids = ids
        self.data = data
        self.model = data.get('model', False)
        self.context = context
        self.pool = pooler.get_pool(cr.dbname)
        self.obj = None
        self.outputFormat = 'pdf'
        self.path = None

    def _jasper_execute(self, ex, current_document, js_conf, pdf_list, attachment='', reload=False,
                        ids=None, attrs=None, context=None):
        """
        After retrieve datas to launch report, execute it and return the content
        """
        if context is None:
            context = {}

        if ids is None:
            ids = []

        if attrs is None:
            attrs = {}

        js_obj = self.pool.get('jasper.server')
        cur_obj = self.pool.get(self.model).browse(self.cr, self.uid, ex, context=self.context)
        aname = False
        if attachment:
            aname = eval(attachment, {'object': cur_obj, 'time': time})

        duplicate = 1
        if current_document.duplicate:
            try:
                duplicate = int(eval(current_document.duplicate, {'o': cur_obj}))
            except SyntaxError, e:
                _logger.warning('Error %s' % str(e))

        log_debug('Number of duplicate copy: %d' % int(duplicate))

        language = self.context.get('lang', 'en_US')
        if current_document.lang:
            try:
                language = eval(current_document.lang, {'o': cur_obj})
            except SyntaxError, e:
                _logger.warning('Error %s' % str(e))

        if reload and aname:
            aids = self.pool.get('ir.attachment').search(self.cr, self.uid,
                    [('datas_fname', '=', aname + '.pdf'), ('res_model', '=', self.model), ('res_id', '=', ex)])
            if aids:
                brow_rec = self.pool.get('ir.attachment').browse(self.cr, self.uid, aids[0])
                if brow_rec.datas:
                    d = base64.decodestring(brow_rec.datas)
                    WriteContent(d, pdf_list)
                    content = d
        else:
            # Bug found in iReport >= 3.7.x (IN doesn't work in SQL Query)
            # We cannot use $X{IN, field, Collection}
            # use $P!{OERP_ACTIVE_IDS} indeed as
            # ids in ($P!{OERP_ACTIVE_IDS} (exclamation mark)
            d_par = {
                'active_id': ex,
                'active_ids': ','.join(str(i) for i in ids),
                'model': self.model,
                'sql_query': attrs.get('query', "SELECT 'NO QUERY' as nothing"),
                'sql_query_where': attrs.get('query_where', '1 = 1'),
                'report_name': attrs.get('report_name', _('No report name')),
                'lang': language or 'en_US',
            }

            # If XML we must compose it
            if self.data['form']['params'][2] == 'xml':
                d_xml = js_obj.generator(self.cr, self.uid, self.model, self.ids[0],
                        self.data['form']['params'][3], context=self.context)
                d_par['xml_data'] = d_xml

            # Retrieve the company information and send them in parameter
            user = self.pool.get('res.users').browse(self.cr, self.uid, self.uid, context=self.context)
            d_par['company_name'] = user.company_id.name
            d_par['company_logo'] = user.company_id.name.encode('ascii', 'ignore').replace(' ', '_')
            d_par['company_hearder1'] = user.company_id.rml_header1 or ''
            d_par['company_footer1'] = user.company_id.rml_footer1 or ''
            d_par['company_footer2'] = user.company_id.rml_footer2 or ''
            d_par['company_website'] = user.company_id.partner_id.website or ''
            d_par['company_currency'] = user.company_id.currency_id.name or ''

            # Search the default address for the company.
            addr_id = self.pool.get('res.partner').address_get(self.cr, self.uid, [user.company_id.partner_id.id], ['default'])['default']
            if not addr_id:
                raise Exception(_('Error\nmain company have no address defined on the partner!'))
            addr = self.pool.get('res.partner.address').browse(self.cr, self.uid, addr_id, context=self.context)
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
                        d_par[p.name.lower()] = eval(p.code.replace('[[', '').replace(']]', ''), {'o': cur_obj, 'c': user.company_id, 't': time}) or ''
                else:
                        d_par[p.name] = p.code

            self.outputFormat = current_document.format.lower()

            par = parameter(self.data['form'], d_par)
            body_args = {
                'format': self.data['form']['params'][0],
                'path': self.path or self.data['form']['params'][1],
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
                raise Exception('Error, Server not found !')
            except HttpLib2Error, e:
                raise Exception('Error: %r' % e)
            except Exception, e:
                raise Exception('Error: %s' % str(e))

            log_debug('HTTP -> RESPONSE:')
            log_debug('\n'.join(['%s: %s' % (x, resp[x]) for x in resp]))
            if resp.get('content-type').startswith('text/xml'):
                log_debug('CONTENT: %r' % content)
                raise Exception('Code: %s\nMessage: %s' % ParseXML(content))
            elif resp.get('content-type').startswith('text/html'):
                log_debug('CONTENT: %r' % content)
                raise Exception('Error: %s' % ParseHTML(content))
            elif resp.get('content-type') == 'application/dime':
                ParseDIME(content, pdf_list)
            else:
                raise Exception('Unknown Error: Content-type: %s\nMessage:%s' % (resp.get('content-type'), content))

            ###
            ## Store the content in ir.attachment if ask
            if aname:
                name = aname + self.outputFormat
                self.pool.get('ir.attachment').create(self.cr, self.uid, {
                            'name': aname,
                            'datas': base64.encodestring(ParseContent(content)),
                            'datas_fname': name,
                            'res_model': self.model,
                            'res_id': ex,
                            }, context=self.context
                )

            ###
            ## Execute the before query if it available
            ##
            if js_conf.get('after'):
                self.cr.execute(js_conf['after'], {'id': ex})

            ## Update the number of print on object
            fld = self.pool.get(self.model).fields_get(self.cr, self.uid)
            if 'number_of_print' in fld:
                self.pool.get(self.model).write(self.cr, self.uid, [cur_obj.id], {'number_of_print': (getattr(cur_obj, 'number_of_print', None) or 0) + 1}, context=self.context)

        return (content, duplicate)

    def execute(self):
        """Launch the report and return it"""
        ids = self.data['form']['ids']
        js_obj = self.pool.get('jasper.server')
        doc_obj = self.pool.get('jasper.document')
        js_ids = js_obj.search(self.cr, self.uid, [('enable', '=', True)])
        if not len(js_ids):
            raise Exception('Error, no JasperServer found!')

        js = js_obj.read(self.cr, self.uid, js_ids, context=self.context)[0]
        log_debug('DATA:')
        log_debug('\n'.join(['%s: %s' % (x, self.data[x]) for x in self.data]))

        att = self.data['form']['params'][4]
        attach = att.get('attachment', '')
        reload = att.get('attachment_use', False)

        ##
        # For each IDS, launch a query, and return only one result
        #
        pdf_list = []
        doc = doc_obj.browse(self.cr, self.uid, att.get('id'), context=self.context)
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
                    (content, duplicate) = self._jasper_execute(ex, d, js, pdf_list, attach, reload, ids, att, context=self.context)
                    one_check[d.id] = True
            else:
                if doc.only_one and one_check.get(doc.id, False):
                    continue
                (content, duplicate) = self._jasper_execute(ex, doc, js, pdf_list, attach, reload, ids, att, context=self.context)
                one_check[doc.id] = True

        ##
        # We use pyPdf to marge all PDF in unique file
        #
        if len(pdf_list) > 1 or duplicate > 1:
            tmp_content = PdfFileWriter()
            for pdf in pdf_list:
                for x in range(0, duplicate):
                    tmp_pdf = PdfFileReader(open(pdf, 'r'))
                    for page in range(tmp_pdf.getNumPages()):
                        tmp_content.addPage(tmp_pdf.getPage(page))
                    c = StringIO()
                    tmp_content.write(c)
                    content = c.getvalue()

            for f in pdf_list:
                os.remove(f)

        self.obj = external_pdf(content)
        self.obj.set_output_type(self.outputFormat)
        return (self.obj.content, self.outputFormat)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
