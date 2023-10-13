frappe.ui.form.on('Item', {
	onload(frm){
		frm.set_query("business_group", function(){
	        return {
	            "filters": {
	               	"disabled": 0
	            }   
	        }
	    });
	},
	item_group(frm) {
		if(frm.doc.__islocal){
			if (frm.doc.item_group){
	    		frappe.db.get_value("Item Group", {
					"name": frm.doc.item_group
				}, ['code', 'parent_code'], function (value) {
					if(!(value.code) || !(value.parent_code)){
						frappe.throw("Please insert Code or Parent Code into the Item Group " + frm.doc.item_group)
						frm.doc.item_code = ""
						frm.refresh_fields()
					}
					else{
						var tax = "P"
						if(frm.doc.tax_or_non_tax == "Non Tax"){
							tax = "N"
						}
						frm.doc.item_code = value.code + "-" + value.parent_code + "-" + tax + "-" + ".######"
						frm.refresh_fields()
					}
				});
		    }
		}
	},
	tax_or_non_tax(frm) {
		if(frm.doc.__islocal){
			if (frm.doc.item_group){
	    		frappe.db.get_value("Item Group", {
					"name": frm.doc.item_group
				}, ['code', 'parent_code'], function (value) {
					if(!(value.code) || !(value.parent_code)){
						frappe.throw("Please insert Code or Parent Code into the Item Group " + frm.doc.item_group)
					}
					else{
						var tax = "P"
						if(frm.doc.tax_or_non_tax == "Non Tax"){
							tax = "N"
						}
						frm.doc.item_code = value.code + "-" + value.parent_code + "-" + tax + "-" + ".######"
						frm.refresh_fields()
					}
				});
		    }
		}
	},
});

cur_frm.fields.forEach(function(l){ 
	if(cur_frm.doc.__islocal == 0){
		if(frappe.user_roles.indexOf("SPV ACC Cabang") > -1)
		{	console.log("1")
			cur_frm.set_df_property(l.df.fieldname, "read_only", 1); 
		}
		else{
			cur_frm.set_df_property(l.df.fieldname, "read_only", 1); 
		}
	}
})


