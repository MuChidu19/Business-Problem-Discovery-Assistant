import os


TENANT_ID = os.getenv("TENANT_ID", "talos")
AUTH_TOKEN = os.getenv("AUTH_TOKEN", "")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

BASE_HEADERS = {
    "Content-Type": "application/json",
    "Tenant-ID": TENANT_ID,
    "X-Tenant-ID": TENANT_ID,
}

