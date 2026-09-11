import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from groq import Groq
from pydantic import BaseModel, Field
from pypdf import PdfReader
from fastapi.middleware.cors import CORSMiddleware


# ============================================================
# Configuration
# ============================================================

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
RESUME_PATH = BASE_DIR / "my_resume.pdf"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    raise ValueError("GROQ_API_KEY is missing from the .env file.")

client = Groq(api_key=GROQ_API_KEY)

# Keep this model unchanged.
MODEL = "openai/gpt-oss-120b"

app = FastAPI(
    title="HireMeAI",
    description="AI-powered resume analysis and candidate Q&A API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# ============================================================
# Pydantic Models
# ============================================================

class Experience(BaseModel):
    company: str | None = None
    role: str | None = None
    duration: str | None = None
    description: str | None = None
    skills_used: list[str] = Field(default_factory=list)


class Resume(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None

    total_experience_years: float | None = None

    skills: list[str] = Field(default_factory=list)
    experiences: list[Experience] = Field(default_factory=list)
    education: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    certifications: list[str] = Field(default_factory=list)


class ChatRequest(BaseModel):
    question: str = Field(
        min_length=1,
        description="Question that HR or the user wants to ask the candidate."
    )


resume_schema = Resume.model_json_schema()


# ============================================================
# PDF Extraction
# ============================================================

def read_pdf(file_path: Path) -> str:
    """
    Extract text from a PDF file.
    """

    if not file_path.exists():
        raise FileNotFoundError(
            f"Resume file not found: {file_path}"
        )

    if file_path.suffix.lower() != ".pdf":
        raise ValueError("The resume file must be a PDF.")

    reader = PdfReader(file_path)

    text_parts = []

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text_parts.append(page_text)

    text = "\n".join(text_parts).strip()

    if not text:
        raise ValueError(
            "No readable text was extracted from the resume PDF."
        )

    return text


# ============================================================
# Resume Parsing
# ============================================================

def parse_resume(resume_text: str) -> Resume:
    """
    Convert raw resume text into structured Resume data
    using the configured LLM.
    """

    system_prompt = f"""
You are an expert resume parser.

Your task is to extract information from the provided resume.

Extract information based on the meaning of the content,
not only exact section headings.

Different resumes may use different headings.

For example:
- Experience
- Professional Experience
- Work History
- Employment
- Internships

These may all contain relevant experience.

Skills may appear in:
- Skills sections
- Work experience
- Internships
- Projects
- Education

Return ONLY valid JSON matching this schema:

{json.dumps(resume_schema, indent=2)}

Important rules:

1. Do not invent information.

2. Extract only information explicitly supported by the resume.

3. Do not infer skills from unrelated technologies.

4. Do not infer professional experience from personal projects.

5. Do not infer years of experience unless the resume explicitly
   provides enough information to support it.

6. If a single-value field is unavailable, return null.

7. If a list has no information, return an empty list.

8. Include internships inside experiences if they are explicitly
   presented as internships.

9. Extract skills mentioned across the entire resume.

10. Preserve the meaning of the candidate's information.

11. Do not add explanations outside the JSON object.
"""

    user_prompt = f"""
Parse the following resume:

---------------- RESUME ----------------

{resume_text}

-------------- END RESUME --------------
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": user_prompt,
                },
            ],
            response_format={
                "type": "json_object"
            },
        )

        raw_output = response.choices[0].message.content

        if not raw_output:
            raise ValueError("The AI returned an empty response.")

        data = json.loads(raw_output)

        return Resume(**data)

    except json.JSONDecodeError as exc:
        raise ValueError(
            "The AI returned invalid JSON while parsing the resume."
        ) from exc

    except Exception as exc:
        raise RuntimeError(
            f"Resume parsing failed: {exc}"
        ) from exc


# ============================================================
# Candidate Q&A
# ============================================================

def ask_candidate(question: str, resume: Resume) -> str:
    """
    Answer a question using ONLY the structured resume data.
    """

    system_prompt = f"""
You are an AI assistant representing a job candidate.

Below is the complete structured information available about
the candidate:

---------------- CANDIDATE DATA ----------------

{resume.model_dump_json(indent=2)}

-------------- END CANDIDATE DATA ---------------

Rules:

1. Use ONLY information explicitly present in the candidate data.

2. Never hallucinate.

3. Never invent skills, experience, education, projects,
   certifications, responsibilities, achievements, or results.

4. Do not assume proficiency simply because a technology is listed.

5. Do not convert a personal project into professional experience.

6. Do not add technologies that are not present in the candidate data.

7. Do not create numerical claims unless the candidate data
   explicitly contains those numbers.

8. If the requested information is unavailable, say exactly:

"I don't have enough information to answer that."

9. Be professional and concise.

10. Answer as if HR is interviewing this candidate.

11. When appropriate, answer in first person because you are
    representing the candidate.
"""

    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": question,
                },
            ],
        )

        answer = response.choices[0].message.content

        if not answer:
            raise ValueError("The AI returned an empty answer.")

        return answer.strip()

    except Exception as exc:
        raise RuntimeError(
            f"Candidate Q&A failed: {exc}"
        ) from exc


# ============================================================
# API Routes
# ============================================================

@app.get("/")
def home():
    """
    Basic health check.
    """

    return {
        "message": "HireMeAI backend is running."
    }


@app.get("/resume", response_model=Resume)
def get_resume():
    """
    Extract and parse the candidate's resume.
    """

    try:
        resume_text = read_pdf(RESUME_PATH)
        resume = parse_resume(resume_text)

        return resume

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )


@app.post("/chat")
def chat(request: ChatRequest):
    """
    Ask the AI a question about the candidate.
    """

    try:
        resume_text = read_pdf(RESUME_PATH)
        resume = parse_resume(resume_text)

        answer = ask_candidate(
            request.question,
            resume,
        )

        return {
            "answer": answer
        }

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        )

    except RuntimeError as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc),
        )