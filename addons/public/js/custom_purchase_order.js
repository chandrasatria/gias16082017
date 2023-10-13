// Copyright (c) 2015, Frappe Technologies Pvt. Ltd. and Contributors
// License: GNU General Public License v3. See license.txt

frappe.provide("erpnext.buying");
frappe.provide("erpnext.accounts.dimensions");
{% include 'erpnext/public/js/controllers/buying.js' %};

frappe.ui.form.on("Purchase Order", {
	type_pembelian(frm) {
	    if(cur_frm.doc.type_pembelian=="Non Inventory"){
	        cur_frm.set_value("naming_series","PO-NON-INV-{tax}-.YY.-.MM.-.#####")
	    }
	    else{
	    	cur_frm.set_value("naming_series","PO-{{initial_supplier}}-INV-{tax}-.YY.-.MM.-.#####")
	    	
	    }
	},
	tax_or_non_tax:function(frm){
		if(frm.doc.tax_or_non_tax == "Non Tax"){
			frm.doc.taxes_and_charges = ""
			frm.doc.taxes = []
			frm.set_df_property("taxes", "hidden", 1);
			frm.set_df_property("taxes_and_charges", "hidden", 1);
			frm.refresh_fields()
		}
		else{
			frm.set_df_property("taxes", "hidden", 0);
			frm.set_df_property("taxes_and_charges", "hidden", 0);
			frm.refresh_fields()
		}
	},
	before_load:function(frm) {
		if(frm.doc.__islocal){
			if(frm.doc.tax_or_non_tax == "Tax"){
				frappe.call({
					method: "addons.custom_standard.custom_purchase_order.get_purchase_tax",
					
					callback: function (data) {
						if(data.message.length > 0){
							frm.doc.taxes_and_charges = data.message[0]["name"]
							frm.trigger("taxes_and_charges")
							frm.refresh_fields()
						} 
					}
				})
			}
		}
		if(frm.doc.tax_or_non_tax == "Non Tax"){
			frm.doc.taxes_and_charges = ""
			frm.doc.taxes = []
			frm.set_df_property("taxes", "hidden", 1);
			frm.set_df_property("taxes_and_charges", "hidden", 1);
			frm.refresh_fields()
		}
	},
	setup: function(frm) {

		frm.set_query("reserve_warehouse", "supplied_items", function() {
			return {
				filters: {
					"company": frm.doc.company,
					"name": ['!=', frm.doc.supplier_warehouse],
					"is_group": 0
				}
			}
		});

		cur_frm.set_query("no_memo_ekspedisi", function() {
		    return {
				filters:{
					"purchase_order_delivery_pod" : "",
					"docstatus" : 0
				}
			}
	    });

		frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.qty<=doc.received_qty) ? "green" : "orange" })

		frm.set_query("expense_account", "items", function() {
			return {
				query: "erpnext.controllers.queries.get_expense_account",
				filters: {'company': frm.doc.company}
			}
		});

		if(frappe.user_roles.indexOf("Purchase Order Without Value") > -1){
			
			var df = frappe.meta.get_docfield("Purchase Order Item", "rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Order Item", "base_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Order Item", "price_list_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Order Item", "base_price_list_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Order Item", "amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Order Item", "base_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Order Item", "net_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Order Item", "base_net_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Order Item", "net_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Purchase Order Item", "base_net_amount",frm.doc.name);
			df.hidden = 1;
			
			frm.set_df_property("total", "hidden", 1);
			frm.set_df_property("nt_sc_break_section", "hidden", 1);
			frm.set_df_property("taxes_section", "hidden", 1);
			frm.set_df_property("totals", "hidden", 1);
			frm.set_df_property("base_net_total", "hidden", 1);
			frm.set_df_property("total_taxes_and_charges", "hidden", 1);
			frm.set_df_property("grand_total", "hidden", 1);
			frm.set_df_property("rounding_adjustment", "hidden", 1);
			frm.set_df_property("rounded_total", "hidden", 1);
			frm.set_df_property("in_words", "hidden", 1);
			frm.set_df_property("sec_tax_breakup", "hidden", 1);
			
			frm.refresh_fields();
		}
		else{
			var df = frappe.meta.get_docfield("Purchase Order Item", "rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Order Item", "base_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Order Item", "price_list_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Order Item", "base_price_list_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Order Item", "amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Order Item", "base_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Order Item", "net_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Order Item", "base_net_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Order Item", "net_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Purchase Order Item", "base_net_amount",frm.doc.name);
			df.hidden = 0;
			
			frm.set_df_property("total", "hidden", 0);
			frm.set_df_property("nt_sc_break_section", "hidden", 0);
			frm.set_df_property("taxes_section", "hidden", 1);
			frm.set_df_property("totals", "hidden", 1);
			frm.set_df_property("base_net_total", "hidden", 0);
			frm.set_df_property("total_taxes_and_charges", "hidden", 0);
			frm.set_df_property("grand_total", "hidden", 0);
			frm.set_df_property("rounding_adjustment", "hidden", 0);
			frm.set_df_property("rounded_total", "hidden", 0);
			frm.set_df_property("in_words", "hidden", 0);
			frm.set_df_property("sec_tax_breakup", "hidden", 0);
			frm.refresh_fields();
		}	

		// $(frm.wrapper).on('grid-row-render', function(e, grid_row) {
		// 	if(in_list(['Purchase Order Item'], grid_row.doc.doctype)) {
		// 		if(grid_row) {
		// 			if(grid_row.doc.supplier_quotation) {
		// 				grid_row.toggle_editable("rate", false);
		// 			}else{
		// 				grid_row.toggle_editable("rate", true);
		// 			}
		// 		}
		// 	}
		// });
		var df = frappe.meta.get_docfield("Purchase Order Item", "rate",frm.doc.name);
		df.read_only = 1;

	},

	company: function(frm) {
		erpnext.accounts.dimensions.update_dimension(frm, frm.doctype);
	},

	onload: function(frm) {
		if(frm.doc.__islocal){
			frm.doc.price_list_currency = "IDR"
		}
		frm.set_query("account_head", "taxes", function() {
			return {
				filters: {
					"is_group": 0,
					"disabled": 0,
				}
			}
		});

		set_schedule_date(frm);
		if (!frm.doc.transaction_date){
			frm.set_value('transaction_date', frappe.datetime.get_today())
		}

		erpnext.queries.setup_queries(frm, "Warehouse", function() {
			return erpnext.queries.warehouse(frm.doc);
		});

		erpnext.accounts.dimensions.setup_dimension_filters(frm, frm.doctype);
	},

	apply_tds: function(frm) {
		if (!frm.doc.apply_tds) {
			frm.set_value("tax_withholding_category", '');
		} else {
			frm.set_value("tax_withholding_category", frm.supplier_tds);
		}
	},

	refresh: function(frm) {
		frm.trigger('get_materials_from_supplier');
		if(frm.doc.__islocal){
			frm.doc.region = ""
			frm.refresh_fields()
			
		}
		/*for(var i=0;i< cur_frm.doc.items.length;i++){
			if(cur_frm.doc.items[i].supplier_quotation){
				frappe.msgprint("test 12345")
				var df1 = frappe.meta.get_docfield("Purchase Order Item","rate", cur_frm.doc.name);
				df1.read_only = 1;
				df1.bold=0;
				cur_frm.set_df_property(cur_frm.doc.items[i].rate, "read_only", 1);
			}
		}*/
	},
	add_global_discount(frm) {
		if(frm.doc.discount_global_amount){
			frappe.db.get_value("Company",cur_frm.doc.company,"discount_global_account").then(
				function(e){
					if(e.message["discount_global_account"]){
						var d = frappe.model.add_child(cur_frm.doc,"Purchase Taxes and Charges","taxes")
						
						d.category = "Total"
						d.add_or_deduct = "Add"
						d.charge_type = "Actual"
						d.account_head = e.message["discount_global_account"]
						d.description = e.message["discount_global_account"]
						d.tax_amount = frm.doc.discount_global_amount * -1
						d.global_discount = "Yes"
						frappe.call({
							method : "addons.custom_standard.custom_global.onload_dimension",
							args : {
								"company" : frm.doc.company
							},
							freeze: true,
							callback : function(hasil){
								if(hasil){
									for(var baris in hasil.message){
										if(hasil.message[baris].default_dimension){
											d.branch = hasil.message[baris].default_dimension
										}
									}					
								}
							}
						})
						cur_frm.trigger('discount_amount');
						cur_frm.refresh_fields()
					}

				}
			)	
		}
	},

	is_pod(frm){
		if(frm.doc.is_pod == "POD" && frm.doc.pod_ppn == "PPN" ){
			frappe.call({
				method : "addons.custom_standard.custom_purchase_order.get_pod_taxes",
				args : {
					
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						for(var baris in hasil.message){
							if(hasil.message[baris].value){
								frm.doc.taxes_and_charges = hasil.message[baris].value
							}
						}
						cur_frm.trigger('taxes_and_charges')
						cur_frm.refresh_fields()						
					}
				}
			})
		}
		else if(frm.doc.is_pod == "POD" && frm.doc.pod_ppn == "Non PPN" ){
			cur_frm.doc.taxes = []
			cur_frm.refresh_fields()
		}
		if(frm.doc.is_pod == "POD"){
		    frappe.call({
		        method: "addons.custom_standard.custom_purchase_order.get_pod_naming_series",
		        args:{
		            
		        },
		        callback:function(hasil){
		            frm.doc.naming_series = hasil.message[0].value
		            frm.refresh_fields()
		        }
		    })
		}
		else{
		    frappe.call({
		        method: "addons.custom_standard.custom_purchase_order.get_non_pod_naming_series",
		        args:{
		            
		        },
		        callback:function(hasil){
		            frm.doc.naming_series = hasil.message[0].value
		            frm.refresh_fields()
		        }
		    })
		}
	},
	no_memo_ekspedisi(frm){
		if(cur_frm.doc.no_memo_ekspedisi){
			// frappe.msgprint("test 123")
			frappe.call({
		        method: "addons.custom_standard.custom_purchase_order.get_memo",
		        args:{
		            "memo_ekspedisi": cur_frm.doc.no_memo_ekspedisi
		        },
		        callback:function(hasil){
		            console.log(hasil)
					if(hasil.message[0].length > 0){
					cur_frm.set_value('supplier',hasil.message[0][0].supplier)
		            cur_frm.set_value('no_po',hasil.message[0][0].purchase_order)
		            cur_frm.set_value('nama_kapal',hasil.message[0][0].nama_kapal)
		            cur_frm.set_value('rute_from',hasil.message[0][0].rute_from)
					}
					cur_frm.doc.rute_to = []
		            for(let i=0;i<hasil.message[1].length;i++){
						var child = cur_frm.add_child("rute_to");
						console.log(hasil.message[1])
		            	frappe.model.set_value(child.doctype, child.name, "rute_to", hasil.message[1][i].rute_to)
		            }
		            cur_frm.refresh_field("rute_to")

					cur_frm.doc.isi_kontainer = []
					for(let i=0;i<hasil.message[2].length;i++){
						var childkontainer = cur_frm.add_child("isi_kontainer")
						childkontainer.kode_material = hasil.message[2][i].kode_material;
						childkontainer.nama_barang = hasil.message[2][i].nama_barang;
						childkontainer.keterangan = hasil.message[2][i].keterangan;
						childkontainer.qty_rq = hasil.message[2][i].qty_rq;
						childkontainer.berat = hasil.message[2][i].berat;
						childkontainer.stuffing = hasil.message[2][i].stuffing;
						childkontainer.berat_uom = hasil.message[2][i].berat_uom;
						childkontainer.qty_uom = hasil.message[2][i].qty_uom;
		            	// frappe.model.set_value(childkontainer.doctype, childkontainer.name, "isi_kontainer", hasil.message[2][i].items)
		            }
					cur_frm.refresh_field("isi_kontainer")
		        }
		    });
		}
	},
	pod_ppn(frm){
		if(frm.doc.is_pod == "POD" && frm.doc.pod_ppn == "PPN" ){
			frappe.call({
				method : "addons.custom_standard.custom_purchase_order.get_pod_taxes",
				args : {
					
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						for(var baris in hasil.message){
							if(hasil.message[baris].value){
								frm.doc.taxes_and_charges = hasil.message[baris].value
							}
						}
						cur_frm.trigger('taxes_and_charges')
						cur_frm.refresh_fields()						
					}
				}
			})
		}
		else if(frm.doc.is_pod == "POD" && frm.doc.pod_ppn == "Non PPN" ){
			cur_frm.doc.taxes = []
			cur_frm.refresh_fields()
		}
	},
	get_materials_from_supplier: function(frm) {
		let po_details = [];

		if (frm.doc.supplied_items && (frm.doc.per_received == 100 || frm.doc.status === 'Closed')) {
			frm.doc.supplied_items.forEach(d => {
				if (d.total_supplied_qty && d.total_supplied_qty != d.consumed_qty) {
					po_details.push(d.name)
				}
			});
		}

		if (po_details && po_details.length) {
			frm.add_custom_button(__('Return of Components'), () => {
				frm.call({
					method: 'erpnext.buying.doctype.purchase_order.purchase_order.get_materials_from_supplier',
					freeze: true,
					freeze_message: __('Creating Stock Entry'),
					args: { purchase_order: frm.doc.name, po_details: po_details },
					callback: function(r) {
						if (r && r.message) {
							const doc = frappe.model.sync(r.message);
							frappe.set_route("Form", doc[0].doctype, doc[0].name);
						}
					}
				});
			}, __('Create'));
		}
	}
});

frappe.ui.form.on("Purchase Order Item", {
	schedule_date: function(frm, cdt, cdn) {
		var row = locals[cdt][cdn];
		if (row.schedule_date) {
			if(!frm.doc.schedule_date) {
				erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "schedule_date");
			} else {
				set_schedule_date(frm);
			}
		}
	},
	supplier_quotation: function(frm, cdt, cdn){
		var d = locals[cdt][cdn];
		if(d.supplier_quotation){
			frappe.msgprint("test supplier_quotation 123")
			frm.set_df_property(d.rate, "read_only", 1);
		}
	}
});

erpnext.buying.PurchaseOrderController = erpnext.buying.BuyingController.extend({
	setup: function() {
		this.frm.custom_make_buttons = {
			'Purchase Receipt': 'Purchase Receipt',
			'Purchase Invoice': 'Purchase Invoice',
			'Stock Entry': 'Material to Supplier',
			'Payment Entry': 'Payment',
		}

		this._super();

	},

	refresh: function(doc, cdt, cdn) {
		var me = this;
		this._super();
		var allow_receipt = false;
		var is_drop_ship = false;

		for (var i in cur_frm.doc.items) {
			var item = cur_frm.doc.items[i];
			if(item.delivered_by_supplier !== 1) {
				allow_receipt = true;
			} else {
				is_drop_ship = true;
			}

			if(is_drop_ship && allow_receipt) {
				break;
			}
		}

		this.frm.set_df_property("drop_ship", "hidden", !is_drop_ship);

		if(doc.docstatus == 1) {
			this.frm.fields_dict.items_section.wrapper.addClass("hide-border");
			if(!this.frm.doc.set_warehouse) {
				this.frm.fields_dict.items_section.wrapper.removeClass("hide-border");
			}

			if(!in_list(["Closed", "Delivered"], doc.status)) {
				if(this.frm.doc.status !== 'Closed' && flt(this.frm.doc.per_received) < 100 && flt(this.frm.doc.per_billed) < 100) {
					this.frm.add_custom_button(__('Update Items'), () => {
						erpnext.utils.update_child_items({
							frm: this.frm,
							child_docname: "items",
							child_doctype: "Purchase Order Detail",
							cannot_add_row: false,
						})
					});
				}
				if (this.frm.has_perm("submit")) {
					if(flt(doc.per_billed, 6) < 100 || flt(doc.per_received, 6) < 100) {
						if (doc.status != "On Hold") {
							this.frm.add_custom_button(__('Hold'), () => this.hold_purchase_order(), __("Status"));
						} else{
							this.frm.add_custom_button(__('Resume'), () => this.unhold_purchase_order(), __("Status"));
						}
						this.frm.add_custom_button(__('Close'), () => this.close_purchase_order(), __("Status"));
					}
				}

				if(is_drop_ship && doc.status!="Delivered") {
					this.frm.add_custom_button(__('Delivered'),
						this.delivered_by_supplier, __("Status"));

					this.frm.page.set_inner_btn_group_as_primary(__("Status"));
				}
			} else if(in_list(["Closed", "Delivered"], doc.status)) {
				if (this.frm.has_perm("submit")) {
					this.frm.add_custom_button(__('Re-open'), () => this.unclose_purchase_order(), __("Status"));
				}
			}
			if(doc.status != "Closed") {
				if (doc.status != "On Hold") {
					if(flt(doc.per_received) < 100 && allow_receipt) {
						cur_frm.add_custom_button(__('Purchase Receipt'), this.make_purchase_receipt, __('Create'));
						if(doc.is_subcontracted==="Yes" && me.has_unsupplied_items()) {
							cur_frm.add_custom_button(__('Material to Supplier'),
								function() { me.make_stock_entry(); }, __("Transfer"));
						}
					}
					if(flt(doc.per_billed) < 100)
						cur_frm.add_custom_button(__('Purchase Invoice'),
							this.make_purchase_invoice, __('Create'));

					if(flt(doc.per_billed)==0 && doc.status != "Delivered") {
						cur_frm.add_custom_button(__('Payment'), cur_frm.cscript.make_payment_entry, __('Create'));
					}

					if(flt(doc.per_billed)==0) {
						this.frm.add_custom_button(__('Payment Request'),
							function() { me.make_payment_request() }, __('Create'));
					}

					if(!doc.auto_repeat) {
						cur_frm.add_custom_button(__('Subscription'), function() {
							erpnext.utils.make_subscription(doc.doctype, doc.name)
						}, __('Create'))
					}

					if (doc.docstatus === 1 && !doc.inter_company_order_reference) {
						let me = this;
						let internal = me.frm.doc.is_internal_supplier;
						if (internal) {
							let button_label = (me.frm.doc.company === me.frm.doc.represents_company) ? "Internal Sales Order" :
								"Inter Company Sales Order";

							me.frm.add_custom_button(button_label, function() {
								me.make_inter_company_order(me.frm);
							}, __('Create'));
						}

					}
				}

				cur_frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		} else if(doc.docstatus===0) {
			cur_frm.cscript.add_from_mappers();
		}
	},

	get_items_from_open_material_requests: function() {
		erpnext.utils.map_current_doc({
			method: "erpnext.stock.doctype.material_request.material_request.make_purchase_order_based_on_supplier",
			args: {
				supplier: this.frm.doc.supplier
			},
			source_doctype: "Material Request",
			source_name: this.frm.doc.supplier,
			target: this.frm,
			setters: {
				company: me.frm.doc.company
			},
			get_query_filters: {
				docstatus: ["!=", 2],
				supplier: this.frm.doc.supplier
			},
			get_query_method: "erpnext.stock.doctype.material_request.material_request.get_material_requests_based_on_supplier"
		});
	},

	validate: function() {
		set_schedule_date(this.frm);
	},

	has_unsupplied_items: function() {
		return this.frm.doc['supplied_items'].some(item => item.required_qty > item.supplied_qty)
	},

	make_stock_entry: function() {
		var items = $.map(cur_frm.doc.items, function(d) { return d.bom ? d.item_code : false; });
		var me = this;

		if(items.length >= 1){
			me.raw_material_data = [];
			me.show_dialog = 1;
			let title = __('Transfer Material to Supplier');
			let fields = [
			{fieldtype:'Section Break', label: __('Raw Materials')},
			{fieldname: 'sub_con_rm_items', fieldtype: 'Table', label: __('Items'),
				fields: [
					{
						fieldtype:'Data',
						fieldname:'item_code',
						label: __('Item'),
						read_only:1,
						in_list_view:1
					},
					{
						fieldtype:'Data',
						fieldname:'rm_item_code',
						label: __('Raw Material'),
						read_only:1,
						in_list_view:1
					},
					{
						fieldtype:'Float',
						read_only:1,
						fieldname:'qty',
						label: __('Quantity'),
						read_only:1,
						in_list_view:1
					},
					{
						fieldtype:'Data',
						read_only:1,
						fieldname:'warehouse',
						label: __('Reserve Warehouse'),
						in_list_view:1
					},
					{
						fieldtype:'Float',
						read_only:1,
						fieldname:'rate',
						label: __('Rate'),
						hidden:1
					},
					{
						fieldtype:'Float',
						read_only:1,
						fieldname:'amount',
						label: __('Amount'),
						hidden:1
					},
					{
						fieldtype:'Link',
						read_only:1,
						fieldname:'uom',
						label: __('UOM'),
						hidden:1
					}
				],
				data: me.raw_material_data,
				get_data: function() {
					return me.raw_material_data;
				}
			}
		]

		me.dialog = new frappe.ui.Dialog({
			title: title, fields: fields
		});

		if (me.frm.doc['supplied_items']) {
			me.frm.doc['supplied_items'].forEach((item, index) => {
			if (item.rm_item_code && item.main_item_code && item.required_qty - item.supplied_qty != 0) {
					me.raw_material_data.push ({
						'name':item.name,
						'item_code': item.main_item_code,
						'rm_item_code': item.rm_item_code,
						'item_name': item.rm_item_code,
						'qty': item.required_qty - item.supplied_qty,
						'warehouse':item.reserve_warehouse,
						'rate':item.rate,
						'amount':item.amount,
						'stock_uom':item.stock_uom
					});
					me.dialog.fields_dict.sub_con_rm_items.grid.refresh();
				}
			})
		}

		me.dialog.get_field('sub_con_rm_items').check_all_rows()

		me.dialog.show()
		this.dialog.set_primary_action(__('Transfer'), function() {
			me.values = me.dialog.get_values();
			if(me.values) {
				me.values.sub_con_rm_items.map((row,i) => {
					if (!row.item_code || !row.rm_item_code || !row.warehouse || !row.qty || row.qty === 0) {
						let row_id = i+1;
						frappe.throw(__("Item Code, warehouse and quantity are required on row {0}", [row_id]));
					}
				})
				me._make_rm_stock_entry(me.dialog.fields_dict.sub_con_rm_items.grid.get_selected_children())
				me.dialog.hide()
				}
			});
		}

		me.dialog.get_close_btn().on('click', () => {
			me.dialog.hide();
		});

	},

	_make_rm_stock_entry: function(rm_items) {
		frappe.call({
			method:"erpnext.buying.doctype.purchase_order.purchase_order.make_rm_stock_entry",
			args: {
				purchase_order: cur_frm.doc.name,
				rm_items: rm_items
			}
			,
			callback: function(r) {
				var doclist = frappe.model.sync(r.message);
				frappe.set_route("Form", doclist[0].doctype, doclist[0].name);
			}
		});
	},

	make_inter_company_order: function(frm) {
		frappe.model.open_mapped_doc({
			method: "erpnext.buying.doctype.purchase_order.purchase_order.make_inter_company_sales_order",
			frm: frm
		});
	},

	make_purchase_receipt: function() {
		frappe.model.open_mapped_doc({
			method: "addons.custom_standard.custom_purchase_order.custom_make_purchase_receipt",
			frm: cur_frm,
			freeze_message: __("Creating Purchase Receipt ...")
		})
	},

	make_purchase_invoice: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.buying.doctype.purchase_order.purchase_order.make_purchase_invoice",
			frm: cur_frm
		})
	},

	add_from_mappers: function() {
		var me = this;
		this.frm.add_custom_button(__('Material Requests'),
			function() {
				erpnext.utils.map_current_doc({
					method: "addons.custom_standard.custom_material_request.make_purchase_order_custom",
					source_doctype: "Material Request",
					target: me.frm,
					setters: {
						schedule_date: undefined,
						status: undefined
					},
					get_query_filters: {
						material_request_type: "Purchase",
						docstatus: 1,
						status: ["!=", "Stopped"],
						per_ordered: ["<", 100],
						company: me.frm.doc.company
					}
				})
			}, __("Get Items From"));

		this.frm.add_custom_button(__('Supplier Quotation'),
			function() {
				erpnext.utils.map_current_doc({
					method: "erpnext.buying.doctype.supplier_quotation.supplier_quotation.make_purchase_order",
					source_doctype: "Supplier Quotation",
					target: me.frm,
					setters: {
						supplier: me.frm.doc.supplier,
						valid_till: undefined
					},
					get_query_filters: {
						docstatus: 1,
						status: ["not in", ["Stopped", "Expired"]],
					}
				})
			}, __("Get Items From"));

		this.frm.add_custom_button(__('Update Rate as per Last Purchase'),
			function() {
				frappe.call({
					"method": "get_last_purchase_rate",
					"doc": me.frm.doc,
					callback: function(r, rt) {
						me.frm.dirty();
						me.frm.cscript.calculate_taxes_and_totals();
					}
				})
			}, __("Tools"));

		this.frm.add_custom_button(__('Link to Material Request'),
		function() {
			var my_items = [];
			for (var i in me.frm.doc.items) {
				if(!me.frm.doc.items[i].material_request){
					my_items.push(me.frm.doc.items[i].item_code);
				}
			}
			frappe.call({
				method: "erpnext.buying.utils.get_linked_material_requests",
				args:{
					items: my_items
				},
				callback: function(r) {
					if(r.exc) return;

					var i = 0;
					var item_length = me.frm.doc.items.length;
					while (i < item_length) {
						var qty = me.frm.doc.items[i].qty;
						(r.message[0] || []).forEach(function(d) {
							if (d.qty > 0 && qty > 0 && me.frm.doc.items[i].item_code == d.item_code && !me.frm.doc.items[i].material_request_item)
							{
								me.frm.doc.items[i].material_request = d.mr_name;
								me.frm.doc.items[i].material_request_item = d.mr_item;
								var my_qty = Math.min(qty, d.qty);
								qty = qty - my_qty;
								d.qty = d.qty  - my_qty;
								me.frm.doc.items[i].stock_qty = my_qty * me.frm.doc.items[i].conversion_factor;
								me.frm.doc.items[i].qty = my_qty;

								frappe.msgprint("Assigning " + d.mr_name + " to " + d.item_code + " (row " + me.frm.doc.items[i].idx + ")");
								if (qty > 0) {
									frappe.msgprint("Splitting " + qty + " units of " + d.item_code);
									var new_row = frappe.model.add_child(me.frm.doc, me.frm.doc.items[i].doctype, "items");
									item_length++;

									for (var key in me.frm.doc.items[i]) {
										new_row[key] = me.frm.doc.items[i][key];
									}

									new_row.idx = item_length;
									new_row["stock_qty"] = new_row.conversion_factor * qty;
									new_row["qty"] = qty;
									new_row["material_request"] = "";
									new_row["material_request_item"] = "";
								}
							}
						});
						i++;
					}
					refresh_field("items");
				}
			});
		}, __("Tools"));
	},
	items:function(){
		console.log("TEST")
	},
	tc_name: function() {
		this.get_terms();
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

	unhold_purchase_order: function(){
		cur_frm.cscript.update_status("Resume", "Draft")
	},

	hold_purchase_order: function(){
		var me = this;
		var d = new frappe.ui.Dialog({
			title: __('Reason for Hold'),
			fields: [
				{
					"fieldname": "reason_for_hold",
					"fieldtype": "Text",
					"reqd": 1,
				}
			],
			primary_action: function() {
				var data = d.get_values();
				let reason_for_hold = 'Reason for hold: ' + data.reason_for_hold;

				frappe.call({
					method: "frappe.desk.form.utils.add_comment",
					args: {
						reference_doctype: me.frm.doctype,
						reference_name: me.frm.docname,
						content: __(reason_for_hold),
						comment_email: frappe.session.user,
						comment_by: frappe.session.user_fullname
					},
					callback: function(r) {
						if(!r.exc) {
							me.update_status('Hold', 'On Hold')
							d.hide();
						}
					}
				});
			}
		});
		d.show();
	},

	unclose_purchase_order: function(){
		cur_frm.cscript.update_status('Re-open', 'Submitted')
	},

	close_purchase_order: function(){
		cur_frm.cscript.update_status('Close', 'Closed')
	},

	delivered_by_supplier: function(){
		cur_frm.cscript.update_status('Deliver', 'Delivered')
	},

	items_on_form_rendered: function() {
		set_schedule_date(this.frm);
	},

	schedule_date: function() {
		set_schedule_date(this.frm);
	}
});

// for backward compatibility: combine new and previous states
$.extend(cur_frm.cscript, new erpnext.buying.PurchaseOrderController({frm: cur_frm}));

cur_frm.cscript.update_status= function(label, status){
	frappe.call({
		method: "erpnext.buying.doctype.purchase_order.purchase_order.update_status",
		args: {status: status, name: cur_frm.doc.name},
		callback: function(r) {
			cur_frm.set_value("status", status);
			cur_frm.reload_doc();
		}
	})
}

cur_frm.fields_dict['items'].grid.get_field('project').get_query = function(doc, cdt, cdn) {
	return {
		filters:[
			['Project', 'status', 'not in', 'Completed, Cancelled']
		]
	}
}

cur_frm.fields_dict['items'].grid.get_field('bom').get_query = function(doc, cdt, cdn) {
	var d = locals[cdt][cdn]
	return {
		filters: [
			['BOM', 'item', '=', d.item_code],
			['BOM', 'is_active', '=', '1'],
			['BOM', 'docstatus', '=', '1'],
			['BOM', 'company', '=', doc.company]
		]
	}
}

function set_schedule_date(frm) {
	if(frm.doc.schedule_date){

		erpnext.utils.copy_value_in_all_rows(frm.doc, frm.doc.doctype, frm.doc.name, "items", "schedule_date");
		for(var row in frm.doc.items){
			frm.doc.items[row].schedule_date = frm.doc.schedule_date
		}
		frm.refresh_fields()
	}
}

frappe.provide("erpnext.buying");

frappe.ui.form.on("Purchase Order", "is_subcontracted", function(frm) {
	if (frm.doc.is_subcontracted === "Yes") {
		erpnext.buying.get_default_bom(frm);
	}
});


cur_frm.add_fetch("nama_company","alamat_dan_kontak","alamat_dan_kontak")
cur_frm.add_fetch("delivery_company","alamat_dan_kontak","delivery")

