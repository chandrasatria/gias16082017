// Copyright (c) 2022, das and contributors
// For license information, please see license.txt

frappe.ui.form.on('Stock Recount Tools', {
	onload: function(frm) {
		frm.set_query("stock_entry", function() {
			return {
				query: "addons.addons.doctype.stock_recount_tools.stock_recount_tools.ste_query",
			
			};
		});
		frm.set_query("purchase_receipt", function() {
			return {
				"filters": {
					"docstatus": 1
				}
			
			};
		});
	}
});
