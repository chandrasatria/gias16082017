frappe.ui.form.on('Customer', {
	// no_ktp(frm) {
	// 	if(frm.doc.no_ktp){
	// 		if(frm.doc.no_ktp.length < 16){
	// 			frappe.msgprint("Your KTP Number needs to be 16 digits.")
	// 		}
	// 	}
	// },
	// tax_id(frm) {
	// 	if(frm.doc.tax_id){
	// 		if(frm.doc.tax_id.length < 15){
	// 			frappe.msgprint("Your Tax Number needs to be 15 digits.")
	// 		}
	// 	}
	// },
	validate(frm) {
		if(frm.doc.no_ktp){
			if(frm.doc.no_ktp.length < 16 || frm.doc.no_ktp.length > 16 ){
				frappe.throw("Your KTP Number needs to be 16 digits.")
			}
		}
		if(frm.doc.tax_id){
			if(frm.doc.tax_id.replace(/[^0-9a-z]/gi, '').length < 15 || frm.doc.tax_id.replace(/[^0-9a-z]/gi, '').length > 15){
				frappe.throw("Your Tax Number needs to be 15 digits.")
			}
		}
		// if(!(frm.doc.no_ktp || frm.doc.tax_id)){
		// 	frappe.throw("One of the KTP Number or Tax Number is mandatory, please input either one.")
		// }
	},
	onload(frm){
		if(!frm.doc.__islocal){
			frm.set_df_property("credit_limits", "read_only", 1);
		}
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
		
		frm.set_query("business_group", function(){
	        return {
	            "filters": {
	               	"disabled": 0
	            }   
	        }
	    });
	}
})
