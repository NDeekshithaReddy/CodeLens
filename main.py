import ollama
import os
from google import genai
import psycopg2
import tree_sitter_python as tspy
from tree_sitter import Language, Parser
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from dotenv import load_dotenv
import git, tempfile, shutil

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
conn = psycopg2.connect(
    dbname="codelens",
    user="postgres",
    password=os.getenv("DB_PASSWORD"),
    host="localhost",
    port=5432
)
cur = conn.cursor()

PY_LANG = Language(tspy.language())
parser = Parser(PY_LANG)

SKIP_DIRS = {'.git', '__pycache__', 'venv', 'node_modules'}


def embed(text):
    response = ollama.embed(input=text, model="mxbai-embed-large")
    if "embeddings" in response:
        return response["embeddings"][0]
    return response["embedding"]


def ask(text, chunks):
    if not chunks:
        return "No relevant code found to answer your question."

    context = ""
    for i, c in enumerate(chunks):
        context += f"--- Chunk {i+1} ({c['file']}) ---\n{c['code']}\n\n"

    prompt = f"""You are a code assistant. Answer only from the code context below.
    Context:
    {context}

    Question: {text}
    Answer concisely with file path and function name and definition."""

    r = client.models.generate_content(model='gemini-2.5-flash', contents=prompt)
    return r.text


def find_functions(node, file_code, results=None):
    if results is None:
        results = []
    if node.type == "function_definition":
        name_node = node.child_by_field_name("name")
        results.append({
            "name": name_node.text.decode(),
            "code": file_code[node.start_byte:node.end_byte].decode(),
            "start": node.start_point[0],
            "end": node.end_point[0]
        })
    for child in node.children:
        find_functions(child, file_code, results)
    return results


def ingest_folder(folder_path, repo_url='local'):
    count = 0

    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]

        for file in files:
            if not file.endswith(".py"):
                continue

            filepath = os.path.join(root, file)
            print(f"Processing file: {filepath}")

            file_code = open(filepath, "rb").read()
            tree = parser.parse(file_code)
            fns = find_functions(tree.root_node, file_code)

            print(f"Found {len(fns)} functions")

            for fn in fns:
                print(f"Indexing function: {fn['name']}")
                try:
                    vec = embed(text = f"""
                    Function Name: {fn['name']}

                    {fn['code']}
                    """)
                    cur.execute(
                        """
                        INSERT INTO code_chunks
                        (repo_url, file_path, function_name, code, embedding)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            repo_url,
                            filepath,
                            fn["name"],
                            fn["code"],
                            str(vec)
                        )
                    )
                    count += 1
                except Exception as e:
                    conn.rollback()
                    print(f"Failed to index {fn['name']}: {e}")

    conn.commit()
    print(f"Indexed {count} functions")


def retrieve(question, top_k=3):
    vec = embed(question)
    cur.execute(
        "SELECT function_name, file_path, code FROM code_chunks ORDER BY embedding <-> %s LIMIT %s",
        (str(vec), top_k)
    )
    rows = cur.fetchall()
    print("\nRetrieved:")
    for r in rows:
        print("FUNCTION:", r[0])
        print("FILE:", r[1])
        print("-" * 50)
    return [{"name": r[0], "file": r[1], "code": r[2]} for r in rows]

status_map = {}
def ingest_repo(url: str):
    status_map[url] = "cloning"
    tmp = tempfile.mkdtemp()
    try:
        git.Repo.clone_from(url, tmp)
        status_map[url] = "indexing"
        print(f"Cloned to: {tmp}")
        print(f"Top level contents: {os.listdir(tmp)}")
        ingest_folder(tmp, repo_url=url)
        status_map[url] = "ready"
    except Exception as e:
        status_map[url] = f"Error : {e}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    cur.execute("TRUNCATE TABLE code_chunks RESTART IDENTITY")
    conn.commit()
    print("Start ingestion")
    ingest_repo("https://github.com/tehmaze/ipcalc.git")
    ques = input("Ask a question: ")
    chunks = retrieve(ques)
    print(ask(ques, chunks))


# Endpoints
app = FastAPI()


class IngestRequest(BaseModel):
    url: str


class QueryRequest(BaseModel):
    question: str


@app.post("/ingest")
async def ingest(req: IngestRequest, bg: BackgroundTasks):
    cur.execute("TRUNCATE TABLE code_chunks RESTART IDENTITY")
    conn.commit()
    bg.add_task(ingest_repo, req.url)
    return {"status": "ingestion started", "repo": req.url}


@app.post("/query")
async def query(req: QueryRequest):
    chunks = retrieve(req.question)
    if not chunks:
        return {"answer": "No relevant code found.", "sources": []}
    answer = ask(req.question, chunks)
    return {
        "answer": answer,
        "sources": [{"function": c["name"], "file": c["file"]} for c in chunks]
    }

@app.get("/status")
async def status(repo : str):
    return {"status" : status_map.get(repo, "not started")}