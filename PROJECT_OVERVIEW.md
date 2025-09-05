# ATA Backend - Project Overview

## Repository Statistics

**Total Files:** 651  
**Total Directories:** 122

## Directory Structure and File Counts

### 📚 Books/ (24 files, 9 directories)
Educational content repository organized by curriculum levels:

- **GCSE/Years 10 & 11/**
  - English Language materials from Pearson Edexcel GCSE curriculum
  - 7 text files covering reading skills, writing skills, exam preparation
  
- **Secondary School/Year 9 (Key Stage 3)/**
  - Science materials from "Activate for AQA KS3 Science - GCSE-Ready"
  - 15 text files covering Biology, Chemistry, Physics topics
  - Topics include: Cells, Structure & Function, Reproduction, Particles, Elements, Reactions, Acids & Alkalis, Forces, Sound, Light, Space
  - Additional materials: Working Scientifically, Glossary, Index, Periodic Table

- **Utility Files:**
  - `directory generator.py` - Tool for generating directory structures
  - `directory_map.txt` - Documentation of directory organization

### 🗄️ alembic/ (4 files, 2 directories)
Database migration management:
- Database schema versioning and migration scripts
- Configuration for SQLAlchemy database migrations
- Contains 1 migration file for initial database schema creation

### 🚀 app/ (177 files, 34 directories) - **MAIN APPLICATION**

#### Core Structure:
- **data/** - File storage and uploads management
- **db/** - Database layer
  - Base configurations and database connection setup
  - **models/** - Database table models (5 files)
    - Assessment, chat, class/student relationships, generation models
- **models/** - Application data models (7 files)
  - Assessment, chatbot, class, dashboard, history, student, tool models
- **routers/** - API endpoints (8 files)
  - RESTful API routes for all major features
  - Endpoints: assessments, chatbot, classes, dashboard, history, library, public, tools
- **services/** - Business logic layer (19+ files)
  - Core services for each major feature
  - **Helper modules:**
    - **assessment_helpers/** - Analytics, data assembly, document parsing, grading, job creation
    - **class_helpers/** - CRUD operations, file processing, roster management
    - **database_helpers/** - Database utility functions

#### Key Services:
- Assessment generation and grading
- AI chatbot functionality
- Document processing and OCR
- Library management
- Report generation
- PDF processing
- Gemini AI integration

### 🧪 tests/ (10 files, 1 directory)
Comprehensive test suite covering:
- Analytics and matching algorithms
- Assessment models and services
- Data assembly processes
- Database operations
- Document parsing functionality
- Job creation helpers
- OCR performance and functionality

### 📦 node_modules/ (401 files, 61 directories)
JavaScript dependencies for logging:
- **winston** - Advanced logging library
- **morgan** - HTTP request logging middleware
- Supporting packages for logging functionality
- *Note: Should be added to .gitignore*

### 📄 Configuration Files

#### Python Configuration:
- **pyproject.toml** - Python project metadata and pytest configuration
- **requirements.txt** - Python dependencies (35 packages)
- **alembic.ini** - Database migration configuration

#### Container Configuration:
- **Dockerfile** - Multi-stage Docker build for production deployment
- Optimized for security with non-root user
- Includes Tesseract OCR and system dependencies

#### JavaScript Configuration:
- **package.json** - Node.js logging dependencies
- **package-lock.json** - Dependency lock file

#### Version Control:
- **.gitignore** - Git ignore rules
- **.git/** - Git repository metadata

## Technology Stack

### Backend Framework
- **FastAPI** - Modern Python web framework
- **Pydantic** - Data validation and settings management
- **Uvicorn/Gunicorn** - ASGI server for production

### Database
- **PostgreSQL** - Primary database
- **SQLAlchemy** - Object-Relational Mapping (ORM)
- **Alembic** - Database migration tool
- **Asyncpg** - Async PostgreSQL driver

### AI and Machine Learning
- **Google Generative AI (Gemini)** - AI model integration
- **Pandas** - Data manipulation and analysis

### Document Processing
- **PyMuPDF** - PDF processing and manipulation
- **pytesseract** - OCR (Optical Character Recognition)
- **python-docx** - Microsoft Word document processing
- **Pillow** - Image processing
- **openpyxl** - Excel file processing

### Security and Utilities
- **RestrictedPython** - Safe Python code execution
- **python-dotenv** - Environment variable management
- **python-multipart** - File upload handling

### Testing
- **pytest** - Testing framework
- **pytest-asyncio** - Async testing support

### Logging
- **winston** (Node.js) - Structured logging
- **morgan** - HTTP request logging

### Deployment
- **Docker** - Containerization
- **Railway** - Cloud deployment platform

## Project Purpose

The **ATA Backend** is an **AI Teaching Assistant** system designed to revolutionize educational technology by providing:

### Core Functionality:
1. **Intelligent Assessment Generation** - AI-powered creation of educational assessments
2. **Document Processing Pipeline** - OCR and parsing of educational materials
3. **AI Chatbot** - Educational support and Q&A functionality
4. **Class Management** - Student roster and class organization
5. **Performance Analytics** - Student assessment analytics and matching
6. **Educational Library** - Curated collection of curriculum-aligned content
7. **Report Generation** - Automated grading and performance reports

### Target Users:
- **Teachers** - Assessment creation, class management, student analytics
- **Students** - AI-powered learning assistance and feedback
- **Educational Institutions** - Curriculum management and performance tracking

### Key Features:
- **Multi-format Document Support** - PDF, Word, Excel processing
- **OCR Capabilities** - Text extraction from images and scanned documents
- **AI-Powered Content Generation** - Leveraging Google's Gemini AI
- **RESTful API Architecture** - Scalable and maintainable design
- **Comprehensive Testing** - Robust test coverage for reliability
- **Containerized Deployment** - Docker-based for consistent environments

## Development Status

The project appears to be in **active development** with:
- Comprehensive API structure in place
- Full database migration support
- Extensive testing framework
- Production-ready Docker configuration
- Rich educational content library
- Multi-service architecture for scalability

This is a sophisticated educational technology platform that combines modern Python web development with AI capabilities to enhance teaching and learning experiences.