/** @odoo-module **/

import { Component, useState, useRef, onMounted, onWillUnmount } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";
import { _t } from "@web/core/l10n/translation";

/**
 * AiChatSidebar — Asistente IA accesible desde el systray de Odoo.
 *
 * Mantiene el historial de conversación en el estado del componente,
 * lo que lo hace persistente mientras el usuario navega entre módulos
 * sin recargar la página.
 */
export class AiChatSidebar extends Component {
    static template = "leulit_ia.AiChatSidebar";
    static props = {};

    setup() {
        this.state = useState({
            isOpen: false,
            messages: [],       // { role: 'user'|'assistant', content: string }
            inputText: "",
            isLoading: false,
        });
        this.conversationHistory = [];  // historial completo para el backend
        this.messagesEndRef = useRef("messagesEnd");
        this.inputRef = useRef("chatInput");
    }

    // ------------------------------------------------------------------
    // Acciones del usuario
    // ------------------------------------------------------------------

    toggleSidebar() {
        this.state.isOpen = !this.state.isOpen;
        if (this.state.isOpen) {
            // Dar foco al input al abrir
            setTimeout(() => {
                if (this.inputRef.el) {
                    this.inputRef.el.focus();
                }
            }, 100);
        }
    }

    onInputKeydown(ev) {
        // Enviar con Enter (sin Shift)
        if (ev.key === "Enter" && !ev.shiftKey) {
            ev.preventDefault();
            this.sendMessage();
        }
    }

    async sendMessage() {
        const text = this.state.inputText.trim();
        if (!text || this.state.isLoading) return;

        // Mostrar el mensaje del usuario inmediatamente
        this.state.messages.push({ role: "user", content: text });
        this.state.inputText = "";
        this.state.isLoading = true;
        this._scrollToBottom();

        try {
            const result = await rpc("/ai/chat", {
                prompt: text,
                conversation_history: this.conversationHistory,
            });

            // Actualizar el historial completo con lo que devuelve el backend
            this.conversationHistory = result.history || [];

            // Mostrar la respuesta del assistant
            this.state.messages.push({
                role: "assistant",
                content: result.response || _t("Sin respuesta del asistente."),
            });
        } catch (error) {
            this.state.messages.push({
                role: "assistant",
                content: _t("Error al contactar con el asistente IA. Por favor, verifica la configuración."),
            });
        } finally {
            this.state.isLoading = false;
            this._scrollToBottom();
        }
    }

    clearChat() {
        this.state.messages = [];
        this.conversationHistory = [];
    }

    // ------------------------------------------------------------------
    // Renderizado de Markdown
    // ------------------------------------------------------------------

    /**
     * Convierte Markdown básico a HTML de forma segura.
     * Soporta: negritas, cursivas, código, listas, saltos de línea.
     * No depende de librerías externas.
     */
    renderMarkdown(text) {
        if (!text) return "";
        let html = text
            // Escapar HTML antes de procesar
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            // Bloques de código (```...```)
            .replace(/```([\s\S]*?)```/g, "<pre><code>$1</code></pre>")
            // Código inline (`...`)
            .replace(/`([^`]+)`/g, "<code>$1</code>")
            // Negritas (**texto** o __texto__)
            .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
            .replace(/__(.+?)__/g, "<strong>$1</strong>")
            // Cursivas (*texto* o _texto_)
            .replace(/\*(.+?)\*/g, "<em>$1</em>")
            .replace(/_([^_]+)_/g, "<em>$1</em>")
            // Headers (## y ###)
            .replace(/^### (.+)$/gm, "<h5>$1</h5>")
            .replace(/^## (.+)$/gm, "<h4>$1</h4>")
            .replace(/^# (.+)$/gm, "<h3>$1</h3>")
            // Listas sin orden (- item o * item)
            .replace(/^\s*[-*] (.+)$/gm, "<li>$1</li>")
            // Envolver <li> consecutivos en <ul>
            .replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`)
            // Saltos de línea dobles → párrafos
            .replace(/\n\n/g, "</p><p>")
            // Saltos de línea simples → <br>
            .replace(/\n/g, "<br>");

        return `<p>${html}</p>`;
    }

    // ------------------------------------------------------------------
    // Utilidades internas
    // ------------------------------------------------------------------

    _scrollToBottom() {
        setTimeout(() => {
            if (this.messagesEndRef.el) {
                this.messagesEndRef.el.scrollIntoView({ behavior: "smooth" });
            }
        }, 50);
    }
}

// Registrar como elemento del systray (persiste al navegar entre módulos)
registry.category("systray").add("leulit_ia.AiChatSidebar", {
    Component: AiChatSidebar,
    sequence: 5,
});
