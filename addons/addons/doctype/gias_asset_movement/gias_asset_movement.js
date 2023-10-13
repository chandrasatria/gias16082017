// Copyright (c) 2021, das and contributors
// For license information, please see license.txt

frappe.ui.form.on('GIAS Asset Movement', {
	refresh: function(frm) {
		frm.set_query("gias_asset", function() {
			return {
				"filters": {
					"status_movement": "Active"
				}
			};
		});
	},
	gias_asset:function(frm){
		if(frm.doc.posting_date && frm.doc.gias_asset){
			frappe.call({
		        method: "addons.addons.doctype.gias_asset_movement.gias_asset_movement.get_accu",
		        args: {
		          asset: frm.doc.gias_asset,
		          posting_date: frm.doc.posting_date
		        },
		        freeze: true,
		        callback: function (hasil) {
		           if (hasil) {
		           	frm.doc.accumulated_depreciation_amount = hasil.message[0][0]
		           	console.log(hasil.message[0][1])
		           	console.log(hasil.message[0][0])
		           	frm.doc.current_asset_amount = hasil.message[0][1]-hasil.message[0][0]
		           	frm.refresh_fields()
		           	
		           } 
		        },
		      });
		}
		else{
			frappe.throw("Please insert posting date and asset as is needed for getting the accumulated depreciation amount.")
		}
	}
});

cur_frm.add_fetch("gias_asset","server_kepemilikan","lokasi_kepemilikan")
cur_frm.add_fetch("gias_asset","cabang","lokasi_cabang")
cur_frm.add_fetch("gias_asset","opening_accumulated_depreciation","opening_accumulated_depreciation")
// cur_frm.add_fetch("gias_asset","depreciation_amount","accumulated_depreciation_amount")
cur_frm.add_fetch("gias_asset","gross_purchase_amount","gross_purchase_amount")
cur_frm.add_fetch("gias_asset","fixed_asset_account","fixed_asset_account")
cur_frm.add_fetch("gias_asset","accumulated_depreciation_account","accumulated_depreciation_account")
// cur_frm.add_fetch("gias_asset","current_asset_amount","current_asset_amount")