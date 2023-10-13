// Copyright (c) 2021, das and contributors
// For license information, please see license.txt

frappe.ui.form.on('Memo Ekspedisi', {
	onload: function(frm) {
		frm.set_query("purchase_order_delivery_pod", function(){
	        return {
	            "filters": {
	               	"is_pod": "POD",
	               	"docstatus": 1
	            }   
	        }
	    });
	    frm.set_query("purchase_order", function(){
	        return {
	            "filters": {
	               	"is_pod": "Non POD",
	               	"docstatus": 1
	            }   
	        }
	    });
	    frm.add_custom_button(__('Make POD'), () => 
				frappe.xcall("addons.addons.doctype.memo_ekspedisi.memo_ekspedisi.make_pod",{
					'memo_ekspedisi': frm.doc.name,
					'po': frm.doc.purchase_order
				}).then(purchase_order =>{
					frappe.model.sync(purchase_order);
					frappe.set_route('Form', purchase_order.doctype, purchase_order.name);
				})
				);
	},
	refresh: function(frm){
		if(!frm.doc.__islocal){
			frm.add_custom_button(__('Make POD'), () => 
				frappe.xcall("addons.addons.doctype.memo_ekspedisi.memo_ekspedisi.make_pod",{
					'memo_ekspedisi': frm.doc.name,
					'po': frm.doc.purchase_order
				}).then(purchase_order =>{
					frappe.model.sync(purchase_order);
					frappe.set_route('Form', purchase_order.doctype, purchase_order.name);
				})
				);
		}
		/*frm.set_df_property("items", "read_only", frm.is_new() ? 0 : 1);
		frm.set_df_property("tonase__kg_", "read_only", frm.is_new() ? 0 : 1);*/
		frm.set_query("purchase_order_delivery_pod", function(){
	        return {
	            "filters": {
	               	"is_pod": "POD",
	               	"docstatus": 1,
	               	"no_memo_ekspedisi" : cur_frm.doc.name
	            }   
	        }
	    });
	},
	purchase_order_delivery_pod:function(frm){
		if(frm.doc.purchase_order_delivery_pod){
			frappe.call({
				method : "addons.addons.doctype.memo_ekspedisi.memo_ekspedisi.get_dpp_ppn_from_pod",
				args : {
					"pod" : frm.doc.purchase_order_delivery_pod
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						frm.doc.harga = []
						for(var baris in hasil.message){
							var d = frappe.model.add_child(cur_frm.doc,"Tabel Harga Memo Siap Ekspedisi","harga")
							d.harga__dpp_ = hasil.message[baris].total
							d.ppn = hasil.message[baris].total_taxes_and_charges
							cur_frm.refresh_fields()
						}
						var total_harga = 0
						for(var baris in frm.doc.harga){
							total_harga += frm.doc.harga[baris].harga__dpp_
						}
						frm.doc.total_harga_dpp = total_harga
						cur_frm.refresh_fields()
					}
				}
			})
			frappe.call({
				method : "addons.custom_standard.custom_purchase_order.get_rute_to",
				args : {
					"no_me" : frm.doc.purchase_order_delivery_pod
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						for(var baris in hasil.message){
							if(hasil.message[baris].rute_to){
								var d = frappe.model.add_child(cur_frm.doc,"Tabel Rute To Memo Permintaan Ekspedisi Eksternal","rute_to")
								d.rute_to = hasil.message[baris].rute_to
							}
						}
						cur_frm.refresh_fields()						
					}
				}
			})
		}
	},
	stock_entry: function(frm) {
		if(cur_frm.doc.stock_entry){
			frappe.db.get_value("Stock Entry", {"name": cur_frm.doc.stock_entry}, "cabang")
            .then(data => {
                cur_frm.set_value("cabang",data.message.cabang);
            })

			frm.doc.no_mrrq = []
			frm.doc.purchase_order = ""
			frappe.call({
				method : "addons.addons.doctype.memo_ekspedisi.memo_ekspedisi.get_rq_from_ste",
				args : {
					"ste" : frm.doc.stock_entry
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						//console.log(hasil)
						for(var baris in hasil.message){
							var d = frappe.model.add_child(cur_frm.doc,"Material Request Table","no_mrrq")

							d.no_mrrq = hasil.message[baris].material_request
							if(hasil.message[baris].parent){
								cur_frm.doc.purchase_order = hasil.message[baris].parent
							}
							cur_frm.refresh_fields()
						}
						frm.set_query("purchase_order_delivery_pod", function(){
					        return {
					            "filters": {
					               	"is_pod": "POD",
					               	"docstatus": 1,
					               	"no_po" : cur_frm.doc.purchase_order
					            }   
					        }
					    });
					}
				}
			})
			frm.doc.items = []
			var items = []
			for(var i = 0;i<cur_frm.doc.items.length;i++){
				var data = {
					"item_code": cur_frm.doc.items[i].kode_material,
					"qty":cur_frm.doc.items[i].qty_rq
				}
				items.push(data)
			}
			
			frappe.call({
				method : "addons.addons.doctype.memo_ekspedisi.memo_ekspedisi.get_items_from_ste",
				args : {
					"ste" : frm.doc.stock_entry
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						console.log(hasil)
						for(var baris in hasil.message){
							
							if(hasil.message[baris].total_qty){
								var qty =   hasil.message[baris].qty_rq - hasil.message[baris].total_qty
							}else{
								qty = hasil.message[baris].qty
							}
							console.log(hasil.message[baris])
							if(qty > 0){
								var d = frappe.model.add_child(cur_frm.doc,"Memo Pengiriman Table","items")
							
								d.kode_material = hasil.message[baris].item_code
								d.nama_barang = hasil.message[baris].item_name
								d.qty_rq = qty
								// minta dimatiin 
								d.stuffing = qty
								d.qty_uom = hasil.message[baris].uom
								d.berat = hasil.message[baris].weight_per_unit
								d.berat_uom = hasil.message[baris].weight_uom
								d.tipe = "Stock Entry"
								d.nama_dokumen = hasil.message[baris].ste_name

							}
							

							cur_frm.refresh_fields()
						}
						var total_berat = 0
						/*for(var baris in frm.doc.items){
							total_berat += d.qty_rq * d.berat
						}*/
						for(var i=0;i<cur_frm.doc.items.length;i++) {
							total_berat += cur_frm.doc.items[i].qty_rq * cur_frm.doc.items[i].berat
						}
						frm.doc.tonase__kg_ = total_berat
						cur_frm.refresh_fields()
					}
				}
			})
		
		}
	},
	purchase_order: function(frm) {
		if(frm.doc.purchase_order){
			frm.set_query("purchase_order_delivery_pod", function(){
		        return {
		            "filters": {
		               	"is_pod": "POD",
		               	"docstatus": 1,
		               	"no_po" : cur_frm.doc.purchase_order
		            }   
		        }
		    });

			frm.doc.no_mrrq = []
			frappe.call({
				method : "addons.addons.doctype.memo_ekspedisi.memo_ekspedisi.get_rq_from_po",
				args : {
					"po" : frm.doc.purchase_order
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						for(var baris in hasil.message){
							var d = frappe.model.add_child(cur_frm.doc,"Material Request Table","no_mrrq")

							d.no_mrrq = hasil.message[baris].material_request
							
							cur_frm.refresh_fields()
						}
					}
				}
			})
			frm.doc.items = []
			frappe.call({
				method : "addons.addons.doctype.memo_ekspedisi.memo_ekspedisi.get_items_from_po",
				args : {
					"po" : frm.doc.purchase_order
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						for(var baris in hasil.message){
							var d = frappe.model.add_child(cur_frm.doc,"Memo Pengiriman Table","items")

							d.kode_material = hasil.message[baris].item_code
							d.nama_barang = hasil.message[baris].item_name
							d.qty_rq = hasil.message[baris].qty
							d.qty_uom = hasil.message[baris].uom
							d.berat = hasil.message[baris].weight_per_unit
							d.berat_uom = hasil.message[baris].weight_uom

							cur_frm.refresh_fields()
						}
						var total_berat = 0
						for(var baris in frm.doc.items){
							total_berat += d.qty_rq * d.berat
						}
						frm.doc.tonase__kg_ = total_berat
						cur_frm.refresh_fields()
					}
				}
			})
		
		}
		else{
			frm.set_query("purchase_order_delivery_pod", function(){
	        return {
	            "filters": {
	               	"is_pod": "POD",
	               	"docstatus": 1,
	               	"no_memo_ekspedisi" : cur_frm.doc.name
	            }   
	        }
	    });
		}
	}
});
cur_frm.add_fetch("list_company_gias","alamat_dan_kontak","alamat")
// cur_frm.add_fetch("stock_entry","posting_date","posting_date")
cur_frm.add_fetch("purchase_order_delivery_pod","nama_kapal","nama_kapal")
cur_frm.add_fetch("purchase_order_delivery_pod","rute_from","rute_from")

frappe.ui.form.on("Memo Pengiriman Table", "qty_rq", function(frm, cdt, cdn) {
    var item = locals[cdt][cdn];
    //frappe.msgprint("test")
    var total = 0
   	for(var i=0;i<cur_frm.doc.items.length;i++) {
		total += cur_frm.doc.items[i].qty_rq * cur_frm.doc.items[i].berat
	}
	cur_frm.set_value("tonase__kg_",total)
	cur_frm.refresh_fields()
});