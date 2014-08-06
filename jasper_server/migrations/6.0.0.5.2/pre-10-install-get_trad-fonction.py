# -*- coding: utf-8 -*-
##############################################################################
#
#    jasper_server module for OpenERP, Management module for Jasper Server
#    Copyright (C) 2011 SYLEAM (<http://www.syleam.fr/>)
#              Christophe CHAUVET <christophe.chauvet@syleam.fr>
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


__name__ = "Add get_trad functions in PostgreSQL Database"


def migrate(cr, v):
    """
    Add translation function get_trad to retrieve translation from OpenERP

    :param cr: Current cursor to the database
    :param v: version number
    """
    cr.execute("""
        CREATE OR REPLACE FUNCTION get_trad(langue varchar, typ varchar,
               nom varchar, texte varchar) RETURNS varchar AS
        $$
            DECLARE
              resultat varchar;
            BEGIN
                IF texte IS NOT NULL THEN
                    SELECT INTO resultat value FROM ir_translation
                     WHERE lang=langue AND type=typ AND name=nom AND src=texte;
                ELSE
                    SELECT INTO resultat value FROM ir_translation
                     WHERE lang=langue AND type=typ AND name=nom;
                END IF;

                IF NOT FOUND THEN
                    RETURN texte;
                ELSE
                    RETURN resultat;
                END IF;
            END;
        $$ LANGUAGE plpgsql;""")

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
