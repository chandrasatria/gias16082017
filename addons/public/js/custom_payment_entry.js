frappe.ui.form.on('Payment Entry', {
	refresh: function(frm) {
		if(frm.doc.__islocal){
			if(frm.doc.payment_type == "Receive"){
				frappe.meta.get_docfield("Payment Entry", "naming_series", frm.doc.name).options = ["PYI-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "PYI-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.payment_type == "Pay"){
				frappe.meta.get_docfield("Payment Entry", "naming_series", frm.doc.name).options = ["PYO-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "PYO-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.payment_type == "Internal Transfer"){
				frappe.meta.get_docfield("Payment Entry", "naming_series", frm.doc.name).options = ["ITS-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "ITS-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			
		}
	},
	payment_type:function(frm){
		if(frm.doc.__islocal){
			if(frm.doc.payment_type == "Receive"){
				frappe.meta.get_docfield("Payment Entry", "naming_series", frm.doc.name).options = ["PYI-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "PYI-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.payment_type == "Pay"){
				frappe.meta.get_docfield("Payment Entry", "naming_series", frm.doc.name).options = ["PYO-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "PYO-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
			else if(frm.doc.payment_type == "Internal Transfer"){
				frappe.meta.get_docfield("Payment Entry", "naming_series", frm.doc.name).options = ["ITS-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"];
		    	frm.doc.naming_series = "ITS-GIAS-{{singkatan}}-{tax}-.YY.-.MM.-.#####"
		    	frm.refresh_fields();
			}
		}
	}
})