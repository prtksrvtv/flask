import sqlite3 as sql
from datetime import datetime

def db_injector(dict_with_invoice_data):
    con = sql.connect('prikaway.db')
    cur = con.cursor()
    cur1=con.cursor()
    my_date= datetime.strptime(dict_with_invoice_data['Date'], '%Y-%m-%d')
    bill_no= 'PWPL/RW/'+str(my_date.year)+'/'+str(my_date.month)+'/'+str(dict_with_invoice_data['Roll No.'])
    for x in dict_with_invoice_data.keys():
        if x not in ['Roll No.','Name','Class','House','Date', 'Grand Total', 'Word Amount', 'Item Total']:
            cur1.execute("select id, item_name from products")
            for y in cur1.fetchall():
                if x==y[1]:
                    break
                           
            render=tuple([dict_with_invoice_data['Roll No.'],'"'+dict_with_invoice_data['Name']+'"',dict_with_invoice_data['Class'],'"'+dict_with_invoice_data['House']+'"',y[0],'"'+x+'"',dict_with_invoice_data[x][0],dict_with_invoice_data[x][2],False,'"'+dict_with_invoice_data['Date']+'"', '"'+bill_no+'"'])
            sql1='insert into sales(roll_no,student_name,class,house,item_id,item_purchased,item_quantity,total_price,tc_leave,date_of_purchase,bill_no) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
            cur.execute(sql1%render)
            con.commit()
    return bill_no

def db_search(dict_with_data):
    con = sql.connect('prikaway.db')
    cur = con.cursor()
    query=""" select item_purchased, p.item_price, sum(item_quantity), sum(total_price) 	
                    from sales s
                    join products p on p.id=s.item_id
                    where date_of_purchase BETWEEN ? AND ? group by item_purchased;""" 
    cur.execute(query,(dict_with_data['start_date'],dict_with_data['end_date']))
    return cur.fetchall()

def db_search_house_cover(dict_with_data):
    con = sql.connect('prikaway.db')
    cur = con.cursor()
    query=""" select roll_no, student_name, class, sum(item_quantity), sum(total_price) 	
                from sales s
                where date_of_purchase BETWEEN ? AND ? AND house=?
                group by roll_no, student_name, class 
                order by class,roll_no ;""" 
    cur.execute(query,(dict_with_data['start_date'],dict_with_data['end_date'],dict_with_data['House']))
    return cur.fetchall()

def db_search_all_house_cover(dict_with_data):
    con = sql.connect('prikaway.db')
    cur = con.cursor()
    query=""" select house, sum(item_quantity), sum(total_price) 	
                from sales
                where date_of_purchase BETWEEN ? AND ? group by house order by house;""" 
    cur.execute(query,(dict_with_data['start_date'],dict_with_data['end_date']))
    return cur.fetchall()
    
def db_delete_invoice(dict_with_data):
    con = sql.connect('prikaway.db')
    cur = con.cursor()
    query= """  select count(distinct bill_no) from sales where bill_no=? and date_of_purchase=? and class=?;  """
    cur.execute(query, (dict_with_data['bill_no'],dict_with_data['date_of_purchase'], dict_with_data['class']))
    records=cur.fetchall()
    for x in records:
        if x[0] == 0:
            return "NF"
        else:
            query= """delete from sales
                    where bill_no=? and date_of_purchase=? and class=?;""" 
            cur.execute(query,(dict_with_data['bill_no'],dict_with_data['date_of_purchase'], dict_with_data['class']))
            con.commit()
    return "S"