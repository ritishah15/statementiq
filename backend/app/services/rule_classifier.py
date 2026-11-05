import os
import re
import json
from typing import Tuple, Optional, Dict, List
from app.config import DATA_DIR, STANDARD_CATEGORIES

DEFAULT_RULES = {
    "Salary": [
        "SALARY", "PAYROLL", "DIR DEP", "DIRECT DEP", "MONTHLY SAL",
        "STIPEND", "WAGES", "REMUNERATION", "HONORARIUM", "TECHCORP SALARY",
        "WIPRO SALARY", "INFOSYS SALARY", "TCS SALARY", "SALARY CREDIT"
    ],
    "Food & Dining": [
        "SWIGGY", "ZOMATO", "RESTAURANT", "MCDONALD", "STARBUCKS", "DOMINOS",
        "PIZZA", "BURGER", "CAFE", "COFFEE", "BAKERY", "DINER", "KITCHEN",
        "EATS", "FOODS", "FOOD", "SUBWAY", "KFC", "CHAI", "SWEETS", "BISTRO",
        "GROCERY", "GROCERIES", "SUPERMARKET", "PROVISION", "ZEPTO", "BLINKIT",
        "BIGBASKET", "DUNZO", "INSTAMART", "NATURES BASKET"
    ],
    "Shopping": [
        "AMAZON", "FLIPKART", "MYNTRA", "AJIO", "RELIANCE RETAIL", "ZARA",
        "H&M", "DMART", "MART", "WALMART", "TARGET", "SHOPPING", "APPAREL",
        "CROCS", "DECATHLON", "IKEA", "CROMA", "VIJAY SALES", "RETAIL STORE",
        "DEPARTMENT STORE", "CLOTHING STORE", "MEESHO", "NYKAA", "TATA CLIQ"
    ],
    "Travel & Transport": [
        "UBER", "OLA", "RAPIDO", "IRCTC", "RAILWAY", "METRO", "AIRLINES",
        "INDIGO", "AIR INDIA", "SPICEJET", "MAKEMYTRIP", "YATRA", "CLEARTRIP",
        "PETROL", "DIESEL", "FUEL", "IOCL", "BPCL", "HPCL", "SHELL", "FASTAG",
        "TOLL", "PARKING", "CAB", "AUTO", "FLIGHT", "BUS TICKET", "RED BUS"
    ],
    "Utilities & Bills": [
        "ELECTRICITY", "POWER", "BESCOM", "TATA POWER", "ADANI ELEC",
        "WATER BILL", "GAS BILL", "INDANE", "BHARAT GAS", "BILLPAY",
        "RECHARGE", "AIRTEL", "JIO", "VODAFONE", "VI PREPAID", "BROADBAND",
        "ACT FIBERNET", "WIFI", "DTH", "TATA PLAY", "POSTPAID", "UTILITY"
    ],
    "Rent": [
        "RENT", "HOUSE RENT", "FLAT RENT", "OFFICE RENT", "NOBROKER",
        "LANDLORD", "TENANCY", "APARTMENT RENT", "MAINTENANCE CHARGE", "SOCIETY MAINT"
    ],
    "Healthcare": [
        "PHARMACY", "MEDICAL", "HOSPITAL", "CLINIC", "APOLLO", "1MG", "MEDPLUS",
        "NETMEDS", "HEALTHCARE", "DOCTOR", "DIAGNOSTICS", "DENTAL",
        "PATHOLOGY", "LAB", "MEDICINE", "WELLNESS", "MAX HEALTHCARE", "FORTIS"
    ],
    "Education": [
        "SCHOOL", "COLLEGE", "UNIVERSITY", "TUITION", "INSTITUTE", "ACADEMY",
        "EDUCATION", "FEES", "EXAM FEE", "COURSERA", "UDEMY", "UNACADEMY",
        "BYJUS", "TEXTBOOK", "LIBRARY", "COURSE"
    ],
    "EMI/Loan": [
        "EMI", "LOAN", "HOME LOAN", "CAR LOAN", "PERSONAL LOAN", "BAJAJ FINANCE",
        "HDFC LOAN", "SBI LOAN", "AUTO LOAN", "EDUCATION LOAN", "MORTGAGE",
        "HOUSING FINANCE", "CREDIT CARD BILL", "CRED EMI", "LOAN REPAYMENT"
    ],
    "ATM Withdrawal": [
        "ATM", "CASH WDL", "CASH WITHDRAWAL", "NFS ATM", "EAW ATM", "ATM WDL", "SELF WDL"
    ],
    "Bank Charges": [
        "BANK CHARGES", "SERVICE CHARGE", "SERVICE CHARGES", "SMS CHARGES", "SMS ALERT", "SMS", "ANNUAL FEE", "AMC",
        "LEDGER FEE", "PENALTY", "INTEREST CHG", "GST ON CHARGES", "CHG", "CHARGES", "BANK FEE",
        "CONVENIENCE FEE", "RETURN CHARGES", "NON MAINT", "MIN BAL CHG"
    ],
    "Interest": [
        "INTEREST CR", "FD INTEREST", "SAVINGS INTEREST", "INT.PAID", "CREDIT INTEREST",
        "INTEREST EARNED", "TERM DEP INT", "RD INTEREST", "INTEREST RECEIVED"
    ],
    "Refunds": [
        "REFUND", "CASHBACK", "REVERSAL", "CHARGEBACK", "RETURN CREDIT", "REFUNDED",
        "REVERSED", "MERCHANT REFUND", "PAYMENT REVERSAL"
    ],
    "Investments": [
        "ZERODHA", "GROWW", "UPSTOX", "MUTUAL FUND", "SIP", "EQUITY", "SECURITIES",
        "DEMAT", "SHAREKHAN", "ANGEL ONE", "INVESTMENT", "STOCKS", "KITE"
    ],
    "Other Income": [
        "DIVIDEND", "BONUS", "PRIZE", "GRANT", "SETTLEMENT", "ANNUITY",
        "ROYALTY", "INCENTIVE", "CASH PRIZE", "INCOME TAX REFUND"
    ],
    "Other Expenses": [
        "MISCELLANEOUS", "DONATION", "CHARITY", "FINE", "STAMP DUTY",
        "SUBSCRIPTION", "MEMBERSHIP", "OTHERS", "SUNDRY"
    ],
    "Transfers": [
        "NEFT", "IMPS", "RTGS", "UPI", "FUND TRANSFER", "FT", "TRF",
        "WIRE TRANSFER", "ACH", "SELF TRANSFER", "P2P", "TRANSFER TO", "TRANSFER"
    ]
}

class RuleClassifier:
    """Deterministic, non-LLM regex and keyword matching classification engine with priority ordering."""

    def __init__(self, rules_file: Optional[str] = None):
        self.rules_file = rules_file or str(DATA_DIR / "rules.json")
        self.custom_rules_file = str(DATA_DIR / "custom_rules.json")
        self.rules: Dict[str, List[str]] = self.load_rules()
        self.custom_rules: Dict[str, List[str]] = self.load_custom_rules()

    def load_rules(self) -> Dict[str, List[str]]:
        try:
            if os.path.exists(self.rules_file):
                with open(self.rules_file, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    for cat, kws in DEFAULT_RULES.items():
                        if cat not in loaded:
                            loaded[cat] = kws
                    return loaded
        except Exception:
            pass
        self.save_rules(DEFAULT_RULES)
        return DEFAULT_RULES

    def load_custom_rules(self) -> Dict[str, List[str]]:
        try:
            if os.path.exists(self.custom_rules_file):
                with open(self.custom_rules_file, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception:
            pass
        return {}

    def save_rules(self, rules: Dict[str, List[str]]):
        try:
            with open(self.rules_file, "w", encoding="utf-8") as f:
                json.dump(rules, f, indent=2)
        except Exception:
            pass

    def save_custom_rules(self, custom_rules: Dict[str, List[str]]):
        try:
            with open(self.custom_rules_file, "w", encoding="utf-8") as f:
                json.dump(custom_rules, f, indent=2)
        except Exception:
            pass

    def add_custom_rule(self, category: str, keyword: str):
        """Adds a high-priority user-defined custom rule."""
        if category not in self.custom_rules:
            self.custom_rules[category] = []
        kw_clean = keyword.strip().upper()
        if kw_clean not in [k.upper() for k in self.custom_rules[category]]:
            self.custom_rules[category].append(kw_clean)
            self.save_custom_rules(self.custom_rules)

    def add_rule(self, category: str, keyword: str):
        """Adds a rule to the classifier rules registry."""
        self.add_custom_rule(category, keyword)
        if category not in self.rules:
            self.rules[category] = []
        kw_clean = keyword.strip().upper()
        if kw_clean not in [k.upper() for k in self.rules[category]]:
            self.rules[category].append(kw_clean)
            self.save_rules(self.rules)

    def classify(self, description: str, return_method: bool = False):
        """
        Matches transaction description against rules in priority order:
        1. Custom Rules (User-defined high priority, confidence 1.0)
        2. Predefined high-confidence rules (Specific merchants before generic channel terms)
        Returns:
            If return_method=True: (category, confidence, matched_keyword, method)
            If return_method=False: (category, confidence, matched_keyword)
        """
        if not description:
            return (None, 0.0, None, None) if return_method else (None, 0.0, None)

        desc_upper = description.upper()

        # Step 1: Check Custom Rules first
        for cat, keywords in self.custom_rules.items():
            for kw in keywords:
                pattern = r'\b' + re.escape(kw) + r'\b' if len(kw) <= 4 else re.escape(kw)
                if re.search(pattern, desc_upper):
                    if return_method:
                        return cat, 1.0, kw, "Custom Rule"
                    return cat, 1.0, kw

        # Step 2: Predefined rules with high specificity priority (Transfers/Others last)
        priority_order = [
            "Salary",
            "Food & Dining",
            "Shopping",
            "Travel & Transport",
            "Utilities & Bills",
            "Rent",
            "Healthcare",
            "Education",
            "EMI/Loan",
            "ATM Withdrawal",
            "Bank Charges",
            "Investments",
            "Interest",
            "Refunds",
            "Other Income",
            "Other Expenses",
            "Transfers"
        ]

        for cat in priority_order:
            keywords = self.rules.get(cat, DEFAULT_RULES.get(cat, []))
            for kw in keywords:
                pattern = r'\b' + re.escape(kw) + r'\b' if len(kw) <= 4 else re.escape(kw)
                if re.search(pattern, desc_upper):
                    confidence = 0.98 if len(kw) > 4 else 0.90
                    if return_method:
                        return cat, confidence, kw, "Rule-Based"
                    return cat, confidence, kw

        return (None, 0.0, None, None) if return_method else (None, 0.0, None)
