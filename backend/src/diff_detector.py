#!/usr/bin/env python3
"""
FRT Diff Detector
Detects changes between FRT database versions
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple

logger = logging.getLogger(__name__)


class FRTDiffDetector:
    """Detects and reports changes between FRT database versions"""

    def __init__(self, data_dir: str = 'data'):
        self.data_dir = Path(data_dir)

    def load_database(self, filepath: Path) -> Dict[str, Dict]:
        """
        Load FRT database and index by FRN

        Args:
            filepath: Path to JSON database file

        Returns:
            Dictionary mapping FRN to record
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                records = json.load(f)

            # Index by FRN
            indexed = {record['frn']: record for record in records}
            logger.info(f"Loaded {len(indexed)} records from {filepath}")

            return indexed

        except Exception as e:
            logger.error(f"Error loading database from {filepath}: {e}")
            return {}

    def detect_changes(
        self,
        current_db: Dict[str, Dict],
        previous_db: Dict[str, Dict]
    ) -> Dict[str, List]:
        """
        Detect changes between two database versions

        Args:
            current_db: Current database indexed by FRN
            previous_db: Previous database indexed by FRN

        Returns:
            Dictionary with change categories
        """
        changes = {
            'added': [],
            'removed': [],
            'modified': [],
            'classification_changed': [],
            'metadata': {
                'detection_date': datetime.now().isoformat(),
                'current_count': len(current_db),
                'previous_count': len(previous_db)
            }
        }

        current_frns = set(current_db.keys())
        previous_frns = set(previous_db.keys())

        # Detect additions
        added_frns = current_frns - previous_frns
        for frn in added_frns:
            changes['added'].append(current_db[frn])

        # Detect removals
        removed_frns = previous_frns - current_frns
        for frn in removed_frns:
            changes['removed'].append(previous_db[frn])

        # Detect modifications
        common_frns = current_frns & previous_frns
        for frn in common_frns:
            current_record = current_db[frn]
            previous_record = previous_db[frn]

            # Compare records
            modifications = self._compare_records(current_record, previous_record)

            if modifications:
                change_entry = {
                    'frn': frn,
                    'make': current_record.get('make'),
                    'model': current_record.get('model'),
                    'changes': modifications,
                    'previous': previous_record,
                    'current': current_record
                }

                changes['modified'].append(change_entry)

                # Special tracking for classification changes (critical!)
                if 'class' in modifications:
                    changes['classification_changed'].append({
                        'frn': frn,
                        'make': current_record.get('make'),
                        'model': current_record.get('model'),
                        'old_class': previous_record.get('class'),
                        'new_class': current_record.get('class'),
                        'oic_references': current_record.get('oic_references', [])
                    })

        changes['metadata']['added_count'] = len(changes['added'])
        changes['metadata']['removed_count'] = len(changes['removed'])
        changes['metadata']['modified_count'] = len(changes['modified'])
        changes['metadata']['classification_changes'] = len(changes['classification_changed'])

        return changes

    def _compare_records(self, current: Dict, previous: Dict) -> Dict[str, Tuple]:
        """
        Compare two records and return differences

        Args:
            current: Current record
            previous: Previous record

        Returns:
            Dictionary of field: (old_value, new_value) for changed fields
        """
        modifications = {}

        # Fields to compare
        fields = ['make', 'model', 'manufacturer', 'type', 'action', 'class', 'notes']

        for field in fields:
            current_value = current.get(field, '').strip()
            previous_value = previous.get(field, '').strip()

            if current_value != previous_value:
                modifications[field] = (previous_value, current_value)

        return modifications

    def generate_report(self, changes: Dict) -> str:
        """
        Generate a human-readable report of changes

        Args:
            changes: Changes dictionary from detect_changes()

        Returns:
            Formatted report string
        """
        lines = []
        lines.append("=" * 70)
        lines.append("FRT DATABASE CHANGE REPORT")
        lines.append("=" * 70)
        lines.append(f"Detection Date: {changes['metadata']['detection_date']}")
        lines.append(f"Current Records: {changes['metadata']['current_count']}")
        lines.append(f"Previous Records: {changes['metadata']['previous_count']}")
        lines.append("")

        # Summary
        lines.append("SUMMARY:")
        lines.append(f"  Added:                    {changes['metadata']['added_count']}")
        lines.append(f"  Removed:                  {changes['metadata']['removed_count']}")
        lines.append(f"  Modified:                 {changes['metadata']['modified_count']}")
        lines.append(f"  Classification Changed:   {changes['metadata']['classification_changes']}")
        lines.append("")

        # Classification changes (CRITICAL)
        if changes['classification_changed']:
            lines.append("=" * 70)
            lines.append("⚠️  CRITICAL: CLASSIFICATION CHANGES")
            lines.append("=" * 70)

            for item in changes['classification_changed']:
                lines.append(f"\nFRN: {item['frn']}")
                lines.append(f"  Make/Model: {item['make']} {item['model']}")
                lines.append(f"  Old Class:  {item['old_class']}")
                lines.append(f"  New Class:  {item['new_class']}")

                if item.get('oic_references'):
                    lines.append(f"  OIC Refs:   {', '.join(item['oic_references'])}")

        # Added firearms
        if changes['added']:
            lines.append("\n" + "=" * 70)
            lines.append(f"ADDED FIREARMS ({len(changes['added'])})")
            lines.append("=" * 70)

            for item in changes['added'][:20]:  # Limit to first 20
                lines.append(f"  FRN {item['frn']}: {item['make']} {item['model']} - {item['class']}")

            if len(changes['added']) > 20:
                lines.append(f"  ... and {len(changes['added']) - 20} more")

        # Removed firearms
        if changes['removed']:
            lines.append("\n" + "=" * 70)
            lines.append(f"REMOVED FIREARMS ({len(changes['removed'])})")
            lines.append("=" * 70)

            for item in changes['removed'][:20]:  # Limit to first 20
                lines.append(f"  FRN {item['frn']}: {item['make']} {item['model']}")

            if len(changes['removed']) > 20:
                lines.append(f"  ... and {len(changes['removed']) - 20} more")

        lines.append("\n" + "=" * 70)

        return "\n".join(lines)

    def run(self, current_file: str = 'frt_database.json', previous_file: str = 'frt_database_previous.json'):
        """
        Run diff detection between two database files

        Args:
            current_file: Current database filename
            previous_file: Previous database filename
        """
        current_path = self.data_dir / current_file
        previous_path = self.data_dir / previous_file

        if not current_path.exists():
            logger.error(f"Current database not found: {current_path}")
            return

        if not previous_path.exists():
            logger.warning(f"Previous database not found: {previous_path}")
            logger.info("This appears to be the first run. No changes to detect.")
            return

        # Load databases
        current_db = self.load_database(current_path)
        previous_db = self.load_database(previous_path)

        # Detect changes
        logger.info("Detecting changes...")
        changes = self.detect_changes(current_db, previous_db)

        # Save changes to JSON
        changes_file = self.data_dir / 'frt_changes.json'
        with open(changes_file, 'w', encoding='utf-8') as f:
            json.dump(changes, f, indent=2, ensure_ascii=False)

        logger.info(f"Changes saved to {changes_file}")

        # Generate and save report
        report = self.generate_report(changes)
        report_file = self.data_dir / 'frt_changes_report.txt'

        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)

        logger.info(f"Report saved to {report_file}")

        # Print summary
        print(report)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Detect changes in FRT database')
    parser.add_argument('--data-dir', default='data', help='Data directory path')
    parser.add_argument('--current', default='frt_database.json', help='Current database filename')
    parser.add_argument('--previous', default='frt_database_previous.json', help='Previous database filename')

    args = parser.parse_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Run diff detector
    detector = FRTDiffDetector(data_dir=args.data_dir)
    detector.run(current_file=args.current, previous_file=args.previous)


if __name__ == '__main__':
    main()
