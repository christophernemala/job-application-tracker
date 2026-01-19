# 💼 O2C Reconciliation Platform

An automated tool for reconciling Accounts Receivable (AR) with Bank Statements. This platform helps you match invoices with bank payments quickly and accurately.

## 🌟 What Does This Do?

This tool helps you:
- **Upload** AR and Bank statement Excel files
- **Automatically match** records based on customer name, amount, and date
- **Identify** unmatched records that need attention
- **Export** results to Excel for further analysis
- **Calculate** aging for overdue invoices

## 🚀 How to Use

### Step 1: Prepare Your Excel Files

**AR File should have these columns:**
- Customer Name
- Amount
- Invoice Number
- Date

**Bank File should have these columns:**
- Customer Name
- Amount
- Reference
- Date

### Step 2: Open the Platform

1. Go to: https://christophernemala.github.io/o2c-reconciliation-platform/
2. Click "Upload AR File" and select your AR Excel file
3. Click "Upload Bank File" and select your Bank Excel file
4. Click "Process Reconciliation"

### Step 3: Review Results

The platform will show you:
- ✅ **Matched Records**: Successfully reconciled transactions
- ⚠️ **Unmatched AR**: Invoices without matching bank payments
- ⚠️ **Unmatched Bank**: Bank payments without matching invoices

### Step 4: Export Results

Click "Export to Excel" to download a report with all results in separate sheets.

## 📁 Project Structure

```
o2c-reconciliation-platform/
│
├── index.html          # Main webpage (structure)
├── styles.css          # Styling (colors, layout, design)
├── app.js              # Logic (file processing, matching, calculations)
└── README.md           # This file (documentation)
```

## 🔧 How It Works (For Learning)

### 1. **index.html** - The Structure
This file creates the webpage layout:
- Upload buttons for files
- Tables to display results
- Buttons to process and export

Think of it like building a house - HTML is the walls and rooms.

### 2. **styles.css** - The Design
This file makes everything look good:
- Colors and gradients
- Button styles
- Table formatting
- Responsive design for mobile

Think of it like painting and decorating the house.

### 3. **app.js** - The Brain
This file does all the work:

**Reading Files:**
```javascript
// Reads Excel file and converts to data we can work with
function readExcelFile(file) { ... }
```

**Matching Logic:**
```javascript
// Compares AR and Bank records to find matches
function performReconciliation() {
    // Check if customer names match
    // Check if amounts match (within 1 cent)
    // Check if dates are close (within 7 days)
}
```

**Displaying Results:**
```javascript
// Shows matched records in a table
function displayMatchedRecords() { ... }
```

## 🎓 Understanding the Code

### Key Concepts:

**1. Variables** - Store data
```javascript
let arData = [];      // Stores AR records
let bankData = [];    // Stores Bank records
```

**2. Functions** - Do specific tasks
```javascript
function parseAmount(value) {
    // Converts "$1,234.56" to 1234.56
}
```

**3. Loops** - Repeat actions
```javascript
for (let i = 0; i < arData.length; i++) {
    // Check each AR record
}
```

**4. Conditions** - Make decisions
```javascript
if (amountMatch && customerMatch) {
    // Records match!
}
```

## 🛠️ How to Set Up GitHub Copilot (Optional)

GitHub Copilot is an AI that helps you write code. Here's how to get it:

### Step 1: Subscribe to GitHub Copilot
1. Go to https://github.com/features/copilot
2. Click "Start free trial" or "Buy now"
3. Choose individual plan

### Step 2: Install VS Code
1. Download from https://code.visualstudio.com/
2. Install on your computer

### Step 3: Install Copilot Extension
1. Open VS Code
2. Click Extensions icon (left sidebar)
3. Search "GitHub Copilot"
4. Click Install
5. Sign in with your GitHub account

### Step 4: Use Copilot
- Start typing code and Copilot will suggest completions
- Press Tab to accept suggestions
- Write comments describing what you want, and Copilot will write the code

## 📚 Learning Resources

**For Beginners:**
- HTML: https://www.w3schools.com/html/
- CSS: https://www.w3schools.com/css/
- JavaScript: https://www.w3schools.com/js/

**Interactive Learning:**
- freeCodeCamp: https://www.freecodecamp.org/
- Codecademy: https://www.codecademy.com/

**YouTube Channels:**
- Traversy Media
- Web Dev Simplified
- Programming with Mosh

## 🐛 Common Issues & Fixes

**Problem: Files won't upload**
- Make sure files are .xlsx or .xls format
- Check that column names match requirements

**Problem: No matches found**
- Verify customer names are spelled exactly the same
- Check that amounts are in number format (not text)
- Ensure dates are in proper date format

**Problem: Page doesn't load**
- Clear browser cache
- Try a different browser (Chrome recommended)
- Check internet connection

## 💡 Tips for Understanding Code

1. **Read the comments** - They explain what each part does
2. **Start small** - Understand one function at a time
3. **Use console.log()** - Print values to see what's happening
4. **Experiment** - Change values and see what happens
5. **Ask questions** - Use ChatGPT or Stack Overflow

## 🔄 Making Changes

To modify the code:

1. **Change colors**: Edit `styles.css`
2. **Change matching rules**: Edit `performReconciliation()` in `app.js`
3. **Add new features**: Add functions in `app.js`
4. **Change layout**: Edit `index.html`

## 📞 Need Help?

- **GitHub Issues**: Report bugs or ask questions
- **Email**: christophernemala@gmail.com
- **Documentation**: Read the comments in the code files

## 📄 License

Free to use and modify for your needs.

---

**Made with ❤️ for learning and automation**

*Remember: Everyone starts as a beginner. Keep learning, keep coding!* 🚀
