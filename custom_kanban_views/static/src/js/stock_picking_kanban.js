// /** @odoo-module **/

// import KanbanRenderer from '@web/views/kanban/kanban_renderer';
// import KanbanView from '@web/views/kanban/kanban_view';
// import KanbanController from '@web/views/kanban/kanban_controller';
// import viewRegistry from '@web/views/view_registry';

// class StockPickingKanbanRenderer extends KanbanRenderer {
//     async _onDragDrop(event) {
//         const { id, targetGroupId } = event;
//         const record = this.props.records.find(r => r.id === id);
//         if (!record || record.data.state === targetGroupId) return;

//         await this.rpc({
//             model: 'stock.picking',
//             method: 'write',
//             args: [[record.resId], { state: targetGroupId }],
//         });

//         this.trigger('reload');
//     }
// }

// export class StockPickingKanbanView extends KanbanView {}

// StockPickingKanbanView.props = {
//     ...KanbanView.props,
//     Renderer: StockPickingKanbanRenderer,
//     Controller: KanbanController,
// };

// viewRegistry.add('stock_picking_kanban_drag', StockPickingKanbanView);
