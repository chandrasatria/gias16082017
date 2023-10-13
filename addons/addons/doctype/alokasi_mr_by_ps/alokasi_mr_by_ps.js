// Copyright (c) 2022, das and contributors
// For license information, please see license.txt

frappe.ui.form.on('Alokasi MR by PS', {
	refresh: function(frm) {
		frm.set_query("material_request", function(doc) {
			return {
				filters: {
					'docstatus': 1,	
				}
			};
		});
	},
	get_item: function(frm){
		if(frm.doc.material_request){
			frappe.call({
				method : "addons.addons.doctype.alokasi_mr_by_ps.alokasi_mr_by_ps.get_item_from_material_request",
				args : {
					"mreq" : frm.doc.material_request
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						for(var baris in hasil.message){
							var d = frappe.model.add_child(cur_frm.doc,"MR by PS Table","mr_by_ps_table")
							
							frm.doc.cabang = hasil.message[baris].cabang

							d.item_code = hasil.message[baris].item_code
							d.item_name = hasil.message[baris].item_name
							d.qty = hasil.message[baris].qty
							d.material_request_item = hasil.message[baris].material_request_item
							
							cur_frm.refresh_fields()
						}
					}
				}
			})
		}
	}
});
