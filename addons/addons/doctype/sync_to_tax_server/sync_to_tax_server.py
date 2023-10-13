# Copyright (c) 2021, das and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils.background_jobs import enqueue

class SynctoTaxServer(Document):
	def onload(self):
		check = 0
		from frappe.core.page.background_jobs.background_jobs import get_info
		enqueued_jobs = [d.get("job_name") for d in get_info()]
		for row in enqueued_jobs:
			if str(row) == "sync_to_tax_server":
				check = 1


		if check == 1:
			self.sync_status = "Ongoing"
			frappe.db.sql(""" UPDATE `tabSingles` SET value = "Ongoing" WHERE doctype = "Sync to Tax Server" AND field = "sync_status" """)
		else:
			self.sync_status = "Idle"
			frappe.db.sql(""" UPDATE `tabSingles` SET value = "Idle" WHERE doctype = "Sync to Tax Server" AND field = "sync_status" """)


	@frappe.whitelist()
	def en_sync_to_tax_server(self):
		check = 0
		from frappe.core.page.background_jobs.background_jobs import get_info
		enqueued_jobs = [d.get("job_name") for d in get_info()]
		for row in enqueued_jobs:
			if str(row) == "sync_to_tax_server":
				check = 1

		if check == 0:
			enqueue(method="addons.custom_standard.temp_method.preparing_backup",timeout=24000,job_name="sync_to_tax_server")
			frappe.db.sql(""" UPDATE `tabSingles` SET value = "Started" WHERE doctype = "Sync to Tax Server" AND field = "sync_status" """)
			self.sync_status = "Started"
			frappe.msgprint("Sync to Tax is on progress.")
		else:
			frappe.throw(str("Sync to Tax Server is still ongoing, please wait while the method complete."))
