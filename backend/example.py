#!/usr/bin/env python3
"""
FRT-Live Parser Example
Demonstrates basic usage of the FRT parser
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from frt_parser import FRTParser
from diff_detector import FRTDiffDetector
import json


def example_parse():
    """Example: Parse FRT PDF"""
    print("=" * 70)
    print("Example 1: Parsing FRT PDF")
    print("=" * 70)

    # Create parser instance
    parser = FRTParser(data_dir='data', output_file='frt_database.json')

    # Run the parser
    # Note: This will attempt to download from the configured URL
    # For testing, you may want to place a sample PDF in data/frt_current.pdf
    print("\nRunning parser...")
    parser.run(force_download=False)


def example_search():
    """Example: Search the FRT database"""
    print("\n" + "=" * 70)
    print("Example 2: Searching FRT Database")
    print("=" * 70)

    db_path = Path('data/frt_database.json')

    if not db_path.exists():
        print("Database not found. Run example_parse() first.")
        return

    # Load database
    with open(db_path, 'r') as f:
        records = json.load(f)

    print(f"\nTotal records: {len(records)}")

    # Search examples
    search_terms = ['Remington', 'AR-15', 'Glock']

    for term in search_terms:
        matches = [
            r for r in records
            if term.lower() in r.get('make', '').lower()
            or term.lower() in r.get('model', '').lower()
        ]

        print(f"\nSearch for '{term}': {len(matches)} matches")

        # Show first 3 matches
        for record in matches[:3]:
            print(f"  FRN {record['frn']}: {record['make']} {record['model']} - {record['class']}")

        if len(matches) > 3:
            print(f"  ... and {len(matches) - 3} more")


def example_diff():
    """Example: Detect changes between versions"""
    print("\n" + "=" * 70)
    print("Example 3: Detecting Changes")
    print("=" * 70)

    detector = FRTDiffDetector(data_dir='data')

    current_path = Path('data/frt_database.json')
    previous_path = Path('data/frt_database_previous.json')

    if not previous_path.exists():
        print("\nNo previous database found.")
        print("To test change detection:")
        print("1. Parse the FRT: python example.py parse")
        print("2. Copy the database: cp data/frt_database.json data/frt_database_previous.json")
        print("3. Modify a record manually in frt_database.json")
        print("4. Run: python example.py diff")
        return

    print("\nRunning diff detector...")
    detector.run()


def example_create_sample():
    """Create a sample FRT database for testing"""
    print("\n" + "=" * 70)
    print("Example 4: Creating Sample Database")
    print("=" * 70)

    sample_data = [
        {
            "frn": "100001",
            "make": "Remington",
            "model": "870",
            "manufacturer": "Remington Arms Company",
            "type": "Shotgun",
            "action": "Pump",
            "class": "Non-Restricted",
            "notes": "Standard hunting shotgun configuration",
            "oic_references": []
        },
        {
            "frn": "100002",
            "make": "Mossberg",
            "model": "500",
            "manufacturer": "O.F. Mossberg & Sons",
            "type": "Shotgun",
            "action": "Pump",
            "class": "Non-Restricted",
            "notes": "Multi-purpose shotgun",
            "oic_references": []
        },
        {
            "frn": "200001",
            "make": "Glock",
            "model": "17",
            "manufacturer": "Glock Ges.m.b.H.",
            "type": "Handgun",
            "action": "Semi-Auto",
            "class": "Restricted",
            "notes": "Standard service pistol, barrel length >105mm",
            "oic_references": []
        },
        {
            "frn": "300001",
            "make": "AR-15",
            "model": "Colt Canada C7",
            "manufacturer": "Colt Canada",
            "type": "Rifle",
            "action": "Semi-Auto",
            "class": "Prohibited",
            "notes": "Affected by OIC 2020-0001. Previously Non-Restricted.",
            "oic_references": ["OIC 2020-0001"]
        },
        {
            "frn": "300002",
            "make": "AK-47",
            "model": "Various",
            "manufacturer": "Various",
            "type": "Rifle",
            "action": "Semi-Auto",
            "class": "Prohibited",
            "notes": "Prohibited device under Criminal Code",
            "oic_references": []
        }
    ]

    # Create data directory
    Path('data').mkdir(exist_ok=True)

    # Write sample database
    output_path = Path('data/frt_database.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(sample_data, f, indent=2, ensure_ascii=False)

    print(f"\nCreated sample database with {len(sample_data)} records:")
    print(f"  {output_path}")

    for record in sample_data:
        print(f"  - {record['make']} {record['model']} ({record['class']})")

    print("\nYou can now:")
    print("  - Search: python example.py search")
    print("  - Test diff: cp data/frt_database.json data/frt_database_previous.json")
    print("              (then modify frt_database.json and run: python example.py diff)")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='FRT-Live Parser Examples')
    parser.add_argument(
        'action',
        choices=['parse', 'search', 'diff', 'sample'],
        help='Example to run'
    )

    args = parser.parse_args()

    # Create required directories
    Path('data').mkdir(exist_ok=True)
    Path('logs').mkdir(exist_ok=True)

    # Run selected example
    if args.action == 'parse':
        example_parse()
    elif args.action == 'search':
        example_search()
    elif args.action == 'diff':
        example_diff()
    elif args.action == 'sample':
        example_create_sample()


if __name__ == '__main__':
    main()
