# 🔧 Troubleshooting Guide

Complete guide to fix common issues with the O2C Reconciliation Platform.

## 🚨 Common Problems & Solutions

### Problem 1: Platform Won't Load

**Symptoms:**
- Blank white page
- "Page not found" error
- Nothing happens when visiting the URL

**Solutions:**

✅ **Solution 1: Check the URL**
- Correct URL: `https://christophernemala.github.io/o2c-reconciliation-platform/`
- Make sure you're using HTTPS (not HTTP)
- Check for typos in the URL

✅ **Solution 2: Clear Browser Cache**
```
Chrome: Ctrl+Shift+Delete → Clear browsing data
Firefox: Ctrl+Shift+Delete → Clear recent history
Safari: Cmd+Option+E → Empty caches
```

✅ **Solution 3: Try Different Browser**
- Chrome (Recommended)
- Firefox
- Edge
- Safari

✅ **Solution 4: Check Internet Connection**
- Make sure you're connected to the internet
- Try loading other websites
- Restart your router if needed

---

### Problem 2: Files Won't Upload

**Symptoms:**
- Nothing happens when selecting files
- "Please select both files" error
- Upload button doesn't work

**Solutions:**

✅ **Solution 1: Check File Format**
- Files must be `.xlsx` or `.xls`
- Not `.csv`, `.txt`, or other formats
- Re-save as Excel format if needed

✅ **Solution 2: Check File Size**
- Files should be under 10MB
- Large files may take longer to process
- Try with smaller test files first

✅ **Solution 3: Select Both Files**
- You need BOTH AR and Bank files
- Don't leave either field empty
- Check that files are actually selected

✅ **Solution 4: Check File Permissions**
- Make sure files aren't locked/protected
- Close Excel if files are open
- Try copying files to a different location

---

### Problem 3: No Matches Found

**Symptoms:**
- All records show as "Unmatched"
- Matched count is 0
- Expected matches don't appear

**Solutions:**

✅ **Solution 1: Check Customer Names**
```
❌ Wrong:
AR File: "ABC Corp"
Bank File: "ABC Corporation"

✅ Correct:
AR File: "ABC Corp"
Bank File: "ABC Corp"
```
- Names must match EXACTLY
- Check for extra spaces
- Check spelling

✅ **Solution 2: Check Amounts**
```
❌ Won't Match:
AR: $1000.00
Bank: $1000.50 (difference > 1 cent)

✅ Will Match:
AR: $1000.00
Bank: $1000.01 (difference ≤ 1 cent)
```

✅ **Solution 3: Check Dates**
```
❌ Won't Match:
AR Date: 2026-01-01
Bank Date: 2026-01-15 (15 days apart)

✅ Will Match:
AR Date: 2026-01-10
Bank Date: 2026-01-15 (5 days apart)
```
- Dates must be within 7 days
- Check date format is correct

✅ **Solution 4: Check Column Names**
Required columns (case-insensitive):
- AR File: Customer Name, Amount, Invoice Number, Date
- Bank File: Customer Name, Amount, Reference, Date

---

### Problem 4: Wrong Number of Matches

**Symptoms:**
- Too many matches
- Too few matches
- Duplicate matches

**Solutions:**

✅ **Solution 1: Check for Duplicates**
- Remove duplicate rows in Excel
- Each invoice should appear once
- Each bank transaction should appear once

✅ **Solution 2: Verify Data Quality**
- Check for blank rows
- Remove empty cells
- Ensure all required fields have data

✅ **Solution 3: Review Matching Rules**
The platform matches when:
1. Customer names match (case-insensitive)
2. Amounts match (within 1 cent)
3. Dates are within 7 days

---

### Problem 5: Export Doesn't Work

**Symptoms:**
- Export button doesn't respond
- No file downloads
- Download fails

**Solutions:**

✅ **Solution 1: Check Browser Settings**
- Allow downloads in browser settings
- Check if pop-ups are blocked
- Look in Downloads folder

✅ **Solution 2: Process Data First**
- You must process files before exporting
- Click "Process Reconciliation" first
- Wait for results to appear

✅ **Solution 3: Check Browser Permissions**
- Allow file downloads
- Check antivirus isn't blocking
- Try different browser

---

### Problem 6: Page Looks Broken

**Symptoms:**
- No colors/styling
- Layout is messy
- Buttons look plain

**Solutions:**

✅ **Solution 1: Wait for Full Load**
- Give page 5-10 seconds to load
- Check internet connection
- Refresh the page (F5)

✅ **Solution 2: Clear Cache**
- Hard refresh: Ctrl+Shift+R (Windows) or Cmd+Shift+R (Mac)
- Clear browser cache
- Close and reopen browser

✅ **Solution 3: Check CSS File**
- CSS file should load automatically
- Check browser console (F12) for errors
- Look for "styles.css" errors

---

### Problem 7: Processing Takes Too Long

**Symptoms:**
- Spinner keeps spinning
- No results after 5+ minutes
- Browser becomes unresponsive

**Solutions:**

✅ **Solution 1: Check File Size**
- Large files (1000+ rows) take longer
- Try with smaller test file first
- Split large files into batches

✅ **Solution 2: Refresh and Retry**
- Refresh page (F5)
- Upload files again
- Try with smaller dataset

✅ **Solution 3: Check Browser Console**
- Press F12
- Look for error messages
- Share errors for help

---

### Problem 8: Data Shows Incorrectly

**Symptoms:**
- Amounts show as text
- Dates show as numbers
- Customer names are wrong

**Solutions:**

✅ **Solution 1: Fix Excel Formatting**
```
Amounts:
- Format as Number (not Text)
- Use 2 decimal places
- Remove currency symbols if causing issues

Dates:
- Format as Date (not Text)
- Use format: YYYY-MM-DD or MM/DD/YYYY
- Don't use custom formats

Customer Names:
- Format as Text
- Remove extra spaces
- Check for hidden characters
```

✅ **Solution 2: Re-export from Source**
- Export fresh data from your system
- Don't manually edit in Excel
- Use proper data types

---

## 🔍 How to Check for Errors

### Step 1: Open Browser Console
```
Chrome/Edge: Press F12 or Ctrl+Shift+I
Firefox: Press F12 or Ctrl+Shift+K
Safari: Cmd+Option+I
```

### Step 2: Look for Red Errors
- Red text = errors
- Yellow text = warnings (usually okay)
- Blue text = information

### Step 3: Common Error Messages

**"XLSX is not defined"**
- SheetJS library didn't load
- Check internet connection
- Refresh page

**"Cannot read property of undefined"**
- Missing column in Excel file
- Check column names match requirements
- Verify data format

**"File is not a valid Excel file"**
- Wrong file format
- Re-save as .xlsx
- Don't use .csv or .txt

---

## 📊 Testing Your Setup

### Quick Test Checklist

1. **Visit Test Page**
   - Go to: `https://christophernemala.github.io/o2c-reconciliation-platform/test.html`
   - All tests should pass (green checkmarks)
   - If any fail, note which ones

2. **Create Sample Files**
   - Follow SAMPLE_DATA_GUIDE.md
   - Create small test files (5 rows each)
   - Test with known data

3. **Upload and Process**
   - Upload both files
   - Click "Process Reconciliation"
   - Verify results match expectations

4. **Export Results**
   - Click "Export to Excel"
   - Open downloaded file
   - Verify data is correct

---

## 🆘 Still Having Issues?

### Gather This Information:

1. **What you're trying to do**
   - Upload files? Export? View results?

2. **What's happening**
   - Error message (exact text)
   - Screenshot if possible
   - When it happens

3. **Your setup**
   - Browser name and version
   - Operating system
   - File sizes

4. **Browser console errors**
   - Press F12
   - Copy any red error messages
   - Include full error text

### Where to Get Help:

1. **Check Documentation**
   - README.md - General usage
   - BEGINNERS_GUIDE.md - Understanding code
   - SAMPLE_DATA_GUIDE.md - Test data

2. **GitHub Issues**
   - Go to repository
   - Click "Issues" tab
   - Create new issue with details

3. **Email Support**
   - christophernemala@gmail.com
   - Include error details
   - Attach sample files if possible

---

## 🔄 Reset Everything

If nothing works, try a complete reset:

### Step 1: Clear Browser Data
```
1. Press Ctrl+Shift+Delete
2. Select "All time"
3. Check: Cookies, Cache, Site data
4. Click "Clear data"
```

### Step 2: Close Browser Completely
```
1. Close all browser windows
2. Wait 10 seconds
3. Reopen browser
```

### Step 3: Visit Platform Fresh
```
1. Type URL manually (don't use bookmark)
2. Wait for full page load
3. Try uploading files again
```

### Step 4: Try Different Browser
```
1. Download Chrome (if not installed)
2. Visit platform in Chrome
3. Test functionality
```

---

## ✅ Prevention Tips

### Keep Files Clean
- Use consistent naming
- Remove blank rows
- Format data properly
- Save as .xlsx

### Regular Testing
- Test with small files first
- Verify results make sense
- Export and review

### Browser Maintenance
- Keep browser updated
- Clear cache weekly
- Allow downloads

### Data Quality
- Validate before upload
- Check for duplicates
- Ensure complete data

---

**Remember: Most issues are simple fixes! Don't give up! 💪**
