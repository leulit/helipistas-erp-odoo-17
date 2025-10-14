# helipistas-erp-odoo-17
Instalar en produccion en odoo:
docker exec -ti helipistas_odoo pip install pypdf
docker exec -ti helipistas_odoo pip install pyqrcode
docker exec -ti helipistas_odoo pip install pypng
docker exec -ti helipistas_odoo pip install pyotp

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

        ALTER TABLE project_project
            DROP CONSTRAINT IF EXISTS project_project_project_status_fkey;

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

        ALTER TABLE ir_attachment
            ADD CONSTRAINT ir_attachment_rel_parte_escuela_fkey
            FOREIGN KEY (rel_parte_escuela)
            REFERENCES leulit_rel_parte_escuela_cursos_alumnos(id)
            ON DELETE SET NULL;

        ALTER TABLE ir_attachment
            ADD CONSTRAINT ir_attachment_piloto_adjunto_id_fkey
            FOREIGN KEY (piloto_adjunto_id)
            REFERENCES leulit_piloto_adjunto(id)
            ON DELETE SET NULL;

        ALTER TABLE ir_attachment
            ADD CONSTRAINT ir_attachment_calibracion_id_fkey
            FOREIGN KEY (calibracion_id)
            REFERENCES leulit_calibracion(id)
            ON DELETE SET NULL;

        ALTER TABLE ir_attachment
            ADD CONSTRAINT ir_attachment_rel_verification_line_fkey
            FOREIGN KEY (rel_verification_line)
            REFERENCES mgmtsystem_verification_line(id)
            ON DELETE SET NULL;

        ALTER TABLE ir_attachment
            ADD CONSTRAINT ir_attachment_original_id_fkey
            FOREIGN KEY (original_id)
            REFERENCES ir_attachment(id)
            ON DELETE SET NULL;

        ALTER TABLE leulit_parte_teorica
            ADD CONSTRAINT leulit_parte_teorica_vuelo_id_fkey
            FOREIGN KEY (vuelo_id)
            REFERENCES leulit_vuelo(id)
            ON DELETE SET NULL;

        ALTER TABLE leulit_anomalia
            ADD CONSTRAINT leulit_anomalia_maintenance_request_id_fkey
            FOREIGN KEY (maintenance_request_id)
            REFERENCES maintenance_request(id)
            ON DELETE SET NULL;

        ALTER TABLE project_task
            ADD CONSTRAINT project_task_parent_id_fkey
            FOREIGN KEY (parent_id)
            REFERENCES project_task(id)
            ON DELETE SET NULL;

        ALTER TABLE project_task
            ADD CONSTRAINT project_task_item_job_card_id_fkey
            FOREIGN KEY (item_job_card_id)
            REFERENCES leulit_job_card_item(id)
            ON DELETE SET NULL;

        ALTER TABLE project_task
            ADD CONSTRAINT project_task_maintenance_planned_activity_id_fkey
            FOREIGN KEY (maintenance_planned_activity_id)
            REFERENCES maintenance_planned_activity(id)
            ON DELETE SET NULL;

        ALTER TABLE project_task
            ADD CONSTRAINT project_task_job_card_id_fkey
            FOREIGN KEY (job_card_id)
            REFERENCES leulit_job_card(id)
            ON DELETE SET NULL;

        ALTER TABLE maintenance_planned_activity
            ADD CONSTRAINT maintenance_planned_activity_job_card_id_fkey
            FOREIGN KEY (job_card_id)
            REFERENCES leulit_job_card(id)
            ON DELETE SET NULL;

        ALTER TABLE leulit_perfil_formacion_curso
            ADD CONSTRAINT leulit_perfil_formacion_curso_pf_curso_tmpl_fkey
            FOREIGN KEY (pf_curso_tmpl)
            REFERENCES leulit_perfil_formacion_curso(id)
            ON DELETE SET NULL;

        ALTER TABLE account_analytic_line
            ADD CONSTRAINT account_analytic_line_general_account_id_fkey
            FOREIGN KEY (general_account_id)
            REFERENCES account_account(id)
            ON DELETE RESTRICT;

        ALTER TABLE account_journal
            ADD CONSTRAINT account_journal_default_account_id_fkey
            FOREIGN KEY (default_account_id)
            REFERENCES account_account(id)
            ON DELETE RESTRICT;

        ALTER TABLE account_journal
            ADD CONSTRAINT account_journal_suspense_account_id_fkey
            FOREIGN KEY (suspense_account_id)
            REFERENCES account_account(id)
            ON DELETE RESTRICT;

        ALTER TABLE account_journal
            ADD CONSTRAINT account_journal_loss_account_id_fkey
            FOREIGN KEY (loss_account_id)
            REFERENCES account_account(id)
            ON DELETE SET NULL;

        ALTER TABLE account_journal
            ADD CONSTRAINT account_journal_profit_account_id_fkey
            FOREIGN KEY (profit_account_id)
            REFERENCES account_account(id)
            ON DELETE SET NULL;

        ALTER TABLE account_payment
            ADD CONSTRAINT account_payment_move_id_fkey
            FOREIGN KEY (move_id)
            REFERENCES account_move(id)
            ON DELETE CASCADE;

        ALTER TABLE project_project
            ADD CONSTRAINT project_project_analytic_account_id_fkey
            FOREIGN KEY (analytic_account_id)
            REFERENCES account_analytic_account(id)
            ON DELETE SET NULL;

        ALTER TABLE project_project
            ADD CONSTRAINT project_project_project_status_fkey
            FOREIGN KEY (project_status)
            REFERENCES project_status(id)
            ON DELETE RESTRICT;

        ALTER TABLE project_task
            ADD CONSTRAINT project_task_maintenance_request_id_fkey
            FOREIGN KEY (maintenance_request_id)
            REFERENCES maintenance_request(id)
            ON DELETE CASCADE;

        ALTER TABLE project_task
            ADD CONSTRAINT project_task_maintenance_equipment_id_fkey
            FOREIGN KEY (maintenance_equipment_id)
            REFERENCES maintenance_equipment(id)
            ON DELETE SET NULL;

        ALTER TABLE project_task
            ADD CONSTRAINT project_task_supervisado_por_fkey
            FOREIGN KEY (supervisado_por)
            REFERENCES leulit_mecanico(id)
            ON DELETE SET NULL;

        ALTER TABLE project_task
            ADD CONSTRAINT project_task_production_lot_id_fkey
            FOREIGN KEY (production_lot_id)
            REFERENCES stock_lot(id)
            ON DELETE SET NULL;

        ALTER TABLE project_task
            ADD CONSTRAINT project_task_sale_order_id_fkey
            FOREIGN KEY (sale_order_id)
            REFERENCES sale_order(id)
            ON DELETE SET NULL;

        ALTER TABLE project_task
            ADD CONSTRAINT project_task_sale_line_id_fkey
            FOREIGN KEY (sale_line_id)
            REFERENCES sale_order_line(id)
            ON DELETE SET NULL;

        ALTER TABLE project_task
            ADD CONSTRAINT project_task_airworthiness_directive_id_fkey
            FOREIGN KEY (airworthiness_directive_id)
            REFERENCES leulit_airworthiness_directive(id)
            ON DELETE SET NULL;

        ALTER TABLE project_task
            ADD CONSTRAINT project_task_reunion_id_fkey
            FOREIGN KEY (reunion_id)
            REFERENCES leulit_reunion(id)
            ON DELETE SET NULL;

        ALTER TABLE account_fiscal_position_account
            ADD CONSTRAINT account_fiscal_position_account_account_src_id_fkey
            FOREIGN KEY (account_src_id)
            REFERENCES account_account(id)
            ON DELETE RESTRICT;

        ALTER TABLE account_fiscal_position_account
            ADD CONSTRAINT account_fiscal_position_account_account_dest_id_fkey
            FOREIGN KEY (account_dest_id)
            REFERENCES account_account(id)
            ON DELETE RESTRICT;

        ALTER TABLE hr_expense_sheet
            ADD CONSTRAINT hr_expense_sheet_message_main_attachment_id_fkey
            FOREIGN KEY (message_main_attachment_id)
            REFERENCES ir_attachment(id)
            ON DELETE SET NULL;

        ALTER TABLE hr_expense_sheet
            ADD CONSTRAINT hr_expense_sheet_journal_id_fkey
            FOREIGN KEY (journal_id)
            REFERENCES account_journal(id)
            ON DELETE SET NULL;

        ALTER TABLE hr_expense
            ADD CONSTRAINT hr_expense_product_id_fkey
            FOREIGN KEY (product_id)
            REFERENCES product_product(id)
            ON DELETE RESTRICT;

        ALTER TABLE hr_expense
            ADD CONSTRAINT hr_expense_sale_order_id_fkey
            FOREIGN KEY (sale_order_id)
            REFERENCES sale_order(id)
            ON DELETE SET NULL;

        ALTER TABLE hr_expense
            ADD CONSTRAINT hr_expense_message_main_attachment_id_fkey
            FOREIGN KEY (message_main_attachment_id)
            REFERENCES ir_attachment(id)
            ON DELETE SET NULL;

        ALTER TABLE account_move
            ADD CONSTRAINT account_move_message_main_attachment_id_fkey
            FOREIGN KEY (message_main_attachment_id)
            REFERENCES ir_attachment(id)
            ON DELETE SET NULL;

        ALTER TABLE account_move
            ADD CONSTRAINT account_move_journal_id_fkey
            FOREIGN KEY (journal_id)
            REFERENCES account_journal(id)
            ON DELETE RESTRICT;

        ALTER TABLE account_move
            ADD CONSTRAINT account_move_fiscal_position_id_fkey
            FOREIGN KEY (fiscal_position_id)
            REFERENCES account_fiscal_position(id)
            ON DELETE RESTRICT;

        ALTER TABLE account_tax_repartition_line
            ADD CONSTRAINT account_tax_repartition_line_tax_id_fkey
            FOREIGN KEY (tax_id)
            REFERENCES account_tax(id)
            ON DELETE CASCADE;

        ALTER TABLE account_move_line
            ADD CONSTRAINT account_move_line_product_id_fkey
            FOREIGN KEY (product_id)
            REFERENCES product_product(id)
            ON DELETE RESTRICT;

        ALTER TABLE account_move_line
            ADD CONSTRAINT account_move_line_journal_id_fkey
            FOREIGN KEY (journal_id)
            REFERENCES account_journal(id)
            ON DELETE SET NULL;

        ALTER TABLE account_move_line
            ADD CONSTRAINT account_move_line_tax_line_id_fkey
            FOREIGN KEY (tax_line_id)
            REFERENCES account_tax(id)
            ON DELETE RESTRICT;

        ALTER TABLE account_move_line
            ADD CONSTRAINT account_move_line_purchase_line_id_fkey
            FOREIGN KEY (purchase_line_id)
            REFERENCES purchase_order_line(id)
            ON DELETE SET NULL;

        ALTER TABLE account_analytic_line
            ADD CONSTRAINT account_analytic_line_byday_id_fkey
            FOREIGN KEY (byday_id)
            REFERENCES leulit_account_analytic_line_byday(id)
            ON DELETE RESTRICT;

        ALTER TABLE account_analytic_line
            ADD CONSTRAINT account_analytic_line_checklist_id_fkey
            FOREIGN KEY (checklist_id)
            REFERENCES leulit_checklist(id)
            ON DELETE SET NULL;

        ALTER TABLE account_analytic_line
            ADD CONSTRAINT account_analytic_line_maintenance_request_id_fkey
            FOREIGN KEY (maintenance_request_id)
            REFERENCES maintenance_request(id)
            ON DELETE SET NULL;

        ALTER TABLE account_analytic_line
            ADD CONSTRAINT account_analytic_line_so_line_fkey
            FOREIGN KEY (so_line)
            REFERENCES sale_order_line(id)
            ON DELETE SET NULL;

        ALTER TABLE account_analytic_line
            ADD CONSTRAINT account_analytic_line_sale_order_fkey
            FOREIGN KEY (sale_order)
            REFERENCES sale_order(id)
            ON DELETE SET NULL;

        ALTER TABLE ir_attachment
            ADD CONSTRAINT ir_attachment_rel_production_lot_fkey
            FOREIGN KEY (rel_production_lot)
            REFERENCES stock_lot(id)
            ON DELETE SET NULL;



    - Buscar esta linea en todo el codigo personalizado y cambiar el 1 por un 2, mirar si se modifica en las sequencias el cambio de companyia en todo caso, cambiarlo a mano desde la interficie web sino desde la base de datos.
        <field name="company_id">1</field>