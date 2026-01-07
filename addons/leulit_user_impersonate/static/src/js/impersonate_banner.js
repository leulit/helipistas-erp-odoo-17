/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

/**
 * Impersonation Banner Component
 * Shows a banner at the top when user is impersonating another user
 */
export class ImpersonationBanner extends Component {
    static template = "leulit_user_impersonate.ImpersonationBanner";

    setup() {
        this.rpc = useService("rpc");
        this.action = useService("action");
        this.notification = useService("notification");
        
        this.state = useState({
            isImpersonating: false,
            originalUser: null,
            impersonatedUser: null,
        });

        onWillStart(async () => {
            await this.checkImpersonationStatus();
        });
    }

    async checkImpersonationStatus() {
        try {
            const result = await this.rpc("/web/impersonate/status", {});
            if (result.is_impersonating) {
                this.state.isImpersonating = true;
                this.state.originalUser = result.original_user;
                this.state.impersonatedUser = result.impersonated_user;
            }
        } catch (error) {
            console.error("Error checking impersonation status:", error);
        }
    }

    async stopImpersonation() {
        try {
            const result = await this.rpc("/web/impersonate/stop", {});
            if (result.success) {
                this.notification.add(
                    "Stopped impersonation. Reloading...",
                    { type: "success" }
                );
                // Reload to return to original user
                window.location.reload();
            } else {
                this.notification.add(
                    result.error || "Failed to stop impersonation",
                    { type: "danger" }
                );
            }
        } catch (error) {
            console.error("Error stopping impersonation:", error);
            this.notification.add(
                "Error stopping impersonation",
                { type: "danger" }
            );
        }
    }
}

// Register as a systray item (top bar component)
export const systrayItem = {
    Component: ImpersonationBanner,
};

registry.category("systray").add("ImpersonationBanner", systrayItem, { sequence: 1 });


/**
 * Client Actions for starting/stopping impersonation
 */
registry.category("actions").add("start_impersonation", async (env, action) => {
    const rpc = env.services.rpc;
    const notification = env.services.notification;
    
    try {
        const result = await rpc("/web/impersonate/start", {
            user_id: action.params.user_id,
        });
        
        if (result.success) {
            notification.add(
                `Now impersonating ${action.params.user_name}. Reloading...`,
                { type: "success" }
            );
            // Reload to switch user context
            setTimeout(() => window.location.reload(), 1000);
        } else {
            notification.add(
                result.error || "Failed to start impersonation",
                { type: "danger" }
            );
        }
    } catch (error) {
        console.error("Error starting impersonation:", error);
        notification.add(
            "Error starting impersonation",
            { type: "danger" }
        );
    }
});

registry.category("actions").add("stop_impersonation", async (env, action) => {
    const rpc = env.services.rpc;
    const notification = env.services.notification;
    
    try {
        const result = await rpc("/web/impersonate/stop", {});
        
        if (result.success) {
            notification.add(
                "Stopped impersonation. Reloading...",
                { type: "success" }
            );
            // Reload to return to original user
            setTimeout(() => window.location.reload(), 1000);
        } else {
            notification.add(
                result.error || "Failed to stop impersonation",
                { type: "danger" }
            );
        }
    } catch (error) {
        console.error("Error stopping impersonation:", error);
        notification.add(
            "Error stopping impersonation",
            { type: "danger" }
        );
    }
});
