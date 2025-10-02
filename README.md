# helipistas-erp-odoo-17
Instalar en produccion en odoo:
pip install pypdf
pip install pyqrcode
pip install pyotp

Antes de hacer la importacion lanzar dos alter tables para quitar algun constraint que luego se debe poner de nuevo:

        ALTER TABLE leulit_perfil_formacion
            DROP CONSTRAINT IF EXISTS leulit_perfil_formacion_alumno_perfil_unique;
            
        ALTER TABLE maintenance_plan
            DROP CONSTRAINT IF EXISTS maintenance_plan_equipment_kind_uniq;

        ALTER TABLE leulit_weight_and_balance
	        ALTER COLUMN vuelo_id DROP NOT NULL;

        ALTER TABLE stock_warehouse
            ALTER COLUMN view_location_id DROP NOT NULL;

        ALTER TABLE stock_picking_type
            DROP CONSTRAINT IF EXISTS stock_picking_type_warehouse_id_fkey;

        ALTER TABLE procurement_group
            DROP CONSTRAINT IF EXISTS procurement_group_sale_id_fkey;

        ALTER TABLE stock_picking
            DROP CONSTRAINT IF EXISTS stock_picking_maintenance_request_id_fkey;

        ALTER TABLE stock_lot
            DROP CONSTRAINT IF EXISTS stock_lot_lot_hlp_ica_fkey;

        ALTER TABLE stock_move_line
            DROP CONSTRAINT IF EXISTS stock_move_line_equipment_id_fkey;

        ALTER TABLE stock_move_line
            DROP CONSTRAINT IF EXISTS stock_move_line_maintenance_request_id_fkey;

        ALTER TABLE ir_attachment
            DROP CONSTRAINT IF EXISTS ir_attachment_rel_parte_escuela_fkey;

        ALTER TABLE ir_attachment
            DROP CONSTRAINT IF EXISTS ir_attachment_piloto_adjunto_id_fkey;

        ALTER TABLE ir_attachment
            DROP CONSTRAINT IF EXISTS ir_attachment_calibracion_id_fkey;

        ALTER TABLE ir_attachment
            DROP CONSTRAINT IF EXISTS ir_attachment_rel_verification_line_fkey;

        ALTER TABLE ir_attachment
            DROP CONSTRAINT IF EXISTS ir_attachment_original_id_fkey;

        ALTER TABLE leulit_parte_teorica
            DROP CONSTRAINT IF EXISTS leulit_parte_teorica_vuelo_id_fkey;

        ALTER TABLE leulit_anomalia
            DROP CONSTRAINT IF EXISTS leulit_anomalia_maintenance_request_id_fkey;

        ALTER TABLE project_task
            DROP CONSTRAINT IF EXISTS project_task_parent_id_fkey;

        ALTER TABLE project_task
            DROP CONSTRAINT IF EXISTS project_task_item_job_card_id_fkey;

        ALTER TABLE project_task
            DROP CONSTRAINT IF EXISTS project_task_maintenance_planned_activity_id_fkey;

        ALTER TABLE project_task
            DROP CONSTRAINT IF EXISTS project_task_job_card_id_fkey;

        ALTER TABLE maintenance_planned_activity
            DROP CONSTRAINT IF EXISTS maintenance_planned_activity_job_card_id_fkey;

        ALTER TABLE leulit_perfil_formacion_curso
            DROP CONSTRAINT IF EXISTS leulit_perfil_formacion_curso_pf_curso_tmpl_fkey;

        ALTER TABLE account_analytic_line
            DROP CONSTRAINT IF EXISTS account_analytic_line_general_account_id_fkey;

        ALTER TABLE account_journal
            DROP CONSTRAINT IF EXISTS account_journal_default_account_id_fkey;

        ALTER TABLE account_journal
            DROP CONSTRAINT IF EXISTS account_journal_suspense_account_id_fkey;

        ALTER TABLE account_journal
            DROP CONSTRAINT IF EXISTS account_journal_loss_account_id_fkey;

        ALTER TABLE account_journal
            DROP CONSTRAINT IF EXISTS account_journal_profit_account_id_fkey;

        ALTER TABLE account_payment
            DROP CONSTRAINT IF EXISTS account_payment_move_id_fkey;

        ALTER TABLE project_project
            DROP CONSTRAINT IF EXISTS project_project_analytic_account_id_fkey;

        ALTER TABLE project_task
            DROP CONSTRAINT IF EXISTS project_task_maintenance_request_id_fkey;

        ALTER TABLE project_task
            DROP CONSTRAINT IF EXISTS project_task_maintenance_equipment_id_fkey;
            
        ALTER TABLE project_task
            DROP CONSTRAINT IF EXISTS project_task_supervisado_por_fkey;

        ALTER TABLE project_task
            DROP CONSTRAINT IF EXISTS project_task_production_lot_id_fkey;

        ALTER TABLE project_task
            DROP CONSTRAINT IF EXISTS project_task_sale_order_id_fkey;

        ALTER TABLE project_task
            DROP CONSTRAINT IF EXISTS project_task_sale_line_id_fkey;

        ALTER TABLE project_task
            DROP CONSTRAINT IF EXISTS project_task_airworthiness_directive_id_fkey;

        ALTER TABLE project_task
            DROP CONSTRAINT IF EXISTS project_task_reunion_id_fkey;

        ALTER TABLE account_fiscal_position_account
            DROP CONSTRAINT IF EXISTS account_fiscal_position_account_account_src_id_fkey;

        ALTER TABLE account_fiscal_position_account
            DROP CONSTRAINT IF EXISTS account_fiscal_position_account_account_dest_id_fkey;

        ALTER TABLE hr_expense_sheet
            DROP CONSTRAINT IF EXISTS hr_expense_sheet_message_main_attachment_id_fkey;

        ALTER TABLE hr_expense_sheet
            DROP CONSTRAINT IF EXISTS hr_expense_sheet_journal_id_fkey;

        ALTER TABLE hr_expense
            DROP CONSTRAINT IF EXISTS hr_expense_product_id_fkey;

        ALTER TABLE hr_expense
            DROP CONSTRAINT IF EXISTS hr_expense_sale_order_id_fkey;

        ALTER TABLE hr_expense
            DROP CONSTRAINT IF EXISTS hr_expense_message_main_attachment_id_fkey;

        ALTER TABLE account_move
            DROP CONSTRAINT IF EXISTS account_move_message_main_attachment_id_fkey;

        ALTER TABLE account_move
            DROP CONSTRAINT IF EXISTS account_move_journal_id_fkey;

        ALTER TABLE account_move
            DROP CONSTRAINT IF EXISTS account_move_fiscal_position_id_fkey;

        ALTER TABLE account_tax_repartition_line
            DROP CONSTRAINT IF EXISTS account_tax_repartition_line_tax_id_fkey;

        ALTER TABLE account_move_line
            DROP CONSTRAINT IF EXISTS account_move_line_product_id_fkey;

        ALTER TABLE account_move_line
            DROP CONSTRAINT IF EXISTS account_move_line_journal_id_fkey;

        ALTER TABLE account_move_line
            DROP CONSTRAINT IF EXISTS account_move_line_tax_line_id_fkey;

        ALTER TABLE account_move_line
            DROP CONSTRAINT IF EXISTS account_move_line_purchase_line_id_fkey;

        ALTER TABLE account_analytic_line
            DROP CONSTRAINT IF EXISTS account_analytic_line_byday_id_fkey;

        ALTER TABLE account_analytic_line
            DROP CONSTRAINT IF EXISTS account_analytic_line_checklist_id_fkey;

        ALTER TABLE account_analytic_line
            DROP CONSTRAINT IF EXISTS account_analytic_line_maintenance_request_id_fkey;

        ALTER TABLE account_analytic_line
            DROP CONSTRAINT IF EXISTS account_analytic_line_so_line_fkey;

        ALTER TABLE account_analytic_line
            DROP CONSTRAINT IF EXISTS account_analytic_line_sale_order_fkey;

        ALTER TABLE ir_attachment
            DROP CONSTRAINT IF EXISTS ir_attachment_rel_production_lot_fkey;



Para instalar el modulo de almacen se requiere que este creado un registro de res_company con id=2







Despues de la migracion:
    - Update para los datos de weight_and_balance para el campo vuelo_id:
        UPDATE leulit_weight_and_balance wb
            SET vuelo_id = v.id
            FROM leulit_vuelo v
            WHERE v.weight_and_balance_id = wb.id;


    - Alters para poner los constraints quitados:

        ALTER TABLE leulit_perfil_formacion
            ADD CONSTRAINT leulit_perfil_formacion_alumno_perfil_unique
            UNIQUE (alumno, perfil_tmpl);

        ALTER TABLE maintenance_plan
            ADD CONSTRAINT maintenance_plan_equipment_kind_uniq
            UNIQUE (equipment_id, maintenance_kind_id);

        ALTER TABLE leulit_weight_and_balance
            ALTER COLUMN vuelo_id SET NOT NULL;

        ALTER TABLE stock_warehouse
            ALTER COLUMN view_location_id SET NOT NULL;

        ALTER TABLE stock_picking_type
            ADD CONSTRAINT stock_picking_type_warehouse_id_fkey
            FOREIGN KEY (warehouse_id)
            REFERENCES stock_warehouse(id)
            ON DELETE SET NULL;

        ALTER TABLE procurement_group
            ADD CONSTRAINT procurement_group_sale_id_fkey
            FOREIGN KEY (sale_id)
            REFERENCES sale_order(id)
            ON DELETE SET NULL;

        ALTER TABLE stock_picking
            ADD CONSTRAINT stock_picking_maintenance_request_id_fkey
            FOREIGN KEY (maintenance_request_id)
            REFERENCES maintenance_request(id)
            ON DELETE SET NULL;

        ALTER TABLE stock_lot
            ADD CONSTRAINT stock_lot_lot_hlp_ica_fkey
            FOREIGN KEY (lot_hlp_ica)
            REFERENCES stock_lot(id)
            ON DELETE SET NULL;

        ALTER TABLE stock_move_line
            ADD CONSTRAINT stock_move_line_equipment_id_fkey
            FOREIGN KEY (equipment_id)
            REFERENCES maintenance_equipment(id)
            ON DELETE SET NULL;

        ALTER TABLE stock_move_line
            ADD CONSTRAINT stock_move_line_maintenance_request_id_fkey
            FOREIGN KEY (maintenance_request_id)
            REFERENCES maintenance_request(id)
            ON DELETE SET NULL;



    - Buscar esta linea en todo el codigo personalizado y cambiar el 1 por un 2, mirar si se modifica en las sequencias el cambio de companyia en todo caso, cambiarlo a mano desde la interficie web sino desde la base de datos.
        <field name="company_id">1</field>