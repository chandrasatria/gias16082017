
import frappe
import time
import os
from frappe.utils import flt, add_months, cint, nowdate, getdate, today, date_diff, month_diff, add_days, get_last_day, get_datetime
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from addons.custom_standard.custom_stock_entry import custom_distribute_additional_costs,repair_gl_entry_tanpa_sl,repair_gl_entry_untuk_ste,patch_cost
from addons.custom_standard.custom_purchase_receipt import repair_gl_entry_untuk_pr
from erpnext.selling.doctype.customer.customer import get_credit_limit, get_customer_outstanding
from erpnext.controllers.accounts_controller import get_taxes_and_charges
from frappe.model.naming import make_autoname, revert_series_if_last

@frappe.whitelist()
def benerin_item():
    item_doc = frappe.get_doc("Item","C-GRAN-P-000044")
    item_doc.disabled = 0
    item_doc.db_update()

@frappe.whitelist()
def mana_ste():
    list_ste = frappe.db.sql(""" SELECT ste.name FROM `tabStock Entry` ste
        JOIN `tabStock Entry Detail` sted ON sted.parent= ste.name
        WHERE ste.stock_opname_number IS NOT NULL
        and ste.stock_entry_type = "Material Receipt"
        and sted.valuation_rate = 0
        and ste.docstatus = 0
        GROUP BY ste.name
     """)

    for row in list_ste:
        ste_doc = frappe.get_doc("Stock Entry",row[0])
        for row_item in ste_doc.items:
            row_item.allow_zero_valuation_rate = 0

        ste_doc.save()
        print(row[0])
        frappe.db.commit()

@frappe.whitelist()
def patch_sle():
    frappe.db.sql(""" UPDATE `tabStock Ledger Entry` set incoming_rate = 0 WHERE incoming_rate > 0 and voucher_type = "Delivery Note" and actual_qty < 0 """)


@frappe.whitelist()
def patch_sle_debug(self,method):
    frappe.db.sql(""" UPDATE `tabStock Ledger Entry` set incoming_rate = 0 WHERE incoming_rate > 0 and voucher_type = "Delivery Note" and actual_qty < 0 """)


@frappe.whitelist()
def patch_sle_benerin():
    frappe.db.sql(""" UPDATE `tabStock Ledger Entry` set incoming_rate = stock_value_difference / actual_qty
     WHERE incoming_rate = 0 AND actual_qty > 0 AND `stock_value_difference` > 0 """)

@frappe.whitelist()
def patch_bin():

    list_bin = frappe.db.sql(""" 
        SELECT item_code, warehouse, COUNT(NAME) jumlah 
        FROM `tabBin`
        GROUP BY item_code,warehouse
        HAVING jumlah > 1;
    """)

    for row in list_bin:
        list_satuan = frappe.db.sql(""" 
            SELECT NAME FROM `tabBin`
            WHERE item_code = "{}"
            AND warehouse = "{}"
            ORDER BY modified ASC
            LIMIT 1 
        """.format(row[0],row[1]))

        if list_satuan:
            frappe.db.sql(""" DELETE FROM `tabBin` WHERE name = "{}" """.format(list_satuan[0][0]))

@frappe.whitelist()
def patch_incoming():
    list_ste = frappe.db.sql(""" SELECT name FROM `tabStock Entry` WHERE name = "STER-PKU-1-23-10-00603" """)
    for row in list_ste:
        ste_doc = frappe.get_doc("Stock Entry",row[0])
        ste_doc.total_incoming_value = ste_doc.total_outgoing_value = 0.0
        for d in ste_doc.get("items"):
            if d.t_warehouse:
                ste_doc.total_incoming_value += flt(d.amount)
            if d.s_warehouse:
                ste_doc.total_outgoing_value += flt(d.amount)

        ste_doc.value_difference = ste_doc.total_incoming_value - ste_doc.total_outgoing_value
        print(ste_doc.value_difference)
        print(row[0])
        ste_doc.db_update()

@frappe.whitelist()
def patch_repack():
    list_ste = frappe.db.sql(""" 
        SELECT name FROM `tabStock Entry` ste
        WHERE ste.name IN ("STERE-BDG-1-23-03-00001") """)

    for row in list_ste:
        ste_doc = frappe.get_doc("Stock Entry", row[0])
        amount = 0
        total_qty = 0
        for item in ste_doc.items:
            if item.s_warehouse:
                amount += item.amount
            elif item.t_warehouse:
                total_qty += item.qty
                # item.valuation_rate = item.basic_rate
                # item.db_update()
        for item in ste_doc.items:
            if item.t_warehouse:
                item.set_basic_rate_manually = 1
                item.basic_rate = amount / total_qty
                rate = item.basic_rate
                item.basic_amount = rate * item.qty
                item.amount = rate * item.qty
                item.db_update()
        
        ste_doc.update_valuation_rate()
        for item in ste_doc.items:
            item.db_update()
        ste_doc.db_update()
        frappe.db.commit()

        ste_doc = frappe.get_doc("Stock Entry", row[0])
        ste_doc.total_incoming_value = ste_doc.total_outgoing_value = 0.0
        for d in ste_doc.get("items"):
            if d.t_warehouse:
                ste_doc.total_incoming_value += flt(d.amount)
            if d.s_warehouse:
                ste_doc.total_outgoing_value += flt(d.amount)

        ste_doc.value_difference = ste_doc.total_incoming_value - ste_doc.total_outgoing_value
        ste_doc.set_total_amount()
        ste_doc.db_update()
        frappe.db.commit()
    
        print(ste_doc.value_difference)
        repair_gl_entry_untuk_ste("Stock Entry",ste_doc.name)

@frappe.whitelist()
def patch_repack_2():
    list_ste = frappe.db.sql(""" 
        SELECT ste.name FROM `tabGL Entry` gl
        JOIN `tabStock Entry` ste ON ste.name=gl.`voucher_no`
        WHERE ste.`stock_entry_type`  = "Repack"
        AND gl.`account` LIKE "%HARGA POKOK%"
        AND gl.`is_cancelled` = 0 
    """)

    for row in list_ste:
        ste_doc = frappe.get_doc("Stock Entry", row[0])
        amount = 0
        total_qty = 0
        for item in ste_doc.items:
            if item.s_warehouse:
                if amount == 0:
                    amount += item.amount

            elif item.t_warehouse and amount != 0:
               
                item.set_basic_rate_manually = 1
                item.basic_rate = amount / item.qty
                rate = item.basic_rate
                item.basic_amount = rate * item.qty
                item.amount = rate * item.qty
                item.db_update()

                amount = 0
        
        ste_doc.update_valuation_rate()
        for item in ste_doc.items:
            item.db_update()
        ste_doc.db_update()
        frappe.db.commit()

        ste_doc = frappe.get_doc("Stock Entry", row[0])
        ste_doc.total_incoming_value = ste_doc.total_outgoing_value = 0.0
        for d in ste_doc.get("items"):
            if d.t_warehouse:
                ste_doc.total_incoming_value += flt(d.amount)
            if d.s_warehouse:
                ste_doc.total_outgoing_value += flt(d.amount)

        ste_doc.value_difference = ste_doc.total_incoming_value - ste_doc.total_outgoing_value
        ste_doc.set_total_amount()
        ste_doc.db_update()
        frappe.db.commit()
    
        print(ste_doc.value_difference)
        repair_gl_entry_untuk_ste("Stock Entry",ste_doc.name)

    repost_stock()

@frappe.whitelist()
def patch_ste_rk():
    list_ste = frappe.db.sql(""" 
       SELECT NAME,docstatus
        FROM `tabStock Entry`
        WHERE name = "STER-BJM-1-23-08-00031" """)

    for row_list in list_ste:
        # print(row_list[0])

        doc = frappe.get_doc("Stock Entry", row_list[0])
        doc.auto_assign_to_rk_account = 1
        doc.db_update()
        
        # repair_gl_entry_untuk_ste(doc.doctype,doc.name)
        for row in doc.items:
            if row.expense_account == "5001 - HARGA POKOK PENJUALAN - G":
                row.expense_account = "1168.04 - R/K STOCK - G"
                row.db_update()
        if row_list[1] == 1:
            frappe.db.sql(""" UPDATE `tabGL Entry` SET account = "{}" WHERE voucher_no = "{}" and account = "{}" """.format("1168.04 - R/K STOCK - G",row_list[0],"5001 - HARGA POKOK PENJUALAN - G"))
            frappe.db.sql(""" UPDATE `tabGL Entry Custom` SET account = "{}" WHERE no_voucher = "{}" and account = "{}" """.format("1168.04 - R/K STOCK - G",row_list[0],"5001 - HARGA POKOK PENJUALAN - G"))


        print("{}-{}".format(row_list[0],row_list[1]))

@frappe.whitelist()
def patch_ste_rk_receipt():
    list_ste = frappe.db.sql(""" 
        SELECT name, docstatus FROM `tabStock Entry` 
        WHERE stock_entry_type = "Material Receipt" and transfer_status = "From Sync" and auto_assign_to_rk_account = 0 """)

    for row_list in list_ste:
        doc = frappe.get_doc("Stock Entry", row_list[0])
        doc.auto_assign_to_rk_account = 1
        doc.db_update()
        
        # for row in doc.items:
        #     if row.expense_account == "5001 - HARGA POKOK PENJUALAN - G":
        #         row.expense_account = "1168.04 - R/K STOCK - G"
        #         row.db_update()
        # if row_list[1] == 1:
        #     frappe.db.sql(""" UPDATE `tabGL Entry` SET account = "{}" WHERE voucher_no = "{}" and account = "{}" """.format("1168.04 - R/K STOCK - G",row_list[0],"5001 - HARGA POKOK PENJUALAN - G"))
        #     frappe.db.sql(""" UPDATE `tabGL Entry Custom` SET account = "{}" WHERE no_voucher = "{}" and account = "{}" """.format("1168.04 - R/K STOCK - G",row_list[0],"5001 - HARGA POKOK PENJUALAN - G"))

        print("{}-{}".format(row_list[0],row_list[1]))
@frappe.whitelist()
def patch_doctype():
    ambil_doc = frappe.get_doc("DocType","Stock Ledger Entry")
    check = 0
    remove = []
    ambil_doc.read_only = 0
    ambil_doc.save()
    frappe.db.commit()

@frappe.whitelist()
def start_repair():
    list_document = frappe.db.sql(""" 
        SELECT sle.voucher_type,sle.`voucher_no`
        FROM `tabStock Ledger Entry` sle
       
        WHERE sle.posting_date = "2023-03-01" and sle.is_cancelled = 0
        GROUP BY sle.`voucher_no` 
        ORDER BY sle.`posting_date`

    """)
    for row in list_document:
        if row[0] == "Stock Reconciliation":
            repair_gl_entry("Stock Reconciliation",row[1])
        elif row[0] == "Stock Entry":
            repair_gl_entry_untuk_ste(row[0],row[1])
        elif row[0] == "Delivery Note":
            repair_gl_entry_untuk_dn(row[0],row[1])
        elif row[0] == "Purchase Receipt":
            repair_gl_entry_untuk_pr(row[0],row[1])


        print(row[1])
        frappe.db.commit()

    enqueue_repost_stock()

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

@frappe.whitelist()
def lakukan_testing_1():
    company_doc = frappe.get_doc("Company", "GIAS")
   
    list_dn = frappe.db.sql(""" 
       SELECT voucher_no

        FROM(
        SELECT voucher_no, COUNT(voucher_detail_no) AS co FROM `tabStock Ledger Entry`
        WHERE voucher_type = "Delivery Note"
        AND is_cancelled = 0
        GROUP BY voucher_detail_no
        HAVING co > 1
        ) a
        GROUP BY voucher_no """)

    for row in list_dn:
        repair_gl_entry_untuk_dn("Delivery Note",row[0])
        frappe.db.commit()

    repost_stock()

@frappe.whitelist()
def repair_gl_entry_untuk_dn_debug():
    list_dn = frappe.db.sql(""" 

        SELECT name FROM `tabDelivery Note` 
        WHERE posting_date = "2022-05-25"
        ORDER BY posting_date """)
    for row in list_dn:
        repair_gl_entry_untuk_dn("Delivery Note",row[0])
        frappe.db.commit()

    repost_stock()

@frappe.whitelist()
def repair_gl_entry_untuk_dn_debug_2():
    list_dn = frappe.db.sql(""" 

        SELECT "DO-1-23-10-00473" """)
    for row in list_dn:
        repair_gl_entry_untuk_dn("Delivery Note",row[0])
        frappe.db.commit()

    repost_stock()

@frappe.whitelist()
def repair_gl_entry_untuk_ste_debug_2():
    list_dn = frappe.db.sql(""" 

        SELECT 
        gle.voucher_no, gle.account, gle.debit, gle.credit 
        FROM `tabGL Entry` gle 
        JOIN `tabStock Entry` ste ON ste.name = gle.`voucher_no`
        WHERE 
        gle.voucher_no LIKE "%ster%"
        AND ste.sync_name IS NOT NULL
        AND gle.account LIKE "%biaya lain%"
        AND (gle.debit > 10 OR gle.credit > 10)
        AND gle.`is_cancelled` = 0
        AND ste.`purpose` = "Material Receipt"
        ORDER BY ste.posting_date

    """)
    for row in list_dn:
        repair_gl_entry_untuk_ste("Stock Entry",row[0])
        frappe.db.commit()

    repost_stock()

@frappe.whitelist()
def recount_ste_tools():
    from addons.addons.doctype.stock_recount_tools.stock_recount_tools import start_stock_recount_stei_by_name
    start_stock_recount_stei_by_name("STEI-HO-22-09-01768")
    from addons.addons.doctype.stock_recount_tools.stock_recount_tools import start_stock_recount_stei_by_name
    start_stock_recount_stei_by_name("STEI-HO-1-23-09-02743")
    from addons.addons.doctype.stock_recount_tools.stock_recount_tools import start_stock_recount_stei_by_name
    start_stock_recount_stei_by_name("STEI-HO-1-23-09-02813")
    


@frappe.whitelist()
def repair_gl_entry_untuk_ste_debug_3():
    from addons.addons.doctype.stock_recount_tools.stock_recount_tools import debug_start_stock_recount_stei_by_name
    debug_start_stock_recount_stei_by_name("db_pku")

@frappe.whitelist()
def repair_gl_entry_untuk_ste_debug_per_site():
    from addons.addons.doctype.stock_recount_tools.stock_recount_tools import debug_start_stock_recount_stei_by_name
    debug_start_stock_recount_stei_by_name("db_kdi")

@frappe.whitelist()
def repair_gl_entry_untuk_ste_debug_per_site2():
    from addons.addons.doctype.stock_recount_tools.stock_recount_tools import debug_start_stock_recount_stei_by_name
    debug_start_stock_recount_stei_by_name("db_kdi")

@frappe.whitelist()
def repair_gl_entry_untuk_ste_debug_per_site3():
    from addons.addons.doctype.stock_recount_tools.stock_recount_tools import debug_start_stock_recount_stei_by_name
    debug_start_stock_recount_stei_by_name("db_kdi")

@frappe.whitelist()
def enqueue_repair_gl_entry_untuk_ste_debug_3():
    enqueued_method = "addons.patch_ste.repair_gl_entry_untuk_ste_debug_3"
    frappe.enqueue(method=enqueued_method,timeout=18000, queue='long')
    
@frappe.whitelist()
def repair_gl_entry_untuk_ste_debug_4():
    print("test")
    
@frappe.whitelist()
def repair_gl_entry_untuk_ste_debug():
    list_dn = frappe.db.sql(""" 

        SELECT name FROM `tabStock Entry` WHERE name IN (
            "STER-JBR-22-04-00001",
            "STER-JBR-22-09-00042",
            "STER-JBR-1-23-09-00076",
            "STER-JBR-1-23-09-00077",
            "STEI-HO-22-03-03298",
            "STEI-HO-22-09-01768",
            "STEI-HO-1-23-09-02743",
            "STEI-HO-1-23-09-02813"
        )

         """)
    for row in list_dn:
        # patch_cost(row[0])
        repair_gl_entry_untuk_ste("Stock Entry",row[0])
        frappe.db.commit()

    repost_stock()

@frappe.whitelist()
def repair_gl_entry_untuk_pr_debug():
    list_dn = frappe.db.sql(""" 

        SELECT name FROM `tabPurchase Receipt` 
        WHERE name IN 
        ("PRI-HO-1-23-09-00320") """)
    for row in list_dn:
        repair_gl_entry_untuk_pr("Purchase Receipt",row[0])
        frappe.db.commit()

    repost_stock()

@frappe.whitelist()
def repair_gl_entry_untuk_dn(doctype,docname):
    repair_gl_entry(doctype,docname)
    from addons.custom_standard.view_ledger_create import create_gl_custom_delivery_note_by_name
    create_gl_custom_delivery_note_by_name(docname,"on_submit")
 

@frappe.whitelist()
def repost_stock():
    from erpnext.stock.doctype.repost_item_valuation.repost_item_valuation import debug_repost
    debug_repost()

@frappe.whitelist()
def enqueue_repost_stock():
    enqueued_method = "addons.patch_ste.repost_stock"
    frappe.enqueue(method=enqueued_method,timeout=18000, queue='long')

@frappe.whitelist()
def cancel_je_auto_repeat():
    list_je = frappe.db.sql(""" 
        SELECT tje.name
        FROM `tabJournal Entry` tje 
        JOIN `tabAuto Repeat` tar ON tar.name = tje.`auto_repeat`
        AND tje.`posting_date` > tar.`end_date`
        AND tje.docstatus = 1
        AND DATEDIFF(tje.`posting_date`, tar.end_date) > 1 
    """)
    for row in list_je:
        print(row[0])

@frappe.whitelist()
def isi_ste_log():
    list_ste = frappe.db.sql(""" 
        SELECT NAME,docstatus,sync_name, transfer_ke_cabang_mana
        FROM `tabStock Entry`
        WHERE sync_name IS NOT NULL
        AND transfer_status="On The Way"
        AND purpose = "Material Issue"
        AND ste_log IS NOT NULL
        AND transfer_ke_cabang_mana NOT IN ("TRIBUANA BUMIPUSAKA","GIAS TANJUNG UNCANG","GIAS TANJUNG PINANG");
    """)
    for row in list_ste:
        ste = frappe.get_doc("Stock Entry",row[0])
        ste_log = ste.ste_log
        print(ste_log)

        from addons.custom_method import check_list_company_gias
        event_producer = check_list_company_gias(ste.transfer_ke_cabang_mana)
        nama_db = event_producer.replace("erp-","db_").replace(".gias.co.id","")
        if nama_db == "db_pal":
            nama_db = "db_palu"

        check_ste = frappe.db.sql(""" SELECT name,docstatus FROM `{}`.`tabStock Entry` WHERE ste_log = "{}" and docstatus < 2 and stock_entry_type = "Material Receipt" """.format(nama_db,ste_log),debug=1)
        if check_ste:
            if check_ste[0][0]:
                if check_ste[0][1] == 0:
                    ste.sync_name = check_ste[0][0]
                    ste.db_update()
                    print(check_ste[0][0])
                    frappe.db.commit()


@frappe.whitelist()
def nyari_buat_balance_sheet():
    company_doc = frappe.get_doc("Company", "GIAS")
   
    list_dn = frappe.db.sql(""" 
        SELECT sle.voucher_type,sle.voucher_no , 
        gle.credit AS satu,SUM(sle.stock_value_difference * -1) AS dua,
        gle.credit - SUM(sle.stock_value_difference * -1) AS tiga

         FROM `tabStock Ledger Entry` sle 
        LEFT JOIN `tabGL Entry` gle ON sle.voucher_no = gle.voucher_no

        WHERE 
        (gle.voucher_type = "Stock Entry" OR gle.voucher_type = "Delivery Note")
        AND (gle.account LIKE "%persediaan%" OR gle.account LIKE "%perlengkapan -%" )
        AND gle.credit > 0 
        AND gle.is_cancelled = 0
        GROUP BY gle.voucher_no
        HAVING satu - dua > 0.01 OR satu - dua < -0.01

    """)

    for row in list_dn:
        if row[0] == "Stock Entry":
            repair_gl_entry_untuk_ste(row[0],row[1])
        else:
            repair_gl_entry_untuk_dn(row[0],row[1])
        print(row[0])
        frappe.db.commit()
    repost_stock()