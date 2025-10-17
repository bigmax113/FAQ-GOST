# Document Q&A System with xAI Grok

## Overview
A Flask-based document question-answering system that downloads files from Google Drive and uses xAI's Grok AI model to answer questions about EU directives, standards, and FAQs. The system processes PDF and DOCX documents, caches the extracted text, and uses intelligent chunking to handle large documents within token limits.

## Current State
- ✅ Flask backend with document processing
- ✅ Google Drive integration for document download
- ✅ xAI Grok API integration for Q&A
- ✅ React-based frontend with Tailwind CSS
- ✅ Three document folders: Декларации (Declarations/Directives), Стандарты (Standards), and FAQ
- ✅ Caching system to avoid re-processing documents
- ✅ Smart chunking for large documents

## Recent Changes (Oct 14, 2025)
- Created Flask application (app.py) with document processing and Q&A endpoints
- Created React-based frontend (index.html) with folder selection and question input
- Set up xAI API key integration via environment variables (✅ Configured)
- Set up Google Drive API key for document downloads (✅ Configured)
- Removed hardcoded Google API key for security
- Configured Google Drive API with fallback to local files
- Added .gitignore for Python project
- Configured Flask workflow on port 5000
- Successfully downloaded and cached documents (~10.6MB total):
  - Декларации: 625KB (8 files)
  - Стандарты: 9.4MB (104 files)
  - FAQ: 584KB

## Project Architecture

### Backend (app.py)
- **Framework**: Flask
- **Document Processing**: PyPDF2 (PDF), python-docx (DOCX)
- **AI Model**: xAI Grok-4-fast-reasoning (1.9M context window)
- **Google Drive**: google-api-python-client

### Key Features
1. **Document Download**: Downloads ZIP archives from Google Drive folders
2. **Text Extraction**: Extracts text from PDF and DOCX files
3. **Caching**: Saves processed document text to avoid re-processing
4. **Smart Chunking**: Splits large documents into chunks that fit within token limits
5. **Multi-part Q&A**: Processes each chunk separately then synthesizes final answer
6. **Update Checking**: Refreshes document cache on demand

### API Endpoints
- `POST /api/initialize` - Initialize all document folders
- `POST /api/check_updates` - Check for and apply updates
- `POST /api/submit_question` - Submit question for AI processing
- `GET /` - Serve frontend
- `GET /favicon.ico` - Favicon handler

### Frontend (index.html)
- **Framework**: React 18 (CDN)
- **Styling**: Tailwind CSS (CDN)
- **HTTP Client**: Axios
- **Features**:
  - Folder selection (radio buttons)
  - Question input with Enter key support
  - Status indicators with loading spinner
  - Answer display area with scrolling
  - Update checking button

## Environment Variables
- `XAI_API_KEY` - xAI API key for Grok model (required) ✅
- `GOOGLE_API_KEY` - Google Drive API key (optional, needed for downloading from Drive) ✅
  
**Note**: If `GOOGLE_API_KEY` is not set, the system will use local files from `data_*` folders.

## Folder IDs
Default Google Drive folder IDs (can be updated in app.py):
- Декларации: `1ZTDzwp_ywHn8bnpTybfCOG4MvcpblaXn`
- Стандарты: `1VnlhnmBWvMpIcBJPtdJwlnPku2-_XtTx`
- FAQ: `1-NrMMZazEkw5N1JvLVo5UuVs62mx97gv`

## File Structure
```
.
├── app.py                  # Flask backend
├── index.html              # React frontend
├── .gitignore              # Git ignore rules
├── replit.md               # This file
├── pyproject.toml          # Python dependencies
├── cache_*.json            # Document caches (gitignored)
└── data_*/                 # Downloaded documents (gitignored)
```

## How It Works
1. **Initialization**: Downloads ZIP archives from Google Drive, extracts documents
2. **Processing**: Extracts text from PDFs and DOCXs, builds document cache
3. **Query**: User selects folder and asks question
4. **Chunking**: System splits document cache into manageable chunks
5. **AI Processing**: Each chunk is sent to Grok with the question
6. **Synthesis**: All partial answers are combined into final response

## Setup Instructions

### Option 1: Use Cached Documents (Current Setup)
The system is currently working with cached documents. You can start asking questions immediately!

### Option 2: Download Fresh Documents from Google Drive
To refresh documents from Google Drive:
1. Add `GOOGLE_API_KEY` to Replit Secrets
2. Get an API key from [Google Cloud Console](https://console.cloud.google.com/)
3. Enable Google Drive API in your project
4. Click "Check Updates" button in the app

### Option 3: Use Local Files
1. Create folders: `data_Декларации`, `data_Стандарты`, `data_FAQ`
2. Place your PDF and DOCX files in these folders
3. Click "Check Updates" to re-process

## User Preferences
- Language: Russian (Русский) - all UI and responses in Russian
- AI Model: xAI Grok-4-fast-reasoning (text-only, 1.9M context)
- Document Sources: EU directives, standards, and internal FAQs
