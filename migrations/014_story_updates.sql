-- Fase 1.4: nota de que cambio cuando llega un articulo nuevo a una historia
-- que ya existia, para que el usuario vea "Actualizacion: ..." sin tener que
-- comparar articulos el mismo.
ALTER TABLE stories ADD COLUMN IF NOT EXISTS last_update_note TEXT NULL;
