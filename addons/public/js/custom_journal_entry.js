frappe.ui.form.on('Journal Entry', {
	onload: function(frm) {
		if(!frm.doc.__islocal) { // document to show
			var list_boleh = frappe.get_children(frappe.workflow.workflows[frm.doc.doctype], "states", {state:frm.doc.workflow_state})
			var list_role = []
			for(var row in list_boleh){
				list_role.push(list_boleh[row].allow_edit)
			}
			for(var row in list_role){
				if(frappe.user_roles.indexOf(list_role[row]) > -1){
					const docperms = frappe.perm.get_perm(frm.doc.doctype);
					frm.perm = docperms.map(p => {
						return {
							amend: p.amend,
							cancel: p.cancel,
							create: p.create,
							export: p.export,
							permlevel: p.permlevel,
							print: p.print,
							read: p.read,
							report: p.report,
							select: p.select,
							submit: p.submit,
							write: p.write
						};
					});	
				}
			}
		}
	},
	refresh: function(frm) {
		cur_frm.set_query("sumber_cash_request", function(doc) {
			return {
				filters:  [
					['Cash Request', 'docstatus', '=', 1]
				]
			}
		});

		if(frm.doc.__islocal){
			if(frm.doc.accounts){
				if(frm.doc.accounts[0]){
					if(!frm.doc.accounts[0].account){	
						frm.doc.accounts = []
						frm.refresh_fields()
					}
				}
				
			}
			frm.doc.cheque_date = frm.doc.posting_date
			frm.refresh_fields()
		}
		if(frm.doc.__islocal){
			if(frm.doc.voucher_type == "Cash Entry"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["CEI-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####","CEO-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "CEI-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Bank Entry"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["BEI-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####","BEO-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "BEI-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Debit Note - Pembelian"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["DN-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "DN-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Credit Note - Penjualan"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["CN-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "CN-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Write Off Entry"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["WTO-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "WTO-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Opening Entry"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["OEB-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "OEB-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Depreciation Entry"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["DPRC-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "DPRC-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Exchange Rate Revaluation"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["REV-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "REV-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Deferred Revenue"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["DEFR-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "DEFR-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Deferred Expense"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["DEFE-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "DEFE-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Journal Special Tax"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["JRE-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "JRE-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else{
				console.log(frm.doc.voucher_type)
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["JE-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####","JEDP-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "JE-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}



			
		}
	},


	posting_date:function(frm){
		frm.doc.cheque_date = frm.doc.posting_date
		frm.refresh_fields()
	},

	// sumber_cash_request:function(frm){
	// 	if(frm.doc.sumber_cash_request){
	// 		if(frm.doc.supplier_cash_request){
	// 			frm.doc.supplier_cash_request = ""
	// 			frm.refresh_fields()
	// 		}
	// 	}
	// },
	/*supplier_cash_request:function(frm){
		if(frm.doc.supplier_cash_request){
			if(frm.doc.sumber_cash_request){
				frm.doc.sumber_cash_request = ""
				frm.refresh_fields()
			}
		}
	},*/
	get_data:function(frm){

		/*if(frm.doc.sumber_cash_request && frm.doc.supplier_cash_request){
			frappe.throw("Please choose as only Cash Request / Supplier are available to get.")
		}*/

		if(frm.doc.sumber_cash_request && frm.doc.supplier_cash_request){
			frm.doc.accounts = []
			frappe.call({
				method: "addons.custom_standard.custom_journal_entry.get_cash_request",
				args:{
					cash_request : frm.doc.sumber_cash_request
				},
				freeze:true,
				callback: function(r){
					console.log(r)
					cur_frm.set_value("tax_or_non_tax",r.message[0].tax_or_non_tax)
					var total_debit = 0
					var total_credit = 0


					var total_debit_in_cure = 0
					var total_credit_in_cure = 0

					for(var baris in r.message){
						var satu_baris = r.message[baris]

						if(satu_baris.currency != "IDR" && !(frm.doc.multi_currency)){
							frm.doc.multi_currency = 1
							frm.trigger("multi_currency")
						}
						console.log(satu_baris)
						var d = frappe.model.add_child(cur_frm.doc,"Journal Entry Account","accounts")

						d.account = satu_baris.account
						d.party_type = satu_baris.party_type
						d.party = satu_baris.party
						if(satu_baris.account_currency == "IDR"){
							d.exchange_rate = 1
						}
						else{
							d.exchange_rate = satu_baris.exchange_rate
						}
						d.account_currency = satu_baris.account_currency
						d.branch = "Jakarta"
						d.sumber_cash_request = frm.doc.sumber_cash_request
						if(satu_baris.difference > 0){
							if(satu_baris.currency != "IDR" && satu_baris.account_currency == "IDR" ){
								d.debit_in_account_currency = Math.ceil(satu_baris.difference * satu_baris.exchange_rate)
								d.debit = Math.ceil(satu_baris.difference * satu_baris.exchange_rate)
							}
							else{
								d.debit_in_account_currency = Math.ceil(satu_baris.difference)
								d.debit = Math.ceil(satu_baris.difference * d.exchange_rate)
							}
						}
						else{
							if(satu_baris.currency != "IDR" && satu_baris.account_currency == "IDR" ){
								d.credit_in_account_currency = 	satu_baris.difference * satu_baris.exchange_rate * -1
								d.credit = 	satu_baris.difference * -1 * satu_baris.exchange_rate					
							}
							else{
								d.credit_in_account_currency = 	satu_baris.difference * -1
								d.credit = 	satu_baris.difference * -1 * d.exchange_rate
							}
							
							
						}
						if(satu_baris.document){
							d.reference_type = "Purchase Invoice"
							d.reference_name = satu_baris.document
							if(satu_baris.difference > 0){
								total_debit += satu_baris.difference * satu_baris.new_rate
								total_debit_in_cure += satu_baris.difference * satu_baris.currency_exchange
							}
							else{
								total_credit += satu_baris.difference * satu_baris.new_rate
								total_credit_in_cure += satu_baris.difference * -1* satu_baris.currency_exchange	
							}
						}
						else{
							d.account_currency = satu_baris.account_currency
							if(d.account_currency == "IDR"){
								if(d.debit){
									d.debit = d.debit_in_account_currency
								}
								else{
									d.credit = d.credit_in_account_currency	
								}
							}
							if(satu_baris.difference > 0){
								total_debit += d.debit
								total_debit_in_cure += d.debit
							}
							else{
								total_credit += d.credit
								total_credit_in_cure += d.credit
							}				
						}
					}
					var d = frappe.model.add_child(cur_frm.doc,"Journal Entry Account","accounts")
					var difference = total_debit - total_credit
					if(difference > 0){
						d.credit = difference
						d.credit_in_account_currency = difference
						total_credit += d.credit
						total_credit_in_cure += d.credit
						
					}
					else{
						d.debit = difference * r.message[0].currency_exchange * -1
						d.debit_in_account_currency = difference * r.message[0].currency_exchange * -1
						total_debit += d.debit
						total_debit_in_cure += d.debit
					}
					d.account = r.message[0].cash_or_bank_account
					d.branch = "Jakarta"
					d.sumber_cash_request = frm.doc.sumber_cash_request
					frm.doc.total_debit = total_debit
					frm.doc.total_credit = total_credit

					if (total_debit_in_cure != total_credit_in_cure){
						if (total_debit_in_cure > total_credit_in_cure){
							var d = frappe.model.add_child(cur_frm.doc,"Journal Entry Account","accounts")
							
							d.branch = "Jakarta"
							d.account_currency = "IDR"
							d.account = "8107 - SELISIH KURS TEREALISASI - G"
							d.sumber_cash_request = frm.doc.sumber_cash_request
							d.credit_in_account_currency = (total_debit_in_cure - total_credit_in_cure) 
							d.credit = total_debit_in_cure - total_credit_in_cure
						}
						else{
							var d = frappe.model.add_child(cur_frm.doc,"Journal Entry Account","accounts")
							d.branch = "Jakarta"
							d.account_currency = "IDR"
							d.account = "8107 - SELISIH KURS TEREALISASI - G"
							d.sumber_cash_request = frm.doc.sumber_cash_request
							d.debit_in_account_currency = (total_credit_in_cure - total_debit_in_cure) 
							d.debit = total_credit_in_cure - total_debit_in_cure
						}
					}
					if(r.message[0].currency_exchange != "IDR"){
						frm.doc.multi_currency = 1
					}
					frm.refresh_fields()
				}
			})
		}

		else if(frm.doc.supplier_cash_request){
			frm.doc.accounts = []
			frappe.call({
				method: "addons.custom_standard.custom_journal_entry.get_cash_request_dr_supplier",
				args:{
					supplier : frm.doc.supplier_cash_request
				},
				freeze:true,
				callback: function(r){

					var total_debit = 0
					var total_credit = 0
					var total_debit_in_cure = 0
					var total_credit_in_cure = 0

					for(var baris in r.message){
						var satu_baris = r.message[baris]

						if(satu_baris.currency != "IDR" && !(frm.doc.multi_currency)){
							frm.doc.multi_currency = 1
							frm.trigger("multi_currency")
						}
						console.log(satu_baris)
						var d = frappe.model.add_child(cur_frm.doc,"Journal Entry Account","accounts")

						d.account = satu_baris.account
						d.party_type = satu_baris.party_type
						d.party = satu_baris.party
						d.exchange_rate = satu_baris.exchange_rate
						d.account_currency = satu_baris.currency
						d.branch = "Jakarta"
						d.sumber_cash_request = frm.doc.sumber_cash_request
						if(satu_baris.difference > 0){
							d.debit_in_account_currency = satu_baris.difference 
							d.debit = satu_baris.difference * d.exchange_rate
							
						}
						else{
							d.credit_in_account_currency = 	satu_baris.difference * -1
							d.credit = 	satu_baris.difference * -1* d.exchange_rate
							
						}
						if(satu_baris.document){
							d.reference_type = "Purchase Invoice"
							d.reference_name = satu_baris.document
							if(satu_baris.difference > 0){
								total_debit += satu_baris.difference * satu_baris.new_rate
								total_debit_in_cure += satu_baris.difference * satu_baris.exchange_rate
							}
							else{
								total_credit += satu_baris.difference * satu_baris.new_rate
								total_credit_in_cure += satu_baris.difference * -1* satu_baris.exchange_rate	
							}
						}
						else{
							d.account_currency = satu_baris.account_currency
							if(d.account_currency == "IDR"){
								if(d.debit){
									d.debit = d.debit_in_account_currency
								}
								else{
									d.credit = d.credit_in_account_currency	
								}
							}
							if(satu_baris.difference > 0){
								total_debit += d.debit
								total_debit_in_cure += d.debit
							}
							else{
								total_credit += d.credit
								total_credit_in_cure += d.credit
							}				
						}

					}

					var d = frappe.model.add_child(cur_frm.doc,"Journal Entry Account","accounts")
					var difference = total_debit - total_credit
					if(difference > 0){
						d.credit = difference
						d.credit_in_account_currency = difference
						total_credit += d.credit
						total_credit_in_cure += d.credit
					}
					else{
						d.debit = difference * -1
						d.debit_in_account_currency = difference * -1
						total_debit += d.debit
						total_debit_in_cure += d.debit
					}
					d.branch = "Jakarta"
					d.sumber_cash_request = frm.doc.sumber_cash_request
					frm.doc.total_debit = total_debit
					frm.doc.total_credit = total_credit
					if (total_debit_in_cure != total_credit_in_cure){
						if (total_debit_in_cure > total_credit_in_cure){
							var d = frappe.model.add_child(cur_frm.doc,"Journal Entry Account","accounts")
							
							d.branch = "Jakarta"
							d.account_currency = "IDR"
							d.account = "5510.010 - Selisih Kurs - G"
							d.sumber_cash_request = frm.doc.sumber_cash_request
							d.credit_in_account_currency = (total_debit_in_cure - total_credit_in_cure) 
							d.credit = total_debit_in_cure - total_credit_in_cure
						}
						else{
							var d = frappe.model.add_child(cur_frm.doc,"Journal Entry Account","accounts")
							d.branch = "Jakarta"
							d.account_currency = "IDR"
							d.account = "5510.010 - Selisih Kurs - G"
							d.sumber_cash_request = frm.doc.sumber_cash_request
							d.debit_in_account_currency = (total_credit_in_cure - total_debit_in_cure) 
							d.debit = total_credit_in_cure - total_debit_in_cure
						}
					}
					if(r.message[0].currency_exchange != "IDR"){
						frm.doc.multi_currency = 1
					}
					frm.refresh_fields()
				}
			})
		}
	},
	from_template: function(frm){
		if (frm.doc.from_template){
			if(frm.doc.__islocal){
				frappe.db.get_doc("Journal Entry Template", frm.doc.from_template)
				.then((doc) => {
					frappe.model.clear_table(frm.doc, "accounts");
					frm.set_value({
						"company": doc.company,
						"voucher_type": doc.voucher_type,
						"naming_series": doc.naming_series,
						"is_opening": doc.is_opening,
						"multi_currency": doc.multi_currency
					})
					update_jv_details(frm.doc, doc.accounts);
				});
			}
			else{
				frappe.db.get_doc("Journal Entry Template", frm.doc.from_template)
				.then((doc) => {
					frappe.model.clear_table(frm.doc, "accounts");
					frm.set_value({
						"company": doc.company,
						"voucher_type": doc.voucher_type,
						"is_opening": doc.is_opening,
						"multi_currency": doc.multi_currency
					})
					update_jv_details(frm.doc, doc.accounts);
				});
			}
			
		}
	},
	voucher_type:function(frm){
		if(frm.doc.__islocal){
			if(frm.doc.voucher_type == "Cash Entry"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["CEI-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####","CEO-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "CEI-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Bank Entry"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["BEI-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####","BEO-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "BEI-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Debit Note - Pembelian"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["DN-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "DN-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Credit Note - Penjualan"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["CN-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "CN-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Write Off Entry"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["WTO-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "WTO-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Opening Entry"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["OEB-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "OEB-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Depreciation Entry"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["DPRC-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "DPRC-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Exchange Rate Revaluation"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["REV-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "REV-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Deferred Revenue"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["DEFR-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "DEFR-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Deferred Expense"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["DEFE-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "DEFE-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.voucher_type == "Journal Special Tax"){
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["JRE-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "JRE-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else{
				console.log(frm.doc.voucher_type)
				frappe.meta.get_docfield("Journal Entry", "naming_series", frm.doc.name).options = ["JE-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####","JEDP-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "JE-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}



			
		}
	}
});


var update_jv_details = function(doc, r) {
	$.each(r, function(i, d) {
		var row = frappe.model.add_child(doc, "Journal Entry Account", "accounts");
		row.account = d.account;
		row.balance = d.balance;
		row.debit_in_account_currency = d.debit
		row.credit_in_account_currency = d.credit
	});
	refresh_field("accounts");
}

frappe.ui.form.on('Journal Entry Account', {
	party: function(frm,cdt,cdn) {
		var baris = locals[cdt][cdn]
		if(baris.party_type == "Customer"){
			frappe.call({
		        method: 'frappe.client.get_value',
		        args: {
		            'doctype': 'Customer',
		            'filters': {'name': baris.party},
		            'fieldname': [
		                'customer_name'
		            ]
		        },
		        callback: function(r) {
		            if (!r.exc) {
		                baris.party_full_name = r.message.customer_name
		                refresh_field("accounts")
		            }
		        }
		    });
		}
		else if(baris.party_type == "Supplier"){
			frappe.call({
		        method: 'frappe.client.get_value',
		        args: {
		            'doctype': 'Supplier',
		            'filters': {'name': baris.party},
		            'fieldname': [
		                'supplier_name'
		            ]
		        },
		        callback: function(r) {
		            if (!r.exc) {
		                baris.party_full_name = r.message.supplier_name
		                refresh_field("accounts")
		            }
		        }
		    });
		}
	},
	cost_center: function(frm, dt, dn) {
		// erpnext.journal_entry.set_account_balance(frm, dt, dn);
		erpnext.journal_entry.set_account_balance_custom(frm, dt, dn);
		// addons.custom_standard.custom_journal_entry.set_account_balance(frm, dt, dn);
	},
	account: function(frm, dt, dn) {
		// erpnext.journal_entry.set_account_balance(frm, dt, dn);
		erpnext.journal_entry.set_account_balance_custom(frm, dt, dn);
	},
});


$.extend(erpnext.journal_entry, {
	set_account_balance_custom: function(frm, dt, dn) {
		// frappe.msgprint("Test");
		var d = locals[dt][dn];
		if(d.account) {
			if(!frm.doc.company) frappe.throw(__("Please select Company first"));
			if(!frm.doc.posting_date) frappe.throw(__("Please select Posting Date first"));

			return frappe.call({
				// method: "erpnext.accounts.doctype.journal_entry.journal_entry.get_account_balance_and_party_type",
				method: "addons.custom_standard.custom_journal_entry.get_account_balance_and_party_type_custom",				
				args: {
					party: d.party,
					account: d.account,
					date: frm.doc.posting_date,
					company: frm.doc.company,
					debit: flt(d.debit_in_account_currency),
					credit: flt(d.credit_in_account_currency),
					exchange_rate: d.exchange_rate,
					cost_center: d.cost_center,
					reference_type: d.reference_type || ""
				},
				callback: function(r) {
					if(r.message) {
						$.extend(d, r.message);
						erpnext.journal_entry.set_debit_credit_in_company_currency(frm, dt, dn);
						refresh_field('accounts');
					}
				}
			});
		}
	},
});