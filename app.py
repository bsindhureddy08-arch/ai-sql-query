import streamlit as st
import sqlite3
import pandas as pd
import ollama
import re

# -----------------------------
# PAGE CONFIG
# -----------------------------
st.set_page_config(
    page_title="AI SQL Query Assistant",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI SQL Query Assistant")
st.write("Ask questions about your database in simple English.")

# -----------------------------
# DATABASE
# -----------------------------
DB_NAME = "students.db"


def create_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            department TEXT NOT NULL,
            marks INTEGER NOT NULL
        )
    """)

    cursor.execute("SELECT COUNT(*) FROM students")
    count = cursor.fetchone()[0]

    if count == 0:
        students = [
            (1, "Sindhu", "CSE", 92),
            (2, "Neha", "CSE", 88),
            (3, "Rahul", "ECE", 76),
            (4, "Priya", "CSE", 95),
            (5, "Kiran", "EEE", 81),
            (6, "Ananya", "CSE", 90),
            (7, "Arjun", "ECE", 72),
            (8, "Sneha", "EEE", 85)
        ]

        cursor.executemany("""
            INSERT INTO students
            (id, name, department, marks)
            VALUES (?, ?, ?, ?)
        """, students)

    conn.commit()
    conn.close()


create_database()


# -----------------------------
# GET DATABASE SCHEMA
# -----------------------------
def get_schema():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        AND name NOT LIKE 'sqlite_%'
    """)

    tables = cursor.fetchall()

    schema = ""

    for table in tables:
        table_name = table[0]

        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()

        schema += f"\nTable: {table_name}\n"

        for column in columns:
            column_name = column[1]
            column_type = column[2]

            schema += f"- {column_name} ({column_type})\n"

    conn.close()

    return schema


# -----------------------------
# GENERATE SQL USING OLLAMA
# -----------------------------
def generate_sql(question, schema):

    prompt = f"""
You are an SQL expert.

Convert the user's question into a valid SQLite SQL query.

Database schema:
{schema}

User question:
{question}

Rules:
1. Return ONLY the SQL query.
2. Do not use markdown.
3. Do not explain the query.
4. Only use tables and columns from the schema.
5. Generate SELECT queries only.
"""

    response = ollama.chat(
        model="llama3.2",
        messages=[
            {
                "role": "user",
                "content": prompt
            }
        ]
    )

    sql = response["message"]["content"].strip()

    # Remove markdown code fences if Ollama returns them
    sql = re.sub(r"```sql", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"```", "", sql)

    return sql.strip()


# -----------------------------
# CHECK SQL SAFETY
# -----------------------------
def is_safe_sql(sql):

    sql_upper = sql.strip().upper()

    if not sql_upper.startswith("SELECT"):
        return False

    dangerous_commands = [
        "DROP",
        "DELETE",
        "UPDATE",
        "INSERT",
        "ALTER",
        "CREATE",
        "REPLACE",
        "ATTACH",
        "DETACH"
    ]

    for command in dangerous_commands:
        if re.search(r"\b" + command + r"\b", sql_upper):
            return False

    return True


# -----------------------------
# RUN SQL
# -----------------------------
def execute_sql(sql):

    conn = sqlite3.connect(DB_NAME)

    try:
        dataframe = pd.read_sql_query(sql, conn)
        return dataframe, None

    except Exception as e:
        return None, str(e)

    finally:
        conn.close()


# -----------------------------
# SIDEBAR
# -----------------------------
with st.sidebar:

    st.header("📊 Database")

    st.write("Current database:")
    st.code(DB_NAME)

    st.subheader("Database Schema")

    schema = get_schema()

    st.code(schema)

    st.subheader("💡 Example Questions")

    st.write("• Show all students")
    st.write("• Show students who scored above 85")
    st.write("• Who got the highest marks?")
    st.write("• Show CSE students")
    st.write("• Find the average marks")


# -----------------------------
# USER INPUT
# -----------------------------
question = st.text_input(
    "Ask your question:",
    placeholder="Example: Show students who scored above 85"
)


# -----------------------------
# GENERATE AND EXECUTE
# -----------------------------
if st.button("🚀 Generate SQL", type="primary"):

    if question.strip() == "":
        st.warning("Please enter a question.")

    else:

        with st.spinner("Generating SQL..."):

            try:

                schema = get_schema()

                sql = generate_sql(
                    question,
                    schema
                )

                st.subheader("📝 Generated SQL")

                st.code(
                    sql,
                    language="sql"
                )

                # Safety check
                if not is_safe_sql(sql):

                    st.error(
                        "❌ Unsafe SQL detected. Only SELECT queries are allowed."
                    )

                else:

                    with st.spinner("Executing SQL..."):

                        result, error = execute_sql(sql)

                    if error:

                        st.error(
                            f"❌ SQL Error: {error}"
                        )

                    else:

                        st.subheader("📊 Query Result")

                        st.dataframe(
                            result,
                            use_container_width=True
                        )

                        st.success(
                            f"✅ Query executed successfully. "
                            f"{len(result)} rows returned."
                        )

            except Exception as e:

                st.error(
                    f"❌ Error: {e}"
                )