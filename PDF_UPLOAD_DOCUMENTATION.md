# PDF Upload Functionality Documentation

## Overview

This document describes the PDF upload functionality added to the Money Tracker application. The feature allows users to upload PDF bank statements, extract transaction data from them, and store the transactions in the database.

## Implementation Details

The following components were implemented:

1. **PDF Parser Service**
   - Created a new `pdf_parser_service.py` file in the `money_tracker/services` directory
   - Implemented the `PDFTableExtractor` class for extracting tables from PDF files
   - Implemented the `PDFParser` class for parsing transaction data from the extracted tables
   - Added functionality to parse counterparty names and transaction IDs from narration fields

2. **Web Application Integration**
   - Added a new route `/upload_pdf` to handle PDF uploads
   - Created a new template `upload_pdf.html` for the PDF upload interface
   - Added a link to the PDF upload page in the navigation menu
   - Implemented file handling and storage for uploaded PDFs

3. **Dependencies**
   - Added PyMuPDF (fitz), pandas, and openpyxl to the requirements.txt file

## How It Works

1. The user navigates to the "Upload PDF" page from the navigation menu
2. The user selects an account and uploads a PDF bank statement
3. The application processes the PDF file:
   - Extracts tables from the PDF using the PDFTableExtractor
   - Parses transaction data from the tables using the PDFParser
   - Extracts counterparty names and transaction IDs from narration fields
   - Determines transaction types based on debit/credit fields
4. The extracted transactions are stored in the database
5. The user is redirected to the account details page to view the imported transactions

## Testing Instructions

To test the PDF upload functionality:

1. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Start the web application:
   ```
   python webapp.py
   ```

3. Navigate to the "Upload PDF" page from the navigation menu

4. Select an account and upload a PDF bank statement
   - The PDF should contain tables with transaction data
   - The first table should have columns: Account Number, Currency, Branch
   - The second table should have columns: Post Date, Value Date, Narration, Debit, Credit, Balance

5. Verify that the transactions are correctly extracted and stored in the database
   - Check the account details page to see the imported transactions
   - Verify that counterparty names and transaction IDs are correctly parsed from narration fields
   - Confirm that transaction types are correctly determined based on debit/credit fields

## Supported PDF Format

The PDF parser is designed to work with bank statements that have the following structure:

1. **First Table (Account Information)**
   - Columns: Account Number, Currency, Branch
   - Located at the top of the first page

2. **Second Table (Transaction Details)**
   - Columns: Post Date, Value Date, Narration, Debit, Credit, Balance
   - Located below the first table on the first page and on subsequent pages

The parser uses predefined table structures to extract data from specific regions of the PDF. If the bank statement has a different format, the table structures in the `PDFTableExtractor` class may need to be adjusted.

## Narration Parsing

The parser extracts counterparty names and transaction IDs from the narration field using regular expressions. It supports the following transaction formats:

1. **POS Transactions**
   - Example: `POS 685694-SHARARAH MART AL M POS251610D175XM3X`
   - Counterparty: `SHARARAH MART AL M`
   - Transaction ID: `POS251610D175XM3X`

2. **Wallet Transactions**
   - Example: `Wallet Trx BMCT010484967766 AHMED NASSER KHALF AL MUFARGI FT25161622715487`
   - Counterparty: `AHMED NASSER KHALF AL MUFARGI`
   - Transaction ID: `BMCT010484967766`

3. **Easy Deposit Transactions**
   - Example: `Easy Deposit CDM12478415 13:38:31 ABDULMAJEED CDM251660294YXKKS`
   - Counterparty: `ABDULMAJEED`
   - Transaction ID: `CDM12478415`

4. **Salary Transactions**
   - Example: `SALARY Salary for 6 202 SALARY 209948320732336.050001`
   - Counterparty: `Salary for 6 202`
   - Transaction ID: None

5. **Transfer Transactions**
   - Example: `Transfer Lunch for new couples and light fix IMAN MOHAMMED KHASIB AL HADHRAMI LF`
   - Counterparty: `IMAN MOHAMMED KHASIB AL HADHRAMI LF Lunch for new couples and light fix`
   - Transaction ID: None

If a narration doesn't match any of these patterns, the entire narration is used as the counterparty name.

## Limitations and Future Improvements

1. **PDF Format Dependency**
   - The current implementation relies on predefined table structures, which may not work for all bank statement formats
   - Future improvement: Implement more flexible table detection algorithms

2. **Narration Parsing**
   - The current implementation uses regex patterns for specific transaction formats
   - Future improvement: Implement more sophisticated NLP techniques for better extraction

3. **Error Handling**
   - The current implementation provides basic error handling
   - Future improvement: Add more detailed error messages and recovery mechanisms

4. **Testing**
   - The current implementation requires manual testing
   - Future improvement: Add automated tests for the PDF parsing functionality