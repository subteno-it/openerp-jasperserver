# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP
#    Copyright (c) 2008-2009 EVERLIBRE (http://everlibre.fr) Eric VERNICHON
#    Copyright (C) 2009-2011 SYLEAM ([http://www.syleam.fr]) Christophe CHAUVET
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
#    along with this program.  If not, see [http://www.gnu.org/licenses/].
#
##############################################################################

{
    'name': 'JasperReport Server Interface',
    'version': '6.5.8',
    'category': 'Tools',
    'description': """This module interface JasperReport Server with OpenERP
Features:
- Document source must be in CSV, XML
- Save document as attachment on object
- Retrieve attachment if present
- Launch multiple reports and merge in one printing action
- Add additionnals parameters (ex from fields function)
- Affect group on report
- Use context to display or not the print button (eg: in stock.picking separate per type)
- Execute SQL query before and after treatement
- Launch report based on SQL View

This module required library to work properly

# pip install httplib2 (>= 0.6.0)
# pip install pyPdf (>= 1.13)
# pip install python-dime (>= 0.2.1)


In collaboration with Eric Vernichon (from Everlibre)
""",
    'author': 'SYLEAM',
    'website': 'http://www.syleam.fr',
    'images': ['images/accueil.png', 'images/palette.png', 'images/document_form.png'],
    'depends': [
        'base',
    ],
    'init_xml': [],
    'update_xml': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'data/jasper_document_extension.xml',
        'view/menu.xml',
        'view/oojasper.xml',
        'view/jasper_document.xml',
        #'report/report.xml',
        'wizard/wizard.xml',
    ],
    'demo_xml': [
        'demo/jasper_document.xml',
    ],
    'installable': True,
    'external_dependencies': {'python': ['httplib2', 'pyPdf', 'dime']},
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
