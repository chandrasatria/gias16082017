// Copyright (c) 2023, das and contributors
// For license information, please see license.txt

frappe.ui.form.on('Alokasi Product Specialist', {
	refresh: function(frm) {
		frm.set_query("item_group", function(doc) {
			return {
				filters: {
					'is_group': 0,	
				}
			};
		});
		frm.set_query("source_warehouse", function(doc) {
			return {
				filters: {
					'is_group': 0,	
				}
			};
		});
	},
	 validate:function(frm) {
        var total = 0;
        for(var row in frm.doc.material_request_not_ready){
            var baris = frm.doc.material_request_not_ready[row];
            total = total + baris.qty_alokasi;
        }
        frm.set_value('total_qty_alokasi',total);
        frm.refresh_field('total_qty_alokasi');
    },
	source_warehouse:function(frm){
		if(frm.doc.item_code && frm.doc.source_warehouse){
			frappe.call({
				method : "addons.addons.doctype.alokasi_product_specialist.alokasi_product_specialist.get_bin",
				args : {
					"item_code" : frm.doc.item_code,
					"source_warehouse" : frm.doc.source_warehouse
				},
				freeze: true,
				callback : function(hasil){
					for(var baris in hasil.message){
						frm.doc.warehouse_qty = hasil.message[baris].actual_qty
						cur_frm.refresh_fields()
					}
				}
			});
		}
	},

	get_mr: function(frm){
		var array_branch = []
		if (frm.doc.cabang){
			
			for(var row in frm.doc.cabang){
				array_branch.push(frm.doc.cabang[row].branch)
			}
		}	
		
		frm.doc.material_request_not_ready = []

		if(frm.doc.from_date && frm.doc.to_date && frm.doc.ps && frm.doc.item_group){
			frappe.call({
				method : "addons.addons.doctype.alokasi_product_specialist.alokasi_product_specialist.get_mr",
				args : {
					"from_date" : frm.doc.from_date,
					"to_date" : frm.doc.to_date,
					"item_group" : frm.doc.item_group,
					"ps" : frm.doc.ps,
					"branch": array_branch

				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						for(var baris in hasil.message){
							var d = frappe.model.add_child(cur_frm.doc,"Alokasi Product Specialist Table","material_request_not_ready")
							
							d.mr_date = hasil.message[baris].mr_date
							d.material_request = hasil.message[baris].material_request
							d.item_code = hasil.message[baris].item_code
							d.item_name = hasil.message[baris].item_name
							d.cabang = hasil.message[baris].cabang
							d.qty = hasil.message[baris].qty
							d.qty_issued = hasil.message[baris].qty_issued
							d.qty_alokasi = 0
							d.qty_outstanding = hasil.message[baris].qty - hasil.message[baris].qty_alokasi_total
							d.nama_mr_item = hasil.message[baris].nama_mr_item

							cur_frm.refresh_fields()
						}
						var total = 0
						for (var baris_alokasi in frm.doc.material_request_not_ready){
							total = total + frm.doc.material_request_not_ready[baris_alokasi].qty_alokasi
						}
						cur_frm.doc.total_qty_alokasi = total
						cur_frm.refresh_fields()
					}
				}
			})
		}
	}
});

frappe.ui.form.on('Alokasi Product Specialist Table', {
	qty_alokasi:function(frm){
		var total = 0
		for(var row in frm.doc.material_request_not_ready){
			var baris = frm.doc.material_request_not_ready[row]
			total = total + baris.qty_alokasi
		}
		frm.doc.total_qty_alokasi = total
		cur_frm.refresh_fields()
	}
});


