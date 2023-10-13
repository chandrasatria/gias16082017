// Copyright (c) 2021, das and contributors
// For license information, please see license.txt

frappe.ui.form.on('Asset', {
	item_code: function(frm) {
		frappe.call({
			method: "addons.addons.doctype.gias_asset.gias_asset.get_item_asset_detail",
			args:{
				"item_code" : frm.doc.item_code
			},
			freeze:true,
			callback: function(r){
				console.log(r)
				frm.doc.asset_category = r["message"][0][0]
				frm.doc.fixed_asset_account = r["message"][0][1]
				frm.doc.accumulated_depreciation_account = r["message"][0][2]
				frm.doc.depreciation_account = r["message"][0][3]
				frm.refresh_fields()
			}
		});
	},
	onload: function(frm) {
		frm.set_query("item_code", function() {
			return {
				"filters": {
					"disabled": 0,
					"is_fixed_asset": 1,
					"is_stock_item": 0
				}
			};
		});
		frm.set_query("accumulated_depreciation_account", function() {
			return {
				"filters": {
					"disabled": 0,
					"account_type": "Accumulated Depreciation",
					"is_group": 0
				}
			};
		});
		frm.set_query("depreciation_account", function() {
			return {
				"filters": {
					"disabled": 0,
					"account_type": "Accumulated Depreciation",
					"is_group": 0
				}
			};
		});
	}
});