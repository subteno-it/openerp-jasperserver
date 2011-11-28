--
-- Create function to retrieve an ID with the XML ID
--
CREATE OR REPLACE FUNCTION get_id(mod varchar, val varchar)
RETURNS integer AS
$syleam$

DECLARE
    res integer;
BEGIN
    SELECT INTO res res_id
    FROM   ir_model_data
    WHERE  module = mod
    AND    name = val;

    IF NOT FOUND THEN
        RETURN NULL;
    ELSE
        RETURN res;
    END IF;

END;
$syleam$ LANGUAGE plpgsql;
