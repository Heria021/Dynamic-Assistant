# RAG Architecture Explanation

## 🤔 Why Do We Need Milvus?

### The Problem Without RAG
When a user asks: **"What is the power output in Hyper-Crunch Mode?"**

Without RAG:
- Assistant only knows what's in its training data (up to training cutoff date)
- Cannot access your uploaded files (nebula_x9_manual.md)
- Gives generic or outdated answers

### The Solution: RAG (Retrieval-Augmented Generation)

**RAG = Retrieval + Augmentation + Generation**

1. **Retrieval**: Find relevant chunks from your uploaded files
2. **Augmentation**: Add those chunks as context to the user's question
3. **Generation**: LLM generates answer using both context + question

### Why Milvus? (Vector Database)

**Milvus is a Vector Database** - it stores and searches by **semantic similarity**, not exact text matching.

**Traditional Database (MongoDB):**
```
Query: "power output"
Result: Only finds documents with exact text "power output"
❌ Misses: "Power Output: 3200 Watts", "output power", "wattage"
```

**Vector Database (Milvus):**
```
Query: "power output" 
→ Converts to embedding vector [0.23, -0.45, 0.67, ...]
→ Finds similar vectors (semantic similarity)
✅ Finds: "Power Output: 3200 Watts", "output power", "wattage", "energy consumption"
```

**Why not just use OpenAI's file search?**
- OpenAI's file search is built-in but less control
- Milvus gives you:
  - Custom chunking strategies
  - Better control over retrieval
  - Can work with multiple LLM providers
  - Local/self-hosted option

---

## 📍 Where Embeddings Happen in RAG Flow

### **Step 1: File Ingestion (When Assistant is Created)**

**Location:** `app/utils/vector_utils.py` → `ingest_file_to_vector_db()`

```python
# Line 78: Create embeddings model
embeddings = OpenAIEmbeddings()  # Uses OpenAI's text-embedding-ada-002

# Line 87-92: Embed and store in Milvus
Milvus.from_documents(
    docs,                    # Text chunks from your file
    embeddings,              # Embedding model (converts text → vectors)
    collection_name=collection_name,
    connection_args={"host": "127.0.0.1", "port": "19530"}
)
```

**What happens:**
1. File loaded → Split into chunks (1000 chars each)
2. **Each chunk → Embedding vector** (via OpenAIEmbeddings)
3. Vectors stored in Milvus with original text

**Example:**
```
Chunk: "Power Output: 1800 Watts (Standard Mode), 3200 Watts (Hyper-Crunch Mode)"
↓ Embedding
Vector: [0.23, -0.45, 0.67, 0.12, ...] (1536 dimensions)
↓ Stored in Milvus
Milvus Collection: "s_asst_ztj4Felvtdh8MoDdmG83j1mm"
```

---

### **Step 2: Query Embedding (When User Asks Question)**

**Location:** `app/helpers/openai_helper.py` → `retrieve_context()`

```python
# Line 110: Create embeddings model (same as ingestion)
embeddings = OpenAIEmbeddings(openai_api_key=self.client.api_key)

# Line 115-119: Connect to Milvus
vector_store = Milvus(
    embedding_function=embeddings,  # Same embedding model
    collection_name=collection_name,
    connection_args={"host": "127.0.0.1", "port": "19530"}
)

# Line 124: Search - THIS EMBEDS THE QUERY
docs = vector_store.similarity_search(sanitized_query, k=top_k)
```

**What happens:**
1. User question: "What is the power output in Hyper-Crunch Mode?"
2. **Question → Embedding vector** (via OpenAIEmbeddings)
3. Milvus finds top 3 most similar chunks (cosine similarity)
4. Returns original text chunks

**Example:**
```
Query: "What is the power output in Hyper-Crunch Mode?"
↓ Embedding
Query Vector: [0.25, -0.42, 0.65, 0.15, ...]
↓ Similarity Search in Milvus
Finds: Chunk about "Power Output: 3200 Watts (Hyper-Crunch Mode)"
↓ Returns
Text: "Power Output: 1800 Watts (Standard Mode), 3200 Watts (Hyper-Crunch Mode)"
```

---

### **Step 3: Context Injection (Before LLM Call)**

**Location:** `app/helpers/openai_helper.py` → `create_message_and_run()`

```python
# Line 262-265: Retrieve context (uses embeddings from Step 2)
retrieved_context = await self.retrieve_context(
    query=message,
    collection_name=collection_name,
    top_k=3
)

# Line 270-282: Inject context into message
augmented_message = f"""[CONTEXT FROM KNOWLEDGE BASE]
{retrieved_context}

[USER QUESTION]
{message}

Please answer based on the context provided above. Keep response to 2-3 lines maximum."""
```

**What happens:**
1. Retrieved chunks added as context
2. User question + context sent to OpenAI
3. LLM generates answer using both

---

## 🔄 Complete RAG Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│ 1. FILE UPLOAD (Assistant Creation)                         │
└─────────────────────────────────────────────────────────────┘
                    ↓
    File: nebula_x9_manual.md
                    ↓
    Split into chunks (1000 chars each)
                    ↓
    ┌───────────────────────────────────────┐
    │ EMBEDDING #1: Chunk → Vector          │
    │ OpenAIEmbeddings()                     │
    │ [0.23, -0.45, 0.67, ...]              │
    └───────────────────────────────────────┘
                    ↓
    Store in Milvus (Vector DB)
    Collection: "s_asst_ztj4Felvtdh8MoDdmG83j1mm"


┌─────────────────────────────────────────────────────────────┐
│ 2. USER QUESTION (Chat Creation)                            │
└─────────────────────────────────────────────────────────────┘
                    ↓
    Question: "What is power output in Hyper-Crunch Mode?"
                    ↓
    ┌───────────────────────────────────────┐
    │ EMBEDDING #2: Query → Vector          │
    │ OpenAIEmbeddings()                     │
    │ [0.25, -0.42, 0.65, ...]              │
    └───────────────────────────────────────┘
                    ↓
    Similarity Search in Milvus
    (Finds top 3 similar chunks)
                    ↓
    Retrieved: "Power Output: 3200 Watts (Hyper-Crunch Mode)"


┌─────────────────────────────────────────────────────────────┐
│ 3. CONTEXT INJECTION                                        │
└─────────────────────────────────────────────────────────────┘
                    ↓
    Augmented Message:
    """
    [CONTEXT FROM KNOWLEDGE BASE]
    Power Output: 3200 Watts (Hyper-Crunch Mode)
    
    [USER QUESTION]
    What is power output in Hyper-Crunch Mode?
    """
                    ↓
    Send to OpenAI GPT-4
                    ↓
    Response: "The power output in Hyper-Crunch Mode is 3200 Watts."
```

---

## 🎯 Key Points

1. **Embeddings happen TWICE:**
   - **Once** when ingesting files (chunks → vectors)
   - **Once** when querying (question → vector)

2. **Same embedding model** must be used for both:
   - Ingestion: `OpenAIEmbeddings()`
   - Retrieval: `OpenAIEmbeddings(openai_api_key=...)`
   - This ensures vectors are in the same "space"

3. **Milvus stores:**
   - Vector embeddings (for fast similarity search)
   - Original text chunks (to return to user)

4. **Why vector similarity works:**
   - "power output" and "Power Output: 3200 Watts" have similar vectors
   - Cosine similarity finds semantically similar text
   - Much better than keyword matching!

---

## 🔧 Alternative: Use OpenAI's Built-in File Search

If you don't want to use Milvus, you can use OpenAI's native file search:

**Location:** `app/utils/open_ai_utils.py` → `create_assistant_with_file()`

```python
# Uses OpenAI's vector store (no Milvus needed)
vector_store = client.beta.vector_stores.create(name=payload.astName)
assistant = client.beta.assistants.create(
    ...,
    tool_resources={
        "file_search": {
            "vector_store_ids": [vector_store_id]
        }
    }
)
```

**Trade-offs:**
- ✅ No Milvus setup needed
- ✅ Managed by OpenAI
- ❌ Less control over chunking
- ❌ Requires OpenAI API for everything
- ❌ Can't use with other LLMs

---

## 📝 Summary

**Milvus = Vector Database for semantic search**
- Stores embeddings of your file chunks
- Finds relevant chunks when user asks questions
- Enables RAG (Retrieval-Augmented Generation)

**Embeddings happen:**
1. **File ingestion** → Chunks embedded and stored
2. **Query time** → Question embedded and searched

**Without Milvus:**
- RAG won't work
- Can't retrieve relevant context from files
- Assistant can't answer questions about uploaded documents

