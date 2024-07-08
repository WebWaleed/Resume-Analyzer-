import spacy
from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from pdfminer.high_level import extract_text
from io import BytesIO
import re
from dateutil import parser
from datetime import datetime
from dateutil.relativedelta import relativedelta

app = FastAPI()

nlp = spacy.load("en_core_web_md")

def extract_text_from_pdf(pdf_file):
    return extract_text(pdf_file)

def normalize_skill(skill):
    return re.sub(r'\d+', '', skill).strip().lower()

def find_skills_in_text(text, skills_list):
    doc = nlp(text.lower())
    skills_found = [skill for skill in skills_list if normalize_skill(skill) in doc.text]
    return skills_found

def extract_contact_info(text):
    email_pattern = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    phone_pattern = re.compile(r'\+92-\d{10}|\+92\d{9}|\+03\d{2}-\d{7}|03\d{9}|\+92\s?\d{10}')
    email = email_pattern.findall(text)
    phone = phone_pattern.findall(text)

    lines = text.split('\n')
    name = None
    if lines:
        first_line = lines[0].strip()
        if len(lines) > 1:
            second_line_words = lines[1].strip().split()[:2]
            if "ENGINEER" not in second_line_words:
                name = f"{first_line} {' '.join(second_line_words)}".strip()
            else:
                name = first_line
    
    email = email[0] if email else None
    phone = phone[0] if phone else None

    return name, email, phone

def extract_experience_dates(resume_text):
    date_patterns = [
        r'\d{2}/\d{4}',  # Matches MM/YYYY
        r'\d{2}/\d{2}/\d{4}',  # Matches DD/MM/YYYY
        r'\w+ \d{4}',  # Matches Month YYYY (e.g., "March 2020")
        r'\d{4}-\d{4}',  # Matches YYYY-YYYY
    ]

    extracted_dates = []

    for pattern in date_patterns:
        dates = re.findall(pattern, resume_text)
        extracted_dates.extend(dates)

    month_mapping = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12',
        'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
        'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
        'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12'
    }

    def convert_date(date_str):
        for month_name, month_num in month_mapping.items():
            if month_name in date_str.lower():
                date_str = date_str.lower().replace(month_name, month_num)
                break
        return date_str

    unique_dates = list(set(extracted_dates))
    print('====== unique_dates', unique_dates)
    return unique_dates

def extract_experience(resume_text):
    resume_headings = [
        "education",
        "contact information",
        "contact",
        "objective or summary",
        "skills",
        "certifications",
        "projects",
        "volunteer work",
        "awards and honors",
        "languages",
        "summary",
    ]

    resume_text_list = resume_text.split("\n\n")
    resume_text_list = [item.strip() for item in resume_text_list]

    exp_sen = ""
    if "Experience" in resume_text_list:
        exp_ind = resume_text_list.index('Experience')
        for section in resume_text_list:
            if section.lower() in resume_headings:
                sec_ind = resume_text_list.index(section)
                if exp_ind < sec_ind:
                    only_exp = resume_text_list[exp_ind:sec_ind]
                else:
                    only_exp = resume_text_list[exp_ind:]
                if only_exp:
                    exp_sen = ', '.join(only_exp)
                break
    else:
        exp_sen = '\n'.join(resume_text_list)

    exp_dates = extract_experience_dates(exp_sen)
    print('============= exp_dates', exp_dates)
    total_experience = relativedelta()
    current_date = datetime.now()

    for date in exp_dates:
        try:
            start_date = parser.parse(date)
            end_date = current_date  # Default to current date if end date is not provided
            
            experience_delta = relativedelta(end_date, start_date)
            total_experience += experience_delta
        except Exception as e:
            print(f"Error parsing dates: {e}")
    
    total_experience_str = f"{total_experience.years} years, {total_experience.months} months"
    return total_experience_str, exp_dates

def print_extracted_information(name, confidence, email, phone, experience):
    print(f"Name: {name}\n")
    print(f"Confidence: {confidence}\n")
    print(f"Email: {email}\n")
    print(f"Phone: {phone if phone else 'no contact info'}\n")
    print(f"Experience: {experience}\n")

@app.post("/single_resume")
async def create_upload_file(skills_required: str = Form(...), resume_file: UploadFile = File(...)):
    try:
        resume_contents = await resume_file.read()
        resume_pdf = BytesIO(resume_contents)
        text = extract_text_from_pdf(resume_pdf)

        skills_list = [skill.strip() for skill_with_slash in skills_required.split(',') for skill in skill_with_slash.split('/')]
        lower_skill_list = [normalize_skill(s) for s in skills_list]
        skills = set(lower_skill_list)
        skills_extracted = set(find_skills_in_text(text, skills))
        
        name, email, phone = extract_contact_info(text)

        total_experience_str, exp_dates = extract_experience(text)
        
        print_extracted_information(name, f'{round((len(skills_extracted) / len(skills)) * 100, 2)}%' if skills_extracted else "0.0%",
                                    email, phone, total_experience_str)

        if skills_extracted:
            skill_rate = round((len(skills_extracted) / len(skills)) * 100, 2)
            response_data = {
                "success": True,
                "responseMessage": "Skills Matched",
                "responseCode": "200",
                "data": {
                    "skills_required": skills_required,
                    "confidence": f'{skill_rate}%',
                    "name": name,
                    "email": email,
                    "phone": phone if phone else "no contact info",
                    "experience_dates": exp_dates,
                    "total_experience": total_experience_str
                }
            }
        elif email is None and phone is None:
            response_data = {
                "success": False,
                "responseMessage": "No contact info",
                "responseCode": "404",
                "data": {}
            }
        else:
            response_data = {
                "success": True,
                "responseMessage": "Skill Not Matched",
                "responseCode": "200",
                "data": {
                    "skills_required": skills_required,
                    "confidence": "0.0%",
                    "name": name,
                    "email": email,
                    "phone": phone if phone else "no contact info",
                    "experience_dates": exp_dates,
                    "total_experience": total_experience_str
                }
            }

        return JSONResponse(content=response_data)

    except Exception as e:
        response_data = {
            "success": False,
            "responseMessage": f"Error: {str(e)}",
            "responseCode": "500",
            "data": {}
        }
        return JSONResponse(content=response_data)

@app.post("/bulk_resume")
async def create_upload_files(skills_required: str = Form(...), resume_files: list[UploadFile] = File(...)):
    results = {}
    id_counter = 1  # Initialize the ID counter
    
    for resume_file in resume_files:
        try:
            resume_contents = await resume_file.read()
            resume_pdf = BytesIO(resume_contents)
            text = extract_text_from_pdf(resume_pdf)

            skills_list = [skill.strip() for skill_with_slash in skills_required.split(',') for skill in skill_with_slash.split('/')]
            lower_skill_list = [normalize_skill(s) for s in skills_list]
            skills = set(lower_skill_list)
            skills_extracted = set(find_skills_in_text(text, skills))
            
            name, email, phone = extract_contact_info(text)

            total_experience_str, exp_dates = extract_experience(text)
            
            print(f"Resume {id_counter}:")
            print_extracted_information(name, f'{round((len(skills_extracted) / len(skills)) * 100, 2)}%' if skills_extracted else "0.0%",
                                        email, phone, total_experience_str)
            
            if skills_extracted:
                skill_rate = round((len(skills_extracted) / len(skills)) * 100, 2)
                response_data = {
                    "success": True,
                    "responseMessage": "Skills Matched",
                    "responseCode": "200",
                    "data": {
                        "skills_required": skills_required,
                        "confidence": f'{skill_rate}%',
                        "name": name,
                        "email": email,
                        "phone": phone if phone else "no contact info",
                        "experience_dates": exp_dates,
                        "total_experience": total_experience_str
                    }
                }
            elif email is None and phone is None:
                response_data = {
                    "success": False,
                    "responseMessage": "No contact info",
                    "responseCode": "404",
                    "data": {}
                }
            else:
                response_data = {
                    "success": True,
                    "responseMessage": "Skill Not Matched",
                    "responseCode": "200",
                    "data": {
                        "skills_required": skills_required,
                        "confidence": "0.0%",
                        "name": name,
                        "email": email,
                        "phone": phone if phone else "no contact info",
                        "experience_dates": exp_dates,
                        "total_experience": total_experience_str
                    }
                }
            
            results[f"Resume {id_counter}"] = response_data
            id_counter += 1

        except Exception as e:
            response_data = {
                "success": False,
                "responseMessage": f"Error: {str(e)}",
                "responseCode": "500",
                "data": {}
            }
            results[f"Resume {id_counter}"] = response_data
            id_counter += 1
    
    return JSONResponse(content=results)
