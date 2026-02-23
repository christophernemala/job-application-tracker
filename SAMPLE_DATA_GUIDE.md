# 📊 Sample Data Guide

This guide shows you how to create sample Excel files to test the O2C Reconciliation Platform.

## 🎯 Quick Start - Create Test Files

### Sample AR File (Accounts Receivable)

Create an Excel file named `AR_Sample.xlsx` with these columns and data:

| Customer Name | Amount | Invoice Number | Date |
|--------------|--------|----------------|------|
| ABC Corp | 5000.00 | INV-001 | 2026-01-10 |
| XYZ Ltd | 3500.50 | INV-002 | 2026-01-12 |
| Tech Solutions | 7200.00 | INV-003 | 2026-01-15 |
| Global Industries | 4500.00 | INV-004 | 2026-01-18 |
| Smart Systems | 2800.75 | INV-005 | 2026-01-20 |

### Sample Bank File (Bank Statement)

Create an Excel file named `Bank_Sample.xlsx` with these columns and data:

| Customer Name | Amount | Reference | Date |
|--------------|--------|-----------|------|
| ABC Corp | 5000.00 | BANK-REF-001 | 2026-01-11 |
| XYZ Ltd | 3500.50 | BANK-REF-002 | 2026-01-13 |
| Tech Solutions | 7200.00 | BANK-REF-003 | 2026-01-16 |
| Unknown Customer | 1500.00 | BANK-REF-004 | 2026-01-19 |

## 📝 Expected Results

When you upload these files, the platform should show:

### ✅ Matched Records (3)
- ABC Corp - $5,000.00
- XYZ Ltd - $3,500.50
- Tech Solutions - $7,200.00

### ⚠️ Unmatched AR Records (2)
- Global Industries - $4,500.00 (No matching bank payment)
- Smart Systems - $2,800.75 (No matching bank payment)

### ⚠️ Unmatched Bank Records (1)
- Unknown Customer - $1,500.00 (No matching AR invoice)

## 🔧 How to Create Excel Files

### Method 1: Using Microsoft Excel
1. Open Excel
2. Create a new workbook
3. Add column headers in Row 1
4. Add data in rows below
5. Save as `.xlsx` format

### Method 2: Using Google Sheets
1. Open Google Sheets
2. Create a new spreadsheet
3. Add column headers and data
4. File → Download → Microsoft Excel (.xlsx)

### Method 3: Using LibreOffice Calc (Free)
1. Download LibreOffice from https://www.libreoffice.org/
2. Open Calc
3. Add your data
4. Save as Excel format

## 📋 Column Requirements

### AR File Must Have:
- **Customer Name** - Text (e.g., "ABC Corp")
- **Amount** - Number (e.g., 5000.00 or $5,000.00)
- **Invoice Number** - Text (e.g., "INV-001")
- **Date** - Date format (e.g., 2026-01-15 or 01/15/2026)

### Bank File Must Have:
- **Customer Name** - Text (must match AR exactly)
- **Amount** - Number (must match AR within 1 cent)
- **Reference** - Text (bank reference number)
- **Date** - Date format (within 7 days of AR date)

## 💡 Tips for Good Test Data

### For Matched Records:
- Use **exact same customer names** in both files
- Use **exact same amounts** (or within 1 cent)
- Keep dates **within 7 days** of each other

### For Unmatched Records:
- Use different customer names
- Use different amounts
- Use dates more than 7 days apart

## 🎨 Advanced Test Scenarios

### Test 1: Case Sensitivity
```
AR File: "ABC Corp"
Bank File: "abc corp"
Result: Should match (case-insensitive)
```

### Test 2: Amount Tolerance
```
AR File: $1000.00
Bank File: $1000.01
Result: Should match (within 1 cent tolerance)
```

### Test 3: Date Proximity
```
AR Date: 2026-01-10
Bank Date: 2026-01-15
Result: Should match (within 7 days)
```

### Test 4: Different Formats
```
Amount formats that work:
- 1000
- 1000.00
- $1,000.00
- 1,000.00

Date formats that work:
- 2026-01-15
- 01/15/2026
- 15-Jan-2026
```

## 🚨 Common Issues

### Issue 1: No Matches Found
**Cause:** Customer names don't match exactly
**Fix:** Make sure names are spelled identically

### Issue 2: Wrong Match Count
**Cause:** Amounts or dates are too different
**Fix:** Check amount tolerance (1 cent) and date tolerance (7 days)

### Issue 3: File Won't Upload
**Cause:** Wrong file format
**Fix:** Save as .xlsx or .xls format

## 📥 Download Sample Files

You can create these files yourself, or use the data above to test the platform.

### Quick Copy-Paste Data

**AR File:**
```
Customer Name,Amount,Invoice Number,Date
ABC Corp,5000.00,INV-001,2026-01-10
XYZ Ltd,3500.50,INV-002,2026-01-12
Tech Solutions,7200.00,INV-003,2026-01-15
Global Industries,4500.00,INV-004,2026-01-18
Smart Systems,2800.75,INV-005,2026-01-20
```

**Bank File:**
```
Customer Name,Amount,Reference,Date
ABC Corp,5000.00,BANK-REF-001,2026-01-11
XYZ Ltd,3500.50,BANK-REF-002,2026-01-13
Tech Solutions,7200.00,BANK-REF-003,2026-01-16
Unknown Customer,1500.00,BANK-REF-004,2026-01-19
```

## 🎯 Testing Checklist

- [ ] Created AR Excel file with required columns
- [ ] Created Bank Excel file with required columns
- [ ] Added at least 3 matching records
- [ ] Added at least 1 unmatched AR record
- [ ] Added at least 1 unmatched Bank record
- [ ] Saved files as .xlsx format
- [ ] Tested upload on the platform
- [ ] Verified results are correct
- [ ] Tested export functionality

## 🆘 Need Help?

If you're stuck:
1. Check that column names match exactly
2. Verify file format is .xlsx or .xls
3. Make sure data is in the correct format
4. Try the sample data provided above
5. Check browser console (F12) for errors

---

**Happy Testing! 🚀**
