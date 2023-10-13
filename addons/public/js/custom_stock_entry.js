frappe.ui.form.on('Stock Entry', {
	validate(frm) {
	    for(var row in frm.doc.additional_costs_transfer_table){
	        if(!frm.doc.additional_costs_transfer_table[row].expense_account){
	           frappe.throw("Please input expense account to additional costs you entered.")
	        }
	    }
	    if(frm.doc.transfer_status == "From Sync"){
	    	for(var row in frm.doc.items){
	    		frm.doc.items[row].basic_rate = frm.doc.items[row].pusat_valuation_rate
	    	}
	    }	   
	},
	
	refresh:function(frm){
		if (frm.doc.docstatus == 0 && !frm.is_new() && frm.doc.workflow_state != "Rejected"){
			
			frm.add_custom_button(__('Reject'), function() {
				frappe.call({
					method : "addons.custom_standard.custom_stock_entry.reject_document",
					args : {
						"name" : frm.doc.name
					},
					freeze: true,
					callback: function(hasil){
						frappe.msgprint("Document has been rejected. Please reload the document to see changes.")
					}
				})

			})
		}
		
		if (frm.doc.docstatus==0){
			frm.add_custom_button(__('Purchase Receipt'), function() {
					erpnext.utils.map_current_doc({
						method: "addons.custom_standard.custom_purchase_receipt.make_stock_entry",
						source_doctype: "Purchase Receipt",
						target: frm,
						date_field: "posting_date",
						setters: {
							supplier: frm.doc.supplier || undefined,
						},
						get_query_filters: {
							docstatus: 1
						}
					})
				}, __("Get Items From"));
		}
		if(frm.doc.transfer_ke_cabang_pusat == 1){
			frm.toggle_display(["additional_costs_transfer_table", "total_additional_costs_transfer", "additional_costs_transfer"],
				frm.doc.purpose=='Material Issue');
		}
		if(frm.doc.transfer_ke_cabang_mana){
			frm.add_custom_button(__('Transfer ke Cabang'), function() {
				const allowed_request_types = ["Material Transfer", "Purchase"];
				const depends_on_condition = "eval:doc.material_request_type==='Customer Provided'";
				var ready = "Ready"
				const d = erpnext.utils.map_current_doc({
					method: "addons.custom_standard.custom_material_request.make_stock_entry_kecabang",
					source_doctype: "Material Request",
					target: frm,
					date_field: "schedule_date",
					setters: [{
						fieldtype: 'Select',
						label: __('Purpose'),
						options: allowed_request_types.join("\n"),
						fieldname: 'material_request_type',
						default: "Material Transfer",
						read_only: 1,
					},
					{
						fieldtype: 'Select',
						label: __('Barang Ready'),
						options: "Ready\nNot Ready",
						fieldname: 'barang_ready',
						default: "Ready",
						mandatory: 1,
						change() {
							if (this.value === 'Ready') {
								ready = "Ready"
							}
							else{
								ready = "Not Ready"
							}
						},
					}
					],
					get_query_filters: {
						docstatus: 1,
						material_request_type: ["in", allowed_request_types],
						cabang: frm.doc.transfer_ke_cabang_mana,
						barang_ready: ready,
						status: ["not in", ["Transferred", "Issued", "Cancelled", "Stopped"]]
					}
				})
			}, __("Get Items From"));
		}

		var df = frappe.meta.get_docfield("Stock Entry Detail", "rates_section",frm.doc.name);
		df.hidden = 0;
		var df = frappe.meta.get_docfield("Stock Entry Detail", "basic_rate",frm.doc.name);
		df.hidden = 1;

		if(frappe.user_roles.indexOf("Stock Entry Without Value") > -1 && frappe.user["name"] != "Administrator"){
			var df = frappe.meta.get_docfield("Stock Entry Detail Deleted", "basic_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Stock Entry Detail Deleted", "basic_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Stock Entry Detail Deleted", "amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Stock Entry Detail Deleted", "valuation_rate",frm.doc.name);
			df.hidden = 1;
			
			
			frm.set_df_property("section_break_19", "hidden", 1);
			frm.refresh_fields();
		}
		else{
			var df = frappe.meta.get_docfield("Stock Entry Detail", "basic_rate",frm.doc.name);
			df.hidden = 0;
			if(frm.doc.name.indexOf("STER") > -1 && frm.doc.ste_log){
				df.read_only = 1;
			}
			else{
				df.read_only = 0;
			}
			var df = frappe.meta.get_docfield("Stock Entry Detail", "qty",frm.doc.name);
			if(frm.doc.name.indexOf("STER") > -1 && frm.doc.ste_log){
				df.read_only = 1;
			}
			else{
				df.read_only = 0;
			}
			
			var df = frappe.meta.get_docfield("Stock Entry Detail", "basic_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Stock Entry Detail", "amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Stock Entry Detail", "valuation_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Stock Entry Detail", "valuation_rate_transfer",frm.doc.name);
			df.hidden = 0;
			
			frm.set_df_property("section_break_19", "hidden", 0);
			frm.refresh_fields();
		}	

		// if(frm.doc.name.indexOf("STER") > -1 && frm.doc.ste_log){
		// 	var df = frappe.meta.get_docfield("Stock Entry Detail", "basic_rate",frm.doc.name);
		// 	df.read_only = 1;
		// 	var df = frappe.meta.get_docfield("Stock Entry Detail", "qty",frm.doc.name);
		// 	df.read_only = 1;
		// 	frm.refresh_fields();
		// }

	},
	onload: function(frm) {

		frm.set_query("memo_ekspedisi", function(){
	        return {
	            "filters": {
	               	"docstatus": 1
	            }   
	        }
	    });
	    frm.set_query("expense_account","additional_costs_transfer_table", function(){
	        return {
				filters: [
	                ["Account", "is_group", "=", 0],
	                ["Account", "account_type", "!=","Receivable"],
	                ["Account", "account_type", "!=","Payable"],
	            ] 
	        }
	    });    
		if(frm.doc.purpose != frm.doc.stock_entry_type){
			frm.doc.purpose = frm.doc.stock_entry_type
		}
		var df = frappe.meta.get_docfield("Stock Entry Detail", "rates_section",frm.doc.name);
		df.hidden = 0;
		var df = frappe.meta.get_docfield("Stock Entry Detail", "basic_rate",frm.doc.name);
		df.hidden = 1;
		
		if(frappe.user_roles.indexOf("Stock Entry Without Value") > -1 && frappe.user["name"] != "Administrator"){
			var df = frappe.meta.get_docfield("Stock Entry Detail", "basic_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Stock Entry Detail", "basic_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Stock Entry Detail", "amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Stock Entry Detail", "valuation_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Stock Entry Detail", "valuation_rate_transfer",frm.doc.name);
			df.hidden = 1;

			var df = frappe.meta.get_docfield("Stock Entry Detail Deleted", "basic_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Stock Entry Detail Deleted", "basic_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Stock Entry Detail Deleted", "amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Stock Entry Detail Deleted", "valuation_rate",frm.doc.name);
			df.hidden = 1;

			
			frm.set_df_property("section_break_19", "hidden", 1);
			frm.refresh_fields();
		}
		else{
			var df = frappe.meta.get_docfield("Stock Entry Detail", "basic_rate",frm.doc.name);
			df.hidden = 0;
			if(frm.doc.name.indexOf("STER") > -1 && frm.doc.ste_log){
				df.read_only = 1;
			}
			else{
				df.read_only = 0;
			}
			var df = frappe.meta.get_docfield("Stock Entry Detail", "qty",frm.doc.name);
			if(frm.doc.name.indexOf("STER") > -1 && frm.doc.ste_log){
				df.read_only = 1;
			}
			else{
				df.read_only = 0;
			}
			var df = frappe.meta.get_docfield("Stock Entry Detail", "basic_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Stock Entry Detail", "amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Stock Entry Detail", "valuation_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Stock Entry Detail", "valuation_rate_transfer",frm.doc.name);
			df.hidden = 0;
			
			frm.set_df_property("section_break_19", "hidden", 0);
			frm.refresh_fields();
		}	
	},
	stock_entry_type:function(frm){
		if(frm.doc.transfer_ke_cabang_pusat == 1){
			frm.toggle_display(["additional_costs_transfer_table", "total_additional_costs_transfer", "additional_costs_transfer"],
				frm.doc.stock_entry_type=='Material Issue');
		}
	},
	transfer_ke_cabang_pusat:function(frm){
		if(frm.doc.transfer_ke_cabang_pusat == 1){
			frm.toggle_display(["additional_costs_transfer_table", "total_additional_costs_transfer", "additional_costs_transfer"],
				frm.doc.stock_entry_type=='Material Issue');

			frm.doc.auto_assign_to_rk_account = 1
			frm.refresh_fields()
		}
		else{
			frm.doc.auto_assign_to_rk_account = 0
			console.log(frm.doc.auto_assign_to_rk_account)
			frm.refresh_fields()
		}
	},
	transfer_ke_cabang_mana:function(frm){
		
			if(frm.doc.transfer_ke_cabang_mana){
				frm.add_custom_button(__('Transfer ke Cabang'), function() {
				const allowed_request_types = ["Material Transfer", "Purchase"];
				const depends_on_condition = "eval:doc.material_request_type==='Customer Provided'";
				var ready = "Ready"
				const d = erpnext.utils.map_current_doc({
					method: "addons.custom_standard.custom_material_request.make_stock_entry_kecabang",
					source_doctype: "Material Request",
					target: frm,
					date_field: "schedule_date",
					setters: [{
						fieldtype: 'Select',
						label: __('Purpose'),
						options: allowed_request_types.join("\n"),
						fieldname: 'material_request_type',
						default: "Material Transfer",
						read_only: 1,
					},
					{
						fieldtype: 'Select',
						label: __('Barang Ready'),
						options: "Ready\nNot Ready",
						fieldname: 'barang_ready',
						default: "Ready",
						mandatory: 1,
						change() {
							if (this.value === 'Ready') {
								ready = "Ready"
							}
							else{
								ready = "Not Ready"
							}
						},
					}
					],
					get_query_filters: {
						docstatus: 1,
						material_request_type: ["in", allowed_request_types],
						cabang: frm.doc.transfer_ke_cabang_mana,
						barang_ready: ready,
						status: ["not in", ["Transferred", "Issued", "Cancelled", "Stopped"]]
					}
				})
				}, __("Get Items From"));
			}
			else{
				frm.remove_custom_button(__('Transfer ke Cabang'),__("Get Items From"));
			}
		
	},
	memo_ekspedisi:function(frm){
		if(frm.doc.memo_ekspedisi){
			frappe.call({
				method : "addons.custom_standard.custom_stock_entry.get_memope",
				args : {
					"memope" : frm.doc.memo_ekspedisi
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						for(var baris in hasil.message){
							console.log(hasil)
							var d = frappe.model.add_child(cur_frm.doc,"Landed Cost Taxes and Charges Transfer","additional_costs_transfer_table")
							d.description = hasil.message[baris].name
							d.amount = hasil.message[baris].total_harga_dpp
							cur_frm.refresh_fields()
							cur_frm.trigger("additional_costs_transfer_table")
						}
						var total_cost = 0
						for(var baris in frm.doc.additional_costs_transfer_table){
							total_cost += frm.doc.additional_costs_transfer_table[baris].amount
						}
						frm.doc.total_additional_costs_transfer = total_cost
						cur_frm.refresh_fields()
						cur_frm.trigger("total_additional_costs_transfer")
					}
				}
			})

			frappe.call({
				method : "addons.custom_standard.custom_stock_entry.get_memope_item",
				args : {
					"memope" : frm.doc.memo_ekspedisi
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						console.log((hasil))
						for(var baris in hasil.message){
							for(var row in frm.doc.items){
								var satu_baris = frm.doc.items[row]
								if(!hasil.message[baris].nama_dokumen){
									console.log("tess")
									if(satu_baris.qty == hasil.message[baris].qty_rq && satu_baris.item_code == hasil.message[baris].kode_material){
										satu_baris.qty = hasil.message[baris].stuffing
									}
								}
								else{
									if(satu_baris.name == hasil.message[baris].nama_dokumen){
										satu_baris.qty = hasil.message[baris].stuffing
									}
								}
								
							}
						}
						cur_frm.refresh_fields()
						cur_frm.trigger("qty")
					}
				}
			})
		}
	},

	cost_by: function(frm) {
		if(frm.doc.cost_by == "Manual"){
			var df1 =frappe.meta.get_docfield("Stock Entry Detail","additional_cost", cur_frm.doc.name)
			df1.read_only = 0
		}

		frm.refresh_fields()
		frm.events.calculate_total_additional_costs(frm);
		let total_basic_amount = 0;
		let total_qty = 0
		let total_volume = 0
		let total_tonase = 0

		if (in_list(["Repack", "Manufacture"], frm.doc.purpose)) {
			total_basic_amount = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.is_finished_item ? flt(i.basic_amount) : 0;
				})
			);
			total_qty = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.t_warehouse ? flt(i.qty) : 0;
				})
			);
			total_volume = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.t_warehouse ? flt(i.qty * i.conversion_factor * i.volume_per_stock_qty) : 0;
				})
			);
			total_tonase = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.t_warehouse ? flt(i.qty * i.conversion_factor * i.weight_per_stock_qty) : 0;
				})
			);
		} else {
			total_basic_amount = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.t_warehouse ? flt(i.basic_amount) : 0;
				})
			);
			total_qty = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.t_warehouse ? flt(i.qty) : 0;
				})
			);
			total_volume = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.t_warehouse ? flt(i.qty) * flt(i.conversion_factor) * flt(i.volume_per_stock_qty) : 0;
				})
			);
			total_tonase = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.t_warehouse ? flt(i.qty) * flt(i.conversion_factor) * flt(i.weight_per_stock_qty) : 0;
				})
			);
		}
		for (let i in frm.doc.items) {
			let item = frm.doc.items[i];

			if (((in_list(["Repack", "Manufacture"], frm.doc.purpose) && item.is_finished_item) || item.t_warehouse) && total_basic_amount) {
				if(frm.doc.cost_by == "By Value"){
					item.additional_cost = (flt(item.basic_amount) / total_basic_amount) * frm.doc.total_additional_costs;	
				}
				else if(frm.doc.cost_by == "By Qty" && total_qty){
					item.additional_cost = (flt(item.qty) / total_qty) * frm.doc.total_additional_costs;		
				}
				else if(frm.doc.cost_by == "By Volume" && total_volume){
					item.additional_cost = (flt(item.qty) * flt(item.conversion_factor) * flt(item.volume_per_stock_qty) / total_volume) * frm.doc.total_additional_costs;
				}
				else if(frm.doc.cost_by == "By Tonase" && total_tonase){
					item.additional_cost = (flt(item.qty) * flt(item.conversion_factor) * flt(item.weight_per_stock_qty) / total_tonase) * frm.doc.total_additional_costs;
				}
				else{
					item.additional_cost = 0
				}
			} else {
				item.additional_cost = 0;
			}

			item.amount = flt(item.basic_amount + flt(item.additional_cost), precision("amount", item));

			if (flt(item.transfer_qty)) {
				item.valuation_rate = flt(flt(item.basic_rate) + (flt(item.additional_cost) / flt(item.transfer_qty)),
					precision("valuation_rate", item));
			}
			else{
				item.valuation_rate = flt(flt(item.basic_rate) + (flt(item.additional_cost)),
					precision("valuation_rate", item));
			}
		}

		

		refresh_field('items');
	},



	calculate_total_additional_costs: function(frm) {
		const total_additional_costs = frappe.utils.sum(
			(frm.doc.additional_costs || []).map(function(c) { return flt(c.base_amount); })
		);

		frm.set_value("total_additional_costs",
			flt(total_additional_costs, precision("total_additional_costs")));
	},

	calculate_amount: function(frm) {
		if(frm.doc.cost_by == "Manual"){
			var df1 =frappe.meta.get_docfield("Stock Entry Detail","additional_cost", cur_frm.doc.name)
			df1.read_only = 0
		}

		frm.events.calculate_total_additional_costs(frm);
		let total_basic_amount = 0;
		let total_qty = 0
		let total_volume = 0
		let total_tonase = 0

		if (in_list(["Repack", "Manufacture"], frm.doc.purpose)) {
			total_basic_amount = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.is_finished_item ? flt(i.basic_amount) : 0;
				})
			);
			total_qty = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.t_warehouse ? flt(i.qty) : 0;
				})
			);
			total_volume = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.t_warehouse ? flt(i.qty * i.conversion_factor * i.volume_per_stock_qty) : 0;
				})
			);
			total_tonase = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.t_warehouse ? flt(i.qty * i.conversion_factor * i.weight_per_stock_qty) : 0;
				})
			);
		} else {
			total_basic_amount = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.t_warehouse ? flt(i.basic_amount) : 0;
				})
			);
			total_qty = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.t_warehouse ? flt(i.qty) : 0;
				})
			);
			total_volume = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.t_warehouse ? flt(i.qty) * flt(i.conversion_factor) * flt(i.volume_per_stock_qty) : 0;
				})
			);
			total_tonase = frappe.utils.sum(
				(frm.doc.items || []).map(function(i) {
					return i.t_warehouse ? flt(i.qty) * flt(i.conversion_factor) * flt(i.weight_per_stock_qty) : 0;
				})
			);
		}
		for (let i in frm.doc.items) {
			let item = frm.doc.items[i];

			if (((in_list(["Repack", "Manufacture"], frm.doc.purpose) && item.is_finished_item) || item.t_warehouse) && total_basic_amount) {
				if(frm.doc.cost_by == "By Value"){
					item.additional_cost = (flt(item.basic_amount) / total_basic_amount) * frm.doc.total_additional_costs;	
				}
				else if(frm.doc.cost_by == "By Qty" && total_qty){
					item.additional_cost = (flt(item.qty) / total_qty) * frm.doc.total_additional_costs;		
				}
				else if(frm.doc.cost_by == "By Volume" && total_volume){
					item.additional_cost = (flt(item.qty) * flt(item.conversion_factor) * flt(item.volume_per_stock_qty) / total_volume) * frm.doc.total_additional_costs;
				}
				else if(frm.doc.cost_by == "By Tonase" && total_tonase){
					item.additional_cost = (flt(item.qty) * flt(item.conversion_factor) * flt(item.weight_per_stock_qty) / total_tonase) * frm.doc.total_additional_costs;
				}
				else{
					item.additional_cost = 0
				}
			} else {
				item.additional_cost = 0;
			}

			item.amount = flt(item.basic_amount + flt(item.additional_cost), precision("amount", item));

			if (flt(item.transfer_qty)) {
				item.valuation_rate = flt(flt(item.basic_rate) + (flt(item.additional_cost) / flt(item.transfer_qty)),
					precision("valuation_rate", item));
			}
			else{
				item.valuation_rate = flt(flt(item.basic_rate) + (flt(item.additional_cost)),
					precision("valuation_rate", item));
			}
		}

		

		refresh_field('items');
	},
})

frappe.ui.form.on('Stock Entry Detail', {
	qty: function(frm,cdt,cdn) {
		var total_weight = 0 
		for(var row in frm.doc.items){
			var baris = frm.doc.items[row]
			if(baris.weight_per_stock_qty){
				total_weight += baris.weight_per_stock_qty * baris.qty
			}
		}
		frm.doc.total_tonase = total_weight
		frm.refresh_fields()
	},
	item_code: function(frm,cdt,cdn) {
		var total_weight = 0 
		for(var row in frm.doc.items){
			var baris = frm.doc.items[row]
			if(baris.weight_per_stock_qty){
				total_weight += baris.weight_per_stock_qty * baris.qty
			}
		}
		frm.doc.total_tonase = total_weight
		frm.refresh_fields()
	},
	additional_cost_transfer:function(frm,cdt,cdn){
		var item = locals[cdt][cdn]
		if (flt(item.transfer_qty)) {
			item.valuation_rate_transfer = flt(flt(item.basic_rate) + (flt(item.additional_cost_transfer) / flt(item.transfer_qty)),
				precision("valuation_rate_transfer", item));
		}
		else{
			item.valuation_rate_transfer = flt(flt(item.basic_rate) + (flt(item.additional_cost_transfer)),
				precision("valuation_rate_transfer", item));
		}
		frm.refresh_fields()
	}
})



frappe.ui.form.on('Landed Cost Taxes and Charges Transfer', {

	amount:function(frm,cdt,cdn){
		const total_additional_costs_transfer = frappe.utils.sum(
			(frm.doc.additional_costs_transfer_table || []).map(function(c) { return flt(c.amount); })
		);

		frm.set_value("total_additional_costs_transfer",
			flt(total_additional_costs_transfer, precision("total_additional_costs_transfer")));

		if(frm.doc.cost_by_transfer == "Manual"){
			var df1 =frappe.meta.get_docfield("Stock Entry Detail","additional_cost_transfer", cur_frm.doc.name)
			df1.read_only = 0
		}
		else{
			var df1 =frappe.meta.get_docfield("Stock Entry Detail","additional_cost_transfer", cur_frm.doc.name)
			df1.read_only = 1
		}

		let total_basic_amount = 0;
		let total_qty = 0
		let total_volume = 0
		let total_tonase = 0

		if(frm.doc.transfer_ke_cabang_pusat == 1){
			if (in_list(["Material Issue"], frm.doc.purpose)) {
				total_basic_amount = frappe.utils.sum(
					(frm.doc.items || []).map(function(i) {
						return i.s_warehouse ? flt(i.basic_amount) : 0;
					})
				);
				total_qty = frappe.utils.sum(
					(frm.doc.items || []).map(function(i) {
						return i.s_warehouse ? flt(i.qty) : 0;
					})
				);
				total_volume = frappe.utils.sum(
					(frm.doc.items || []).map(function(i) {
						return i.s_warehouse ? flt(i.qty) * flt(i.conversion_factor) * flt(i.volume_per_stock_qty) : 0;
					})
				);
				total_tonase = frappe.utils.sum(
					(frm.doc.items || []).map(function(i) {
						return i.s_warehouse ? flt(i.qty) * flt(i.conversion_factor) * flt(i.weight_per_stock_qty) : 0;
					})
				);
			}
			for (let i in frm.doc.items) {
				let item = frm.doc.items[i];

				if(frm.doc.cost_by_transfer == "By Value"){
					item.additional_cost_transfer = (flt(item.basic_amount) / total_basic_amount) * frm.doc.total_additional_costs_transfer;	
				}
				else if(frm.doc.cost_by_transfer == "By Qty" && total_qty){
					item.additional_cost_transfer = (flt(item.qty) / total_qty) * frm.doc.total_additional_costs_transfer;		
				}
				else if(frm.doc.cost_by_transfer == "By Volume" && total_volume){
					item.additional_cost_transfer = (flt(item.qty) * flt(item.conversion_factor) * flt(item.volume_per_stock_qty) / total_volume) * frm.doc.total_additional_costs_transfer;
				}
				else if(frm.doc.cost_by_transfer == "By Tonase" && total_tonase){
					item.additional_cost_transfer = (flt(item.qty) * flt(item.conversion_factor) * flt(item.weight_per_stock_qty) / total_tonase) * frm.doc.total_additional_costs_transfer;
				}
				else{
					item.additional_cost_transfer = 0
				}
				
				item.amount = flt(item.basic_amount + flt(item.additional_cost_transfer), precision("amount", item));

				if (flt(item.transfer_qty)) {
					item.valuation_rate_transfer = flt(flt(item.basic_rate) + (flt(item.additional_cost_transfer) / flt(item.transfer_qty)),
						precision("valuation_rate_transfer", item));
				}
				else{
					item.valuation_rate_transfer = flt(flt(item.basic_rate) + (flt(item.additional_cost_transfer)),
						precision("valuation_rate_transfer", item));
				}
			}
		}
		
		refresh_field('items');
	}

});

cur_frm.add_fetch("item_code", "volume" ,"volume_per_stock_qty")
cur_frm.add_fetch("item_code", "weight_per_unit" ,"weight_per_stock_qty")

cur_frm.add_fetch("memo_ekspedisi", "tanggal_muat" ,"send_date")
cur_frm.add_fetch("memo_ekspedisi", "estimasi_tanggal_tiba" ,"receipt_date")


