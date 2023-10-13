frappe.ui.form.on('Exchange Rate Revaluation', {
	refresh: function(frm) {
		if(frm.doc.docstatus==1) {
			frm.remove_custom_button('Journal Entry','Create')
			frappe.call({
				method: 'check_journal_entry_condition',
				doc: frm.doc,
				callback: function(r) {
					if (r.message) {
						frm.add_custom_button(__('Journal Entry'), function() {
							return frm.events.make_jv_custom(frm);
						}, __('Create'));
					}
				}
			});
		}
	},
	make_jv_custom : function(frm) {
		frappe.call({
			method: "addons.custom_standard.custom_exchange_rate_revaluation.custom_make_jv_entry",
			args: {'name':frm.doc.name},
			callback: function(r){
				if (r.message) {
					var doc = frappe.model.sync(r.message)[0];
					frappe.set_route("Form", doc.doctype, doc.name);
				}
			}
		});
	}
})