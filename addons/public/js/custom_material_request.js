
frappe.ui.form.on('Material Request', {
	refresh(frm) {
	    apply_item_code_filter(frm)
	},
	type_pembelian(frm) {
	   apply_item_code_filter(frm)
	},
	tax_or_non_tax(frm) {
	   apply_item_code_filter(frm)
	},
	ps_approver(frm) {
	   apply_item_code_filter(frm)
	},
	onload: function(frm) {
    	if(frm.doc.__islocal){
    		frappe.call({
				method: "addons.custom_standard.custom_material_request.get_cabang",
				args: {
					user : frappe.user.name
				},
				callback: function (data) {
					if(data.message.length > 0){
						frm.doc.cabang = data.message[0]["cabang"]

						cur_frm.set_query("cabang", function() {
			    		    return {
								query: "addons.custom_standard.custom_material_request.get_cabang_query",
							}
			    	    });
						frm.refresh_fields()
					} 
				}
			})
    	}
    	else{
    		frappe.call({
				method: "addons.custom_standard.custom_material_request.get_cabang",
				args: {
					user : frappe.user.name
				},
				callback: function (data) {
					if(data.message.length > 0){
					// 	frm.doc.cabang = data.message[0]["cabang"]
						cur_frm.set_df_property("cabang","read_only",1);
						frm.refresh_fields()
					} 
				}
			})
    	}

    }
})




// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

// eslint-disable-next-line
frappe.provide("erpnext.accounts.dimensions");
{% include 'erpnext/public/js/controllers/buying.js' %};

frappe.ui.form.on('Material Request', {
	setup: function(frm) {
		frm.custom_make_buttons = {
			'Stock Entry': 'Issue Material',
			'Pick List': 'Pick List',
			'Purchase Order': 'Purchase Order',
			'Request for Quotation': 'Request for Quotation',
			'Supplier Quotation': 'Supplier Quotation',
			'Work Order': 'Work Order',
			'Purchase Receipt': 'Purchase Receipt'
		};

		// formatter for material request item
		frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.stock_qty<=doc.ordered_qty) ? "green" : "orange"; });

		frm.set_query("item_code", "items", function() {
			return {
				query: "erpnext.controllers.queries.item_query"
			};
		});

		frm.set_query("from_warehouse", "items", function(doc) {
			return {
				filters: {'company': doc.company}
			};
		});

		frm.set_query("bom_no", "items", function(doc, cdt, cdn) {
			var row = locals[cdt][cdn];
			return {
				filters: {
					"item": row.item_code
				}
			}
		});

	},

	onload: function(frm) {
		// add item, if previous view was item

		erpnext.utils.add_item(frm);
		// if(frm.doc.__islocal){
		// 	frm.doc.items = []
		// 	frm.refresh_fields()
		// }

		// set schedule_date
		set_schedule_date(frm);

		frm.set_query("warehouse", "items", function(doc) {
			return {
				filters: {'company': doc.company}
			};
		});

		frm.set_query("set_warehouse", function(doc){
			return {
				filters: {'company': doc.company}
			};
		});

		frm.set_query("set_from_warehouse", function(doc){
			return {
				filters: {'company': doc.company}
			};
		});

		frm.set_query("get_material_request_not_ready", function() {
			return {
				filters: [
	                ["Material Request", "barang_ready", "=", "Not Ready"],
	                ["Material Request", "material_request_type", "=", "Material Transfer"],
	                ["Material Request", "workflow_state", "=", "Approved"],
	                ["Material Request", "cabang", "!=", ""]
	            ]
			}
		});

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	get_mr: function(frm){
		if(frm.doc.get_material_request_not_ready){
			frappe.call({
				method : "addons.custom_standard.custom_material_request.get_items_mr_non_ready",
				args : {
					"mreq" : frm.doc.get_material_request_not_ready
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						cur_frm.doc.items=[]
						for(var baris in hasil.message){
							
						
							if(frm.doc.cabang){
								if(hasil.message[baris].cabang != frm.doc.cabang){
									frappe.throw("Cabang untuk Material Request hanya bisa untuk " + frm.doc.cabang)
								}
							}
							var d = frappe.model.add_child(cur_frm.doc,"Material Request Item","items")

							frm.doc.cabang = hasil.message[baris].cabang

							d.cabang_material_request = hasil.message[baris].parent
							d.item_code = hasil.message[baris].item_code
							d.item_name = hasil.message[baris].item_name
							d.description = hasil.message[baris].description
							d.qty = hasil.message[baris].qty
							d.uom = hasil.message[baris].uom
							d.stock_uom = hasil.message[baris].stock_uom
							d.stock_qty = hasil.message[baris].stock_qty
							d.conversion_factor = hasil.message[baris].conversion_factor
							d.warehouse = hasil.message[baris].warehouse
							d.rate = hasil.message[baris].rate
							if(frm.doc.schedule_date){
								d.schedule_date = frm.doc.schedule_date
							}
							cur_frm.refresh_fields()
						}
					}
				}
			})
		}
	},
	company: function(frm) {
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	onload_post_render: function(frm) {
		frm.get_field("items").grid.set_multiple_add("item_code", "qty");
	},

	refresh: function(frm) {
		cur_frm.remove_custom_button("Purchase Order","Create")
		cur_frm.remove_custom_button("Request for Quotation","Create")
		cur_frm.remove_custom_button("Supplier Quotation","Create")
		cur_frm.remove_custom_button("Pick List","Create")
		cur_frm.remove_custom_button("Transfer Material","Create")
		cur_frm.remove_custom_button("Transfer ke Cabang","Create")
		cur_frm.remove_custom_button("Bill of Materials","Get Items From")
		cur_frm.remove_custom_button("Sales Order","Get Items From")
		
		frm.events.make_custom_buttons(frm);
		frm.toggle_reqd('customer', frm.doc.material_request_type=="Customer Provided");
	},

	set_from_warehouse: function(frm) {
		if (frm.doc.material_request_type == "Material Transfer"
			&& frm.doc.set_from_warehouse) {
			frm.doc.items.forEach(d => {
				frappe.model.set_value(d.doctype, d.name,
					"from_warehouse", frm.doc.set_from_warehouse);
			})
		}
	},

	make_custom_buttons: function(frm) {
		if (frm.doc.docstatus==0) {
			frm.add_custom_button(__("Bill of Materials"),
				() => frm.events.get_items_from_bom(frm), __("Get Items From"));
		}

		if (frm.doc.docstatus == 1 && frm.doc.status != 'Stopped') {
			let precision = frappe.defaults.get_default("float_precision");
			
			if (frm.doc.material_request_type == "Material Transfer" && frm.doc.cabang  && frm.doc.barang_ready == "Not Ready") {
				frm.add_custom_button(__("Transfer Material"),
					() => frm.events.make_stock_entry(frm), __('Create'));

				if (frm.doc.transferred_percentage != 100){
					frm.add_custom_button(__("Transfer ke Cabang"),
						() => frm.events.make_stock_entry_kecabang(frm), __('Create'));
				}
			}
			else if (frm.doc.material_request_type == "Purchase" && frm.doc.cabang) {
				frm.add_custom_button(__("Transfer Material"),
					() => frm.events.make_stock_entry(frm), __('Create'));

				frm.add_custom_button(__("Transfer ke Cabang"),
					() => frm.events.make_stock_entry_kecabang(frm), __('Create'));
			}

			if (flt(frm.doc.per_ordered, precision) < 100) {
				let add_create_pick_list_button = () => {
					frm.add_custom_button(__('Pick List'),
						() => frm.events.create_pick_list(frm), __('Create'));
				}

				if (frm.doc.material_request_type == "Material Transfer" && frm.doc.barang_ready == "Ready") {
					add_create_pick_list_button();
					// console.log("TEST")
					frm.add_custom_button(__("Transfer Material"),
						() => frm.events.make_stock_entry(frm), __('Create'));
					
				}

				if (frm.doc.material_request_type === "Material Issue") {
					frm.add_custom_button(__("Issue Material"),
						() => frm.events.make_stock_entry(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Customer Provided") {
					frm.add_custom_button(__("Material Receipt"),
						() => frm.events.make_stock_entry(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Purchase") {
					frm.add_custom_button(__('Purchase Order'),
						() => frm.events.make_purchase_order(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Purchase") {
					frm.add_custom_button(__("Request for Quotation"),
						() => frm.events.make_request_for_quotation(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Purchase") {
					frm.add_custom_button(__("Supplier Quotation"),
						() => frm.events.make_supplier_quotation(frm), __('Create'));
				}

				if (frm.doc.material_request_type === "Manufacture") {
					frm.add_custom_button(__("Work Order"),
						() => frm.events.raise_work_orders(frm), __('Create'));
				}

				frm.page.set_inner_btn_group_as_primary(__('Create'));

				// stop
				frm.add_custom_button(__('Stop'),
					() => frm.events.update_status(frm, 'Stopped'));

			}
		}

		if (frm.doc.docstatus===0) {
			frm.add_custom_button(__('Sales Order'), () => frm.events.get_items_from_sales_order(frm),
				__("Get Items From"));
		}

		if (frm.doc.docstatus == 1 && frm.doc.status == 'Stopped') {
			frm.add_custom_button(__('Re-open'), () => frm.events.update_status(frm, 'Submitted'));
		}
	},

	update_status: function(frm, stop_status) {
		frappe.call({
			method: 'erpnext.stock.doctype.material_request.material_request.update_status',
			args: { name: frm.doc.name, status: stop_status },
			callback(r) {
				if (!r.exc) {
					frm.reload_doc();
				}
			}
		});
	},

	get_items_from_sales_order: function(frm) {
		erpnext.utils.map_current_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_material_request",
			source_doctype: "Sales Order",
			target: frm,
			setters: {
				customer: frm.doc.customer || undefined,
				delivery_date: undefined,
			},
			get_query_filters: {
				docstatus: 1,
				status: ["not in", ["Closed", "On Hold"]],
				per_delivered: ["<", 99.99],
				company: frm.doc.company
			}
		});
	},

	get_item_data: function(frm, item, overwrite_warehouse=false,overwrite_desc=false) {
		
		if (item && !item.item_code) { return; }
		
		frm.call({
			method: "erpnext.stock.get_item_details.get_item_details",
			child: item,
			args: {
				args: {
					item_code: item.item_code,
					from_warehouse: item.from_warehouse,
					warehouse: item.warehouse,
					doctype: frm.doc.doctype,
					buying_price_list: frappe.defaults.get_default('buying_price_list'),
					currency: frappe.defaults.get_default('Currency'),
					name: frm.doc.name,
					qty: item.qty || 1,
					stock_qty: item.stock_qty,
					company: frm.doc.company,
					conversion_rate: 1,
					material_request_type: frm.doc.material_request_type,
					plc_conversion_rate: 1,
					rate: item.rate,
					conversion_factor: item.conversion_factor
				},
				overwrite_warehouse: overwrite_warehouse
			},
			callback: function(r) {
				const d = item;
				const qty_fields = ['actual_qty', 'projected_qty', 'min_order_qty'];
				if(!r.exc) {
					$.each(r.message, function(k, v) {
						if (!overwrite_desc && k=="description"){}
						else if(!d[k] || in_list(qty_fields, k)) d[k] = v;
					});
				}
			}
		});
	},

	get_items_from_bom: function(frm) {
		var d = new frappe.ui.Dialog({
			title: __("Get Items from BOM"),
			fields: [
				{"fieldname":"bom", "fieldtype":"Link", "label":__("BOM"),
					options:"BOM", reqd: 1, get_query: function() {
						return {filters: { docstatus:1 }};
					}},
				{"fieldname":"warehouse", "fieldtype":"Link", "label":__("For Warehouse"),
					options:"Warehouse", reqd: 1},
				{"fieldname":"qty", "fieldtype":"Float", "label":__("Quantity"),
					reqd: 1, "default": 1},
				{"fieldname":"fetch_exploded", "fieldtype":"Check",
					"label":__("Fetch exploded BOM (including sub-assemblies)"), "default":1}
			],
			primary_action_label: 'Get Items',
			primary_action(values) {
				if(!values) return;
				values["company"] = frm.doc.company;
				if(!frm.doc.company) frappe.throw(__("Company field is required"));
				frappe.call({
					method: "erpnext.manufacturing.doctype.bom.bom.get_bom_items",
					args: values,
					callback: function(r) {
						if (!r.message) {
							frappe.throw(__("BOM does not contain any stock item"));
						} else {
							erpnext.utils.remove_empty_first_row(frm, "items");
							$.each(r.message, function(i, item) {
								var d = frappe.model.add_child(cur_frm.doc, "Material Request Item", "items");
								d.item_code = item.item_code;
								d.item_name = item.item_name;
								d.description = item.description;
								d.warehouse = values.warehouse;
								d.uom = item.stock_uom;
								d.stock_uom = item.stock_uom;
								d.conversion_factor = 1;
								d.qty = item.qty;
								d.project = item.project;
							});
						}
						d.hide();
						refresh_field("items");
					}
				});
			}
		});

		d.show();
	},

	make_purchase_order: function(frm) {
		
			frappe.model.open_mapped_doc({
				method: "addons.custom_standard.custom_material_request.custom_make_purchase_order",
				frm: frm,
				args: {  },
				run_link_triggers: true
			});
			
	},

	make_request_for_quotation: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_request_for_quotation",
			frm: frm,
			run_link_triggers: true
		});
	},

	make_supplier_quotation: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_supplier_quotation",
			frm: frm
		});
	},

	make_stock_entry: function(frm) {
		frappe.model.open_mapped_doc({
			method: "addons.custom_standard.custom_material_request.make_stock_entry",
			frm: frm
		});
	},
	
	make_stock_entry_kecabang: function(frm) {
		frappe.model.open_mapped_doc({
			method: "addons.custom_standard.custom_material_request.make_stock_entry_kecabang",
			frm: frm
		});
	},

	create_pick_list: (frm) => {
		frappe.model.open_mapped_doc({
			method: "erpnext.stock.doctype.material_request.material_request.create_pick_list",
			frm: frm
		});
	},

	raise_work_orders: function(frm) {
		frappe.call({
			method:"erpnext.stock.doctype.material_request.material_request.raise_work_orders",
			args: {
				"material_request": frm.doc.name
			},
			freeze: true,
			callback: function(r) {
				if(r.message.length) {
					frm.reload_doc();
				}
			}
		});
	},
	material_request_type: function(frm) {
		frm.toggle_reqd('customer', frm.doc.material_request_type=="Customer Provided");

		if (frm.doc.material_request_type !== 'Material Transfer' && frm.doc.set_from_warehouse) {
			frm.set_value('set_from_warehouse', '');
		}
	},

});

frappe.ui.form.on("Material Request Item", {
	qty: function (frm, doctype, name) {
		var d = locals[doctype][name];
		if (flt(d.qty) < flt(d.min_order_qty)) {
			frappe.msgprint(__("Warning: Material Requested Qty is less than Minimum Order Qty"));
		}

		const item = locals[doctype][name];
		//frm.events.get_item_data(frm, item, false);
		

		var total = 0
		for(var baris in frm.doc.items){
			var satu_baris = frm.doc.items[baris]
			var qty = 0 
			var rate = 0
			
			if(satu_baris.qty){
				qty = satu_baris.qty
			}
			if(satu_baris.rate){
				rate = satu_baris.rate
			}
			total = total + (qty * rate)
		}
		frm.doc.total = total
		frm.refresh_field("total")
	},

	from_warehouse: function(frm, doctype, name) {
		const item = locals[doctype][name];
		frm.events.get_item_data(frm, item, false,false);
	},

	warehouse: function(frm, doctype, name) {
		const item = locals[doctype][name];
		frm.events.get_item_data(frm, item, false,false);
		var total = 0
		for(var baris in frm.doc.items){
			var satu_baris = frm.doc.items[baris]
			var qty = 0 
			var rate = 0
			
			if(satu_baris.qty){
				qty = satu_baris.qty
			}
			if(satu_baris.rate){
				rate = satu_baris.rate
			}
			total = total + (qty * rate)
		}
		frm.doc.total = total
		frm.refresh_fields()
	},

	rate: function(frm, doctype, name) {
		const item = locals[doctype][name];
		// frm.events.get_item_data(frm, item, false);
		
		var total = 0
		for(var baris in frm.doc.items){
			var satu_baris = frm.doc.items[baris]
			var qty = 0 
			var rate = 0
			
			if(satu_baris.qty){
				qty = satu_baris.qty
			}
			if(satu_baris.rate){
				rate = satu_baris.rate
			}
			total = total + (qty * rate)
		}
		frm.doc.total = total
		frm.refresh_field("total")
	},

	item_code: function(frm, doctype, name) {
		const item = locals[doctype][name];
		// item.rate = 0;
		set_schedule_date(frm);
		frm.events.get_item_data(frm, item, true,true);
		var total = 0
		for(var baris in frm.doc.items){
			var satu_baris = frm.doc.items[baris]
			var qty = 0 
			var rate = 0
			
			if(satu_baris.qty){
				qty = satu_baris.qty
			}
			if(satu_baris.rate){
				rate = satu_baris.rate
			}
			total = total + (qty * rate)
		}
		frm.doc.total = total
		frm.refresh_fields()
	},

	schedule_date: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.schedule_date) {
			if(!frm.doc.schedule_date) {
				erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "schedule_date");
			} else {
				set_schedule_date(frm);
			}
		}
	}
});

erpnext.buying.MaterialRequestController = erpnext.buying.BuyingController.extend({
	tc_name: function() {
		this.get_terms();
	},

	item_code: function() {
		// to override item code trigger from transaction.js
	},

	validate_company_and_party: function() {
		return true;
	},

	calculate_taxes_and_totals: function() {
		return;
	},

	validate: function() {
		set_schedule_date(this.frm);
	},

	onload: function(doc, cdt, cdn) {
		var cond={};
	    if ((cur_frm.doc.type_pembelian=="Inventory" || cur_frm.doc.material_request_type == "Material Transfer") && cur_frm.doc.ps_approver != "None" ){
	        cond={"is_stock_item":1, "ps_approver" : cur_frm.doc.ps_approver};
	    }else if (cur_frm.doc.type_pembelian=="Non Inventory" || cur_frm.doc.ps_approver == "None" ){
	        cond={"is_stock_item":0 , "ps_approver" : cur_frm.doc.ps_approver};
	    }else if (cur_frm.doc.type_pembelian=="GA"){
	        cond={"is_stock_item":0 ,"is_fixed_asset":1, "ps_approver" : cur_frm.doc.ps_approver};
	    }

		this.frm.set_query("item_code", "items", function() {
			return{	
				filters: cond
			}
		});
		cur_frm.set_df_property("items","read_only",0);
	},

	items_add: function(doc, cdt, cdn) {
		var row = frappe.get_doc(cdt, cdn);
		if(doc.schedule_date) {
			row.schedule_date = doc.schedule_date;
			refresh_field("schedule_date", cdn, "items");
		} else {
			this.frm.script_manager.copy_from_first_row("items", row, ["schedule_date"]);
		}
	},

	items_on_form_rendered: function() {
		set_schedule_date(this.frm);
	},

	schedule_date: function() {
		set_schedule_date(this.frm);
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.MaterialRequestController({frm: cur_frm}));

function set_schedule_date(frm) {
	if(frm.doc.schedule_date){
		erpnext.utils.copy_value_in_all_rows(frm.doc, frm.doc.doctype, frm.doc.name, "items", "schedule_date");
		// for(var row in frm.doc.items){
		// 	frm.doc.items[row].schedule_date = frm.doc.schedule_date
		// 	frm.refresh_fields()
		// }
	}
}

function apply_item_code_filter(frm){
	var cond={};
    if ((frm.doc.type_pembelian=="Inventory" || frm.doc.material_request_type == "Material Transfer") && frm.doc.ps_approver != "None" ){
        cond={"is_stock_item":1, "ps_approver" : frm.doc.ps_approver,"tax_or_non_tax":frm.doc.tax_or_non_tax};
    }else if (frm.doc.type_pembelian=="Non Inventory" || frm.doc.ps_approver == "None" ){
        cond={"tax_or_non_tax":frm.doc.tax_or_non_tax};
    }else if (frm.doc.type_pembelian=="GA"){
        cond={"is_stock_item":0 ,"is_fixed_asset":1,"tax_or_non_tax":frm.doc.tax_or_non_tax};
    }
    else if (frm.doc.type_pembelian=="Pengajuan Inventaris" || frm.doc.ps_approver == "None" ){
        cond={"is_stock_item":0 ,"tax_or_non_tax":frm.doc.tax_or_non_tax};}
    else if (frm.doc.type_pembelian=="Pengajuan Jasa/Biaya" || frm.doc.ps_approver == "None" ){
        cond={"is_stock_item":0 ,"tax_or_non_tax":frm.doc.tax_or_non_tax};}
        
    if (cond != {}){

		cur_frm.set_query("item_code", "items", function() {
		    return {
			    filters: cond
		    }
	    });
	    cur_frm.refresh_fields()
    }
}