# CFP Professional Data Extractor (Data Scraper)

This repository contains a Python scraper for extracting CFP® professional listing data from the `letsmakeaplan.org` search API. The primary output is a CSV file containing:

- First Name
- Last Name
- Company Name
- Phone Number
- Street Address
- Zip Code

## What this project does

The script `Extract Data/scrape_cfp_professionals.py` requests paginated search results from the CFP® professional search API and writes cleaned, deduplicated records to CSV.

It includes:

- pagination support for multiple pages
- safe field extraction and exception handling
- validation for zip codes (only full 9-digit ZIPs are retained)
- phone normalization to standard 10-digit format

## Installation

1. Open a terminal in the project directory.

2. Create a virtual environment (recommended):

```powershell
python -m venv .venv
```

3. Activate the virtual environment:

```powershell
.venv\Scripts\Activate.ps1
```

4. Install required packages:

```powershell
pip install -r requirements.txt
```

## Usage

Run the scraper from the project directory:

```powershell
python scrape_cfp_professionals.py --start-page 1 --max-pages 10 --limit 10 --out-file cfp_professionals.csv
```

### Key arguments

- `--start-page`: first page number to fetch (default: 1)
- `--max-pages`: how many pages to fetch
- `--limit`: number of results per page (default: 10)
- `--random-key`: random key parameter used by the source URL (default: 803)
- `--sort`: result sort order (default: `random`)
- `--distance`: search radius distance (default: 5)
- `--planning-services`: planning services UUID used by the search API
- `--delay`: seconds to wait between page requests (default: 0.5)
- `--out-file`: CSV output file path

### Example

Fetch 5 pages of results and write output to `Extract Data\cfp_professionals.csv`:

```powershell
python "Extract Data\scrape_cfp_professionals.py" --start-page 1 --max-pages 5 --limit 10 --out-file "Extract Data\cfp_professionals.csv"
```

## Output

The script writes a CSV with the following headers:

- `First Name`
- `Last Name`
- `Company Name`
- `Phone Number`
- `Street Address`
- `Zip Code`

Invalid phone numbers are cleared.
Only valid 9-digit ZIP codes are preserved.

## Notes

- The scraper relies on the public API endpoint used by the website.
- If the API response changes, the script may need updates.
- Use `--delay` to avoid overwhelming the service.
