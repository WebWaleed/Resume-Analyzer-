# Resume Processing API

This FastAPI application processes resumes to extract relevant information such as skills, contact information, and work experience. It uses libraries like `spacy` for NLP tasks and `pdfminer` for extracting text from PDF files.

## Features

- Extract text from PDF resumes.
- Normalize and identify required skills in the resume text.
- Extract contact information (name, email, phone) from the resume.
- Extract and calculate total work experience based on date patterns in the resume.
- Provide endpoints for processing single and multiple resumes.

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/resume-processing-api.git
