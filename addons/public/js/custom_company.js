erpnext.company.setup_queries = function(frm) {

	if (frm.doc.enable_perpetual_inventory) {
		$.each([
			["stock_adjustment_account",
				{"root_type": "Expense", "account_type": "Cost of Goods Sold"}],
		], function(i, v) {
			erpnext.company.set_custom_query(frm, v);
		});
	}
}

erpnext.company.set_custom_query = function(frm, v) {
	var filters = {
		"company": frm.doc.name,
		"is_group": 0
	};

	for (var key in v[1]) {
		filters[key] = v[1][key];
	}

	frm.set_query(v[0], function() {
		return {
			filters: filters
		}
	});
}

frappe.ui.form.on('Company', {
	refresh: function(frm) {
		cur_frm.set_query("gudang_penerimaan", function(doc) {
			return {
				filters:  [
					['Warehouse', 'is_group', '=', 0]
				]
			}
		});
	}
})