from rag.engine import get_rag_engine
import time

print("Loading engine...")
engine = get_rag_engine()
print("Starting query...")
t0 = time.time()
try:
    ans = engine.query("Hi, can you explain the architecture?")
    print("Response obtained in", time.time() - t0, "seconds")
    print("Answer:", ans[:200], "...")
except Exception as e:
    print("Error:", e)
