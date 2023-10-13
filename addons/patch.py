import frappe
import time
import os
from frappe.utils import flt, add_months, cint, nowdate, getdate, today, date_diff, month_diff, add_days, get_last_day, get_datetime
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from addons.custom_standard.custom_stock_entry import custom_distribute_additional_costs,repair_gl_entry_tanpa_sl

from erpnext.selling.doctype.customer.customer import get_credit_limit, get_customer_outstanding
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from frappe.model.naming import make_autoname, revert_series_if_last

@frappe.whitelist()
def save_doctype():
    
    lis_field = frappe.db.sql(""" SELECT name FROM `tabProperty Setter` 
        WHERE name LIKE "%precision%" and doc_type != "Journal Entry Account" and (value = 3 or value = 5) """)
    for row_field in lis_field:
        doc = frappe.get_doc("Property Setter",row_field[0])
        doc.delete()
        print(doc.name)
        frappe.db.commit()


@frappe.whitelist()
def update_tnc():
    list_pi = ["PI-1-23-07-01525"]

    from bs4 import BeautifulSoup
    import six    
    for row in list_pi:
        pi_doc = frappe.get_doc("Purchase Invoice", row)
        soup = BeautifulSoup(pi_doc.terms)
        pi_doc.remarks = soup.get_text(separator="\n")
        pi_doc.db_update()

@frappe.whitelist()
def item_uom():
    list_item= frappe.db.sql(""" SELECT parent,COUNT(NAME) AS c
        FROM `tabUOM Conversion Detail`
        GROUP BY parent
        HAVING c > 1 """)

    for row in list_item:
        item_doc = frappe.get_doc("Item", row[0])
        list_uom = []
        hasil_baris = []

        for row_uom in item_doc.uoms:
            if row_uom.uom not in list_uom:
                list_uom.append(row_uom.uom)
                hasil_baris.append(row_uom)

        item_doc.uoms = hasil_baris
        item_doc.save()
        print(row[0])

@frappe.whitelist()
def insert_cron():
    new = frappe.get_doc({"__islocal":1,"name":"addons.custom_standard.view_ledger_create.gelondongan_gl_custom","owner":"Administrator","creation":"2022-03-26 01:02:27.581653","modified":"2022-03-26 01:02:27.581653","modified_by":"Administrator","idx":63,"docstatus":0,"stopped":0,"method":"addons.custom_standard.view_ledger_create.gelondongan_gl_custom","frequency":"Cron","cron_format":"0/5 * * * *","last_execution":"2023-07-27 15:45:05.909445","create_log":0,"doctype":"Scheduled Job Type","__last_sync_on":"2023-07-27T08:57:56.959Z"})
    new.save()

@frappe.whitelist()
def patch_je():
    list_je = frappe.db.sql("""SELECT je.name, COUNT(gl.name) AS jumlah FROM `tabJournal Entry` je 
    JOIN `tabGL Entry` gl ON gl.voucher_no = je.name
    WHERE je.docstatus = 1
    GROUP BY je.name
    HAVING jumlah = 1 """)
    for row in list_je:
        name = row[0]
        repair_gl_entry_tanpa_sl("Journal Entry", name)
        print(name)
        from addons.custom_standard.view_ledger_create import create_gl_custom_journal_entry_by_name
        create_gl_custom_journal_entry_by_name(name)

@frappe.whitelist()
def make_new_site():

    doc_baru = frappe.new_doc("Branch")
    doc_baru.branch = "AMBON"
    try:
        doc_baru.save()
    except:
        pass

    doc_baru = frappe.new_doc("List Company GIAS")
    doc_baru.nama_company = "GIAS AMBON"
    doc_baru.singkatan_cabang = "AMB"
    doc_baru.accounting_dimension = "AMBON"
    doc_baru.save()

    doc_baru = frappe.new_doc("Branch")
    doc_baru.branch = "BUNGO"
    try:
        doc_baru.save()
    except:
        pass

    doc_baru = frappe.new_doc("List Company GIAS")
    doc_baru.nama_company = "GIAS BUNGO"
    doc_baru.singkatan_cabang = "MRB"
    doc_baru.accounting_dimension = "BUNGO"
    doc_baru.save()

@frappe.whitelist()
def patch_stock_entry():
    list_si = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE voucher_type = "Stock Entry"
        and posting_date >= "2022-06-01"
        and posting_date <= "2022-06-31"
        GROUP BY voucher_no
        ORDER BY posting_date
     """)
    for row in list_si:
        si_doc = frappe.get_doc("Stock Entry", row[0])
        repair_gl_entry_tanpa_sl(si_doc.doctype,si_doc.name)
        print(si_doc.name)



@frappe.whitelist()
def enqueue_patch_pure_rate():
    enqueued_method = "addons.patch.patch_pure_rate"
    frappe.enqueue(method=enqueued_method,timeout=7200, queue='long')

@frappe.whitelist()
def patch_pure_rate():
    list_si = frappe.db.sql(""" SELECT parent FROM `tabSales Invoice Item` WHERE net_rate = pure_rate GROUP BY parent """)
    
    for row_doc in list_si:
        doc = frappe.get_doc("Sales Invoice", row_doc[0])
        total_pure = 0
        for row in doc.items:
            if row.pure_rate == row.net_rate:
                row.pure_amount = row.net_amount
                row.db_update()
            total_pure = total_pure + row.pure_amount

        doc.pure_total_amount = total_pure
        doc.db_update()
        print(row_doc[0])
        frappe.db.commit()

@frappe.whitelist()
def patch_event_producer():
    lis_ep = frappe.db.sql(""" SELECT name FROM `tabEvent Producer` WHERE name LIKE "%pusat%" """)
    for row in lis_ep:
        doc = frappe.get_doc("Event Producer", row[0])
        for row_item in doc.producer_doctypes:
            if row_item.ref_doctype == "Material Request":
                row_item.condition = row_item.condition.replace(' or doc.workflow_state == "Waiting Deputy GM Branch"','')

        doc.save()


@frappe.whitelist()
def patch_item():
    frappe.db.sql(""" UPDATE `tabItem` SET disabled = 0 WHERE name IN ("C-GRAN-P-000047","C-GRAN-P-000046","C-GRAN-P-000045") """)

@frappe.whitelist()
def patch_terms():
    list_pi = frappe.db.sql(""" SELECT NAME,terms,remarks FROM `tabPurchase Invoice` WHERE type_pembelian = "Non Inventory" """)
    for row in list_pi:
        doc = frappe.get_doc("Purchase Invoice", row[0])
        if doc.remarks:
            list_view = frappe.db.sql(""" SELECT name FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(row[0]))
            for row_view in list_view:
                doct = frappe.get_doc("GL Entry", row_view[0])
                doct.remarks = doc.remarks
                doct.db_update()

        print(row[0])


@frappe.whitelist()
def patch_report():
    doc = frappe.get_doc("Report","View Ledger by Detail")
    doc.disable_prepared_report = 0
    doc.save()

@frappe.whitelist()
def renameminus():
    frappe.db.sql(""" UPDATE `tabSales Order Item` SET item_name = REPLACE(item_name,"–","-")
        WHERE item_name LIKE "%–%" """)
    frappe.db.sql(""" UPDATE `tabDelivery Note Item` SET item_name = REPLACE(item_name,"–","-")
        WHERE item_name LIKE "%–%" """)
    frappe.db.sql(""" UPDATE `tabSales Invoice Item` SET item_name = REPLACE(item_name,"–","-")
        WHERE item_name LIKE "%–%" """)
    frappe.db.sql(""" UPDATE `tabPurchase Order Item` SET item_name = REPLACE(item_name,"–","-")
        WHERE item_name LIKE "%–%" """)
    frappe.db.sql(""" UPDATE `tabPurchase Receipt Item` SET item_name = REPLACE(item_name,"–","-")
        WHERE item_name LIKE "%–%" """)
    frappe.db.sql(""" UPDATE `tabPurchase Invoice Item` SET item_name = REPLACE(item_name,"–","-")
        WHERE item_name LIKE "%–%" """)
    frappe.db.sql(""" UPDATE `tabStock Entry Detail` SET item_name = REPLACE(item_name,"–","-")
        WHERE item_name LIKE "%–%" """)
    frappe.db.sql(""" UPDATE `tabMaterial Request Item` SET item_name = REPLACE(item_name,"–","-")
        WHERE item_name LIKE "%–%" """)



@frappe.whitelist()
def patch_custom_field():
    list_cf = frappe.db.sql(""" SELECT name FROM `tabCustom Field` where name LIKE "%pure%" """)
    for row in list_cf:
        cf = frappe.get_doc("Custom Field", row[0])
        cf.options = "currency"
        cf.save()
        print(cf.name)

@frappe.whitelist()
def patch_customer():
    list_cu = frappe.db.sql(""" SELECT name FROM `tabSales Invoice` """)
    for row in list_cu:
        frappe.rename_doc("Customer", row[0], str(row[0]).replace("TUBTM","TU-BTM"))
        print(row[0])
        frappe.db.commit()

@frappe.whitelist()
def patch_si():
    list_si = frappe.db.sql(""" 
        SELECT name FROM `tabSales Invoice` 
        WHERE OWNER = "Administrator"
        AND DATE(creation) = "2023-06-10" and docstatus = 0""")
    for row in list_si:
        si_doc = frappe.get_doc("Sales Invoice", row[0])
        si_doc.submit()
        print(row[0])
        frappe.db.commit()


@frappe.whitelist()
def item_group():
    if frappe.get_doc("Company","GIAS").server == "Cabang":
        frappe.rename_doc("Item Group","GLASWOOL ITEM","GLASSWOOL ITEM")

@frappe.whitelist()
def patch_pesan_rk():
    lis_rk = frappe.db.sql(""" 
        SELECT jea.parent FROM `tabJournal Entry Account` jea
        JOIN `tabJournal Entry` je ON je.name = jea.parent
        WHERE
        jea.`user_remark` IS NULL
        AND
        je.`remark` LIKE "%GL Move%"
        GROUP BY jea.parent """)

    for row in lis_rk:
        doc_je = frappe.get_doc("Journal Entry", row[0])
        rema = doc_je.user_remark
        for row_acc in doc_je.accounts:
            row_acc.user_remark = rema
            row_acc.db_update()

        print(row[0])


@frappe.whitelist()
def rename_dong():
    if frappe.get_doc("Company","GIAS").server == "Cabang":
        print(frappe.get_doc("Company","GIAS").nama_cabang)
        frappe.rename_doc("Item Group","Z","CORNICE COMPOUND NON KNAUF")
        doc = frappe.get_doc("Item Group","CORNICE COMPOUND NON KNAUF")
        doc.code = "Z"
        doc.parent_code = "OTHE"
        doc.save()
        print("1")

@frappe.whitelist()
def patch_sales_invoice_tanggal():
    si_list = frappe.db.sql(""" SELECT name FROM `tabSales Invoice`
    WHERE name IN ("SI-GIAS-SKB-1-23-04-00068",
"SI-GIAS-SKB-1-23-04-00069") """)

    for row in si_list:
        si_doc = frappe.get_doc("Sales Invoice",row[0])
        for si_item in si_doc.items:
            if si_item.delivery_note:
                dn_doc = frappe.get_doc("Delivery Note", si_item.delivery_note)
                tanggal_dn = dn_doc.posting_date

                frappe.db.sql(""" UPDATE `tabSales Invoice` SET posting_date = "{}" WHERE name = "{}" """.format(tanggal_dn,si_doc.name))
                frappe.db.sql(""" UPDATE `tabGL Entry` SET posting_date = "{}" WHERE voucher_no = "{}" """.format(tanggal_dn,si_doc.name))
                frappe.db.sql(""" UPDATE `tabGL Entry Custom` SET posting_date = "{}" WHERE no_voucher = "{}" """.format(tanggal_dn,si_doc.name))
                frappe.db.commit()
                print(si_doc.name)
            else:
                frappe.throw("FAIL")


@frappe.whitelist()
def check_item_group():
    listnya = frappe.db.sql(""" SELECT ti.name,ti.item_group,ti.`parent_item_group`, tig.`parent_item_group`
FROM `tabItem` ti
JOIN `tabItem Group` tig ON tig.name = ti.item_group
WHERE ti.parent_item_group != tig.`parent_item_group` """)

    for row in listnya:
        item_doc = frappe.get_doc("Item", row[0])
        item_doc.parent_item_group = str(row[2])
        item_doc.db_update()
        print(str(item_doc.name))

@frappe.whitelist()
def create_gl_custom_expense_claim():
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
    and voucher_type = "Expense Claim" 
    and voucher_no not in (select no_voucher FROM `tabGL Entry Custom`)
    GROUP BY voucher_no """)
    for nomor_doc in doc_list:
        self = frappe.get_doc("Expense Claim", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(self.name))

        for baris_query in gl_list:
            if frappe.utils.flt(baris_query[2]) > 0:
                nyari = 0
                for row_expense in self.expenses:
                    exp_typ = frappe.get_doc("Expense Claim Type",row_expense.expense_type)
                    account = exp_typ.accounts[0].default_account
                    if account == baris_query[1]:
                        nyari = 1
                        sle_new = frappe.new_doc("GL Entry Custom")
                        sle_new.update({
                            "posting_date": baris_query[0],
                            "account": baris_query[1],
                            "debit": row_expense.sanctioned_amount,
                            "credit": baris_query[3],
                            "party_type": baris_query[4],
                            "party": baris_query[5],
                            "remarks": str(row_expense.get("description")) + "|" + str(row_expense.get("user_remark")) ,
                            "doc_remarks": self.remark,
                            "voucher_type":baris_query[7],
                            "no_voucher":baris_query[8],
                            "branch": baris_query[10],
                            "cost_center": baris_query[11],
                            "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                        })  
                        sle_new.save()

                if nyari == 0:
                    sle_new = frappe.new_doc("GL Entry Custom")
                    sle_new.update({
                        "posting_date": baris_query[0],
                        "account": baris_query[1],
                        "debit": baris_query[2],
                        "credit": baris_query[3],
                        "party_type": baris_query[4],
                        "party": baris_query[5],
                        "remarks": baris_query[6],
                        "doc_remarks": self.remark,
                        "voucher_type":baris_query[7],
                        "no_voucher":baris_query[8],
                        "branch": baris_query[10],
                        "cost_center": baris_query[11],
                        "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                    })  
                    sle_new.save()
            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks": self.remark,
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                })  
                sle_new.save()

        print(nomor_doc[0])
        frappe.db.commit()



@frappe.whitelist()
def create_gl_custom_stock_entry():
    doc_list = frappe.db.sql(""" SELECT voucher_no FROM `tabGL Entry` WHERE is_cancelled = 0
    and voucher_type = "Stock Entry" 
    and voucher_no not in (select no_voucher FROM `tabGL Entry Custom`)
    GROUP BY voucher_no """)
    for nomor_doc in doc_list:
        self = frappe.get_doc("Stock Entry", nomor_doc[0])
        frappe.db.sql(""" DELETE FROM `tabGL Entry Custom` WHERE no_voucher = "{}" """.format(self.name))
        gl_list = frappe.db.sql(""" 
                SELECT posting_date,
                 account,
                 debit,
                 credit,
                 party_type,
                 party,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', 1)),
                 voucher_type,
                 voucher_no,
                 TRIM(SUBSTRING_INDEX(remarks, 'Note:', -1)),
                 branch,
                 cost_center,
                 name 
                 FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(self.name))

        for baris_query in gl_list:
            self = frappe.get_doc("Purchase Invoice", baris_query[8])
                
            pakai_di_item = 0
            for baris in self.items:
                if baris.expense_account == baris_query[1]:
                    pakai_di_item = 1

            if pakai_di_item == 1:
                if baris_query[8] not in list_transaction:
                    list_transaction.append(baris_query[8])
                    grand_total = self.rounded_total if (self.rounding_adjustment and self.rounded_total) else self.grand_total
                    base_grand_total = flt(self.base_rounded_total if (self.base_rounding_adjustment and self.base_rounded_total)
                        else self.base_grand_total, self.precision("base_grand_total")) 

                    list_account = []
                    item_remark = ""
                    for item in self.get("items"):

                        if item.expense_account not in list_account:
                            if filters.get("nama_account"):
                                if filters.get("nama_account") == item.expense_account:
                                    list_account.append(item.expense_account)
                            else:
                                list_account.append(item.expense_account)

                        sle = {}

                        expense_account = item.expense_account
                        if item.purchase_receipt and frappe.get_doc("Item",item.item_code).is_stock_item:
                            self.stock_received_but_not_billed = self.get_company_default("stock_received_but_not_billed")
                            expense_account = self.stock_received_but_not_billed

                        if filters.get("nama_account"):

                            if filters.get("nama_account") == expense_account:
                                sle_new = frappe.new_doc("GL Entry Custom")
                                sle_new.update({
                                    "posting_date": self.posting_date,
                                    "account": expense_account,
                                    "debit": flt(item.base_net_amount + item.item_tax_amount, item.precision("base_net_amount")),
                                    "credit": 0 ,
                                    "remarks": item.user_remark,
                                    "voucher_type":"Purchase Invoice",
                                    "no_voucher": self.name,
                                    "item_code" : item.item_code,
                                    "item_name": item.item_name,
                                    "branch": item.branch,
                                    "cost_center": item.cost_center,
                                    "tax_or_non_tax": self.tax_or_non_tax,
                                    "doc_remarks":self.remark
                                })  
                                sle_new.save()
                        else:
                            sle_new = frappe.new_doc("GL Entry Custom")
                            sle.update({
                                "posting_date": self.posting_date,
                                "account": expense_account,
                                "debit": flt(item.base_net_amount + item.item_tax_amount, item.precision("base_net_amount")),
                                "credit": 0 ,
                                "remarks": item.user_remark,
                                "voucher_type":"Purchase Invoice",
                                "no_voucher": self.name,
                                "item_code" : item.item_code,
                                "item_name": item.item_name,
                                "branch": item.branch,
                                "cost_center": item.cost_center,
                                "tax_or_non_tax": self.tax_or_non_tax,
                                "doc_remarks":self.remark
                            })  
                            sle_new.save()
            else:
                sle_new = frappe.new_doc("GL Entry Custom")
                sle_new.update({
                    "posting_date": baris_query[0],
                    "account": baris_query[1],
                    "debit": baris_query[2],
                    "credit": baris_query[3],
                    "party_type": baris_query[4],
                    "party": baris_query[5],
                    "remarks": baris_query[6],
                    "doc_remarks":self.remark,
                    "voucher_type":baris_query[7],
                    "no_voucher":baris_query[8],
                    "branch": baris_query[10],
                    "cost_center": baris_query[11],
                    "tax_or_non_tax": frappe.get_doc(baris_query[7], baris_query[8]).tax_or_non_tax
                })  
                sle_new.save()
            

        print(nomor_doc[0])
        frappe.db.commit()


@frappe.whitelist()
def rename_je_asset():
    je_list = frappe.db.sql(""" 
        SELECT NAME, remark,naming_series,posting_date
        FROM `tabJournal Entry` WHERE NAME LIKE "%-2-%"
        AND tax_or_non_tax = "Tax" """)

    for row in je_list:
        doc = frappe.get_doc("Journal Entry",row[0])
        company_doc = frappe.get_doc("Company", doc.company)
        list_company_gias_doc = frappe.get_doc("List Company GIAS",company_doc.nama_cabang)
        singkatan = list_company_gias_doc.singkatan_cabang
        month = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"MM")
        year = frappe.utils.formatdate(frappe.utils.getdate(doc.posting_date),"YY")

        frappe.rename_doc("Journal Entry",row[0],make_autoname("JE-GIAS-{{singkatan}}-.YY.-.MM.-".replace("{{singkatan}}",singkatan).replace(".YY.",year).replace(".MM.",month)))
        print(row[0])
        frappe.db.commit()


@frappe.whitelist()
def add_html_to_attachment():
    list_attach = frappe.db.sql(""" 
        SELECT NAME,attachment,parent 
        FROM `tabAttachment Table`
        WHERE parenttype = "Material Request" 
        AND attachment NOT LIKE "https:%"
        AND parent NOT LIKE "%HO%"
        ORDER BY parent
    """)
    for row in list_attach:
        mr = frappe.get_doc("Material Request",row[2])
        cabang = mr.cabang
        url = "https://"+check_list_company_gias(cabang)
        mr_attach = frappe.get_doc("Attachment Table",row[0])
        mr_attach.attachment = url + mr_attach.attachment
        mr_attach.db_update()

@frappe.whitelist()
def rename_je_tax():
    je_list = frappe.db.sql(""" SELECT name FROM `tabJournal Entry Tax` """)
    
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00001","journal-entry-tax-1-22-02-0001")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00002","journal-entry-tax-1-22-02-0002")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00003","journal-entry-tax-1-22-02-0003")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00004","journal-entry-tax-1-22-02-0004")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00005","journal-entry-tax-1-22-02-0005")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00006","journal-entry-tax-1-22-02-0006")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00007","journal-entry-tax-1-22-02-0007")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00008","journal-entry-tax-1-22-02-0008")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00009","journal-entry-tax-1-22-02-0009")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00010","journal-entry-tax-1-22-02-0010")

    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00011","journal-entry-tax-1-22-02-0011")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00012","journal-entry-tax-1-22-02-0012")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00013","journal-entry-tax-1-22-02-0013")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00014","journal-entry-tax-1-22-02-0014")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00015","journal-entry-tax-1-22-02-0015")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00016","journal-entry-tax-1-22-02-0016")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00017","journal-entry-tax-1-22-02-0017")
    frappe.rename_doc("Journal Entry Tax","ACC-JV-2023-00018","journal-entry-tax-1-22-02-0018")
    


@frappe.whitelist()
def check_list_company_gias(list_company_gias):
    site = ""
    if list_company_gias == "GIAS SERANG":
        site = "erp-srg.gias.co.id"
    if list_company_gias == "GIAS SPRINGHILL":
        site = "erp-pusat.gias.co.id"
    if list_company_gias == "GIAS BALI":
        site = "erp-bali.gias.co.id"
    if list_company_gias == "GIAS BALIKPAPAN":
        site = "erp-bpp.gias.co.id"
    if list_company_gias == "GIAS BANDUNG":
        site = "erp-bdg.gias.co.id"
    if list_company_gias == "GIAS BANGKA":
        site = "erp-bnk.gias.co.id"
    if list_company_gias == "GIAS BANJARMASIN":
        site = "erp-bjm.gias.co.id"
    if list_company_gias == "GIAS BENGKULU":
        site = "erp-bkl.gias.co.id"
    if list_company_gias == "GIAS BERAU":
        site = "erp-bru.gias.co.id"
    if list_company_gias == "GIAS CIREBON":
        site = "erp-crb.gias.co.id"
    if list_company_gias == "GIAS GORONTALO":
        site = "erp-gto.gias.co.id"
    if list_company_gias == "GIAS JAMBI":
        site = "erp-jbi.gias.co.id"
    if list_company_gias == "GIAS JEMBER":
        site = "erp-jbr.gias.co.id"
    if list_company_gias == "GIAS KENDARI":
        site = "erp-kdi.gias.co.id"
    if list_company_gias == "GIAS LAMPUNG":
        site = "erp-lmp.gias.co.id"
    if list_company_gias == "GIAS LINGGAU":
        site = "erp-lgu.gias.co.id"
    if list_company_gias == "GIAS MADIUN":
        site = "erp-mdu.gias.co.id"
    if list_company_gias == "GIAS MAKASAR":
        site = "erp-mks.gias.co.id"
    if list_company_gias == "GIAS MANADO":
        site = "erp-mnd.gias.co.id"
    if list_company_gias == "GIAS MEDAN":
        site = "erp-mdn.gias.co.id"
    if list_company_gias == "GIAS PALEMBANG":
        site = "erp-plg.gias.co.id"
    if list_company_gias == "GIAS PEKANBARU":
        site = "erp-pku.gias.co.id"
    if list_company_gias == "GIAS PONTIANAK":
        site = "erp-ptk.gias.co.id"
    if list_company_gias == "GIAS PURWOKERTO":
        site = "erp-pwt.gias.co.id"
    if list_company_gias == "GIAS SAMARINDA":
        site = "erp-smd.gias.co.id"
    if list_company_gias == "GIAS SEMARANG":
        site = "erp-smg.gias.co.id"
    if list_company_gias == "GIAS SERANG":
        site = "erp-srg.gias.co.id"
    if list_company_gias == "GIAS SURABAYA":
        site = "erp-sby.gias.co.id"
    if list_company_gias == "GIAS TASIK":
        site = "erp-tsk.gias.co.id"
    if list_company_gias == "GIAS TEGAL":
        site = "erp-tgl.gias.co.id"
    if list_company_gias == "GIAS YOGYAKARTA":
        site = "erp-ygy.gias.co.id"
    if list_company_gias == "GIAS LOMBOK":
        site = "erp-lop.gias.co.id"

    return site

@frappe.whitelist()
def rename_item_group():
    frappe.rename_doc("Item Group","METAL - BLUESCOPE","METAL-BLUESCOPE")

@frappe.whitelist()
def rename_je():
    frappe.rename_doc("Journal Entry","CEI-GIAS-YGY-22-02-00001","CEI-GIAS-YGY-2-22-02-00001")
    frappe.rename_doc("Journal Entry","BEI-GIAS-YGY-22-02-00002","BEI-GIAS-YGY-2-22-02-00001")
    frappe.rename_doc("Journal Entry","JEDP-GIAS-YGY-22-02-00001","JEDP-GIAS-YGY-2-22-02-00001")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00001","JE-GIAS-YGY-2-22-02-00001")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00002","JE-GIAS-YGY-2-22-02-00002")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00003","JE-GIAS-YGY-2-22-02-00003")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00004","JE-GIAS-YGY-2-22-02-00004")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00005","JE-GIAS-YGY-2-22-02-00005")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00006","JE-GIAS-YGY-2-22-02-00006")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00007","JE-GIAS-YGY-2-22-02-00007")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00008","JE-GIAS-YGY-2-22-02-00008")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00009","JE-GIAS-YGY-2-22-02-00009")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00010","JE-GIAS-YGY-2-22-02-00010")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00011","JE-GIAS-YGY-2-22-02-00011")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00012","JE-GIAS-YGY-2-22-02-00012")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00013","JE-GIAS-YGY-2-22-02-00013")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00018","JE-GIAS-YGY-2-22-02-00014")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00019","JE-GIAS-YGY-2-22-02-00015")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00022","JE-GIAS-YGY-2-22-02-00016")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00023","JE-GIAS-YGY-2-22-02-00017")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00024","JE-GIAS-YGY-2-22-02-00018")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00017","JE-GIAS-YGY-2-22-02-00019")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00021","JE-GIAS-YGY-2-22-02-00020")
    frappe.rename_doc("Journal Entry","JE-GIAS-YGY-22-02-00025","JE-GIAS-YGY-2-22-02-00021")






@frappe.whitelist()
def check_out():
    list_asset = frappe.db.sql(""" 
        SELECT NAME,tax_or_non_tax FROM `db_pusat`.`tabAsset` WHERE docstatus = 1 """)

    for row in list_asset:
        nama_asset = str(row[0])
        tax_asset = str(row[1])

        list_je = frappe.db.sql(""" 
            SELECT NAME,tax_or_non_tax,REPLACE(LEFT(remark,46),"Depreciation Entry From HO. ","") AS asset_no 
            FROM `tabJournal Entry` 
            WHERE `voucher_type` = "Depreciation Entry"
            AND remark LIKE "%ACC%" and tax_or_non_tax != "{}"
            HAVING asset_no = "{}" 
            """.format(tax_asset, nama_asset))
        for row_je in list_je:
            je_doc = frappe.get_doc("Journal Entry", row_je[0])
            je_doc.tax_or_non_tax = tax_asset
            je_doc.db_update()
            frappe.db.commit()
            print(je_doc.name)

    print(frappe.get_doc("Company","GIAS").nama_cabang)


@frappe.whitelist()
def patch_po():
    so = frappe.get_doc("Purchase Order", "PO-PEN-INV-1-22-12-00181")

@frappe.whitelist()
def patch_so_dn():
    list_so = frappe.db.sql(""" 
        SELECT
        so.name,so.`taxes_and_charges`, dn.name,dn.`taxes_and_charges`,dn.`docstatus`
        FROM `tabSales Order` so
        JOIN `tabSales Order Item` soi ON soi.parent= so.name
        JOIN `tabSales Invoice Item` dni ON dni.so_detail = soi.name
        JOIN `tabSales Invoice` dn ON dn.name = dni.parent
        WHERE 
        so.`taxes_and_charges` IS NOT NULL
        AND (dn.`taxes_and_charges` = "" OR dn.`taxes_and_charges` IS NULL)
        AND so.`total_taxes_and_charges` != dn.`total_taxes_and_charges`
        AND so.transaction_date >= "2022-12-01"
        GROUP BY dn.name
    """)

    for row in list_so:
        dn = frappe.get_doc("Sales Invoice",row[2])
        so = frappe.get_doc("Sales Order", row[0])
        
        docstatus = 0

        if dn.docstatus != 0:
            docstatus = dn.docstatus
            frappe.db.sql(""" UPDATE `tabSales Invoice` SET docstatus = 0 WHERE name = "{}" """.format(dn.name))
            frappe.db.commit()

        dn = frappe.get_doc("Sales Invoice",row[2])

        dn.taxes_and_charges = so.taxes_and_charges
        dn.set_posting_time = 1
        dn.taxes = []
        for row_so in so.taxes:
            dn.append("taxes",{
                "account_currency" : row_so.account_currency,
                "account_head" : row_so.account_head,
                "base_tax_amount" : row_so.base_tax_amount,
                "base_tax_amount_after_discount_amount" : row_so.base_tax_amount_after_discount_amount,
                "base_total" : row_so.base_total,
                "charge_type" : row_so.charge_type,
                "cost_center" : row_so.cost_center,
                "description" : row_so.description,
                "docstatus" : dn.docstatus,
                "included_in_paid_amount" : row_so.included_in_paid_amount,
                "included_in_print_rate" : row_so.included_in_print_rate,
                "rate" : row_so.rate,
                "tax_amount": row_so.tax_amount,
                "tax_amount_after_discount_amount": row_so.tax_amount_after_discount_amount,
                "total" : row_so.total,
                "branch" : row_so.branch
            })
        dn.save()

        if docstatus != 0:
            frappe.db.sql(""" UPDATE `tabSales Invoice` SET docstatus = {} WHERE name = "{}" """.format(docstatus,dn.name))
            frappe.db.sql(""" UPDATE `tabSales Invoice Item` SET docstatus = {} WHERE parent = "{}" """.format(docstatus,dn.name))
            frappe.db.sql(""" UPDATE `tabSales Taxes and Charges` SET docstatus = {} WHERE name = "{}" """.format(docstatus,dn.name))
            frappe.db.commit()
            if docstatus == 1:
                repair_gl_entry_tanpa_sl(dn.doctype, dn.name)

@frappe.whitelist()
def update_doctype():
    doc = frappe.get_doc("DocType","RK Tools GL Move")
    for row in doc.fields:
        if row.fieldname == "nomor_je_pusat":
            row.fieldtype = "Link"
            row.options = "Journal Entry"

    doc.save()


@frappe.whitelist()
def kosongkan_sinv():
    list_so = frappe.db.sql(""" 
        SELECT
        name
        FROM `tabSales Invoice`
        WHERE name IN ("SI-GIAS-HO-1-23-01-00005","SI-GIAS-HO-1-23-01-00004","SI-GIAS-HO-1-23-01-00008")
    """)

    for row in list_so:
        dn = frappe.get_doc("Sales Invoice",row[0])
        docstatus = 0

        if dn.docstatus != 0:
            docstatus = dn.docstatus
            frappe.db.sql(""" UPDATE `tabSales Invoice` SET docstatus = 0 WHERE name = "{}" """.format(dn.name))
            frappe.db.commit()

        dn = frappe.get_doc("Sales Invoice",row[0])

        dn.taxes_and_charges = ""
        dn.set_posting_time = 1
        dn.taxes = []
        dn.save()

        if docstatus != 0:
            frappe.db.sql(""" UPDATE `tabSales Invoice` SET docstatus = {} WHERE name = "{}" """.format(docstatus,dn.name))
            frappe.db.sql(""" UPDATE `tabSales Invoice Item` SET docstatus = {} WHERE parent = "{}" """.format(docstatus,dn.name))
            frappe.db.sql(""" UPDATE `tabSales Taxes and Charges` SET docstatus = {} WHERE name = "{}" """.format(docstatus,dn.name))
            frappe.db.commit()
            if docstatus == 1:
                repair_gl_entry_tanpa_sl(dn.doctype, dn.name)
@frappe.whitelist()
def patch_period():
    list_dn = frappe.db.sql( """SELECT name FROM `tabSales Invoice`
        WHERE docstatus = 1 AND name IN (
        "SI-GIAS-BKL-2-22-12-00001",
        "SI-GIAS-BKL-2-22-12-00002",
        "SI-GIAS-BKL-2-22-12-00003",
        "SI-GIAS-BKL-2-22-12-00004",
        "SI-GIAS-BKL-2-22-12-00005",
        "SI-GIAS-BKL-2-22-12-00010",
        "SI-GIAS-BKL-2-22-12-00009",
        "SI-GIAS-BKL-2-23-01-00001",
        "SI-GIAS-BRU-2-22-12-00001",
        "SI-GIAS-JBI-2-22-12-00001",
        "SI-GIAS-MDU-2-22-12-00001",
        "SI-GIAS-PNK-2-22-12-00002",
        "SI-GIAS-HO-2-22-12-00004",
        "SI-GIAS-HO-2-22-12-00005",
        "SI-GIAS-HO-2-22-12-00006",
        "SI-GIAS-HO-2-22-12-00007",
        "SI-GIAS-HO-2-22-12-00008",
        "SI-GIAS-HO-2-23-01-00001",
        "SI-GIAS-SMD-2-22-12-00007") """)
    docstatus = 1
    for row in list_dn:
        dn = frappe.get_doc("Sales Invoice",row[0])
        # frappe.db.sql(""" UPDATE `tabDelivery Note` SET docstatus = {} WHERE name = "{}" """.format(docstatus,dn.name))
        # frappe.db.sql(""" UPDATE `tabDelivery Note Item` SET docstatus = {} WHERE parent = "{}" """.format(docstatus,dn.name))
        # frappe.db.sql(""" UPDATE `tabSales Taxes and Charges` SET docstatus = {} WHERE name = "{}" """.format(docstatus,dn.name))
        # frappe.db.commit()
        repair_gl_entry("Sales Invoice",row[0])
        print(row[0])

def add_scheduler():
    frappe.get_doc({"docstatus":0,"stopped":0,"method":"addons.custom_method.cancel_prepared_report","frequency":"Daily","create_log":1,"doctype":"Scheduled Job Type"}).insert()

@frappe.whitelist()
def isi_val_rate_0():
    list_so = frappe.db.sql(""" SELECT name, item_code, warehouse, parent 
        FROM `tabSales Order Item` WHERE valuation_rate = 0 and docstatus = 1 """)
    for row in list_so:
        soi_doc = frappe.get_doc("Sales Order Item", row[0])
        so_doc = frappe.get_doc("Sales Order", row[3])
        tanggal_so = so_doc.transaction_date
        warehouse = row[2]
        val_rate = frappe.db.sql(""" SELECT valuation_rate FROM `tabStock Ledger Entry`
            WHERE item_code = '{}' AND warehouse = '{}' and posting_date <= '{}' and valuation_rate > 0
            ORDER by posting_date DESC
          """.format(row[1],warehouse, tanggal_so))

        if val_rate:
            if val_rate[0]:
                if val_rate[0][0]:
                    soi_doc.valuation_rate = val_rate[0][0]
                    soi_doc.gross_profit = flt(((soi_doc.base_rate - soi_doc.valuation_rate) * soi_doc.stock_qty), so_doc.precision("amount", soi_doc))
                    soi_doc.db_update()
                    print(row[3])
                    frappe.db.commit()

@frappe.whitelist()
def isi_asset_prec():
    list_prec = frappe.db.sql(""" 
        SELECT tab.`purchase_receipt`
        FROM `tabAsset` tab
        WHERE tab.`purchase_receipt` IS NOT NULL
        AND tab.`docstatus` = 1
        GROUP BY tab.purchase_receipt
         """)

    for row in list_prec:
        print(list_prec)
        prec_doc = frappe.get_doc("Purchase Receipt", row[0])
        for row_item in prec_doc.items:
            list_asset = frappe.db.sql(""" SELECT
            name
            FROM `tabAsset` 
            WHERE purchase_receipt = "{}" and item_code = "{}" 
            and docstatus = 1
            """.format(prec_doc.name, row_item.item_code))
            print(list_asset)
            message = ""
            for row_asset in list_asset:
                message = message + row_asset[0] + "\n"

            print(message)
            row_item.asset_list = message
            row_item.db_update()


@frappe.whitelist()
def submit_payment():
    frappe.get_doc("Payment Entry","PYI-GIAS-JBI-1-22-08-00067").submit()

@frappe.whitelist()
def list_membenarkan_po():
    list_prec = frappe.db.sql(""" 
        SELECT tpr.parent, tpr.`item_code`, tii.rate, tpr.rate
        FROM `tabPurchase Order Item` tpr
        JOIN `tabPurchase Receipt Item` tii
        ON tii.purchase_order_item = tpr.`name`
        WHERE tpr.rate != tii.`rate`
        AND tii.`docstatus` = 1
        AND tpr.`docstatus` = 1
        AND tpr.parent = "PO-SIA-INV-1-22-07-00006"
        GROUP BY tpr.parent
        ORDER BY tpr.parent 
    """)

    for row in list_prec:
        print(row[0])
        membenarkan_po(row[0])
    print("+==========PO DONE============+")

@frappe.whitelist()
def list_membenarkan_prec():
    list_prec = [
        ["PRI-HO-1-22-08-00413","B-BUBB-P-000002",235000]
    ]

    for row in list_prec:
        print(row[0])
        membenarkan_prec(row[0])
    print("+==========PREC DONE============+")
    # command = """ cd /home/frappe/frappe-bench/ && bench --site erp-pusat.gias.co.id execute erpnext.stock.doctype.repost_item_valuation.repost_item_valuation.repost_entries """
    # os.system(command)
    # print("+==========COMMENCING SYNC============+")
    # for row in list_prec:
    #     membenarkan_prec_sync(row[0],row[2],row[1])

@frappe.whitelist()
def mengisi_je():
    list_je = frappe.db.sql(""" 
        SELECT tds.name, tds.detil_je_log, tje.name, ta.name
        FROM `db_pusat`.`tabAsset` ta 
        JOIN `db_pusat`.`tabDepreciation Schedule` tds 
        ON ta.name = tds.parent
        LEFT JOIN `tabJournal Entry` tje ON tje.je_log = tds.detil_je_log
        WHERE MONTH(tds.schedule_date) = 10
        AND YEAR(tds.schedule_date) = 2022
        AND list_company_gias IN (SELECT nama_cabang FROM `tabCompany` )
        AND tje.name IS NULL
        AND ta.on_depreciation = 1
        AND ta.docstatus = 1 
    """)

    for row in list_je:
        tds_name = row[0]
        command = """ cd /home/frappe/frappe-bench/ && bench --site erp-pusat.gias.co.id execute addons.patch.kosongkan_je_log --kwargs "{{'tds_name':'{}'}}" """.format(tds_name)
        os.system(command)
        print(str(tds_name))

@frappe.whitelist()
def kosongkan_je_log(tds_name):
    frappe.db.sql(""" UPDATE `tabDepreciation Schedule` SET detil_je_log = "" WHERE name = "{}" """.format(tds_name))


@frappe.whitelist()
def membenarkan_po(po):
    prec_doc = frappe.get_doc("Purchase Order", po)
    for row in prec_doc.items:
        nilai_rate = frappe.db.sql(""" SELECT 
            pii.rate FROm `tabPurchase Receipt Item` pii 
            JOIN `tabPurchase Receipt` pi ON pi.name = pii.parent
            WHERE pii.purchase_order_item = "{}" and pi.workflow_state != "Rejected" 
            and pi.docstatus = 1 """.format(row.name))

        if nilai_rate:
            if nilai_rate[0]:
                if nilai_rate[0][0]:
                    row.price_list_rate = nilai_rate[0][0]
                    row.rate = nilai_rate[0][0]
                    row.margin_rate_or_amount = 0
                    row.discount_amount = 0


    prec_doc.run_method("calculate_taxes_and_totals")

    for row in prec_doc.items:
        row.db_update()

    prec_doc.db_update()
    # print(prec)
@frappe.whitelist()
def membenarkan_prec(prec):
    prec_doc = frappe.get_doc("Purchase Receipt", prec)
    for row in prec_doc.items:
        nilai_rate = frappe.db.sql(""" SELECT 
            pii.rate FROm `tabPurchase Invoice Item` pii 
            JOIN `tabPurchase Invoice` pi ON pi.name = pii.parent
            WHERE pii.pr_detail = "{}" 
            and pi.workflow_state != "Rejected" and pi.docstatus = 0 """.format(row.name))

        if nilai_rate:
            if nilai_rate[0]:
                if nilai_rate[0][0]:
                    row.price_list_rate = nilai_rate[0][0]
                    row.rate = nilai_rate[0][0]
                    row.margin_rate_or_amount = 0
                    row.discount_amount = 0

    prec_doc.run_method("calculate_taxes_and_totals")
    prec_doc.update_valuation_rate()

    for row in prec_doc.items:
        row.db_update()

    prec_doc.db_update()
    
    # repair_gl_entry(prec_doc.doctype, prec_doc.name)
    print(prec)

@frappe.whitelist()
def list_pinv():
    list_pi = [
    "PI-1-22-04-00894",
    "PI-1-22-05-00304",
    "PI-1-22-05-00641",
    "PI-1-22-04-02863",
    "PI-1-22-07-00318",
    "PI-1-22-05-00003",
    "PI-1-22-05-00218",
    "PI-1-22-04-00461",
    "PI-1-22-04-02841",
    "PI-1-22-04-01491",
    "PI-1-22-06-00288",
    "PI-1-22-05-00023",
    "PI-1-22-06-00293",
    "PI-1-22-05-01504",
    "PI-1-22-05-00218",
    "PI-1-22-06-00477",
    "PI-1-22-05-00630",
    "PI-1-22-07-00419",
    "PI-1-22-05-00004",
    "PI-1-22-06-00856",
    "PI-1-22-04-01934",
    "PI-1-22-04-01989",
    "PI-1-22-07-00157",
    "PI-1-22-06-00651",
    "PI-1-22-06-00067",
    "PI-1-22-05-00024",
    "PI-1-22-04-01900",
    "PI-1-22-06-00653",
    "PI-1-22-04-02896",
    "PI-1-22-04-00358",
    "PI-1-22-04-01957",
    "PI-1-22-06-00486",
    "PI-1-22-04-02845",
    "PI-1-22-05-01597",
    "PI-1-22-05-00196",
    "PI-1-22-06-01091",
    "PI-1-22-05-00023",
    "PI-1-22-07-01413",
    "PI-1-22-05-00023",
    "PI-1-22-04-01975",
    "PI-1-22-05-01471",
    "PI-1-22-05-01597",
    "PI-1-22-05-01470",
    "PI-1-22-04-01965",
    "PI-1-22-05-00292",
    "PI-1-22-04-00972",
    "PI-1-22-07-00066",
    "PI-1-22-07-00055",
    "PI-1-22-05-01470",
    "PI-1-22-04-01975",
    "PI-1-22-06-01007",
    "PI-1-22-06-00660",
    "PI-1-22-04-02840",
    "PI-1-22-07-00157",
    "PI-1-22-04-00421",
    "PI-1-22-07-00066"
    ]
    for row in list_pi:
        membenarkan_pinv(row)

frappe.whitelist()
def membenarkan_pinv(pinv):
    prec_doc = frappe.get_doc("Purchase Invoice", pinv)
    for row in prec_doc.items:
       
        row.price_list_rate = row.rate
        row.margin_rate_or_amount = 0
        row.discount_amount = 0

    prec_doc.run_method("calculate_taxes_and_totals")
    prec_doc.update_valuation_rate()

    for row in prec_doc.items:
        row.db_update()

    prec_doc.db_update()
    
    repair_gl_entry_tanpa_sl(prec_doc.doctype, prec_doc.name)
    print(pinv)
    
@frappe.whitelist()
def membenarkan_prec_sync(a,b,c):
    prec = a
    nilai = b
    item = c
    prec_doc = frappe.get_doc("Purchase Receipt", prec)
    tanggal_prec = prec_doc.posting_date
    waktu_prec = prec_doc.posting_time

    list_ste_perlu_stock = frappe.db.sql(""" SELECT ste.transfer_ke_cabang_mana, ste.name 
        FROM `tabStock Ledger Entry` sle JOIN `tabStock Entry` ste ON ste.name = sle.voucher_no
        where sle.item_code = "{}"
        and TIMESTAMP(ste.posting_date, ste.posting_time) >= TIMESTAMP("{}","{}")
        and ste.stock_entry_type = "Material Issue" and ste.transfer_ke_cabang_pusat = 1
        ORDER BY TIMESTAMP(ste.posting_date, ste.posting_time)
        
    """.format(item, tanggal_prec, waktu_prec))

    for row in list_ste_perlu_stock:
        list_company_gias = row[0]
        site = ""
        patch = 0
        rate = 0 
        # check ledgible
        ste_doc = frappe.get_doc("Stock Entry", row[1])
        for row_item in ste_doc.items:
            if row_item.item_code == item:
                patch = 1
                rate = row_item.valuation_rate

        if patch == 1:
            if list_company_gias == "GIAS SERANG":
                site = "erp-srg.gias.co.id"
            if list_company_gias == "GIAS SPRINGHILL":
                site = "erp-pusat.gias.co.id"
            if list_company_gias == "GIAS BALI":
                site = "erp-bali.gias.co.id"
            if list_company_gias == "GIAS BALIKPAPAN":
                site = "erp-bpp.gias.co.id"
            if list_company_gias == "GIAS BANDUNG":
                site = "erp-bdg.gias.co.id"
            if list_company_gias == "GIAS BANGKA":
                site = "erp-bnk.gias.co.id"
            if list_company_gias == "GIAS BANJARMASIN":
                site = "erp-bjm.gias.co.id"
            if list_company_gias == "GIAS BENGKULU":
                site = "erp-bkl.gias.co.id"
            if list_company_gias == "GIAS BERAU":
                site = "erp-bru.gias.co.id"
            if list_company_gias == "GIAS CIREBON":
                site = "erp-crb.gias.co.id"
            if list_company_gias == "GIAS GORONTALO":
                site = "erp-gto.gias.co.id"
            if list_company_gias == "GIAS JAMBI":
                site = "erp-jbi.gias.co.id"
            if list_company_gias == "GIAS JEMBER":
                site = "erp-jbr.gias.co.id"
            if list_company_gias == "GIAS KENDARI":
                site = "erp-kdi.gias.co.id"
            if list_company_gias == "GIAS LAMPUNG":
                site = "erp-lmp.gias.co.id"
            if list_company_gias == "GIAS LINGGAU":
                site = "erp-lgu.gias.co.id"
            if list_company_gias == "GIAS MADIUN":
                site = "erp-mdu.gias.co.id"
            if list_company_gias == "GIAS MAKASAR":
                site = "erp-mks.gias.co.id"
            if list_company_gias == "GIAS MANADO":
                site = "erp-mnd.gias.co.id"
            if list_company_gias == "GIAS MEDAN":
                site = "erp-mdn.gias.co.id"
            if list_company_gias == "GIAS PALEMBANG":
                site = "erp-plg.gias.co.id"
            if list_company_gias == "GIAS PEKANBARU":
                site = "erp-pku.gias.co.id"
            if list_company_gias == "GIAS PONTIANAK":
                site = "erp-ptk.gias.co.id"
            if list_company_gias == "GIAS PURWOKERTO":
                site = "erp-pwt.gias.co.id"
            if list_company_gias == "GIAS SAMARINDA":
                site = "erp-smd.gias.co.id"
            if list_company_gias == "GIAS SEMARANG":
                site = "erp-smg.gias.co.id"
            if list_company_gias == "GIAS SERANG":
                site = "erp-srg.gias.co.id"
            if list_company_gias == "GIAS SURABAYA":
                site = "erp-sby.gias.co.id"
            if list_company_gias == "GIAS TASIK":
                site = "erp-tsk.gias.co.id"
            if list_company_gias == "GIAS TEGAL":
                site = "erp-tgl.gias.co.id"
            if list_company_gias == "GIAS YOGYAKARYA":
                site = "erp-ygy.gias.co.id"
            if site:
                command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.patch.update_sync_ste --kwargs "{{'ste':'{1}','item':'{2}','nilai':'{3}'}}" """.format(site,ste_doc.name,item,rate)
                os.system(command)

@frappe.whitelist()
def distributed_cost_ste():
    list_ste = [
        "STEI-HO-1-22-03-00848",
        "STEI-HO-1-22-03-01221",
        "STEI-HO-1-22-03-01197",
        "STEI-HO-1-22-03-00781",
        "STEI-HO-1-22-04-00212",
        "STEI-HO-1-22-05-00203",
        "STEI-HO-1-22-07-01892",
        "STEI-HO-1-22-08-00013",
        "STEI-HO-1-22-08-01461",
        "STEI-HO-1-22-08-01797",
        "STEI-HO-1-22-06-00315",
        "STEI-HO-1-22-07-01688",
        "STEI-HO-1-22-06-02702",
        "STEI-HO-1-22-08-00923",
        "STEI-HO-1-22-07-01478",
        "STEI-HO-1-22-04-00383",
        "STEI-HO-1-22-05-01482",
        "STEI-HO-1-22-05-01472",
        "STEI-HO-1-22-05-00480",
        "STEI-HO-1-22-04-00957",
        "STEI-HO-1-22-06-02101",
        "STEI-HO-1-22-06-01671",
        "STEI-HO-1-22-06-03308",
        "STEI-HO-1-22-04-03516",
        "STEI-HO-1-22-05-01141",
        "STEI-HO-1-22-05-00241",
        "STEI-HO-1-22-04-01774",
        "STEI-HO-1-22-04-02002",
        "STEI-HO-1-22-07-00906",
        "STEI-HO-1-22-08-00092",
        "STEI-HO-1-22-04-01996",
        "STEI-HO-1-22-08-01574",
        "STEI-HO-1-22-06-02631",
        "STEI-HO-1-22-04-00952",
        "STEI-HO-1-22-03-00997",
        "STEI-HO-1-22-04-01743",
        "STEI-HO-1-22-05-01997",
        "STEI-HO-1-22-04-00645",
        "STEI-HO-1-22-04-00947",
        "STEI-HO-1-22-05-00371",
        "STEI-HO-1-22-05-00378",
        "STEI-HO-1-22-05-01199",
        "STEI-HO-1-22-05-01311",
        "STEI-HO-1-22-08-00366",
        "STEI-HO-1-22-05-01761",
        "STEI-HO-1-22-06-00682",
        "STEI-HO-1-22-04-03585",
        "STEI-HO-1-22-08-00572",
        "STEI-HO-1-22-04-02028",
        "STEI-HO-1-22-04-02996",
        "STEI-HO-1-22-07-00375",
        "STEI-HO-1-22-06-00342",
        "STEI-HO-1-22-05-01310",
        "STEI-HO-1-22-08-00737",
        "STEI-HO-1-22-04-03011",
        "STEI-HO-1-22-08-02049",
        "STEI-HO-1-22-07-02241",
        "STEI-HO-1-22-06-02655",
        "STEI-HO-1-22-04-01295",
        "STEI-HO-1-22-07-02209",
        "STEI-HO-1-22-03-00462",
        "STEI-HO-1-22-04-03417",
        "STEI-HO-1-22-06-00847",
        "STEI-HO-1-22-04-02225",
        "STEI-HO-1-22-05-01469",
        "STEI-HO-1-22-08-02854",
        "STEI-HO-1-22-04-00481",
        "STEI-HO-1-22-05-00926",
        "STEI-HO-1-22-07-00119",
        "STEI-HO-1-22-06-01616",
        "STEI-HO-1-22-08-00081",
        "STEI-HO-1-22-08-02330",
        "STEI-HO-1-22-06-02100",
        "STEI-HO-1-22-07-01160",
        "STEI-HO-1-22-06-02401",
        "STEI-HO-1-22-07-01815",
        "STEI-HO-1-22-08-02702",
        "STEI-HO-1-22-06-00472",
        "STEI-HO-1-22-07-01976",
        "STEI-HO-1-22-08-01196",
        "STEI-HO-1-22-07-02838",
        "STEI-HO-1-22-08-02696",
        "STEI-HO-1-22-05-00076",
        "STEI-HO-1-22-07-02328",
        "STEI-HO-1-22-07-00605",
        "STEI-HO-1-22-08-02698",
        "STEI-HO-1-22-03-03255",
        "STEI-HO-1-22-04-00475",
        "STEI-HO-1-22-06-01647",
        "STEI-HO-1-22-04-00662",
        "STEI-HO-1-22-05-01810",
        "STEI-HO-1-22-04-00679",
        "STEI-HO-1-22-05-01811",
        "STEI-HO-1-22-04-00680",
        "STEI-HO-1-22-05-01140",
        "STEI-HO-1-22-07-02659",
        "STEI-HO-1-22-06-00468",
        "STEI-HO-1-22-07-02119",
        "STEI-HO-1-22-03-02412",
        "STEI-HO-1-22-06-01649",
        "STEI-HO-1-22-04-00385",
        "STEI-HO-1-22-06-02703",
        "STEI-HO-1-22-05-00598",
        "STEI-HO-1-22-03-00139",
        "STEI-HO-1-22-03-00140",
        "STEI-HO-1-22-07-01748",
        "STEI-HO-1-22-03-01774",
        "STEI-HO-1-22-07-01893",
        "STEI-HO-1-22-06-01645",
        "STEI-HO-1-22-03-01776",
        "STEI-HO-1-22-07-02854",
        "STEI-HO-1-22-04-02905",
        "STEI-HO-1-22-06-00012",
        "STEI-HO-1-22-04-03483",
        "STEI-HO-1-22-04-02712",
        "STEI-HO-1-22-06-01633",
        "STEI-HO-1-22-04-02919",
        "STEI-HO-1-22-04-01298",
        "STEI-HO-1-22-05-01457",
        "STEI-HO-1-22-05-01950",
        "STE-HO-1-22-04-00002",
        "STEI-HO-1-22-04-01917",
        "STEI-HO-1-22-04-03355",
        "STEI-HO-1-22-04-00798"
    ]
    for row in list_ste:
        membenarkan_ste_sync(row)

@frappe.whitelist()
def membenarkan_ste_sync(ste):
    ste_doc = frappe.get_doc("Stock Entry", ste)

    
    ste_tujuan = ste_doc.sync_name
    list_company_gias = ste_doc.transfer_ke_cabang_mana

    for row in ste_doc.items:

        item_code = row.item_code
        rate = row.basic_rate

        site = ""
        if not site:
            if list_company_gias == "GIAS SERANG":
                site = "erp-srg.gias.co.id"
            if list_company_gias == "GIAS SPRINGHILL":
                site = "erp-pusat.gias.co.id"
            if list_company_gias == "GIAS BALI":
                site = "erp-bali.gias.co.id"
            if list_company_gias == "GIAS BALIKPAPAN":
                site = "erp-bpp.gias.co.id"
            if list_company_gias == "GIAS BANDUNG":
                site = "erp-bdg.gias.co.id"
            if list_company_gias == "GIAS BANGKA":
                site = "erp-bnk.gias.co.id"
            if list_company_gias == "GIAS BANJARMASIN":
                site = "erp-bjm.gias.co.id"
            if list_company_gias == "GIAS BENGKULU":
                site = "erp-bkl.gias.co.id"
            if list_company_gias == "GIAS BERAU":
                site = "erp-bru.gias.co.id"
            if list_company_gias == "GIAS CIREBON":
                site = "erp-crb.gias.co.id"
            if list_company_gias == "GIAS GORONTALO":
                site = "erp-gto.gias.co.id"
            if list_company_gias == "GIAS JAMBI":
                site = "erp-jbi.gias.co.id"
            if list_company_gias == "GIAS JEMBER":
                site = "erp-jbr.gias.co.id"
            if list_company_gias == "GIAS KENDARI":
                site = "erp-kdi.gias.co.id"
            if list_company_gias == "GIAS LAMPUNG":
                site = "erp-lmp.gias.co.id"
            if list_company_gias == "GIAS LINGGAU":
                site = "erp-lgu.gias.co.id"
            if list_company_gias == "GIAS MADIUN":
                site = "erp-mdu.gias.co.id"
            if list_company_gias == "GIAS MAKASAR":
                site = "erp-mks.gias.co.id"
            if list_company_gias == "GIAS MANADO":
                site = "erp-mnd.gias.co.id"
            if list_company_gias == "GIAS MEDAN":
                site = "erp-mdn.gias.co.id"
            if list_company_gias == "GIAS PALEMBANG":
                site = "erp-plg.gias.co.id"
            if list_company_gias == "GIAS PEKANBARU":
                site = "erp-pku.gias.co.id"
            if list_company_gias == "GIAS PONTIANAK":
                site = "erp-ptk.gias.co.id"
            if list_company_gias == "GIAS PURWOKERTO":
                site = "erp-pwt.gias.co.id"
            if list_company_gias == "GIAS SAMARINDA":
                site = "erp-smd.gias.co.id"
            if list_company_gias == "GIAS SEMARANG":
                site = "erp-smg.gias.co.id"
            if list_company_gias == "GIAS SERANG":
                site = "erp-srg.gias.co.id"
            if list_company_gias == "GIAS SURABAYA":
                site = "erp-sby.gias.co.id"
            if list_company_gias == "GIAS TASIK":
                site = "erp-tsk.gias.co.id"
            if list_company_gias == "GIAS TEGAL":
                site = "erp-tgl.gias.co.id"
            if list_company_gias == "GIAS YOGYAKARTA":
                site = "erp-ygy.gias.co.id"
            if site:
                command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.patch.update_sync_ste --kwargs "{{'ste':'{1}','item':'{2}','nilai':'{3}'}}" """.format(site,ste,item_code,rate)
                os.system(command)

@frappe.whitelist()
def update_sync_ste(ste,item,nilai):

    StockEntry.distribute_additional_costs = custom_distribute_additional_costs

    ste_list = frappe.db.sql(""" SELECT name, docstatus FROM `tabStock Entry` WHERE sync_name = "{}" and docstatus >= 0 """.format(ste))
    for row in ste_list:
        ste_doc = frappe.get_doc("Stock Entry", row[0])
        print("{}-{}".format(row[0],frappe.get_doc("Company","GIAS").nama_cabang))
        check = 0
        check_gl = 1

        if ste_doc.total_additional_costs > 0:
            ste_doc.distribute_additional_costs()
            check = 1

        for row_item in ste_doc.items:
            if row_item.item_code == item:
                if nilai != row_item.pusat_valuation_rate or check == 1:
                    row_item.pusat_valuation_rate = nilai
                    row_item.basic_rate = nilai
                    row_item.valuation_rate = flt(row_item.basic_rate) + (flt(row_item.additional_cost)/flt(row_item.transfer_qty))
                    row_item.basic_amount = flt(row_item.basic_rate) * flt(row_item.qty)
                    row_item.amount = flt(row_item.valuation_rate) * flt(row_item.qty)
                    row_item.db_update()
                    check = 1


        # if check == 1 and row[1] == 1:
        #     repair_gl_entry(ste_doc.doctype, ste_doc.name)
@frappe.whitelist()
def repost_stock():
    from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import debug_repost
    debug_repost()


@frappe.whitelist()
def debug_repair_gl_entry():
    repair_gl_entry("Stock Reconciliation","ADJ-GIAS-BRU-1-22-06-00008")

@frappe.whitelist()
def repair_gl_entry(doctype,docname):
    docu = frappe.get_doc(doctype, docname) 
    delete_sl = frappe.db.sql(""" DELETE FROM `tabStock Ledger Entry` WHERE voucher_no = "{}" """.format(docname))
    delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
    frappe.flags.repost_gl = True
    
    frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 1 WHERE `field` = "allow_negative_stock" """)
    docu.update_stock_ledger()
    docu.make_gl_entries()
    docu.repost_future_sle_and_gle()
    frappe.db.sql(""" UPDATE `tabSingles` SET VALUE = 0 WHERE `field` = "allow_negative_stock" """)

    frappe.db.commit()

@frappe.whitelist()
def patch_gl():
    asset_doc = frappe.get_doc("Asset","ACC-ASS-2022-02039")
    for row in asset_doc.schedules:
        if not row.detil_je_log:
            if asset_doc.server_kepemilikan == "Pusat":
                row.list_company_gias = frappe.get_doc("Company", asset_doc.company).nama_cabang
                row.db_update()
            else:
                row.list_company_gias = asset_doc.cabang
                row.db_update()
@frappe.whitelist()
def patch_je_kosong():
    je_list = frappe.db.sql("""
    SELECT tjea.`parent`,tgl.name FROM `tabJournal Entry Account` tjea
    LEFT JOIN `tabGL Entry` tgl ON tjea.`parent` = tgl.voucher_no 
    WHERE tjea.`docstatus` = 1
    GROUP BY tjea.`parent`
    HAVING tgl.name IS NULL """)

    for row in je_list:

        print(row[0])
        repair_gl_entry_tanpa_sl("Journal Entry", row[0])

@frappe.whitelist()
def repair_gl_entry_tanpa_sl(doctype,docname):
    
    docu = frappe.get_doc(doctype, docname) 
    if doctype == "Stock Entry":
        if docu.purpose == "Material Issue":
            if docu.dari_branch == 1 and docu.stock_entry_type == "Material Issue":
                StockController.make_gl_entries = custom_make_gl_entries

    delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(docname))
    docu.make_gl_entries()


@frappe.whitelist()
def auto_status(self):
    if self.docstatus == 0:
        status = "Draft"
    elif self.docstatus == 1:
        status = "Submitted"
        if self.tanggal_scrap:
            status = "Scrapped"
        elif self.finance_books:
            idx = self.get_default_finance_book_idx() or 0

            depreciation_amount = self.depreciation_amount
            gross_purchase = self.gross_purchase_amount

            if flt(depreciation_amount,0) >= flt(gross_purchase,0):
                status = "Fully Depreciated"
            elif flt(depreciation_amount,0) > 0:
                status = 'Partially Depreciated'
    elif self.docstatus == 2:
        status = "Cancelled"
    return status


@frappe.whitelist()
def patch_je_log():
    file = open("/home/frappe/frappe-bench/apps/addons/addons/je_log_data.txt").readlines()
    list_docs = [row.strip() for row in file]
    for doc in list_docs:
        data = doc.split()
        jelog = str(data[0])
        site = ""
        list_company_gias = "GIAS " + str(data[2]) 

        if list_company_gias == "GIAS SERANG":
            site = "erp-srg.gias.co.id"
        if list_company_gias == "GIAS SPRINGHILL":
            site = "erp-pusat.gias.co.id"
        if list_company_gias == "GIAS BALI":
            site = "erp-bali.gias.co.id"
        if list_company_gias == "GIAS BALIKPAPAN":
            site = "erp-bpp.gias.co.id"
        if list_company_gias == "GIAS BANDUNG":
            site = "erp-bdg.gias.co.id"
        if list_company_gias == "GIAS BANGKA":
            site = "erp-bnk.gias.co.id"
        if list_company_gias == "GIAS BANJARMASIN":
            site = "erp-bjm.gias.co.id"
        if list_company_gias == "GIAS BENGKULU":
            site = "erp-bkl.gias.co.id"
        if list_company_gias == "GIAS BERAU":
            site = "erp-bru.gias.co.id"
        if list_company_gias == "GIAS CIREBON":
            site = "erp-crb.gias.co.id"
        if list_company_gias == "GIAS GORONTALO":
            site = "erp-gto.gias.co.id"
        if list_company_gias == "GIAS JAMBI":
            site = "erp-jbi.gias.co.id"
        if list_company_gias == "GIAS JEMBER":
            site = "erp-jbr.gias.co.id"
        if list_company_gias == "GIAS KENDARI":
            site = "erp-kdi.gias.co.id"
        if list_company_gias == "GIAS LAMPUNG":
            site = "erp-lmp.gias.co.id"
        if list_company_gias == "GIAS LINGGAU":
            site = "erp-lgu.gias.co.id"
        if list_company_gias == "GIAS MADIUN":
            site = "erp-mdu.gias.co.id"
        if list_company_gias == "GIAS MAKASAR":
            site = "erp-mks.gias.co.id"
        if list_company_gias == "GIAS MANADO":
            site = "erp-mnd.gias.co.id"
        if list_company_gias == "GIAS MEDAN":
            site = "erp-mdn.gias.co.id"
        if list_company_gias == "GIAS PALEMBANG":
            site = "erp-plg.gias.co.id"
        if list_company_gias == "GIAS PEKANBARU":
            site = "erp-pku.gias.co.id"
        if list_company_gias == "GIAS PONTIANAK":
            site = "erp-ptk.gias.co.id"
        if list_company_gias == "GIAS PURWOKERTO":
            site = "erp-pwt.gias.co.id"
        if list_company_gias == "GIAS SAMARINDA":
            site = "erp-smd.gias.co.id"
        if list_company_gias == "GIAS SEMARANG":
            site = "erp-smg.gias.co.id"
        if list_company_gias == "GIAS SERANG":
            site = "erp-srg.gias.co.id"
        if list_company_gias == "GIAS SURABAYA":
            site = "erp-sby.gias.co.id"
        if list_company_gias == "GIAS TASIK":
            site = "erp-tsk.gias.co.id"
        if list_company_gias == "GIAS TEGAL":
            site = "erp-tgl.gias.co.id"
        if list_company_gias == "GIAS YOGYAKARYA":
            site = "erp-ygy.gias.co.id"
        if site:
            command = """ cd /home/frappe/frappe-bench/ && bench --site {0} execute addons.patch.cancel_delete_je --kwargs "{{'je_log':'{1}'}}" """.format(site,jelog)
            os.system(command)


@frappe.whitelist()
def cancel_delete_je(je_log):
    list_je = frappe.db.sql(""" 
        SELECT name
        FROM `tabJournal Entry` je
        WHERE je_log = "{0}"
    """.format(je_log))

    for row in list_je:
        delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(row[0]))
        
        print(str(row[0]))
        je_doc = frappe.get_doc("Journal Entry", row[0])
        je_doc.cancel()
        je_doc.delete()

    

def patch_sinv():
    file = open("/home/frappe/frappe-bench/apps/addons/addons/sinv.txt").readlines()
    
    list_docs = [row.strip() for row in file]
    for doc in list_docs:
        list_sinv = doc.split()
        sinv_item = frappe.db.get_list('Sales Invoice Item', filters={ 
            'parent' : list_sinv[0] 
        }, fields=['name', 'item_code','sales_order', 'so_detail', 'delivery_note', 'dn_detail'])
        print(list_sinv[0])
        for item in sinv_item:
            if item.sales_order or item.so_detail or item.delivery_note or item.dn_detail:
                continue
            so_item = frappe.db.get_value('Sales Order Item', { 'parent' : list_sinv[1], 'item_code' : item.item_code }, 'name')
            dn_item = frappe.db.get_value('Delivery Note Item', { 'parent' : list_sinv[2], 'item_code' : item.item_code }, 'name')
            frappe.db.set_value('Sales Invoice Item', { 'name' : item.name, 'item_code' : item.item_code, 'parent' : list_sinv[0] }, {
                'sales_order': list_sinv[1],
                'so_detail': so_item,
                'delivery_note' : list_sinv[2],
                'dn_detail' : dn_item
            })

@frappe.whitelist()
def cancel_je_depreciation():
    list_je = frappe.db.sql(""" 
        SELECT name, je.`voucher_type`, docstatus
        FROM `tabJournal Entry` je
        WHERE voucher_type = "Depreciation Entry"
        AND docstatus = 1 
    """)

    for row in list_je:
        delete_gl = frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no = "{}" """.format(row[0]))
        
        print(str(row[0]))
        je_doc = frappe.get_doc("Journal Entry", row[0])
        je_doc.cancel()

@frappe.whitelist()
def cancel_asset():
    list_je = frappe.db.sql(""" 
        SELECT name
        FROM `tabAsset Movement`
        WHERE docstatus = 2
    """)

    for row in list_je:
        print(str(row[0]))
        je_doc = frappe.get_doc("Asset Movement", row[0])
        je_doc.delete()


@frappe.whitelist()
def draft_asset():
    list_asset = [    "ACC-ASS-2022-00570",
    "ACC-ASS-2022-00441",
    "ACC-ASS-2022-00611",
    "ACC-ASS-2022-00591",
    "ACC-ASS-2022-00389",
    "ACC-ASS-2022-00338",
    "ACC-ASS-2022-00440",
    "ACC-ASS-2022-00439",
    "ACC-ASS-2022-00610",
    "ACC-ASS-2022-00603",
    "ACC-ASS-2022-00443",
    "ACC-ASS-2022-00455",
    "ACC-ASS-2022-00729",
    "ACC-ASS-2022-00341",
    "ACC-ASS-2022-00226",
    "ACC-ASS-2022-00127",
    "ACC-ASS-2022-00558",
    "ACC-ASS-2022-00129",
    "ACC-ASS-2022-00125",
    "ACC-ASS-2022-00126",
    "ACC-ASS-2022-00384",
    "ACC-ASS-2022-00461",
    "ACC-ASS-2022-00680",
    "ACC-ASS-2022-00595",
    "ACC-ASS-2022-00349",
    "ACC-ASS-2022-00340",
    "ACC-ASS-2022-00342",
    "ACC-ASS-2022-00158",
    "ACC-ASS-2022-00571",
    "ACC-ASS-2022-00386",
    "ACC-ASS-2022-00431",
    "ACC-ASS-2022-00432",
    "ACC-ASS-2022-00433",
    "ACC-ASS-2022-00434",
    "ACC-ASS-2022-00435",
    "ACC-ASS-2022-00436",
    "ACC-ASS-2022-00437",
    "ACC-ASS-2022-00438",
    "ACC-ASS-2022-00442",
    "ACC-ASS-2022-00444",
    "ACC-ASS-2022-00445",
    "ACC-ASS-2022-00446",
    "ACC-ASS-2022-00447",
    "ACC-ASS-2022-00448",
    "ACC-ASS-2022-00449",
    "ACC-ASS-2022-00450",
    "ACC-ASS-2022-00451",
    "ACC-ASS-2022-00452",
    "ACC-ASS-2022-00453",
    "ACC-ASS-2022-00454",
    "ACC-ASS-2022-00456",
    "ACC-ASS-2022-00468",
    "ACC-ASS-2022-00469",
    "ACC-ASS-2022-00470",
    "ACC-ASS-2022-00471",
    "ACC-ASS-2022-00472",
    "ACC-ASS-2022-00473",
    "ACC-ASS-2022-00474",
    "ACC-ASS-2022-00475",
    "ACC-ASS-2022-00476",
    "ACC-ASS-2022-00477",
    "ACC-ASS-2022-00478",
    "ACC-ASS-2022-00479",
    "ACC-ASS-2022-00480",
    "ACC-ASS-2022-00481",
    "ACC-ASS-2022-00482",
    "ACC-ASS-2022-00483",
    "ACC-ASS-2022-00484",
    "ACC-ASS-2022-00485",
    "ACC-ASS-2022-00486",
    "ACC-ASS-2022-00487",
    "ACC-ASS-2022-00488",
    "ACC-ASS-2022-00489",
    "ACC-ASS-2022-00490",
    "ACC-ASS-2022-00491",
    "ACC-ASS-2022-00492",
    "ACC-ASS-2022-00493",
    "ACC-ASS-2022-00494",
    "ACC-ASS-2022-00495",
    "ACC-ASS-2022-00496",
    "ACC-ASS-2022-00497",
    "ACC-ASS-2022-00498",
    "ACC-ASS-2022-00499",
    "ACC-ASS-2022-00500",
    "ACC-ASS-2022-00501",
    "ACC-ASS-2022-00502",
    "ACC-ASS-2022-00503",
    "ACC-ASS-2022-00504",
    "ACC-ASS-2022-00505",
    "ACC-ASS-2022-00506",
    "ACC-ASS-2022-00507",
    "ACC-ASS-2022-00508",
    "ACC-ASS-2022-00509",
    "ACC-ASS-2022-00510",
    "ACC-ASS-2022-00511",
    "ACC-ASS-2022-00512",
    "ACC-ASS-2022-00513",
    "ACC-ASS-2022-00514"]
    for row in list_asset:
        
        asset_doc = frappe.get_doc("Asset", row)
        asset_doc.submit()


@frappe.whitelist()
def hapus_sejarah():
    list_asset = [
    "ACC-ASS-2022-00570",
    "ACC-ASS-2022-00441",
    "ACC-ASS-2022-00611",
    "ACC-ASS-2022-00591",
    "ACC-ASS-2022-00389",
    "ACC-ASS-2022-00338",
    "ACC-ASS-2022-00440",
    "ACC-ASS-2022-00439",
    "ACC-ASS-2022-00610",
    "ACC-ASS-2022-00603",
    "ACC-ASS-2022-00443",
    "ACC-ASS-2022-00455",
    "ACC-ASS-2022-00729",
    "ACC-ASS-2022-00341",
    "ACC-ASS-2022-00226",
    "ACC-ASS-2022-00127",
    "ACC-ASS-2022-00558",
    "ACC-ASS-2022-00129",
    "ACC-ASS-2022-00125",
    "ACC-ASS-2022-00126",
    "ACC-ASS-2022-00384",
    "ACC-ASS-2022-00461",
    "ACC-ASS-2022-00680",
    "ACC-ASS-2022-00595",
    "ACC-ASS-2022-00349",
    "ACC-ASS-2022-00340",
    "ACC-ASS-2022-00342",
    "ACC-ASS-2022-00158",
    "ACC-ASS-2022-00571",
    "ACC-ASS-2022-00386",
    "ACC-ASS-2022-00431",
    "ACC-ASS-2022-00432",
    "ACC-ASS-2022-00433",
    "ACC-ASS-2022-00434",
    "ACC-ASS-2022-00435",
    "ACC-ASS-2022-00436",
    "ACC-ASS-2022-00437",
    "ACC-ASS-2022-00438",
    "ACC-ASS-2022-00442",
    "ACC-ASS-2022-00444",
    "ACC-ASS-2022-00445",
    "ACC-ASS-2022-00446",
    "ACC-ASS-2022-00447",
    "ACC-ASS-2022-00448",
    "ACC-ASS-2022-00449",
    "ACC-ASS-2022-00450",
    "ACC-ASS-2022-00451",
    "ACC-ASS-2022-00452",
    "ACC-ASS-2022-00453",
    "ACC-ASS-2022-00454",
    "ACC-ASS-2022-00456",
    "ACC-ASS-2022-00468",
    "ACC-ASS-2022-00469",
    "ACC-ASS-2022-00470",
    "ACC-ASS-2022-00471",
    "ACC-ASS-2022-00472",
    "ACC-ASS-2022-00473",
    "ACC-ASS-2022-00474",
    "ACC-ASS-2022-00475",
    "ACC-ASS-2022-00476",
    "ACC-ASS-2022-00477",
    "ACC-ASS-2022-00478",
    "ACC-ASS-2022-00479",
    "ACC-ASS-2022-00480",
    "ACC-ASS-2022-00481",
    "ACC-ASS-2022-00482",
    "ACC-ASS-2022-00483",
    "ACC-ASS-2022-00484",
    "ACC-ASS-2022-00485",
    "ACC-ASS-2022-00486",
    "ACC-ASS-2022-00487",
    "ACC-ASS-2022-00488",
    "ACC-ASS-2022-00489",
    "ACC-ASS-2022-00490",
    "ACC-ASS-2022-00491",
    "ACC-ASS-2022-00492",
    "ACC-ASS-2022-00493",
    "ACC-ASS-2022-00494",
    "ACC-ASS-2022-00495",
    "ACC-ASS-2022-00496",
    "ACC-ASS-2022-00497",
    "ACC-ASS-2022-00498",
    "ACC-ASS-2022-00499",
    "ACC-ASS-2022-00500",
    "ACC-ASS-2022-00501",
    "ACC-ASS-2022-00502",
    "ACC-ASS-2022-00503",
    "ACC-ASS-2022-00504",
    "ACC-ASS-2022-00505",
    "ACC-ASS-2022-00506",
    "ACC-ASS-2022-00507",
    "ACC-ASS-2022-00508",
    "ACC-ASS-2022-00509",
    "ACC-ASS-2022-00510",
    "ACC-ASS-2022-00511",
    "ACC-ASS-2022-00512",
    "ACC-ASS-2022-00513",
    "ACC-ASS-2022-00514"
        ]
    for row in list_asset:    
        check_je = frappe.db.sql(""" SELECT NAME,remark FROM `tabJournal Entry` WHERE remark LIKE
            "Depreciation Entry From HO. {}%"  """.format(row))

        if len(check_je)>0:
          
            # delete gl_entry
            frappe.db.sql(""" DELETE FROM `tabGL Entry` WHERE voucher_no in (
                SELECT name FROM `tabJournal Entry` WHERE remark LIKE
                "Depreciation Entry From HO. {}%"
                ) """.format(row))
            # delete je account
            frappe.db.sql(""" DELETE FROM `tabJournal Entry Account` WHERE parent in (
                SELECT name FROM `tabJournal Entry` WHERE remark LIKE
                "Depreciation Entry From HO. {}%"
                ) """.format(row))
            # delete je
            frappe.db.sql(""" DELETE FROM `tabJournal Entry` WHERE name in (
                SELECT name FROM `tabJournal Entry` WHERE remark LIKE
                "Depreciation Entry From HO. {}%"
                ) """.format(row))
            print(row)

@frappe.whitelist()        
def apply_sales_taxes_and_charges():
    list_inv = frappe.db.sql(""" 
        SELECT NAME FROM `tabDelivery Note` 
        WHERE name = "DO-1-23-01-00359" """)
    # list_so = []
    # list_dn = []
    # for row in list_inv:
    #     doc_inv = frappe.get_doc("Sales Invoice", row)
    #     for row_item in doc_inv.items:
    #         if row_item.sales_order not in list_so:
    #             list_so.append(row_item.sales_order)
    #         if row_item.delivery_note not in list_dn:
    #             list_dn.append(row_item.delivery_note)

    # # patch_so 

    # for row in list_inv:
    #     patch_tax("Sales Order", row[0])

    for row in list_inv:
        patch_tax("Delivery Note", row[0])

    # for row in list_inv:
    #     patch_tax("Sales Invoice", row[0])
        

@frappe.whitelist()
def patch_tax(dt,dn):
   
    so_doc = frappe.get_doc(dt, dn)

    docstatus = so_doc.docstatus
    check = 0

    if docstatus == 1:
        check = 1
    frappe.db.sql(""" UPDATE `tab{}` SET docstatus = 0 WHERE name = "{}" """.format(dt,dn))
    so_doc = frappe.get_doc(dt, dn)
    print(dn)
    so_doc.taxes_and_charges = "INDONESIA TAX PENJUALAN 11 PERSEN - G"
    so_doc.taxes = []
    so_doc.append("taxes",get_taxes_and_charges("Sales Taxes and Charges Template",so_doc.taxes_and_charges)[0])
    for rowt in so_doc.taxes:
        rowt.parent = dt
    so_doc.calculate_taxes_and_totals()        
    so_doc.save()

    if check == 1:
        frappe.db.sql(""" UPDATE `tab{}` SET docstatus = 1 WHERE name = "{}" """.format(dt,dn))
        frappe.db.sql(""" UPDATE `tab{} Item` SET docstatus = 1 WHERE parent = "{}" """.format(dt,dn))
        frappe.db.sql(""" UPDATE `tabSales Taxes and Charges` SET docstatus = 1 WHERE parent = "{}" """.format(dt,dn))

        if dt == "Sales Invoice":
            repair_gl_entry_tanpa_sl(dt,dn)
        if dt == "Delivery Note":
            repair_gl_entry(dt,dn)

@frappe.whitelist()        
def apply_purchase_taxes_and_charges():
    list_inv = frappe.db.sql(""" 
        SELECT NAME FROM `tabPurchase Receipt` 
        WHERE name IN ("PRI-HO-1-22-12-02614","PRI-HO-1-22-12-02046") """)
    # list_so = []
    # list_dn = []
    # for row in list_inv:
    #     doc_inv = frappe.get_doc("Sales Invoice", row)
    #     for row_item in doc_inv.items:
    #         if row_item.sales_order not in list_so:
    #             list_so.append(row_item.sales_order)
    #         if row_item.delivery_note not in list_dn:
    #             list_dn.append(row_item.delivery_note)

    # # patch_so 

    # for row in list_inv:
    #     patch_tax_purchase("Purchase Order", row[0])

    for row in list_inv:
        patch_tax_purchase("Purchase Receipt", row[0])

    # for row in list_inv:
    #     patch_tax_purchase("Sales Invoice", row[0])
        

@frappe.whitelist()
def patch_tax_purchase(dt,dn):
   
    so_doc = frappe.get_doc(dt, dn)

    docstatus = so_doc.docstatus
    check = 0

    if docstatus == 1:
        check = 1
    frappe.db.sql(""" UPDATE `tab{}` SET docstatus = 0 WHERE name = "{}" """.format(dt,dn))
    so_doc = frappe.get_doc(dt, dn)
    print(dn)
    so_doc.taxes_and_charges = "Indonesia Tax 11 persen - G"
    so_doc.taxes = []
    so_doc.append("taxes",get_taxes_and_charges("Purchase Taxes and Charges Template",so_doc.taxes_and_charges)[0])
    for rowt in so_doc.taxes:
        rowt.parent = dt
    so_doc.calculate_taxes_and_totals()        
    so_doc.save()

    if check == 1:
        frappe.db.sql(""" UPDATE `tab{}` SET docstatus = 1 WHERE name = "{}" """.format(dt,dn))
        frappe.db.sql(""" UPDATE `tab{} Item` SET docstatus = 1 WHERE parent = "{}" """.format(dt,dn))
        frappe.db.sql(""" UPDATE `tabPurchase Taxes and Charges` SET docstatus = 1 WHERE parent = "{}" """.format(dt,dn))

        if dt == "Purchase Invoice":
            repair_gl_entry_tanpa_sl(dt,dn)
        if dt == "Purchase Receipt":
            repair_gl_entry(dt,dn)

@frappe.whitelist()
def buat_old_name(dt,nn,on):
    check = frappe.db.sql(""" SELECT * FROM `tabHistory Old Name` WHERE old_name = "{}" and new_name = "{}" """.format(on,nn))
    if len(check) == 0:
        hon = frappe.new_doc("History Old Name")
        hon.document_type = dt
        hon.old_name = on
        hon.new_name = nn
        hon.save()
        print("{}-{}".format(on,nn))
        frappe.db.commit()