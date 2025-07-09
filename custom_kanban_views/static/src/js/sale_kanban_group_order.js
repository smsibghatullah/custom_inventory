/** @odoo-module **/

import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";

export class SaleOrderKanbanRenderer extends KanbanRenderer {
    get orderedGroups() {
        const stateOrder = ["draft", "sent", "sale", "cancel"];
        const ordered = [...this.props.groups];
        ordered.sort((a, b) => {
            const indexA = stateOrder.indexOf(a.value[0]);
            const indexB = stateOrder.indexOf(b.value[0]);
            return indexA - indexB;
        });
        return ordered;
    }

    get groups() {
        return this.orderedGroups;
    }
}
