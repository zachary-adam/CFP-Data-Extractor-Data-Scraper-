import argparse
import csv
import os
import re
import time
import requests
from typing import Any, Dict, List, Tuple

ENDPOINT = "https://www.letsmakeaplan.org/api/feature/lmapprofilesearch/search"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0 Safari/537.36"
}

DEFAULT_PLANNING_SERVICES = "f42d193a-baea-4329-aee0-4d287c321ea4"

FIELDNAMES = [
    "First Name",
    "Last Name",
    "Company Name",
    "Phone Number",
    "Street Address",
    "Zip Code",
]


def fetch_results(
    limit: int,
    page: int,
    random_key: int,
    sort: str,
    distance: int,
    planning_services: str,
    session: requests.Session,
) -> Dict[str, Any]:
    params = {
        "_limit": limit,
        "pg": page,
        "randomKey": random_key,
        "sort": sort,
        "distance": distance,
        "planning_services": planning_services,
        "s": "on",
    }
    response = session.get(ENDPOINT, params=params, timeout=20)
    response.raise_for_status()
    return response.json()


def safe_str(value: Any) -> str:
    if value is None:
        return ""
    try:
        return str(value).strip()
    except Exception:
        return ""


def safe_list_first(value: Any) -> str:
    try:
        if isinstance(value, list) and value:
            return safe_str(value[0])
        return safe_str(value)
    except Exception:
        return ""


def normalize_phone(phones: Any) -> str:
    raw_phone = safe_list_first(phones)
    if not raw_phone:
        return ""

    raw_phone = raw_phone.strip()
    raw_phone = re.sub(r"(?:ext(?:ension)?|x)[\s:\-\.]*(\d{1,6})$", "", raw_phone, flags=re.I).strip()

    digits = "".join(ch for ch in raw_phone if ch.isdigit())
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        print(f"Warning: phone number {raw_phone!r} did not match a valid 10-digit format, clearing")
        return ""

    return f"({digits[:3]}) {digits[3:6]}-{digits[6:]}"


def normalize_zip_code(post_code: Any) -> str:
    raw = safe_str(post_code)
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 9:
        return f"{digits[:5]}-{digits[5:]}"
    if digits:
        print(f"Warning: zip code {raw!r} is not full 9 digits, clearing")
    return ""


def extract_address(item: Dict[str, Any]) -> Tuple[str, str]:
    try:
        children = item.get("_childDocuments_") or []
        if not isinstance(children, list):
            return "", ""
        for child in children:
            if not isinstance(child, dict):
                continue
            if child.get("content_type") == "address":
                street = safe_str(child.get("adr_line1", ""))
                adr_line2 = child.get("adr_line2")
                if adr_line2:
                    street = f"{street} {safe_str(adr_line2)}".strip()
                return street.strip(), safe_str(child.get("adr_post_code"))
    except Exception:
        return "", ""
    return "", ""


def parse_item(item: Dict[str, Any]) -> Dict[str, str]:
    first_name = ""
    last_name = ""
    company_name = ""
    phone_number = ""
    street_address = ""
    zip_code = ""

    try:
        first_name = safe_str(item.get("ind_first_name"))
        last_name = safe_str(item.get("ind_last_name"))
        if not first_name and not last_name:
            full_name = safe_str(item.get("cst_ind_full_name_dn"))
            parts = full_name.split()
            if parts:
                first_name = safe_str(parts[0])
                if len(parts) > 1:
                    last_name = safe_str(parts[-1])

        company_name = safe_str(item.get("cst_org_name_dn"))
        phone_number = normalize_phone(item.get("phones"))
        street_address, post_code = extract_address(item)
        zip_code = normalize_zip_code(post_code)
    except Exception as e:
        print(f"Warning: failed to parse item fields: {e}")

    return {
        "First Name": first_name,
        "Last Name": last_name,
        "Company Name": company_name,
        "Phone Number": phone_number,
        "Street Address": street_address,
        "Zip Code": zip_code,
    }


def write_csv(rows: List[Dict[str, str]], output_path: str) -> None:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def fetch_pages(
    limit: int,
    start_page: int,
    max_pages: int,
    random_key: int,
    sort: str,
    distance: int,
    planning_services: str,
    delay: float,
    session: requests.Session,
    output_path: str,
) -> int:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    seen = set()
    total_written = 0

    with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=FIELDNAMES)
        writer.writeheader()

        for page_offset in range(max_pages):
            page = start_page + page_offset
            print(f"Fetching page {page}...")
            json_data = fetch_results(
                limit=limit,
                page=page,
                random_key=random_key,
                sort=sort,
                distance=distance,
                planning_services=planning_services,
                session=session,
            )
            results = json_data.get("results", [])
            if not results:
                print(f"No results returned for page {page}. Stopping early.")
                break

            written_this_page = 0
            for item in results:
                try:
                    row = parse_item(item)
                    key = (
                        row["First Name"].lower(),
                        row["Last Name"].lower(),
                        row["Company Name"].lower(),
                        row["Phone Number"].lower(),
                        row["Street Address"].lower(),
                        row["Zip Code"].lower(),
                    )
                    if key in seen:
                        continue
                    seen.add(key)
                    writer.writerow(row)
                    written_this_page += 1
                    total_written += 1
                except Exception as e:
                    print(f"Warning: failed to process item on page {page}: {e}")

            print(f"Wrote {written_this_page} unique records from page {page}.")
            if page_offset < max_pages - 1:
                time.sleep(delay)

    return total_written


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape CFP professional data from letsmakeaplan.org")
    parser.add_argument("--limit", type=int, default=10, help="Number of results per page")
    parser.add_argument("--page", type=int, help="Legacy single page number to fetch")
    parser.add_argument("--start-page", type=int, default=1, help="Start page number to fetch")
    parser.add_argument("--max-pages", type=int, default=1, help="Number of pages to fetch")
    parser.add_argument("--random-key", type=int, default=803, help="Random key parameter from the source URL")
    parser.add_argument("--sort", default="random", help="Sort order for results")
    parser.add_argument("--distance", type=int, default=5, help="Search radius distance")
    parser.add_argument("--planning-services", default=DEFAULT_PLANNING_SERVICES, help="Planning services UUID from the source URL")
    parser.add_argument("--delay", type=float, default=0.5, help="Seconds to wait between page requests")
    parser.add_argument("--out-file", default="cfp_professionals.csv", help="CSV output file")
    args = parser.parse_args()

    start_page = args.start_page if args.page is None else args.page
    max_pages = args.max_pages if args.max_pages != 1 or args.page is not None else 1

    session = requests.Session()
    session.headers.update(HEADERS)

    total = fetch_pages(
        limit=args.limit,
        start_page=start_page,
        max_pages=max_pages,
        random_key=args.random_key,
        sort=args.sort,
        distance=args.distance,
        planning_services=args.planning_services,
        delay=args.delay,
        session=session,
        output_path=args.out_file,
    )

    print(f"Saved {total} records to {args.out_file}")


if __name__ == "__main__":
    main()
