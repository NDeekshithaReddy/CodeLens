import ollama
import os
from google import genai
import psycopg2
import tree_sitter_python as tspy
from tree_sitter import Language, Parser
from dotenv import load_dotenv
load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY")) #LLM generation
conn = psycopg2.connect(
    dbname="codelens",
    user="postgres",
    password=os.getenv("DB_PASSWORD"),
    host="localhost",
    port=5432
)
cur = conn.cursor() #db cursor

PY_LANG = Language(tspy.language())
parser = Parser(PY_LANG)

code = open("D:/VSCode Projects/FastAPI/fastAPI.py", "rb").read()
tree = parser.parse(code)

SKIP_DIRS = {'.git', '__pycache__','venv','node_modules'}

def embed(text):
    response = ollama.embed(input=text, model="mxbai-embed-large")
    return response["embeddings"][0]

def ask(text, context):
    prompt = f"""You are a code assistant. Answer only from the code context below.
    Context:
    {context}

    Question:
    {text}"""
    r = client.models.generate_content(model = 'gemini-2.5-flash', contents = prompt)
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

def ingest_folder(folder_path, repo_url = 'local'):
    count = 0
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for file in files:
            if not file.endswith(".py"):
                continue
            filepath = os.path.join(root, file)
            file_code = open(filepath, "rb").read()
            tree = parser.parse(file_code)
            fns = find_functions(tree.root_node, file_code)
            for fn in fns:
                vec = embed(fn['code'])
                cur.execute("INSERT INTO code_chunks (repo_url, file_path, function_name, code, embedding) VALUES (%s, %s, %s, %s, %s)", 
                            (repo_url, filepath, fn["name"], fn["code"], str(vec)))
                count += 1
        conn.commit()
        print(f"Indexed {count} functions")

def retrieve(question, top_k=3):
    vec = embed(question)
    cur.execute(
        "SELECT function_name, file_path, code FROM code_chunks ORDER BY embedding <-> %s LIMIT %s",
        (str(vec), top_k)
    )
    rows = cur.fetchall()
    return [{"name": r[0], "file": r[1], "code": r[2]} for r in rows]
    
if __name__ == "__main__":
    cur.execute("TRUNCATE TABLE code_chunks RESTART IDENTITY")
    conn.commit()
    ingest_folder("D:/VSCode Projects/FastAPI") 
    ques = input("Ask a question: ")
    chunks = retrieve(ques)
    cont = "\n\n".join(c["code"] for c in chunks)
    print(ask(ques, cont))
