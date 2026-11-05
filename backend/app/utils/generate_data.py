import csv
from pathlib import Path

TRAINING_DATA = [
    # Salary
    ("ACH CREDIT TECHCORP SALARY MAY 2024", "Salary"),
    ("SALARY CREDIT WIPRO LTD MAY24", "Salary"),
    ("INFOSYS TECHNOLOGIES DIRECT DEP SALARY", "Salary"),
    ("NEFT CR-SALARY-TCS LTD MUMBAI", "Salary"),
    ("MONTHLY PAYROLL DIRECT DEPOSIT COGNIZANT", "Salary"),
    ("SALARY FOR THE MONTH OF APRIL 2024", "Salary"),
    ("ACCENTURE SERVICES PVT LTD SALARY CR", "Salary"),
    ("MONTHLY STIPEND RESEARCH INTERNSHIP", "Salary"),
    ("DIR DEP PAYROLL AMAZON DEV CENTRE", "Salary"),
    ("CREDIT SALARY GOOGLE INDIA PVT LTD", "Salary"),
    ("REMUNERATION CONSULTING RETAINER MAY", "Salary"),
    ("MICROSOFT INDIA PAYROLL CLEARING", "Salary"),
    ("DELOITTE TAX SERVICES SALARY DISBURSEMENT", "Salary"),
    ("HCL TECH MONTHLY SALARY CREDIT", "Salary"),
    ("PAYROLL CREDIT CAPGEMINI INDIA", "Salary"),

    # Food & Dining
    ("POS SWIGGY BANGALORE IN", "Food & Dining"),
    ("ZOMATO ORDER #49102 GURGAON", "Food & Dining"),
    ("MCDONALDS MUMBAI STORE 201", "Food & Dining"),
    ("STARBUCKS COFFEE KORAMANGALA BLR", "Food & Dining"),
    ("DOMINOS PIZZA ONLINE ORDER 8912", "Food & Dining"),
    ("CAFE COFFEE DAY AIRPORT TERMINAL 1", "Food & Dining"),
    ("BARBEQUE NATION DINNER FOR 4", "Food & Dining"),
    ("CHAAYOS CONNAUGHT PLACE NEW DELHI", "Food & Dining"),
    ("SUBWAY SANDWICHES BANDRA WEST", "Food & Dining"),
    ("KFC RESTAURANT SEC 29 GURGAON", "Food & Dining"),
    ("BURGER KING INDIRANAGAR BANGALORE", "Food & Dining"),
    ("PIZZA HUT DINE IN POWAI", "Food & Dining"),
    ("HALDIRAMS RESTAURANT NOIDA", "Food & Dining"),
    ("SWIGGY INSTAMART FOOD KITCHEN", "Food & Dining"),
    ("THE BLACK PEARL RESTAURANT BUFFET", "Food & Dining"),
    ("BLUE TOKAI COFFEE ROASTERS", "Food & Dining"),
    ("THIRD WAVE COFFEE ROASTERS PUNE", "Food & Dining"),
    ("BEHROUZ BIRYANI CLOUD KITCHEN", "Food & Dining"),
    ("FAASOS EATS ONLINE ORDER", "Food & Dining"),
    ("MAINLAND CHINA RESTAURANT CHENNAI", "Food & Dining"),

    # Shopping
    ("AMAZON PAY INDIA MUMBAI RETAIL", "Shopping"),
    ("FLIPKART INTERNET BANGALORE ORDER", "Shopping"),
    ("MYNTRA DESIGNS PVT LTD FASHION", "Shopping"),
    ("RELIANCE SMART BAZAAR GROCERIES", "Shopping"),
    ("DMART SUPERMARKET THANE WEST", "Shopping"),
    ("ZARA PALLADIUM MALL LOWER PAREL", "Shopping"),
    ("H&M CLOTHING STORE PHOENIX MARKETCITY", "Shopping"),
    ("IKEA INDIA HOME FURNISHING HYD", "Shopping"),
    ("CROMA ELECTRONICS STORE KORAMANGALA", "Shopping"),
    ("DECATHLON SPORTS INDIA GEAR", "Shopping"),
    ("NYKAA E-RETAIL COSMETICS", "Shopping"),
    ("BIGBASKET SUPERMARKET ONLINE", "Shopping"),
    ("BLINKIT GROCERY DELIVERY IN 10 MIN", "Shopping"),
    ("ZEPTO QUICK COMMERCE GROCERIES", "Shopping"),
    ("VIJAY SALES ELECTRONICS BANDRA", "Shopping"),
    ("AJIO ONLINE TRENDS CLOTHING", "Shopping"),
    ("SHOPPERS STOP DEPT STORE ANDHERI", "Shopping"),
    ("LIFESTYLE INTERNATIONAL CLOTHING", "Shopping"),
    ("TATA CLIQ LUXURY APPAREL", "Shopping"),
    ("UNIQLO AMBIENCE MALL GURGAON", "Shopping"),

    # Rent
    ("UPI/RENT/MR SHARMA/HDFC BANK", "Rent"),
    ("MONTHLY FLAT RENT MAY FLAT 402", "Rent"),
    ("NOBROKER HOUSING RENT PAYMENT", "Rent"),
    ("APARTMENT SOCIETY MAINTENANCE CHARGES", "Rent"),
    ("OFFICE SPACE LEASE RENT KORAMANGALA", "Rent"),
    ("LANDLORD PROPERTY RENT TRANSFER", "Rent"),
    ("HOUSE RENT FOR THE MONTH OF JUNE", "Rent"),
    ("TRF TO RAJESH GUPTA TOWARDS RENT", "Rent"),
    ("RESIDENTIAL LEASE PAYMENT MAY 2024", "Rent"),
    ("COMMERCIAL SHOP RENT DEFENCE COLONY", "Rent"),

    # Utilities & Bills
    ("ELECTRICITY BILL TATA POWER MUMBAI", "Utilities & Bills"),
    ("BESCOM BANGALORE ONLINE ELEC BILL", "Utilities & Bills"),
    ("AIRTEL BROADBAND BILLPAY FIBER", "Utilities & Bills"),
    ("JIO PREPAID RECHARGE 666 PLAN", "Utilities & Bills"),
    ("MAHANAGAR GAS LTD PIPELINE BILL", "Utilities & Bills"),
    ("BWSSB WATER SUPPLY BILL WATER BOARD", "Utilities & Bills"),
    ("TATA PLAY DTH RECHARGE MONTHLY", "Utilities & Bills"),
    ("ACT FIBERNET INTERNET BILLPAY", "Utilities & Bills"),
    ("INDANE LPG CYLINDER REFILL BOOKING", "Utilities & Bills"),
    ("BHARAT GAS COMMERCIAL CYLINDER", "Utilities & Bills"),
    ("ADANI ELECTRICITY BILL PAYMENT", "Utilities & Bills"),
    ("VODAFONE IDEA POSTPAID MOBILE BILL", "Utilities & Bills"),
    ("TORRENT POWER LIMITED ELEC BILL", "Utilities & Bills"),
    ("AIRTEL DIGITAL TV DTH MONTHLY PACK", "Utilities & Bills"),

    # Travel & Transport
    ("UBER INDIA RIDES BANGALORE TRIP", "Travel & Transport"),
    ("OLA CABS TRIP #90212 AIRPORT DROP", "Travel & Transport"),
    ("IRCTC TICKET BOOKING NEW DELHI", "Travel & Transport"),
    ("INDIGO AIRLINES FLIGHT 6E-204 BOM-DEL", "Travel & Transport"),
    ("BPCL PETROL PUMP WHITEFIELD FUEL", "Travel & Transport"),
    ("HPCL AUTO LPG STATION SEC 18", "Travel & Transport"),
    ("INDIAN OIL FUEL DISPENSER DIESEL", "Travel & Transport"),
    ("FASTAG TOLL PLAZA NH48 HIGHWAY", "Travel & Transport"),
    ("DELHI METRO RECHARGE DMRC SMART CARD", "Travel & Transport"),
    ("RAPIDO BIKE TAXI COMMUTE RIDE", "Travel & Transport"),
    ("AIR INDIA FLIGHT TICKETS BKK", "Travel & Transport"),
    ("MAKEMYTRIP HOLIDAYS HOTEL & FLIGHT", "Travel & Transport"),
    ("SHELL PETROL STATION BELLARY ROAD", "Travel & Transport"),
    ("MUMBAI METRO ONE SMART CARD RELOAD", "Travel & Transport"),
    ("YATRA ONLINE TRAVEL TICKETS", "Travel & Transport"),

    # ATM Withdrawal
    ("ATM CASH WDL HDFC INDIRANAGAR", "ATM Withdrawal"),
    ("NFS CASH WITHDRAWAL SBI ATM #401", "ATM Withdrawal"),
    ("EAW ATM WDL KOTAK MAHINDRA BANK", "ATM Withdrawal"),
    ("ATM WDL CIRRUS/MAESTRO CASH WITHDRAW", "ATM Withdrawal"),
    ("CASH WITHDRAWAL ICICI ATM CONNAUGHT", "ATM Withdrawal"),
    ("ATM DISPENSE CASH AXIS BANK KORAMANGALA", "ATM Withdrawal"),
    ("WDL NFS 8901 CASH BANK OF BARODA ATM", "ATM Withdrawal"),
    ("PUNJAB NATL BANK ATM WITHDRAWAL", "ATM Withdrawal"),

    # Bank Charges
    ("CONSOLIDATED CHARGES FOR DEBIT CARD", "Bank Charges"),
    ("SMS ALERT CHARGES Q1 2024", "Bank Charges"),
    ("MINIMUM BALANCE NON MAINTENANCE CHG", "Bank Charges"),
    ("OUTWARD CHEQUE RETURN CHARGES UNPAID", "Bank Charges"),
    ("GST @ 18% ON BANK SERVICE CHARGES", "Bank Charges"),
    ("ANNUAL DEBIT CARD MAINTENANCE FEE AMC", "Bank Charges"),
    ("OVERDRAFT INTEREST CHARGES MAY", "Bank Charges"),
    ("INTERNATIONAL ATM USAGE FEE", "Bank Charges"),
    ("CONVENIENCE CHARGE ONLINE ECS TRANSACTION", "Bank Charges"),
    ("LEDGER FOLIO CHARGES HDFC", "Bank Charges"),

    # Investments
    ("ZERODHA BROKING LTD EQUITY ADD FUNDS", "Investments"),
    ("GROWW INVESTMENTS MUTUAL FUND PURCHASE", "Investments"),
    ("UTI NIFTY 50 INDEX FUND SIP AUTO DEBIT", "Investments"),
    ("HDFC BALANCED ADVANTAGE SIP DIRECT GROWTH", "Investments"),
    ("DIVIDEND CR ITC LIMITED 500 SHARES", "Investments"),
    ("TERM DEPOSIT INTEREST CREDIT QUARTERLY", "Investments"),
    ("RECURRING DEPOSIT MONTHLY INSTALLMENT RD", "Investments"),
    ("ANGEL ONE SECURITIES TRADING ACCOUNT", "Investments"),
    ("UPSTOX CAPITAL MARKETS MARGIN TOPUP", "Investments"),
    ("SBI MUTUAL FUND EQUITY HYBRID SIP", "Investments"),
    ("NPS NATIONAL PENSION SCHEME TIER 1", "Investments"),
    ("PPF PUBLIC PROVIDENT FUND TRANSFER", "Investments"),

    # Transfers
    ("UPI/412984920194/TRANSFER TO RAHUL VERMA", "Transfers"),
    ("IMPS-P2A-491028301-TRANSFER TO PRIYA S", "Transfers"),
    ("NEFT DR-HDFC0001234-SAVINGS TRANSFER", "Transfers"),
    ("ACH DEBIT WIRE TO SIBLING ACCOUNT", "Transfers"),
    ("FUNDS TRANSFER TO ACC 98201 DEEPAK", "Transfers"),
    ("RTGS TRANSFER TO VENDOR CLEARING", "Transfers"),
    ("UPI/501928401/SENT TO FRIEND DINNER SPLIT", "Transfers"),
    ("SELF TRANSFER TO SBI SAVINGS ACCOUNT", "Transfers"),
    ("NEFT CR-MR ANAND DESHMUKH PAYMENT", "Transfers"),
    ("IMPS OUTWARD FUND TRANSFER 77201", "Transfers"),

    # Healthcare
    ("APOLLO PHARMACY MEDICAL STORE BLR", "Healthcare"),
    ("1MG TECHNOLOGIES MEDICINES ORDER", "Healthcare"),
    ("MAX SUPER SPECIALITY HOSPITAL BILL", "Healthcare"),
    ("MEDPLUS PHARMACY ONLINE DELIVERY", "Healthcare"),
    ("LAL PATHLABS BLOOD TEST DIAGNOSTICS", "Healthcare"),
    ("DR BATRA CLINIC CONSULTATION FEE", "Healthcare"),
    ("FORTIS HOSPITAL OPD DOCTOR CHARGES", "Healthcare"),
    ("DENTAL CARE CLINIC ROOT CANAL", "Healthcare"),
    ("NETMEDS MARKETPLACE PHARMACEUTICALS", "Healthcare"),
    ("MANIPAL HOSPITAL HEALTH CHECKUP PACK", "Healthcare"),

    # Education
    ("DELHI PUBLIC SCHOOL TERM 1 FEE", "Education"),
    ("NIRMA UNIVERSITY TUITION FEES SEMESTER", "Education"),
    ("COURSERA CERTIFICATION COURSE DATA SCIENCE", "Education"),
    ("UDEMY ONLINE COURSE PYTHON DEVELOPMENT", "Education"),
    ("BYJUS LEARNING SUBSCRIPTION CLASS 10", "Education"),
    ("OXFORD UNIVERSITY PRESS TEXTBOOKS", "Education"),
    ("ALLEN CAREER INSTITUTE COACHING FEES", "Education"),
    ("UNACADEMY SUBSCRIPTION PLUS IIT JEE", "Education"),
    ("BRITISH COUNCIL LIBRARY ANNUAL MEMBERSHIP", "Education"),

    # Others
    ("MISCELLANEOUS SUNDRY CLEARING ADJUSTMENT", "Others"),
    ("UNKNOWN ENTRY BATCH ID #9042", "Others"),
    ("INTERNAL RECONCILIATION DIFFERENCE MEMO", "Others"),
    ("REFUND ROUNDING CORRECTION", "Others"),
    ("SETTLEMENT REVERSAL ENTRY #0029", "Others")
]

def generate_csv(dest_path: Path):
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    with open(dest_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["description", "category"])
        for desc, cat in TRAINING_DATA:
            writer.writerow([desc, cat])
    print(f"Generated {len(TRAINING_DATA)} training rows at {dest_path}")

if __name__ == "__main__":
    p = Path(__file__).resolve().parent.parent / "data" / "training_data.csv"
    generate_csv(p)
