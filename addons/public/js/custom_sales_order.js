{% include 'erpnext/selling/sales_common.js' %}

frappe.ui.form.on('Sales Order', {
	validate: function(frm) {
		var is_below_hpp="No";
		for(var row in frm.doc.items){
			var baris = frm.doc.items[row]
			if (baris.rate < baris.valuation_rate){
				is_below_hpp="Yes"
				msgprint("Harga Item "+baris.item_name+" ada di bawah HPP")
			}
		}
		frm.doc.is_below_hpp = is_below_hpp;
		frm.refresh_field("is_below_hpp");
	},
	schedule_date:function(frm){
		if(frm.doc.schedule_date){
			for(var row in frm.doc.items){
				var baris = frm.doc.items[row]
				baris.schedule_date = frm.doc.schedule_date
				frm.refresh_fields()
			}
		}
	},
	before_load:function(frm) {
		if(frappe.user_roles.indexOf("Repack User") == -1){
			var df=frappe.meta.get_docfield("Sales Order Item", "rate",frm.doc.name);
			df.read_only=1;
			frm.refresh_fields();
		}
		else{
			var df=frappe.meta.get_docfield("Sales Order Item", "rate",frm.doc.name);
			df.read_only=0;
			frm.refresh_fields();
		}

		if(frm.doc.__islocal){
			if(frm.doc.tax_or_non_tax == "Tax"){
				frappe.call({
					method: "addons.custom_standard.custom_sales_order.get_sales_tax",
					
					callback: function (data) {
						if(data.message.length > 0){
							frm.doc.taxes_and_charges = data.message[0]["name"]
							frm.trigger("taxes_and_charges")
							frm.set_df_property("taxes", "hidden", 0);
							frm.set_df_property("taxes_and_charges", "hidden", 0);
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

	tax_or_non_tax: function(frm) {
		if(frm.doc.__islocal){
			if(frm.doc.tax_or_non_tax == "Tax"){
				frappe.call({
					method: "addons.custom_standard.custom_sales_order.get_sales_tax",
					
					callback: function (data) {
						if(data.message.length > 0){
							frm.doc.taxes_and_charges = data.message[0]["name"]
							frm.trigger("taxes_and_charges")
							frm.set_df_property("taxes", "hidden", 0);
							frm.set_df_property("taxes_and_charges", "hidden", 0);
							frm.refresh_fields()
						} 
					}
				})
			}
			else{
				frm.doc.taxes_and_charges = ""
				frm.doc.taxes = []
				frm.refresh_fields()
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
		frm.custom_make_buttons = {
			'Delivery Note': 'Delivery Note',
			'Pick List': 'Pick List',
			'Sales Invoice': 'Sales Invoice',
			'Material Request': 'Material Request',
			'Purchase Order': 'Purchase Order',
			'Project': 'Project',
			'Payment Entry': "Payment",
			'Work Order': "Work Order"
		}
		frm.add_fetch('customer', 'payment_terms', 'payment_terms_template');
		frm.add_fetch('customer', 'tax_id', 'tax_id');

		// formatter for material request item
		frm.set_indicator_formatter('item_code',
			function(doc) { return (doc.stock_qty<=doc.delivered_qty) ? "green" : "orange" })

		frm.set_query('company_address', function(doc) {
			if(!doc.company) {
				frappe.throw(__('Please set Company'));
			}

			return {
				query: 'frappe.contacts.doctype.address.address.address_query',
				filters: {
					link_doctype: 'Company',
					link_name: doc.company
				}
			};
		})

		frm.set_query("bom_no", "items", function(doc, cdt, cdn) {
			var row = locals[cdt][cdn];
			return {
				filters: {
					"item": row.item_code
				}
			}
		});

		frm.set_df_property('packed_items', 'cannot_add_rows', true);
		frm.set_df_property('packed_items', 'cannot_delete_rows', true);

		if(frappe.user_roles.indexOf("Sales Order Without Value") > -1 && frappe.user.name != "Administrator"){
			var df = frappe.meta.get_docfield("Sales Order Item", "rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "price_list_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_price_list_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "net_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_net_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "net_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_net_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "billed_amt",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "valuation_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "gross_profit",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "tax_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "total",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "tax_amount_after_discount_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "base_tax_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "base_total",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "base_tax_amount_after_discount_amount",frm.doc.name);
			df.hidden = 1;
			
			frm.set_df_property("total", "hidden", 1);
			frm.set_df_property("net_total", "hidden", 1);
			frm.set_df_property("section_break_31", "hidden", 1);
			frm.set_df_property("total_taxes_and_charges", "hidden", 1);
			frm.set_df_property("grand_total", "hidden", 1);
			frm.set_df_property("rounding_adjustment", "hidden", 1);
			frm.set_df_property("rounded_total", "hidden", 1);
			frm.set_df_property("in_words", "hidden", 1);
			frm.refresh_fields();
		}
		else{
			var df = frappe.meta.get_docfield("Sales Order Item", "rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "price_list_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_price_list_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "net_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_net_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "net_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_net_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "billed_amt",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "valuation_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "gross_profit",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "tax_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "total",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "tax_amount_after_discount_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "base_tax_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "base_total",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "base_tax_amount_after_discount_amount",frm.doc.name);
			df.hidden = 0;
			frm.set_df_property("section_break_31", "hidden", 0);
			frm.refresh_fields();
		}	
	},
	refresh: function(frm) {
		if(frm.doc.docstatus === 1 && frm.doc.status !== 'Closed'
			&& flt(frm.doc.per_delivered, 6) < 100 && flt(frm.doc.per_billed, 6) < 100) {
			frm.add_custom_button(__('Update Items'), () => {
				erpnext.utils.update_child_items({
					frm: frm,
					child_docname: "items",
					child_doctype: "Sales Order Detail",
					cannot_add_row: false,
				})
			});
		}
		if(frm.doc.__islocal){
			if(frm.doc.tax_or_non_tax == "Tax"){
				frappe.call({
					method: "addons.custom_standard.custom_sales_order.get_sales_tax",
					
					callback: function (data) {
						if(data.message.length > 0){
							console.log(data.message[0])
							frm.doc.taxes_and_charges = data.message[0]["name"]
							frm.trigger("taxes_and_charges")
				    	    frm.refresh_fields()
						} 
					}
				})
			}
			else{

				frm.doc.taxes_and_charges = ""
				frm.doc.taxes = []
	    	    frm.refresh_fields()
				
			}
		}
		if(frappe.user_roles.indexOf("Sales Order Without Value") > -1 && frappe.user.name != "Administrator"){
			var df = frappe.meta.get_docfield("Sales Order Item", "rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "price_list_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_price_list_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "net_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_net_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "net_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_net_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "billed_amt",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "valuation_rate",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Order Item", "gross_profit",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "tax_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "total",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "tax_amount_after_discount_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "base_tax_amount",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "base_total",frm.doc.name);
			df.hidden = 1;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "base_tax_amount_after_discount_amount",frm.doc.name);
			df.hidden = 1;
			
			frm.set_df_property("total", "hidden", 1);
			frm.set_df_property("net_total", "hidden", 1);
			frm.set_df_property("section_break_31", "hidden", 1);
			frm.set_df_property("total_taxes_and_charges", "hidden", 1);
			frm.set_df_property("grand_total", "hidden", 1);
			frm.set_df_property("rounding_adjustment", "hidden", 1);
			frm.set_df_property("rounded_total", "hidden", 1);
			frm.set_df_property("in_words", "hidden", 1);
			frm.refresh_fields();
		}
		else{
			var df = frappe.meta.get_docfield("Sales Order Item", "rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "price_list_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_price_list_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "net_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_net_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "net_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "base_net_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "billed_amt",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "valuation_rate",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Order Item", "gross_profit",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "tax_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "total",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "tax_amount_after_discount_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "base_tax_amount",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "base_total",frm.doc.name);
			df.hidden = 0;
			var df = frappe.meta.get_docfield("Sales Taxes and Charges", "base_tax_amount_after_discount_amount",frm.doc.name);
			df.hidden = 0;
			frm.set_df_property("net_total", "hidden", 0);
			frm.set_df_property("section_break_31", "hidden", 0);
			frm.refresh_fields();
		}	

	},
	onload: function(frm) {
		if (!frm.doc.transaction_date){
			frm.set_value('transaction_date', frappe.datetime.get_today())
		}
		erpnext.queries.setup_queries(frm, "Warehouse", function() {
			return erpnext.queries.warehouse(frm.doc);
		});

		frm.set_query('project', function(doc, cdt, cdn) {
			return {
				query: "erpnext.controllers.queries.get_project_name",
				filters: {
					'customer': doc.customer
				}
			}
		});

		erpnext.queries.setup_warehouse_query(frm);

		frm.ignore_doctypes_on_cancel_all = ['Purchase Order'];

		frm.set_query("account_head", "taxes", function() {
			return {
				filters: {
					"is_group": 0,
					"disabled": 0
				}
			}
		});

		
		if(frappe.user_roles.indexOf("Read Valuation Rate") == -1){
			frm.set_df_property("transaction_date", "hidden", 1);
			var df = frappe.meta.get_docfield("Sales Order Item", "gross_profit", frm.doc.name)
			df.hidden = 1
			var df = frappe.meta.get_docfield("Sales Order Item", "valuation_rate", frm.doc.name)
			df.hidden = 1
			frm.refresh_fields()
		}
		
		frm.set_df_property("transaction_date", "read_only", 0);

		if(frappe.user_roles.indexOf("Head Admin") == -1 && frappe.user_roles.indexOf("Admin Penjualan") == -1 && frappe.user_roles.indexOf("Input Backdate Sales Order") == -1){
			frm.set_df_property("transaction_date", "read_only", 1);
			frm.set_df_property("transaction_date", "hidden", 0);
			frm.refresh_fields()
		}
		else{
			
			frm.set_df_property("transaction_date", "read_only", 0);
			frm.set_df_property("transaction_date", "hidden", 0);
			frm.refresh_fields()
		}
		frm.refresh_fields()
	
	},

	delivery_date: function(frm) {
		$.each(frm.doc.items || [], function(i, d) {
			if(!d.delivery_date) d.delivery_date = frm.doc.delivery_date;
		});
		refresh_field("items");
	}
});

frappe.ui.form.on("Sales Order Item", {
	item_code: function(frm,cdt,cdn) {
		var row = locals[cdt][cdn];
		if (frm.doc.delivery_date) {
			row.delivery_date = frm.doc.delivery_date;
			refresh_field("delivery_date", cdn, "items");
		} else {
			frm.script_manager.copy_from_first_row("items", row, ["delivery_date"]);
		}
	},
	delivery_date: function(frm, cdt, cdn) {
		if(!frm.doc.delivery_date) {
			erpnext.utils.copy_value_in_all_rows(frm.doc, cdt, cdn, "items", "delivery_date");
		}
	}
});

erpnext.selling.SalesOrderController = erpnext.selling.SellingController.extend({
	onload: function(doc, dt, dn) {
		this._super();
	},

	refresh: function(doc, dt, dn) {
		var me = this;
		this._super();
		let allow_delivery = false;

		if (doc.docstatus==1) {

			if(this.frm.has_perm("submit")) {
				if(doc.status === 'On Hold') {
				   // un-hold
				   this.frm.add_custom_button(__('Resume'), function() {
					   me.frm.cscript.update_status('Resume', 'Draft')
				   }, __("Status"));

				   if(flt(doc.per_delivered, 6) < 100 || flt(doc.per_billed) < 100) {
					   // close
					   this.frm.add_custom_button(__('Close'), () => this.close_sales_order(), __("Status"))
				   }
				}
			   	else if(doc.status === 'Closed') {
				   // un-close
				   this.frm.add_custom_button(__('Re-open'), function() {
					   me.frm.cscript.update_status('Re-open', 'Draft')
				   }, __("Status"));
			   }
			}
			if(doc.status !== 'Closed') {
				if(doc.status !== 'On Hold') {
					allow_delivery = this.frm.doc.items.some(item => item.delivered_by_supplier === 0 && item.qty > flt(item.delivered_qty))
						&& !this.frm.doc.skip_delivery_note

					if (this.frm.has_perm("submit")) {
						if(flt(doc.per_delivered, 6) < 100 || flt(doc.per_billed) < 100) {
							// hold
							this.frm.add_custom_button(__('Hold'), () => this.hold_sales_order(), __("Status"))
							// close
							this.frm.add_custom_button(__('Close'), () => this.close_sales_order(), __("Status"))
						}
					}

					this.frm.add_custom_button(__('Pick List'), () => this.create_pick_list(), __('Create'));

					const order_is_a_sale = ["Sales", "Shopping Cart"].indexOf(doc.order_type) !== -1;
					const order_is_maintenance = ["Maintenance"].indexOf(doc.order_type) !== -1;
					// order type has been customised then show all the action buttons
					const order_is_a_custom_sale = ["Sales", "Shopping Cart", "Maintenance"].indexOf(doc.order_type) === -1;

					// delivery note
					if(flt(doc.per_delivered, 6) < 100 && (order_is_a_sale || order_is_a_custom_sale) && allow_delivery) {
						this.frm.add_custom_button(__('Delivery Notes'), () => this.make_delivery_note_based_on_delivery_date(), __('Create'));
						this.frm.add_custom_button(__('Work Order'), () => this.make_work_order(), __('Create'));
					}

					// sales invoice
					if(flt(doc.per_billed, 6) < 100) {
						this.frm.add_custom_button(__('Sales Invoice'), () => me.make_sales_invoice(), __('Create'));
					}

					// material request
					if(!doc.order_type || (order_is_a_sale || order_is_a_custom_sale) && flt(doc.per_delivered, 6) < 100) {
						this.frm.add_custom_button(__('Material Request'), () => this.make_material_request(), __('Create'));
						this.frm.add_custom_button(__('Request for Raw Materials'), () => this.make_raw_material_request(), __('Create'));
					}

					// Make Purchase Order
					if (!this.frm.doc.is_internal_customer) {
						this.frm.add_custom_button(__('Purchase Order'), () => this.make_purchase_order(), __('Create'));
					}

					// maintenance
					if(flt(doc.per_delivered, 2) < 100 && (order_is_maintenance || order_is_a_custom_sale)) {
						this.frm.add_custom_button(__('Maintenance Visit'), () => this.make_maintenance_visit(), __('Create'));
						this.frm.add_custom_button(__('Maintenance Schedule'), () => this.make_maintenance_schedule(), __('Create'));
					}

					// project
					if(flt(doc.per_delivered, 2) < 100) {
							this.frm.add_custom_button(__('Project'), () => this.make_project(), __('Create'));
					}

					if(!doc.auto_repeat) {
						this.frm.add_custom_button(__('Subscription'), function() {
							erpnext.utils.make_subscription(doc.doctype, doc.name)
						}, __('Create'))
					}

					if (doc.docstatus === 1 && !doc.inter_company_order_reference) {
						let me = this;
						let internal = me.frm.doc.is_internal_customer;
						if (internal) {
							let button_label = (me.frm.doc.company === me.frm.doc.represents_company) ? "Internal Purchase Order" :
								"Inter Company Purchase Order";

							me.frm.add_custom_button(button_label, function() {
								me.make_inter_company_order();
							}, __('Create'));
						}
					}
				}
				// payment request
				if(flt(doc.per_billed)<100) {
					this.frm.add_custom_button(__('Payment Request'), () => this.make_payment_request(), __('Create'));
					this.frm.add_custom_button(__('Payment'), () => this.make_payment_entry(), __('Create'));
				}
				this.frm.page.set_inner_btn_group_as_primary(__('Create'));
			}
		}

		if (this.frm.doc.docstatus===0) {
			this.frm.add_custom_button(__('Quotation'),
				function() {
					erpnext.utils.map_current_doc({
						method: "erpnext.selling.doctype.quotation.quotation.make_sales_order",
						source_doctype: "Quotation",
						target: me.frm,
						setters: [
							{
								label: "Customer",
								fieldname: "party_name",
								fieldtype: "Link",
								options: "Customer",
								default: me.frm.doc.customer || undefined
							}
						],
						get_query_filters: {
							company: me.frm.doc.company,
							docstatus: 1,
							status: ["!=", "Lost"]
						}
					})
				}, __("Get Items From"));
		}

		this.order_type(doc);
	},

	create_pick_list() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.create_pick_list",
			frm: this.frm
		})
	},

	make_work_order() {
		var me = this;
		this.frm.call({
			doc: this.frm.doc,
			method: 'get_work_order_items',
			callback: function(r) {
				if(!r.message) {
					frappe.msgprint({
						title: __('Work Order not created'),
						message: __('No Items with Bill of Materials to Manufacture'),
						indicator: 'orange'
					});
					return;
				}
				else if(!r.message) {
					frappe.msgprint({
						title: __('Work Order not created'),
						message: __('Work Order already created for all items with BOM'),
						indicator: 'orange'
					});
					return;
				} else {
					const fields = [{
						label: 'Items',
						fieldtype: 'Table',
						fieldname: 'items',
						description: __('Select BOM and Qty for Production'),
						fields: [{
							fieldtype: 'Read Only',
							fieldname: 'item_code',
							label: __('Item Code'),
							in_list_view: 1
						}, {
							fieldtype: 'Link',
							fieldname: 'bom',
							options: 'BOM',
							reqd: 1,
							label: __('Select BOM'),
							in_list_view: 1,
							get_query: function (doc) {
								return { filters: { item: doc.item_code } };
							}
						}, {
							fieldtype: 'Float',
							fieldname: 'pending_qty',
							reqd: 1,
							label: __('Qty'),
							in_list_view: 1
						}, {
							fieldtype: 'Data',
							fieldname: 'sales_order_item',
							reqd: 1,
							label: __('Sales Order Item'),
							hidden: 1
						}],
						data: r.message,
						get_data: () => {
							return r.message
						}
					}]
					var d = new frappe.ui.Dialog({
						title: __('Select Items to Manufacture'),
						fields: fields,
						primary_action: function() {
							var data = {items: d.fields_dict.items.grid.get_selected_children()};
							me.frm.call({
								method: 'make_work_orders',
								args: {
									items: data,
									company: me.frm.doc.company,
									sales_order: me.frm.docname,
									project: me.frm.project
								},
								freeze: true,
								callback: function(r) {
									if(r.message) {
										frappe.msgprint({
											message: __('Work Orders Created: {0}', [r.message.map(function(d) {
													return repl('<a href="/app/work-order/%(name)s">%(name)s</a>', {name:d})
												}).join(', ')]),
											indicator: 'green'
										})
									}
									d.hide();
								}
							});
						},
						primary_action_label: __('Create')
					});
					d.show();
				}
			}
		});
	},

	order_type: function() {
		this.toggle_delivery_date();
	},

	tc_name: function() {
		this.get_terms();
	},

	make_material_request: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_material_request",
			frm: this.frm
		})
	},

	skip_delivery_note: function() {
		this.toggle_delivery_date();
	},

	toggle_delivery_date: function() {
		this.frm.fields_dict.items.grid.toggle_reqd("delivery_date",
			(this.frm.doc.order_type == "Sales" && !this.frm.doc.skip_delivery_note));
	},

	make_raw_material_request: function() {
		var me = this;
		this.frm.call({
			doc: this.frm.doc,
			method: 'get_work_order_items',
			args: {
				for_raw_material_request: 1
			},
			callback: function(r) {
				if(!r.message) {
					frappe.msgprint({
						message: __('No Items with Bill of Materials.'),
						indicator: 'orange'
					});
					return;
				}
				else {
					me.make_raw_material_request_dialog(r);
				}
			}
		});
	},

	make_raw_material_request_dialog: function(r) {
		var fields = [
			{fieldtype:'Check', fieldname:'include_exploded_items',
				label: __('Include Exploded Items')},
			{fieldtype:'Check', fieldname:'ignore_existing_ordered_qty',
				label: __('Ignore Existing Ordered Qty')},
			{
				fieldtype:'Table', fieldname: 'items',
				description: __('Select BOM, Qty and For Warehouse'),
				fields: [
					{fieldtype:'Read Only', fieldname:'item_code',
						label: __('Item Code'), in_list_view:1},
					{fieldtype:'Link', fieldname:'warehouse', options: 'Warehouse',
						label: __('For Warehouse'), in_list_view:1},
					{fieldtype:'Link', fieldname:'bom', options: 'BOM', reqd: 1,
						label: __('BOM'), in_list_view:1, get_query: function(doc) {
							return {filters: {item: doc.item_code}};
						}
					},
					{fieldtype:'Float', fieldname:'required_qty', reqd: 1,
						label: __('Qty'), in_list_view:1},
				],
				data: r.message,
				get_data: function() {
					return r.message
				}
			}
		]
		var d = new frappe.ui.Dialog({
			title: __("Items for Raw Material Request"),
			fields: fields,
			primary_action: function() {
				var data = d.get_values();
				me.frm.call({
					method: 'erpnext.selling.doctype.sales_order.sales_order.make_raw_material_request',
					args: {
						items: data,
						company: me.frm.doc.company,
						sales_order: me.frm.docname,
						project: me.frm.project
					},
					freeze: true,
					callback: function(r) {
						if(r.message) {
							frappe.msgprint(__('Material Request {0} submitted.',
							['<a href="/app/material-request/'+r.message.name+'">' + r.message.name+ '</a>']));
						}
						d.hide();
						me.frm.reload_doc();
					}
				});
			},
			primary_action_label: __('Create')
		});
		d.show();
	},

	make_delivery_note_based_on_delivery_date: function() {
		var me = this;

		var delivery_dates = [];
		$.each(this.frm.doc.items || [], function(i, d) {
			if(!delivery_dates.includes(d.delivery_date)) {
				delivery_dates.push(d.delivery_date);
			}
		});

		var item_grid = this.frm.fields_dict["items"].grid;
		if(!item_grid.get_selected().length && delivery_dates.length > 1) {
			var dialog = new frappe.ui.Dialog({
				title: __("Select Items based on Delivery Date"),
				fields: [{fieldtype: "HTML", fieldname: "dates_html"}]
			});

			var html = $(`
				<div style="border: 1px solid #d1d8dd">
					<div class="list-item list-item--head">
						<div class="list-item__content list-item__content--flex-2">
							${__('Delivery Date')}
						</div>
					</div>
					${delivery_dates.map(date => `
						<div class="list-item">
							<div class="list-item__content list-item__content--flex-2">
								<label>
								<input type="checkbox" data-date="${date}" checked="checked"/>
								${frappe.datetime.str_to_user(date)}
								</label>
							</div>
						</div>
					`).join("")}
				</div>
			`);

			var wrapper = dialog.fields_dict.dates_html.$wrapper;
			wrapper.html(html);

			dialog.set_primary_action(__("Select"), function() {
				var dates = wrapper.find('input[type=checkbox]:checked')
					.map((i, el) => $(el).attr('data-date')).toArray();

				if(!dates) return;

				$.each(dates, function(i, d) {
					$.each(item_grid.grid_rows || [], function(j, row) {
						if(row.doc.delivery_date == d) {
							row.doc.__checked = 1;
						}
					});
				})
				me.make_delivery_note();
				dialog.hide();
			});
			dialog.show();
		} else {
			this.make_delivery_note();
		}
	},

	make_delivery_note: function() {
		frappe.model.open_mapped_doc({
			method: "addons.custom_standard.custom_sales_order.custom_make_delivery_note",
			frm: this.frm
		})
	},

	make_sales_invoice: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_sales_invoice",
			frm: this.frm
		})
	},

	make_maintenance_schedule: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_maintenance_schedule",
			frm: this.frm
		})
	},

	make_project: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_project",
			frm: this.frm
		})
	},

	make_inter_company_order: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_inter_company_purchase_order",
			frm: this.frm
		});
	},

	make_maintenance_visit: function() {
		frappe.model.open_mapped_doc({
			method: "erpnext.selling.doctype.sales_order.sales_order.make_maintenance_visit",
			frm: this.frm
		})
	},

	make_purchase_order: function(){
		let pending_items = this.frm.doc.items.some((item) =>{
			let pending_qty = flt(item.stock_qty) - flt(item.ordered_qty);
			return pending_qty > 0;
		})
		if(!pending_items){
			frappe.throw({message: __("Purchase Order already created for all Sales Order items"), title: __("Note")});
		}

		var me = this;
		var dialog = new frappe.ui.Dialog({
			title: __("Select Items"),
			fields: [
				{
					"fieldtype": "Check",
					"label": __("Against Default Supplier"),
					"fieldname": "against_default_supplier",
					"default": 0
				},
				{
					fieldname: 'items_for_po', fieldtype: 'Table', label: 'Select Items',
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
							fieldname:'item_name',
							label: __('Item name'),
							read_only:1,
							in_list_view:1
						},
						{
							fieldtype:'Float',
							fieldname:'pending_qty',
							label: __('Pending Qty'),
							read_only: 1,
							in_list_view:1
						},
						{
							fieldtype:'Link',
							read_only:1,
							fieldname:'uom',
							label: __('UOM'),
							in_list_view:1,
						},
						{
							fieldtype:'Data',
							fieldname:'supplier',
							label: __('Supplier'),
							read_only:1,
							in_list_view:1
						},
					]
				}
			],
			primary_action_label: 'Create Purchase Order',
			primary_action (args) {
				if (!args) return;

				let selected_items = dialog.fields_dict.items_for_po.grid.get_selected_children();
				if(selected_items.length == 0) {
					frappe.throw({message: 'Please select Items from the Table', title: __('Items Required'), indicator:'blue'})
				}

				dialog.hide();

				var method = args.against_default_supplier ? "make_purchase_order_for_default_supplier" : "make_purchase_order"
				return frappe.call({
					method: "erpnext.selling.doctype.sales_order.sales_order." + method,
					freeze: true,
					freeze_message: __("Creating Purchase Order ..."),
					args: {
						"source_name": me.frm.doc.name,
						"selected_items": selected_items
					},
					freeze: true,
					callback: function(r) {
						if(!r.exc) {
							if (!args.against_default_supplier) {
								frappe.model.sync(r.message);
								frappe.set_route("Form", r.message.doctype, r.message.name);
							}
							else {
								frappe.route_options = {
									"sales_order": me.frm.doc.name
								}
								frappe.set_route("List", "Purchase Order");
							}
						}
					}
				})
			}
		});

		dialog.fields_dict["against_default_supplier"].df.onchange = () => set_po_items_data(dialog);

		function set_po_items_data (dialog) {
			var against_default_supplier = dialog.get_value("against_default_supplier");
			var items_for_po = dialog.get_value("items_for_po");

			if (against_default_supplier) {
				let items_with_supplier = items_for_po.filter((item) => item.supplier)

				dialog.fields_dict["items_for_po"].df.data = items_with_supplier;
				dialog.get_field("items_for_po").refresh();
			} else {
				let po_items = [];
				me.frm.doc.items.forEach(d => {
					let pending_qty = (flt(d.stock_qty) - flt(d.ordered_qty)) / flt(d.conversion_factor);
					if (pending_qty > 0) {
						po_items.push({
							"doctype": "Sales Order Item",
							"name": d.name,
							"item_name": d.item_name,
							"item_code": d.item_code,
							"pending_qty": pending_qty,
							"uom": d.uom,
							"supplier": d.supplier
						});
					}
				});

				dialog.fields_dict["items_for_po"].df.data = po_items;
				dialog.get_field("items_for_po").refresh();
			}
		}

		set_po_items_data(dialog);
		dialog.get_field("items_for_po").grid.only_sortable();
		dialog.get_field("items_for_po").refresh();
		dialog.wrapper.find('.grid-heading-row .grid-row-check').click();
		dialog.show();
	},

	hold_sales_order: function(){
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
				frappe.call({
					method: "frappe.desk.form.utils.add_comment",
					args: {
						reference_doctype: me.frm.doctype,
						reference_name: me.frm.docname,
						content: __('Reason for hold: ')+data.reason_for_hold,
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
	close_sales_order: function(){
		this.frm.cscript.update_status("Close", "Closed")
	},
	update_status: function(label, status){
		var doc = this.frm.doc;
		var me = this;
		frappe.ui.form.is_saving = true;
		frappe.call({
			method: "erpnext.selling.doctype.sales_order.sales_order.update_status",
			args: {status: status, name: doc.name},
			callback: function(r){
				me.frm.reload_doc();
			},
			always: function() {
				frappe.ui.form.is_saving = false;
			}
		});
	}
});
$.extend(cur_frm.cscript, new erpnext.selling.SalesOrderController({frm: cur_frm}));
