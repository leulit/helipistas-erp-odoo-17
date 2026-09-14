/** @odoo-module **/

import { registry } from "@web/core/registry";

// ponytail: mapa fijo para las compañías conocidas (1=Helipistas, 2=Icarus, 3=Leulit S.L.,
// ver CLAUDE.md). Compañía nueva sin entrada aquí -> gris por defecto. Si esto crece mucho,
// mover a un campo color en res.company e inyectarlo en session_info.
const LEULIT_COMPANY_COLORS = {
    1: "#39ff14",
    2: "#ff6600",
    3: "#00e5ff",
};
const LEULIT_COMPANY_COLOR_DEFAULT = "#c0c0c0";

// Cinta diagonal esquina superior izquierda con el nombre de la compañía activa,
// inspirada en OCA web_environment_ribbon. Un <div> pintado directo en <body>, sin
// componente OWL: no hay estado que reaccione a nada (cambio de compañía = reload).
//
// session.user_companies.current_company es res.users.company_id (la compañía por
// defecto del usuario), NO la compañía activa del selector multi-compañía del navbar
// (esa la decide el parámetro cids de la URL). Usar la primera dejaba la cinta
// desincronizada del badge junto al avatar en cuanto el usuario cambiaba de compañía
// sin que coincidiera con su company_id por defecto. El servicio "company" del core
// es la misma fuente que usa ese badge.
registry.category("services").add("leulitCompanyTheme", {
    dependencies: ["company"],
    start(env, { company }) {
        const current = company.currentCompany;
        const color = LEULIT_COMPANY_COLORS[current.id] || LEULIT_COMPANY_COLOR_DEFAULT;

        const ribbon = document.createElement("div");
        ribbon.className = "leulit-company-ribbon";
        ribbon.style.backgroundColor = color;
        ribbon.style.setProperty("--leulit-ribbon-glow", color);
        ribbon.textContent = current.name;
        document.body.appendChild(ribbon);

        // ponytail: pointer-events:none en el CSS hace que la cinta nunca reciba sus
        // propios eventos de ratón (por eso los clics en los menús de debajo ya
        // funcionaban), así que el fundido al pasar por encima no puede ser un simple
        // :hover en la propia cinta: hay que vigilar la posición global del cursor.
        // getBoundingClientRect() en un elemento rotado da el rectángulo que lo
        // envuelve, algo más grande que el rombo real dibujado — vale como zona de
        // detección, no hace falta la geometría exacta del rombo.
        window.addEventListener("mousemove", (ev) => {
            const rect = ribbon.getBoundingClientRect();
            const inside =
                ev.clientX >= rect.left &&
                ev.clientX <= rect.right &&
                ev.clientY >= rect.top &&
                ev.clientY <= rect.bottom;
            ribbon.classList.toggle("leulit-company-ribbon-hover", inside);
        });
    },
});
