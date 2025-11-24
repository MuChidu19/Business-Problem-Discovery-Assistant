# Account to industry mapping and derived lists

ACCOUNT_INDUSTRY_MAP = {
    "Select Account": "Select Industry",
    "Abbott Ireland": "Pharma",
    "Abbott Laboratories": "Pharma",
    "Abbvie": "Pharma",
    "BMS Germany": "Pharma",
    "BMS Japan": "Pharma",
    "Bristol-Myers Squibb": "Pharma",
    "Envista": "Healthcare",
    "Gilead Sciences, Inc.": "Pharma",
    "J&J Inc": "Pharma",
    "J&J Japan": "Pharma",
    "J&J Singapore": "Pharma",
    "Novartis": "Pharma",
    "Sanofi": "Pharma",
    "Dell": "Technology",
    "Microsoft": "Technology",
    "RECURSION": "Technology",
    "Chevron India": "Energy",
    "CHEVRON U.S.A. INC.": "Energy",
    "OXY": "Energy",
    "SABIC": "Energy",
    "BMO": "Finance",
    "Citigroup": "Finance",
    "Coles": "Retail",
    "Home Depot": "Retail",
    "Nike": "Consumer Goods",
    "THD": "Retail",
    "Walmart": "Retail",
    "Walmart Mexico": "Retail",
    "ADM": "Food & Beverage",
    "Mars": "Consumer Goods",
    "MARS China": "Consumer Goods",
    "Southwest": "Airlines",
    "T Mobile": "Telecom",
    "NCLH": "Hospitality",
    "RTX": "Aerospace",
    "Itkan": "Technology",
    "Loyalty Pacific": "Services",
    "Skills Development": "Education",
    "Others": "Other",
}

ALL_ACCOUNTS = [acc for acc in ACCOUNT_INDUSTRY_MAP.keys() if acc not in ("Select Account", "Others")]
ALL_ACCOUNTS.sort()
ALL_ACCOUNTS.append("Others")

ACCOUNTS = ["Select Account"] + ALL_ACCOUNTS

_industries = set(ACCOUNT_INDUSTRY_MAP.values())
INDUSTRIES = sorted([i for i in _industries if i != "Select Industry"])
if "Other" not in INDUSTRIES:
    INDUSTRIES.append("Other")
INDUSTRIES = ["Select Industry"] + INDUSTRIES

