/** @odoo-module **/

import { registry } from "@web/core/registry";

registry.category("actions").add("attendance_csv_download", async (env, action) => {

    const ids = env.model.root.selection.map(r => r.resId);
    if (!ids.length) {
        alert("Select at least one record");
        return;
    }

    const result = await env.services.orm.call(
        "hr.attendance",
        "action_export_attendance_csv",
        [ids]
    );

    const blob = new Blob([result.csv], { type: "text/csv;charset=utf-8;" });
    const link = document.createElement("a");

    link.href = URL.createObjectURL(blob);
    link.download = result.filename;

    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
});
