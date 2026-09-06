import os
import json
import uuid
from typing import List, Optional, TypedDict
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.checkpoint.memory import MemorySaver
load_dotenv()


# from langchain_groq import ChatGroq
# llm = ChatGroq(
#     model="openai/gpt-oss-120b",
#     temperature=0.4,
#     api_key=os.getenv("GROQ_API_KEY")
# )

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "openai/gpt-oss-120b")

#store the running interview in DATA_FILE = "interview.json"
DATA_FILE = "interviews.json"

#iterview parameters
TOTAL_QUESTIONS = 7         
SCORE_THRESHOLD = 7          
MAX_FOLLOW_UPS = 2  

if not GROQ_API_KEY:
    raise RuntimeError("GROQ_API_KEY not found. Add it to your .env file.")
 
client = Groq(api_key=GROQ_API_KEY)

#fastapi 
app = FastAPI(title="AI Interview System (LangGraph)")
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#json file storage
def _ensure_file_exists():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({}, f)
 
 
def load_all() -> dict:
    _ensure_file_exists()
    with open(DATA_FILE, "r") as f:
        return json.load(f)
 
 
def save_all(data: dict):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)
 
 
def upsert_record(interview_id: str, updates: dict):
    data = load_all()
    record = data.get(interview_id, {})
    record.update(updates)
    data[interview_id] = record
    save_all(data)
 
 
#llm helpers
def call_llm(system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
    )
    return response.choices[0].message.content.strip()
 
 
def call_llm_json(system_prompt: str, user_prompt: str) -> dict:
    raw = call_llm(system_prompt, user_prompt)
    cleaned = raw.replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {"error": "Could not parse LLM response", "raw": raw}
 
 
#graph state

class interviewState(TypedDict,total=False):
    role:str
    experience:str
    job_description:str

    skills:List[str]
    experience_requirements: str
    tools: List[str]

    questions:List[str]
    current_idx:int
    follow_up_count:int

    current_question: str
    current_answer: str
    current_score: int
    current_feedback: str

        
    log: List[dict]
    status: str
    report: dict

#prompt

SKILLS_SYSTEM = (
    "Extract the core technical/programming skills required for this role. "
    "Return ONLY a JSON array of short strings, e.g. [\"Python\", \"SQL\"]."
)
 
EXPERIENCE_SYSTEM = (
    "Summarize the experience/seniority expectations for this role in ONE "
    "short sentence. Return ONLY that sentence, no JSON, no quotes."
)
 
TOOLS_SYSTEM = (
    "Extract the tools, frameworks, or platforms required for this role "
    "(e.g. FastAPI, Docker, REST APIs). Return ONLY a JSON array of short strings."
)
 
 
QUESTION_GEN_SYSTEM = (
    "You are an expert technical interviewer. Generate clear, concise interview "
    "questions tailored to the role, experience level, and required skills/tools. "
    "Return ONLY a JSON array of strings, nothing else."
)
 
EVALUATE_SYSTEM = (
    "You are a strict but fair technical interview evaluator. Score answers from "
    "0 to 10 based on correctness, completeness, and clarity. "
    "Return ONLY a JSON object with keys: score (int), feedback (string, 1-2 sentences)."
)
 
FOLLOW_UP_SYSTEM = (
    "You are a technical interviewer. The candidate gave a weak or incomplete "
    "answer. Ask ONE short, targeted follow-up question that probes deeper into "
    "the same topic. Return ONLY the follow-up question text, nothing else."
)
 
REPORT_SYSTEM = (
    "You are an interview performance analyst. Based on the full interview log, "
    "produce a structured performance report. Return ONLY a JSON object with keys: "
    "overall_score (float 0-10), "
    "category_scores (object with keys technical_knowledge, communication, "
    "problem_solving, answer_quality — each an int 0-10), "
    "strengths (array of strings), weaknesses (array of strings), "
    "recommendations (array of strings), "
    "overall_feedback (string, 2-3 sentences)."
)
 
def jd_context(state: interviewState) -> str:
    jd = state.get("job_description") or "(no job description provided)"
    return f"Role: {state['role']}\nExperience Level: {state['experience']}\nJob Description:\n{jd}"

#nodes

#parallal 
          #       Job Description
          #              ↓
          #    ┌─────────┼─────────┐
          #    ↓         ↓         ↓
          # Skills   Experience   Tools
          #    ↓         ↓         ↓
          #    └─────────┼─────────┘
          #              ↓
          #        Combined Data

def analyze_skill_node(state:interviewState)->dict:
    res=call_llm_json(SKILLS_SYSTEM,jd_context(state))
    return{"skills":res if isinstance(res,list)else []}

def analyze_exp_node(state:interviewState)->dict:
    res=call_llm(EXPERIENCE_SYSTEM,jd_context(state))
    return{"experience_requirements":res}

def anlyze_tool_node(state:interviewState)->dict:
    res=call_llm_json(TOOLS_SYSTEM,jd_context(state))
    return{"tools":res if isinstance(res,list)else []}

#after these parallel workflow combine all three

def combine_analysis_node(state: interviewState) -> dict:
    return {}

# ---- SEQUENTIAL step after the parallel analysis ----

def gen_qs_node(state:interviewState)->dict:
    prompt=(
        f"Role: {state['role']}\n"
        f"Experience Level: {state['experience']}\n"
        f"Required Skills: {', '.join(state.get('skills', [])) or 'N/A'}\n"
        f"Required Tools/Frameworks: {', '.join(state.get('tools', [])) or 'N/A'}\n"
        f"Experience Expectations: {state.get('experience_requirements', 'N/A')}\n\n"
        f"Generate exactly {TOTAL_QUESTIONS} interview questions, ordered from "
        f"fundamental to more advanced. Return ONLY a JSON array of "
        f"{TOTAL_QUESTIONS} question strings."

    )

    res=call_llm_json(QUESTION_GEN_SYSTEM,prompt)
    questions=res if isinstance(res,list) else [str(res)]

    return{
        "questions":questions[:TOTAL_QUESTIONS],
        "current_idx":0,
        "follow_up_count":0,
        "log": [],
        "status": "in_progress",
    }

# ---- ITERATIVE loop point: pauses here and waits for the user's answer ----

def ask_qs_node(state:interviewState)->dict:
    qs=state["questions"][state["current_idx"]]
    ans=interrupt({
        "question": qs,
        "question_number": state["current_idx"] + 1,
        "total_questions": len(state["questions"]),

    })
    return {"current_question": qs, "current_answer": ans}


def evaluate_ans_node(state:interviewState)->dict:
    prompt=(
      f"Question: {state['current_question']}\n"
      f"Candidate's Answer: {state['current_answer']}\n\n"
      f'Return ONLY JSON like: {{"score": 8, "feedback": "..."}}' 
    )
    res=call_llm_json(EVALUATE_SYSTEM,prompt)
    score=int(res.get("score",0))if isinstance(res,dict)else 0
    feedback=(
        res.get("feedback","Could not evaluate answer.")
        if isinstance(res,dict) else "Could not evaluate answer."
    )
    new_log_entry={
        "question": state["current_question"],
        "answer": state["current_answer"],
        "score": score,
        "feedback": feedback,
    }

    return{
        "current_score": score,
        "current_feedback": feedback,
        "log": state["log"] + [new_log_entry],
    }

# ---- CONDITIONAL router: decides which branch to take next ----

def route_after_evaluation(state:interviewState)->str:
    is_last_qs=state["current_idx"]>=len(state["questions"])-1
    if state["current_score"]<SCORE_THRESHOLD and state["follow_up_count"]<MAX_FOLLOW_UPS:
        return "follow_up"

    return "generate_report" if is_last_qs else "next_question"


def follow_up_node(state:interviewState)->dict:
    prompt=(
        f"Original Question: {state['current_question']}\n"
        f"Candidate's Answer: {state['current_answer']}\n"
        f"Feedback: {state['current_feedback']}\n\n"
        f"Write one concise follow-up question."
    )
    follow_up_qs=call_llm(FOLLOW_UP_SYSTEM,prompt)
    updated_qs=list(state["questions"])
    updated_qs[state["current_idx"]]=follow_up_qs

    return{
        "questions": updated_qs,
        "follow_up_count": state["follow_up_count"] + 1,
    }

def next_qs_node(state:interviewState)->dict:
    return {
        "current_idx": state["current_idx"] + 1,
        "follow_up_count": 0,
    }

def gen_final_report(state:interviewState)->dict:
    log_text="\n\n".join(
        f"Q: {item['question']}\nA: {item['answer']}\nScore: {item['score']}/10\nFeedback: {item['feedback']}"
        for item in state["log"]
    )

    prompt=f"Role: {state['role']}\n\nInterview Log:\n{log_text}\n\nGenerate the final structured report as JSON."
    result = call_llm_json(REPORT_SYSTEM, prompt)
    if not isinstance(result, dict) or "error" in result:
        avg = sum(item["score"] for item in state["log"]) / len(state["log"])
        result = {
            "overall_score": round(avg, 1),
            "category_scores": {},
            "strengths": [],
            "weaknesses": [],
            "recommendations": [],
            "overall_feedback": "Report generation had an issue; showing average score only.",
        }
 
    return {"status": "completed", "report": result}


#building graph

builder=StateGraph(interviewState)

builder.add_node("analyze_skills",analyze_skill_node)
builder.add_node("analyze_exp",analyze_exp_node)
builder.add_node("analyze_tools",anlyze_tool_node)
builder.add_node("combined_analysis",combine_analysis_node)
builder.add_node("generate_questions",gen_qs_node)
builder.add_node("ask_questions",ask_qs_node)
builder.add_node("evaluate_ans",evaluate_ans_node)
builder.add_node("follow_up",follow_up_node)
builder.add_node("next_question",next_qs_node)
builder.add_node("generate_final_report",gen_final_report)

#paralel edge 
builder.add_edge(START,"analyze_skills")
builder.add_edge(START,"analyze_exp")
builder.add_edge(START,"analyze_tools")

#combine upper three

builder.add_edge("analyze_skills","combined_analysis")
builder.add_edge("analyze_exp","combined_analysis")
builder.add_edge("analyze_tools","combined_analysis")

#seq
builder.add_edge("combined_analysis","generate_questions")
builder.add_edge("generate_questions","ask_questions")
builder.add_edge("ask_questions","evaluate_ans")

#condi

builder.add_conditional_edges(
    "evaluate_ans",
    route_after_evaluation,{
        "follow_up": "follow_up",
        "next_question": "next_question",
        "generate_report": "generate_final_report",
    },
)

# ITERATIVE loop back to ask_question

builder.add_edge("follow_up","ask_questions")
builder.add_edge("next_question","ask_questions")

builder.add_edge("generate_final_report",END)


checkpointer = MemorySaver()
graph = builder.compile(checkpointer=checkpointer)


#pydantic schema

class StartInterviewRequest(BaseModel):
    role: str
    experience: str
    job_description: Optional[str] = ""

class StartInterviewResponse(BaseModel):
    interview_id: str
    question: str
    question_number: int
    total_questions: int
    skills: List[str]
    tools: List[str]
    experience_requirements: str


class AnswerRequest(BaseModel):
    interview_id: str
    answer: str

class AnswerResponse(BaseModel):
    score: int
    feedback: str
    next_action: str              # "follow_up" | "next_question" | "finished"
    next_question: Optional[str] = None
    question_number: Optional[int] = None
    total_questions: int = TOTAL_QUESTIONS


class ReportResponse(BaseModel):
    role: str
    overall_score: float
    category_scores: dict
    strengths: List[str]
    weaknesses: List[str]
    recommendations: List[str]
    overall_feedback: str
 
#api routes

def _config_for(interview_id: str) -> dict:
    return {"configurable": {"thread_id": interview_id}}

@app.post("/interview/start", response_model=StartInterviewResponse)
def start_interview(payload: StartInterviewRequest):
    interview_id = str(uuid.uuid4())
    config = _config_for(interview_id)
 
    initial_state: interviewState = {
        "role": payload.role,
        "experience": payload.experience,
        "job_description": payload.job_description or "",
    }
 
    result = graph.invoke(initial_state, config=config)
 
    # graph paused inside ask_question via interrupt()
    interrupt_payload = result["__interrupt__"][0].value
 
    state_values = graph.get_state(config).values
 
    upsert_record(interview_id, {
        "role": payload.role,
        "experience": payload.experience,
        "job_description": payload.job_description or "",
        "skills": state_values.get("skills", []),
        "tools": state_values.get("tools", []),
        "experience_requirements": state_values.get("experience_requirements", ""),
        "log": [],
        "status": "in_progress",
    })
 
    return StartInterviewResponse(
        interview_id=interview_id,
        question=interrupt_payload["question"],
        question_number=interrupt_payload["question_number"],
        total_questions=interrupt_payload["total_questions"],
        skills=state_values.get("skills", []),
        tools=state_values.get("tools", []),
        experience_requirements=state_values.get("experience_requirements", ""),
    )
 

@app.post("/interview/answer", response_model=AnswerResponse)
def submit_answer(payload: AnswerRequest):
    config = _config_for(payload.interview_id)
 
    existing_state = graph.get_state(config)
    if not existing_state.values:
        raise HTTPException(status_code=404, detail="Interview not found.")
 
    result = graph.invoke(Command(resume=payload.answer), config=config)
    state_values = graph.get_state(config).values
 
    # persist human-readable log after every turn
    upsert_record(payload.interview_id, {"log": state_values.get("log", [])})
 
    if "__interrupt__" in result:
        # graph looped back and is paused on the next question / follow-up
        interrupt_payload = result["__interrupt__"][0].value
        next_action = "follow_up" if state_values["follow_up_count"] > 0 else "next_question"
 
        return AnswerResponse(
            score=state_values["current_score"],
            feedback=state_values["current_feedback"],
            next_action=next_action,
            next_question=interrupt_payload["question"],
            question_number=interrupt_payload["question_number"],
            total_questions=interrupt_payload["total_questions"],
        )
 
    
    upsert_record(payload.interview_id, {
        "status": "completed",
        "report": state_values.get("report", {}),
    })
 
    return AnswerResponse(
        score=state_values["current_score"],
        feedback=state_values["current_feedback"],
        next_action="finished",
        next_question=None,
        question_number=None,
        total_questions=TOTAL_QUESTIONS,
    )
 
 

@app.get("/interview/report/{interview_id}", response_model=ReportResponse)
def get_report(interview_id: str):
    config = _config_for(interview_id)
    state = graph.get_state(config)
 
    if not state.values:
        raise HTTPException(status_code=404, detail="Interview not found.")
 
    if state.values.get("status") != "completed":
        raise HTTPException(status_code=400, detail="Interview not finished yet.")
 
    report = state.values.get("report", {})
 
    return ReportResponse(
        role=state.values["role"],
        overall_score=float(report.get("overall_score", 0)),
        category_scores=report.get("category_scores", {}),
        strengths=report.get("strengths", []),
        weaknesses=report.get("weaknesses", []),
        recommendations=report.get("recommendations", []),
        overall_feedback=report.get("overall_feedback", ""),
    )
 
#endpoint

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend:app", host="0.0.0.0", port=8000, reload=True)