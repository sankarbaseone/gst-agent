from fastapi.testclient import TestClient
from app.main import app
import csv
import io

client = TestClient(app)

def create_csv_content(rows):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=rows[0].keys())
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode('utf-8')

def test_valid_upload():
    print("Testing valid upload...")
    data = [
        {
            "gstin": "29ABCDE1234F1Z5",
            "invoice_no": "INV-001",
            "invoice_date": "2023-10-25",
            "taxable_value": "1000.00",
            "cgst": "90.0",
            "sgst": "90.0",
            "igst": "0.0"
        }
    ]
    files = {"file": ("invoices.csv", create_csv_content(data), "text/csv")}
    response = client.post("/invoices/upload", files=files)
    if response.status_code != 200:
        print(f"FAILED: Expected 200, got {response.status_code}")
        print(response.json())
        return

    json_resp = response.json()
    assert json_resp["status"] == "success"
    assert json_resp["total_invoices"] >= 1
    item = json_resp["normalized_invoices"][0]
    assert item["gstin"] == "29ABCDE1234F1Z5"
    assert item["invoice_number"] == "INV-001"
    assert item["source"] == "customer"
    print("PASSED: Valid upload")

def test_invalid_date_format():
    print("Testing invalid date format...")
    data = [
        {
            "gstin": "29ABCDE1234F1Z5",
            "invoice_no": "INV-002",
            "invoice_date": "25-10-2023", # Invalid format
            "taxable_value": "100.00",
            "cgst": "9.0",
            "sgst": "9.0",
            "igst": "0.0"
        }
    ]
    files = {"file": ("invoices.csv", create_csv_content(data), "text/csv")}
    response = client.post("/invoices/upload", files=files)
    if response.status_code == 400 and "Date must be in YYYY-MM-DD format" in response.json()["detail"]:
        print("PASSED: Invalid date rejection")
    else:
        print(f"FAILED: Expected 400 with date error, got {response.status_code}")
        print(response.json())

def test_non_numeric():
    print("Testing non-numeric values...")
    data = [
        {
            "gstin": "29ABCDE1234F1Z5",
            "invoice_no": "INV-003",
            "invoice_date": "2023-10-25",
            "taxable_value": "1000USD", # Invalid numeric
            "cgst": "90.0",
            "sgst": "90.0",
            "igst": "0.0"
        }
    ]
    files = {"file": ("invoices.csv", create_csv_content(data), "text/csv")}
    response = client.post("/invoices/upload", files=files)
    if response.status_code == 400 and "taxable_value must be strictly numeric" in response.json()["detail"]:
        print("PASSED: Non-numeric rejection")
    else:
        print(f"FAILED: Expected 400 with numeric error, got {response.status_code}")
        print(response.json())

if __name__ == "__main__":
    try:
        test_valid_upload()
        test_invalid_date_format()
        test_non_numeric()
    except Exception as e:
        print(f"An error occurred: {e}")
