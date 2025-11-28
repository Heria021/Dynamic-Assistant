# 📍 Exact Code Locations: Where Embeddings Happen

## 🎯 Quick Answer

**Embeddings happen in 2 places:**

1. **File Ingestion** → `app/utils/vector_utils.py:78` (Line 78)
2. **Query Retrieval** → `app/helpers/openai_helper.py:110` (Line 110)

---

## 📂 Location 1: File Ingestion Embeddings

**File:** `app/utils/vector_utils.py`  
**Function:** `ingest_file_to_vector_db()`  
**Line:** 78

```python
# Line 77-79: CREATE EMBEDDING MODEL
print(f'[RAG-DEBUG] Initializing embeddings...')
embeddings = OpenAIEmbeddings()  # ← EMBEDDING MODEL CREATED HERE
print(f'[RAG-DEBUG] Embeddings initialized')

# Line 87-92: EMBED CHUNKS AND STORE IN MILVUS
Milvus.from_documents(
    docs,                    # Text chunks: ["Chunk 1 text...", "Chunk 2 text..."]
    embeddings,              # ← EMBEDDING MODEL USED HERE
    collection_name=collection_name,
    connection_args={"host": "127.0.0.1", "port": "19530"}
)
```

**What this does:**
- Takes each text chunk
- Converts to embedding vector via `OpenAIEmbeddings()`
- Stores vector + text in Milvus

**Example:**
```python
Input chunk: "Power Output: 3200 Watts (Hyper-Crunch Mode)"
↓ OpenAIEmbeddings().embed_query()
Output vector: [0.23, -0.45, 0.67, 0.12, ...] (1536 dimensions)
↓ Stored in Milvus
Milvus has: {vector: [0.23, ...], text: "Power Output: 3200 Watts..."}
```

---

## 📂 Location 2: Query Embeddings (RAG Retrieval)

**File:** `app/helpers/openai_helper.py`  
**Function:** `retrieve_context()`  
**Line:** 110

```python
# Line 109-111: CREATE EMBEDDING MODEL (SAME AS INGESTION)
print(f"[RAG-DEBUG] Initializing OpenAI embeddings...")
embeddings = OpenAIEmbeddings(openai_api_key=self.client.api_key)  # ← EMBEDDING MODEL
print(f"[RAG-DEBUG] Embeddings initialized")

# Line 115-119: CONNECT TO MILVUS WITH EMBEDDING FUNCTION
vector_store = Milvus(
    embedding_function=embeddings,  # ← EMBEDDING MODEL PASSED HERE
    collection_name=collection_name,
    connection_args={"host": "127.0.0.1", "port": "19530"}
)

# Line 124: SEARCH - THIS EMBEDS THE QUERY
docs = vector_store.similarity_search(sanitized_query, k=top_k)
# ↑ Internally calls: embeddings.embed_query(sanitized_query)
```

**What this does:**
- Takes user's question
- Converts to embedding vector via `OpenAIEmbeddings()`
- Searches Milvus for similar vectors
- Returns matching text chunks

**Example:**
```python
Input query: "What is power output in Hyper-Crunch Mode?"
↓ OpenAIEmbeddings().embed_query()
Query vector: [0.25, -0.42, 0.65, 0.15, ...] (1536 dimensions)
↓ Similarity search in Milvus
Finds similar vector: [0.23, -0.45, 0.67, ...] (from chunk)
↓ Returns
Text chunk: "Power Output: 3200 Watts (Hyper-Crunch Mode)"
```

---

## 🔄 Complete Flow with Code References

```
┌─────────────────────────────────────────────────────────────┐
│ STEP 1: FILE UPLOAD                                         │
│ File: app/controllers/assistant.py:139                       │
└─────────────────────────────────────────────────────────────┘
                    ↓
    ingest_file_to_vector_db(tmp_file_path, assistant_id, extension)
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 2: FILE PROCESSING                                     │
│ File: app/utils/vector_utils.py:55-95                        │
└─────────────────────────────────────────────────────────────┘
                    ↓
    Line 67: documents = loader.load()
    Line 72: docs = text_splitter.split_documents(documents)
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 3: EMBEDDING #1 - CHUNKS → VECTORS                     │
│ File: app/utils/vector_utils.py:78                           │
│ Function: ingest_file_to_vector_db()                        │
└─────────────────────────────────────────────────────────────┘
                    ↓
    embeddings = OpenAIEmbeddings()  # ← EMBEDDING MODEL
                    ↓
    Milvus.from_documents(docs, embeddings, ...)  # ← EMBEDS & STORES
                    ↓
    Stored in Milvus: {vector, text} pairs


┌─────────────────────────────────────────────────────────────┐
│ STEP 4: USER ASKS QUESTION                                  │
│ File: app/controllers/chats.py:178                          │
└─────────────────────────────────────────────────────────────┘
                    ↓
    response = await openai_helper.create_message_and_run(
        collection_name=collection_name,  # ← Enables RAG
        ...
    )
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 5: RAG RETRIEVAL                                       │
│ File: app/helpers/openai_helper.py:262                      │
└─────────────────────────────────────────────────────────────┘
                    ↓
    retrieved_context = await self.retrieve_context(
        query=message,
        collection_name=collection_name,
        top_k=3
    )
                    ↓
┌─────────────────────────────────────────────────────────────┐
│ STEP 6: EMBEDDING #2 - QUERY → VECTOR                      │
│ File: app/helpers/openai_helper.py:110                      │
│ Function: retrieve_context()                                │
└─────────────────────────────────────────────────────────────┘
                    ↓
    embeddings = OpenAIEmbeddings(...)  # ← EMBEDDING MODEL
                    ↓
    vector_store = Milvus(embedding_function=embeddings, ...)
                    ↓
    docs = vector_store.similarity_search(query, k=3)
    # ↑ Internally: query → embedding → similarity search
                    ↓
    Returns: Relevant text chunks


┌─────────────────────────────────────────────────────────────┐
│ STEP 7: CONTEXT INJECTION                                   │
│ File: app/helpers/openai_helper.py:270-282                  │
└─────────────────────────────────────────────────────────────┘
                    ↓
    augmented_message = f"""[CONTEXT FROM KNOWLEDGE BASE]
    {retrieved_context}
    
    [USER QUESTION]
    {message}"""
                    ↓
    Send to OpenAI GPT-4
                    ↓
    Response with context!
```

---

## 🎓 Key Concepts

### What is an Embedding?
- **Text** → **Vector of numbers** (e.g., 1536 dimensions)
- Similar text → Similar vectors
- Enables semantic search (meaning-based, not keyword-based)

### Why Same Model?
- **Ingestion:** `OpenAIEmbeddings()` 
- **Retrieval:** `OpenAIEmbeddings(openai_api_key=...)`
- Must use same model so vectors are in same "space"

### What Does Milvus Do?
- Stores: `{vector: [0.23, ...], text: "original chunk"}`
- Searches: Given query vector, finds most similar stored vectors
- Returns: Original text chunks (not vectors)

---

## 🔍 How to Verify Embeddings Are Working

1. **Check ingestion logs:**
   ```
   [RAG-DEBUG] Embeddings initialized
   [RAG-DEBUG] ✓ Successfully ingested into collection
   ```

2. **Check retrieval logs:**
   ```
   [RAG-DEBUG] Embeddings initialized
   [RAG-DEBUG] ✓ Retrieved 3 document(s)
   ```

3. **If Milvus not running:**
   ```
   [RAG-DEBUG] ✗ ERROR: Fail connecting to server on 127.0.0.1:19530
   ```
   → Start Milvus server!

