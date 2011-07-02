# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP,
#    Copyright (C) 2009-2011 SYLEAM Info Services (<http://www.syleam.fr/>) Christophe CHAUVET
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
from lxml.etree import Element, tostring
from tools import ustr
from tools.translate import _
import logging
_logger = logging.getLogger('jasper_server')


def log_error(message):
    _logger.error(message)


class jasper_server(osv.osv):
    """
    Class to store the Jasper Server configuration
    """
    _name = 'jasper.server'
    _description = 'Jasper server configuration'
    _rec_name = 'host'

    _columns = {
        'host': fields.char('Host', size=128, required=True, help='Enter hostname or IP address'),
        'port': fields.integer('Port'),
        'user': fields.char('Username', size=128, required=True, help='Enter the username for JasperServer user, by default is jasperadmin'),
        'pass': fields.char('Password', size=128, required=True, help='Enter the password for the user, by defaul is jasperadmin'),
        'repo': fields.char('Repository', size=256, required=True, help='Enter the address of the repository'),
        'sequence': fields.integer('Sequence'),
        'enable': fields.boolean('Enable', help='Check this, if the server is available',),
    }

    _defaults = {
        'host': lambda *a: 'localhost',
        'port': lambda *a: 8180,
        'user': lambda *a: 'jasperadmin',
        'pass': lambda *a: 'jasperadmin',
        'repo': lambda *a: '/jasperserver/services/repository',
        'sequence': lambda *a: 10,
    }

    def __init__(self, pool, cr):
        """
        Check if analysis schema and temporal table is present in the database
        if not, create it
        """
        cr.execute("""show server_version""")
        pg_version = cr.fetchone()[0].split('.')
        pg_version = tuple([int(x) for x in pg_version])

        if pg_version >= (8, 3, 0):
            cr.execute("""SELECT count(*)
                          FROM   pg_namespace
                          WHERE  nspname='analysis'""")
            if not cr.fetchone()[0]:
                _logger.info('Analysis schema have been created !')
                cr.execute("""CREATE SCHEMA analysis;
                       COMMENT ON SCHEMA analysis
                       IS 'Schema use for customize view in Jasper BI';""")

            cr.execute("""SELECT count(*)
                          FROM   pg_tables
                          WHERE  schemaname = 'analysis'
                          AND    tablename='dimension_date'""")
            if not cr.fetchone()[0]:
                _logger.info('Analysis temporal table have been created !')
                cr.execute("""create table analysis.dimension_date as
                              select to_number(to_char(x.datum, 'YYYYMMDD'), 'FM99999999') as id,
                                     to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD') as "date",
                                     extract(year from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "year",
                                     extract(month from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "month",
                                     extract(day from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "day",
                                     extract(quarter from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "quarter",
                                     extract(week from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "week",
                                     extract(dow from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "day_of_week",
                                     extract(isodow from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "iso_day_of_week",
                                     extract(doy from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "day_of_year",
                                     extract(century from to_date(to_char(x.datum, 'YYYY-MM-DD'), 'YYYY-MM-DD'))::integer as "century"
                              from
                              (select to_date('2000-01-01','YYYY-MM-DD') + (to_char(m, 'FM9999999999')||' day')::interval as datum
                               from   generate_series(0, 15000) m) x""")

        # Check if plpgsql language is installed, if not raise an error
        cr.execute("""select count(*) as "installed" from pg_language where lanname='plpgsql';""")
        if not cr.fetchone()[0]:
            _logger.warn('Please installed plpgsql in your database, before update your OpenERP server!\nused for translation')

        super(jasper_server, self).__init__(pool, cr)

    ## ************************************************
    # These method can create an XML for Jasper Server
    # *************************************************
    # TODO: ban element per level
    ban = (
        'res.company', 'ir.model', 'ir.model.fields', 'res.groups', 'ir.model.data',
        'ir.model.grid', 'ir.model.access', 'ir.ui.menu', 'ir.actions.act_window',
        'ir.action.wizard', 'ir.attachment', 'ir.cron', 'ir.rule', 'ir.rule.group',
        'ir.actions.actions', 'ir.actions.report.custom', 'ir.actions.report.xml',
        'ir.actions.url', 'ir.ui.view', 'ir.sequence', 'res.partner.event',
    )

    @staticmethod
    def format_element(element):
        """
        convert element in lowercase and replace space per _
        """
        return ustr(element).lower().replace(' ', '_')

    def generate_context(self, cr, uid, context=None):
        """
        generate xml with context header
        """
        f_list = (
            'context_tz', 'context_lang', 'name', 'signature', 'company_id',
        )

        # TODO: Use browse to add the address of the company
        user = self.pool.get('res.users')
        usr = user.read(cr, uid, [uid], context=context)[0]
        ctx = Element('context')

        for val in usr:
            if val in f_list:
                e = Element(val)
                if usr[val]:
                    if isinstance(usr[val], list):
                        e.set('id', str(usr[val][0]))
                        e.text = str(usr[val][1])
                    else:
                        e.text = str(usr[val])
                ctx.append(e)

        return ctx

    def generate_xml(self, cr, uid, relation, id, depth, old_relation='', old_field='', context=None):
        """
        Generate xml for an object recursively
        """
        if not context:
            context = {}
        irm = self.pool.get('ir.model')
        if isinstance(relation, int):
            irm_ids = [relation]
        else:
            irm_ids = irm.search(cr, uid, [('model', '=', relation)])

        if not irm_ids:
            log_error('Model %s not found !' % relation)

        ##
        # We must ban many model
        #
        ban = (
            'res.company', 'ir.model', 'ir.model.fields', 'res.groups', 'ir.model.data',
            'ir.model.grid', 'ir.model.access', 'ir.ui.menu', 'ir.actions.act_window',
            'ir.action.wizard', 'ir.attachment', 'ir.cron', 'ir.rule', 'ir.rule.group',
            'ir.actions.actions', 'ir.actions.report.custom', 'ir.actions.report.xml',
            'ir.actions.url', 'ir.ui.view', 'ir.sequence',
        )

        ##
        # If generate_xml was called by a relation field, we must keep
        # the original filename
        ir_model = irm.read(cr, uid, irm_ids[0])
        if isinstance(relation, int):
            relation = ir_model['model']

        irm_name = self.format_element(ir_model['name'])
        if old_field:
            x = Element(self.format_element(old_field), relation=relation, id=str(id))
        else:
            x = Element(irm_name, id='%s' % id)

        if not id:
            return x

        if isinstance(id, (int, long)):
            id = [id]

        obj = self.pool.get(relation)
        mod_ids = obj.read(cr, uid, id, context=context)
        mod_fields = obj.fields_get(cr, uid)
        for mod in mod_ids:
            for f in mod_fields:
                field = f.lower()
                name = mod_fields[f]['string']
                type = mod_fields[f]['type']
                value = mod[f]
                e = Element(field, label='%s' % self.format_element(name))
                if type in ('char', 'text', 'selection'):
                    e.text = value and unicode(value) or ''
                elif type == 'integer':
                    e .text = value and str(value) or '0'
                elif type == 'float':
                    e.text = value and str(value) or '0.0'
                elif type == 'date':
                    e.set('format', 'YYYY-mm-dd')
                    e.text = value or ''
                elif type == 'datetime':
                    e.set('format', 'YYYY-mm-dd HH:MM:SS')
                    e.text = value or ''
                elif type == 'boolean':
                    e.text = str(value)
                elif type == 'many2one':
                    if not isinstance(value, int):
                        value = value and value[0] or 0
                    #log_error('Current: %r Old: %r' % (mod_fields[f]['relation'], relation))
                    if depth > 0 and value and mod_fields[f]['relation'] != old_relation and mod_fields[f]['relation'] not in ban:
                        e = self.generate_xml(cr, uid, mod_fields[f]['relation'], value, depth - 1, relation, field)
                    else:
                        e.set('id', '%r' % value or 0)
                        if not isinstance(value, int):
                            e.text = str(mod[f][1])
                elif type in ('one2many', 'many2many'):
                    if depth > 0 and value and mod_fields[f]['relation'] not in ban:
                        for v in value:
                            x.append(self.generate_xml(cr, uid, mod_fields[f]['relation'], v, depth - 1, relation, field))
                        continue
                    else:
                        e.set('id', '%r' % value)
                elif type in ('binary', 'reference'):
                    e.text = 'Not supported'
                else:
                    log_error('OUPS un oubli %s: %s(%s)' % (field, name, type))
                x.append(e)
        return x

    def generator(self, cr, uid, model, id, depth, context=None):
        root = Element('data')
        root.append(self.generate_context(cr, uid, context=context))
        root.append(self.generate_xml(cr, uid, model, id, depth, context=context))
        return tostring(root, pretty_print=context.get('indent', False))

jasper_server()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
