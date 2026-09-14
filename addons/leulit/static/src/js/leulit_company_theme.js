/** @odoo-module **/

import { registry } from "@web/core/registry";
import { session } from "@web/session";

// ponytail: mapa fijo para las compañías conocidas (1=Helipistas, 2=Icarus, ver CLAUDE.md).
// Compañía nueva sin entrada aquí -> gris por defecto. Si esto crece mucho, mover a un
// campo color en res.company e inyectarlo en session_info.
const LEULIT_COMPANY_COLORS = {
    1: "#00594f",
    2: "#8a4b00",
};
const LEULIT_COMPANY_COLOR_DEFAULT = "#546e7a";

// Servicio sin dependencias: fija el color de marca de la compañía activa como variable
// CSS en <html> antes de que se pinte el resto del webclient. El cambio de compañía en
// Odoo siempre recarga la página (company_service.js: setCompanies -> location.reload()),
// así que no hace falta reaccionar a cambios en caliente.
registry.category("services").add("leulitCompanyTheme", {
    start() {
        const companyId = session.user_companies.current_company;
        const color = LEULIT_COMPANY_COLORS[companyId] || LEULIT_COMPANY_COLOR_DEFAULT;
        document.documentElement.style.setProperty("--leulit-company-color", color);
    },
});
