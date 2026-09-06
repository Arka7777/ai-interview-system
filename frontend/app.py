"""
AI Interview Preparation & Mock Interview System — Streamlit Frontend (V1)

Run backend first:  uvicorn backend:app --reload
Run this with:       streamlit run app.py
"""

import requests
import streamlit as st

API_URL = "https://ai-interview-system-backend-0hoo.onrender.com"

st.set_page_config(page_title="AI Mock Interview", page_icon="🧑‍💼", layout="centered")


# ---------------------------------------------------------------------------
# SESSION STATE INIT
# ---------------------------------------------------------------------------

def init_state():
    defaults = {
        "interview_id": None,
        "current_question": None,
        "question_number": None,
        "total_questions": None,
        "history": [],          # list of (question, answer, score, feedback)
        "stage": "setup",       # "setup" | "interview" | "report"
        "last_feedback": None,
        "report": None,
        "jd_analysis": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


def reset_all():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_state()


# ---------------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------------

st.title("🧑‍💼 AI Interview Preparation & Mock Interview System")
st.caption("Practice technical interviews with an AI interviewer that adapts to your answers.")

st.divider()


# ---------------------------------------------------------------------------
# STAGE 1: SETUP — collect role / experience / JD, start interview
# ---------------------------------------------------------------------------

if st.session_state.stage == "setup":
    st.subheader("Start a new mock interview")

    role = st.text_input("Job Role", placeholder="e.g. Python Developer")
    experience = st.selectbox("Experience Level", ["Fresher", "Intermediate", "Experienced"])
    job_description = st.text_area(
        "Job Description (optional)",
        placeholder="Paste the job description here for more relevant questions...",
        height=150,
    )

    if st.button("Start Interview", type="primary", disabled=not role.strip()):
        with st.spinner("Generating your interview questions..."):
            try:
                response = requests.post(
                    f"{API_URL}/interview/start",
                    json={
                        "role": role,
                        "experience": experience,
                        "job_description": job_description,
                    },
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()

                st.session_state.interview_id = data["interview_id"]
                st.session_state.current_question = data["question"]
                st.session_state.question_number = data["question_number"]
                st.session_state.total_questions = data["total_questions"]
                st.session_state.jd_analysis = {
                    "skills": data.get("skills", []),
                    "tools": data.get("tools", []),
                    "experience_requirements": data.get("experience_requirements", ""),
                }
                st.session_state.stage = "interview"
                st.rerun()

            except requests.exceptions.RequestException as e:
                st.error(f"Could not reach backend. Is it running? ({e})")


# ---------------------------------------------------------------------------
# STAGE 2: INTERVIEW — ask question, take answer, show feedback, loop
# ---------------------------------------------------------------------------

elif st.session_state.stage == "interview":
    if st.session_state.jd_analysis:
        analysis = st.session_state.jd_analysis
        with st.expander("📋 Job requirements identified from your input", expanded=False):
            if analysis["skills"]:
                st.markdown("**Required Skills:** " + ", ".join(f"`{s}`" for s in analysis["skills"]))
            if analysis["tools"]:
                st.markdown("**Required Tools/Frameworks:** " + ", ".join(f"`{t}`" for t in analysis["tools"]))
            if analysis["experience_requirements"]:
                st.markdown(f"**Experience Expectations:** {analysis['experience_requirements']}")

    st.subheader(
        f"Question {st.session_state.question_number} / {st.session_state.total_questions}"
    )
    st.info(st.session_state.current_question)

    # show feedback from the previous answer, if any
    if st.session_state.last_feedback:
        score = st.session_state.last_feedback["score"]
        feedback = st.session_state.last_feedback["feedback"]
        color = "green" if score >= 7 else "orange" if score >= 4 else "red"
        st.markdown(f"**Previous score:** :{color}[{score}/10]")
        st.markdown(f"*{feedback}*")
        st.divider()

    answer = st.text_area("Your Answer", key=f"answer_{st.session_state.question_number}", height=150)

    if st.button("Submit Answer", type="primary", disabled=not answer.strip()):
        with st.spinner("Evaluating your answer..."):
            try:
                response = requests.post(
                    f"{API_URL}/interview/answer",
                    json={
                        "interview_id": st.session_state.interview_id,
                        "answer": answer,
                    },
                    timeout=60,
                )
                response.raise_for_status()
                data = response.json()

                st.session_state.history.append({
                    "question": st.session_state.current_question,
                    "answer": answer,
                    "score": data["score"],
                    "feedback": data["feedback"],
                })
                st.session_state.last_feedback = {
                    "score": data["score"],
                    "feedback": data["feedback"],
                }

                if data["next_action"] == "finished":
                    st.session_state.stage = "report"
                else:
                    st.session_state.current_question = data["next_question"]
                    st.session_state.question_number = data["question_number"]

                st.rerun()

            except requests.exceptions.RequestException as e:
                st.error(f"Could not reach backend. ({e})")

    with st.expander("Interview log so far"):
        for i, item in enumerate(st.session_state.history, start=1):
            st.markdown(f"**Q{i}: {item['question']}**")
            st.markdown(f"Your answer: {item['answer']}")
            st.markdown(f"Score: {item['score']}/10 — {item['feedback']}")
            st.markdown("---")


# ---------------------------------------------------------------------------
# STAGE 3: REPORT — fetch and display final report
# ---------------------------------------------------------------------------

elif st.session_state.stage == "report":
    st.subheader("📊 Interview Report")

    if st.session_state.report is None:
        with st.spinner("Generating your performance report..."):
            try:
                response = requests.get(
                    f"{API_URL}/interview/report/{st.session_state.interview_id}",
                    timeout=60,
                )
                response.raise_for_status()
                st.session_state.report = response.json()
            except requests.exceptions.RequestException as e:
                st.error(f"Could not reach backend. ({e})")

    if st.session_state.report:
        report = st.session_state.report

        st.metric("Overall Score", f"{report['overall_score']} / 10")
        st.markdown(f"**Role:** {report['role']}")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### ✅ Strengths")
            for s in report["strengths"]:
                st.markdown(f"- {s}")
        with col2:
            st.markdown("### ⚠️ Weak Areas")
            for w in report["weaknesses"]:
                st.markdown(f"- {w}")

        st.markdown("### 📚 Recommended Topics")
        for r in report["recommendations"]:
            st.markdown(f"- {r}")

        st.markdown("### 📝 Overall Feedback")
        st.write(report["overall_feedback"])

        st.divider()
        if st.button("Start a New Interview"):
            reset_all()
            st.rerun()