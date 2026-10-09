"""Controlled category lists for income and expense transactions."""

EXPENSE_CATEGORIES = [
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Health",
    "Education",
    "Entertainment",
    "Other",
]

INCOME_CATEGORIES = [
    "Salary",
    "Freelance",
    "Other",
]

ALL_CATEGORIES = sorted(set(EXPENSE_CATEGORIES + INCOME_CATEGORIES))

TRANSACTION_TYPES = ("income", "expense")

PAYMENT_METHODS = [
    ("", "— Optional —"),
    ("Cash", "Cash"),
    ("UPI", "UPI"),
    ("Card", "Card"),
    ("Bank Transfer", "Bank Transfer"),
    ("Other", "Other"),
]


def categories_for_type(transaction_type: str) -> list[str]:
    if transaction_type == "income":
        return INCOME_CATEGORIES
    return EXPENSE_CATEGORIES
