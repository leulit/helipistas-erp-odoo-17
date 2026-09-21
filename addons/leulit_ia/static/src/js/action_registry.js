/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SearchPage } from "../components/search_page/search_page";

// Register the client action using the tag defined in ir.actions.client
// The tag must match field name="tag" in ai_search_views.xml
registry.category("actions").add("leulit_ia.search_page", SearchPage);
