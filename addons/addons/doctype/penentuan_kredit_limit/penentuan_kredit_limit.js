frappe.ui.form.on('Penentuan Kredit Limit', {
	refresh: function(frm){
		frm.set_query('customer', function(doc) {
			return {
				query: "addons.custom_standard.custom_customer.get_all_with_no_business_group",
			};
		})
	},
	onload:function(frm){
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
	pilihan1: function(frm) {
		if(frm.doc.pilihan1 == "< 5 Tahun"){
		    frm.doc.poin_1 = 1
		}
		else if(frm.doc.pilihan1 == "5 - 10 Tahun"){
		    frm.doc.poin_1 = 3
		}
		else if(frm.doc.pilihan1 == "> 10 Tahun"){
		    frm.doc.poin_1 = 5
		}
		calculate_poin(frm)
	},
	pilihan2: function(frm) {
    	if(frm.doc.pilihan2 == "1 - 5 Jenis"){
    	    frm.doc.poin_2 = 1
    	}
    	else if(frm.doc.pilihan2 == "6 - 10 Jenis"){
    	    frm.doc.poin_2 = 3
    	}
    	else if(frm.doc.pilihan2 == "> 10 Jenis"){
    	    frm.doc.poin_2 = 5
    	}
    	calculate_poin(frm)
    },
    pilihan3: function(frm) {
    	if(frm.doc.pilihan3 == "< 25 tahun"){
    	    frm.doc.poin_3 = 1
    	}
    	else if(frm.doc.pilihan3 == "26 - 39 tahun"){
    	    frm.doc.poin_3 = 3
    	}
    	else if(frm.doc.pilihan3 == "> 40 tahun"){
    	    frm.doc.poin_3 = 5
    	}
    	calculate_poin(frm)
    },
    pilihan4: function(frm) {
		if(frm.doc.pilihan4 == "Tidak"){
		    frm.doc.poin_4 = 1
		}
		else if(frm.doc.pilihan4 == "Ya"){
		    frm.doc.poin_4 = 5
		}
		calculate_poin(frm)
	},
	pilihan5: function(frm) {
		if(frm.doc.pilihan5 == "Sewa"){
		    frm.doc.poin_5 = 1
		}
		else if(frm.doc.pilihan5 == "Milik Pribadi"){
		    frm.doc.poin_5 = 5
		}
		calculate_poin(frm)
	},
	pilihan6: function(frm) {
		if(frm.doc.pilihan6 == "Tidak Ada"){
		    frm.doc.poin_6 = 1
		}
		else if(frm.doc.pilihan6 == "Ada"){
		    frm.doc.poin_6 = 5
		}
		calculate_poin(frm)
	},
	pilihan7: function(frm) {
		if(frm.doc.pilihan7 == "Tidak Ada"){
		    frm.doc.poin_7 = 0
		}
		else if(frm.doc.pilihan7 == "1 - 2 unit"){
		    frm.doc.poin_7 = 1
		}
		else if(frm.doc.pilihan7 == "3 - 5 unit"){
		    frm.doc.poin_7 = 3
		}
		else if(frm.doc.pilihan7 == "> 5 unit"){
		    frm.doc.poin_7 = 5
		}
		calculate_poin(frm)
	},
	pilihan8: function(frm) {
		if(frm.doc.pilihan8 == "Tidak ada" || frm.doc.pilihan8 == "Tidak Ada"){
		    frm.doc.poin_8 = 1
		}
		else if(frm.doc.pilihan8 == "2 cabang"){
		    frm.doc.poin_8 = 3
		}
		else if(frm.doc.pilihan8 == "> 3 cabang"){
		    frm.doc.poin_8 = 5
		}
		calculate_poin(frm)
	},
	pilihan9: function(frm) {
		if(frm.doc.pilihan9 == "1 - 10 orang"){
		    frm.doc.poin_9 = 1
		}
		else if(frm.doc.pilihan9 == "11 - 15 orang"){
		    frm.doc.poin_9 = 3
		}
		else if(frm.doc.pilihan9 == "16 orang"){
		    frm.doc.poin_9 = 5
		}
		calculate_poin(frm)
	},
	pilihan10: function(frm) {
		if(frm.doc.pilihan10 == "< 5 Supplier"){
		    frm.doc.poin_10 = 1
		}
		else if(frm.doc.pilihan10 == "6 -9 Supplier"){
		    frm.doc.poin_10 = 3
		}
		else if(frm.doc.pilihan10 == "> 10 Supplier"){
		    frm.doc.poin_10 = 5
		}
		calculate_poin(frm)
	},
	perubahan_kredit_limit:function(frm){
		if(frm.doc.perubahan_kredit_limit){
			frm.doc.limit_disetujui = frm.doc.perubahan_kredit_limit
			frm.refresh_fields()
		}
	},
	term_of_payment:function(frm){
		if(frm.doc.term_of_payment){
			frm.doc.top_disetujui = frm.doc.term_of_payment
			frm.refresh_fields()
		}
	},
	customer: function(frm){
		if(frm.doc.customer){
			frappe.call({
				method : "addons.custom_standard.custom_customer.get_credit_limit",
				args : {
					"customer" : frm.doc.customer
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						frm.doc.credit_limit_awal = hasil.message
						cur_frm.refresh_fields()						
					}
				}
			})
			frappe.call({
				method : "addons.custom_standard.custom_customer.get_overdue_and_credit_limit",
				args : {
					"customer" : frm.doc.customer
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						console.log(hasil["message"][0])
						cur_frm.doc.overdue_percentage = hasil["message"][0]
						if(hasil["message"][1]){
							cur_frm.doc.customer_credit_limit_available = hasil["message"][1]
						}
						else{
							cur_frm.doc.customer_credit_limit_available = 0
						}
						cur_frm.refresh_fields()
					}
				}
			})
			frappe.call({
				method : "addons.custom_standard.custom_customer.get_address_contact_from_customer",
				args : {
					"customer" : frm.doc.customer
				},
				freeze: true,
				callback : function(hasil){
					if(hasil){
						frm.doc.contact_person = hasil["message"][0].contact
						frm.doc.address = hasil["message"][0].address
						frm.doc.handphone = hasil["message"][0].mobile_no
						frm.doc.term_of_payment = hasil["message"][0].payment_terms
						frm.doc.top_disetujui = hasil["message"][0].payment_terms
						cur_frm.refresh_fields()						

					}
				}
			})
		}
	}
})

function calculate_poin(frm){
    var poin_1 = 0
    var poin_2 = 0
    var poin_3 = 0
    var poin_4 = 0
    var poin_5 = 0
    var poin_6 = 0
    var poin_7 = 0
    var poin_8 = 0
    var poin_9 = 0
    var poin_10 = 0
    
    if(frm.doc.poin_1){
        poin_1 = frm.doc.poin_1
    }
    if(frm.doc.poin_2){
        poin_2 = frm.doc.poin_2
    }
    if(frm.doc.poin_3){
        poin_3 = frm.doc.poin_3
    }
    if(frm.doc.poin_4){
        poin_4 = frm.doc.poin_4
    }
    if(frm.doc.poin_5){
        poin_5 = frm.doc.poin_5
    }
    if(frm.doc.poin_6){
        poin_6 = frm.doc.poin_6
    }
    if(frm.doc.poin_7){
        poin_7 = frm.doc.poin_7
    }
    if(frm.doc.poin_8){
        poin_8 = frm.doc.poin_8
    }
    if(frm.doc.poin_9){
        poin_9 = frm.doc.poin_9
    }
    if(frm.doc.poin_10){
        poin_10 = frm.doc.poin_10
    }
    
    frm.doc.total_poin = poin_1+poin_2+poin_3+poin_4+poin_5+poin_6+poin_7+poin_8+poin_9+poin_10  
        
    if(frm.doc.total_poin >= 36){
        frm.doc.adjustment = "Low Risk"
    }
    else if(frm.doc.total_poin >= 21){
        frm.doc.adjustment = "Medium Risk"
    }
    else{
        frm.doc.adjustment = "High Risk"
    }
    
    frm.refresh_fields()
}

cur_frm.add_fetch("customer","customer_name","customer_name")
cur_frm.add_fetch("business_group","credit_limit","credit_limit_awal")
cur_frm.add_fetch("business_group","term_of_payment","term_of_payment")
cur_frm.add_fetch("business_group","term_of_payment","top_disetujui")