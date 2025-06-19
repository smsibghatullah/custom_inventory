/** @odoo-module **/

import { registry } from "@web/core/registry";
import { Component, onMounted } from "@odoo/owl";
import { ajax } from "@web/core/network/rpc_service";

export class CustomerStatementCheckbox extends Component {
    setup() {
        onMounted(() => {
            const wrapper = this.el;
            const checkboxes = wrapper.querySelectorAll("input[type='checkbox'][data-line-id]");
            console.log(checkboxes,"pppppppppppppppppppppppp")
            checkboxes.forEach((checkbox) => {
                checkbox.addEventListener("change", async (event) => {
                    const lineId = parseInt(event.target.dataset.lineId);
                    const isChecked = event.target.checked;

                    if (!isNaN(lineId)) {
                        await ajax.rpc("/customer_statement/update_line_selection", {
                            line_id: lineId,
                            is_selected: isChecked,
                        });
                    }
                });
            });
        });
    }
}

registry.category("fields").add("customer_statement_html_wrapper", CustomerStatementCheckbox);
