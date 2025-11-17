# FRT-Live: Real-Time Canadian Firearm Compliance Oracle

> **Mission**: Transform the static, 100,000+ page RCMP Firearms Reference Table PDF into a dynamic, searchable JSON API with active push notifications for classification changes.

## The Problem

The Canadian firearm regulatory landscape is "evergreen" - classifications can change overnight via Order in Council (OIC). Gun owners relying on static PDF downloads face a dangerous knowledge gap:

- **Regulatory Vacuum**: Public access limited to massive, outdated PDFs (100+ MB, 100,000+ pages)
- **Real Criminal Risk**: Missing a classification change can transform a law-abiding owner into a criminal overnight
- **Amnesty Deadline**: October 2026 deadline for prohibited firearm compliance
- **Data Obsolescence**: Previous scraping attempts (Armalytics) highlight community desperation for structured data

**Example**: The March 7, 2025 OIC prohibited 179 "assault-style" firearms. Anyone using a February PDF would be unknowingly possessing prohibited devices.

## The Solution

**FRT-Live** provides three critical services:

1. **Automated PDF Ingestion**: Smart parsing of RCMP FRT PDFs with change detection
2. **JSON API**: RESTful API for real-time firearm classification queries
3. **Mobile App**: Instant verification with push notifications for reclassifications

## Project Structure

```
frt-live/
├── backend/              # Python PDF parser & data pipeline
│   ├── src/
│   │   ├── frt_parser.py       # Main PDF parser
│   │   ├── diff_detector.py    # Change detection engine
│   │   ├── config.py           # Configuration
│   │   └── __init__.py
│   ├── data/                   # Data storage (gitignored)
│   ├── logs/                   # Logs (gitignored)
│   ├── requirements.txt
│   ├── example.py              # Usage examples
│   └── README.md
├── api/                  # FastAPI REST server (planned)
├── mobile/               # Expo/React Native app (planned)
└── README.md            # This file
```

## Quick Start

### Backend: PDF Parser

The backend parses RCMP FRT PDFs into structured JSON and detects changes between versions.

```bash
# Setup
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Create sample database for testing
python example.py sample

# Search the database
python example.py search

# Parse actual FRT PDF (requires valid URL)
python src/frt_parser.py

# Detect changes between versions
python src/diff_detector.py
```

**See [backend/README.md](backend/README.md) for detailed documentation.**

## Features

### 1. Automated PDF Ingestion

- **Smart Download**: Checks HTTP Last-Modified headers to avoid redundant downloads
- **Column Detection**: Automatically identifies table structure from PDF
- **Multi-line Handling**: Intelligently merges rows spanning multiple pages
- **Data Sanitization**: Standardizes classifications (Non-Restricted, Restricted, Prohibited)
- **OIC Extraction**: Identifies Order in Council references from notes

### 2. Change Detection

- **Version Comparison**: Diffs current vs. previous database
- **Classification Alerts**: Flags critical changes (Non-Restricted → Prohibited)
- **Detailed Reports**: Human and machine-readable change summaries
- **Audit Trail**: Tracks all modifications, additions, and removals

### 3. JSON API (Planned)

- **RESTful Endpoints**: `/api/firearms/search`, `/api/firearms/{frn}`
- **Fuzzy Search**: Find firearms by make, model, or partial matches
- **Real-time Updates**: WebSocket notifications for database changes
- **B2B Access**: API keys for retail POS integration

### 4. Mobile App (Planned)

- **OCR Scanning**: Photograph receiver markings for instant lookup
- **Watch List**: Favorite firearms to monitor for classification changes
- **Push Notifications**: Immediate alerts on reclassifications
- **Offline Mode**: Local database cache for field use

## Use Cases

### Individual Gun Owners
- Verify current legal status of owned firearms
- Receive alerts if firearms are reclassified
- Check before purchasing new firearms

### Retail Stores
- POS integration to prevent illegal sales
- Real-time inventory compliance checks
- Automated regulatory updates

### Ranges & Clubs
- Verify member firearms comply with range rules
- Track prohibited weapons for exclusion
- Maintain compliance records

### Developers
- Build inventory management systems
- Create auction platform integrations
- Develop compliance tools

## Technology Stack

### Backend (Current)
- **Python 3.8+**: Core parsing logic
- **pdfplumber**: Advanced PDF table extraction
- **requests**: HTTP downloads with caching
- **JSON**: Structured data output

### API (Planned)
- **FastAPI**: High-performance REST API
- **PostgreSQL**: Searchable database
- **Supabase**: Backend-as-a-Service (Auth, RLS)
- **Redis**: Caching layer

### Mobile (Planned)
- **Expo**: Cross-platform React Native framework
- **TypeScript**: Type-safe development
- **Tamagui/NativeWind**: Native-first styling
- **Supabase**: Real-time sync & auth

## Current Status

✅ **Phase 1: PDF Parser** (Complete)
- [x] PDF download with caching
- [x] Column boundary detection
- [x] Multi-line row handling
- [x] Data sanitization
- [x] Change detection
- [x] JSON output

🚧 **Phase 2: API Server** (Planned)
- [ ] FastAPI REST endpoints
- [ ] PostgreSQL database
- [ ] Search functionality
- [ ] WebSocket notifications
- [ ] API authentication

🔮 **Phase 3: Mobile App** (Planned)
- [ ] Expo app scaffold
- [ ] Firearm search UI
- [ ] OCR scanning
- [ ] Push notifications
- [ ] Watch list feature

## Example: Parsed FRT Data

```json
{
  "frn": "123456",
  "make": "Remington",
  "model": "870",
  "manufacturer": "Remington Arms Company",
  "type": "Shotgun",
  "action": "Pump",
  "class": "Non-Restricted",
  "notes": "Standard hunting configuration",
  "oic_references": []
}
```

## Example: Change Detection

```json
{
  "classification_changed": [
    {
      "frn": "789012",
      "make": "AR-15",
      "model": "Colt Canada C7",
      "old_class": "Non-Restricted",
      "new_class": "Prohibited",
      "oic_references": ["OIC 2020-0001"]
    }
  ],
  "metadata": {
    "detection_date": "2025-03-07T12:00:00",
    "classification_changes": 179
  }
}
```

## Legal Disclaimer

**IMPORTANT**: This tool is for informational purposes only. It does NOT constitute legal advice.

- Always verify firearm classifications with official RCMP sources
- Consult legal counsel for compliance questions
- Developers assume NO liability for legal issues arising from use
- Users are solely responsible for ensuring legal compliance

This is a public service tool designed to improve access to public regulatory data.

## Contributing

Contributions welcome! This project aims to serve the Canadian firearms community with better access to regulatory information.

### Areas for Contribution
- PDF parser improvements
- API development
- Mobile app development
- Documentation
- Testing

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## Roadmap

### Q2 2025
- Complete FastAPI backend
- PostgreSQL migration
- Basic search API

### Q3 2025
- Expo mobile app MVP
- OCR scanning
- Push notifications

### Q4 2025
- Public beta launch
- Retail API partnerships
- Community feedback integration

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/frt-live/issues)
- **Documentation**: See `backend/README.md` and other READMEs
- **Community**: (Forum/Discord TBD)

## License

MIT License - See LICENSE file for details

## Acknowledgments

- RCMP Specialized Firearms Support Services for maintaining the FRT
- Canadian firearms community for feedback and requirements
- Armalytics project for pioneering FRT data extraction

---

**Status**: Active Development | **Version**: 0.1.0 | **Last Updated**: Nov 2025
