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

// Cinta diagonal esquina superior izquierda con el nombre de la compañía activa,
// inspirada en OCA web_environment_ribbon. Un <div> pintado directo en <body>, sin
// componente OWL: no hay estado que reaccione a nada (cambio de compañía = reload).
registry.category("services").add("leulitCompanyTheme", {
    start() {
        const companyId = session.user_companies.current_company;
        const company = session.user_companies.allowed_companies[companyId];
        const color = LEULIT_COMPANY_COLORS[companyId] || LEULIT_COMPANY_COLOR_DEFAULT;

        const ribbon = document.createElement("div");
        ribbon.className = "leulit-company-ribbon";
        ribbon.style.backgroundColor = color;
        ribbon.textContent = company ? company.name : "";
        document.body.appendChild(ribbon);
    },
});
