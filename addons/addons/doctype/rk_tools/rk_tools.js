// Copyright (c) 2021, das and contributors
// For license information, please see license.txt

frappe.ui.form.on('RK Tools', {
	get_movable_gl: function(frm) {
		
		
		var filter_by = ""
		var from_date = ""
		var to_date = ""
		if(!(frm.doc.account)){
			frappe.throw("Please enter account for filter.")
		}

		if(!(frm.doc.from_date && frm.doc.to_date)){
			frappe.throw("Please enter from date and to date for date range filter.")
		}
		else{
			from_date = frm.doc.from_date
			to_date = frm.doc.to_date
			var array_branch = []
			var array_account = []
			for(var row in frm.doc.branch1){
				array_branch.push(frm.doc.branch1[row].branch)
			}
			for(var row in frm.doc.account){
				array_account.push(frm.doc.account[row].account)
			}
			frappe.call({
		        method: "addons.addons.doctype.rk_tools.rk_tools.get_gl_from_date",
		        args: {
					from_date : from_date,
					to_date : to_date,
					array_branch : array_branch,
					array_account : array_account,
					tax : frm.doc.tax_or_non_tax
		        },
		        freeze: true,
		        callback: function (hasil) {
		          if (hasil) {
		            frm.doc.gl_movement = [];
		            for (var baris in hasil.message) {
		              var d = frappe.model.add_child(cur_frm.doc, "RK Tools GL Move", "gl_movement");

		              d.document_type = hasil.message[baris].voucher_type;
		              d.document_no = hasil.message[baris].voucher_no;
		              d.document_account = hasil.message[baris].doc_account;
		              d.rk_account = hasil.message[baris].account;
		              d.value = hasil.message[baris].debit;
		              d.remarks = hasil.message[baris].remarks;
		              d.gl_entry_name = hasil.message[baris].name;
		              d.gl_entry_branch = hasil.message[baris].gl_entry_branch;
		              d.target_cabang = hasil.message[baris].lcg
		              
		            }
		            cur_frm.refresh_fields();
		          }
		        },
			});
		}
	},
	rk_type: function(frm){
		frm.doc.gl_movement = []
		frm.doc.refresh_fields()
	}
});


frappe.ui.form.on('RK Tools GL Move', {
	cancel_je: function(frm,cdt,cdn){
		if(!frm.doc.__islocal){
			var d = locals[cdt][cdn]
			if(d.nomor_je_pusat){
				frappe.call({
			        method: "addons.addons.doctype.rk_tools.rk_tools.get_je_to_cancel",
			        args: {
						no_doc: d.nomor_je_pusat
			        },
			        freeze: true,
			        callback: function (hasil) {
			          frappe.throw(hasil)
			        },
				});	
			}
			else{
				frappe.throw("No Journal Entry to be cancelled.")
			}
			
		}
	}
})

cur_frm.add_fetch("target","accounting_dimension","branch")
cur_frm.add_fetch("target","accounting_dimension","target_accounting_dimension")