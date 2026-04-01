# Advanced Retrieval Techniques Beyond QMD

Research into state-of-the-art retrieval methods (2025-2026) that go beyond QMD's
BM25 + vector + LLM reranking approach. These are candidates for inclusion in py-qmd.

## 1. Contextual Retrieval (Anthropic)

**How it works:** Before embedding each chunk, prepend a short LLM-generated context
sentence explaining where the chunk fits in the overall document. This gives the
embedding model more semantic grounding.

**Example:**
```
Original chunk: "Use the `--no-cache` flag to disable caching."
With context:   "This section is about CLI flags for the build tool. Use the `--no-cache` flag to disable caching."
```

**Impact:** Anthropic reported ~49% reduction in retrieval failures when combined
with BM25 hybrid search.

**Complexity:** Low-moderate. One LLM call per chunk at index time (cacheable with
prompt caching). Can batch process.

**Python libraries:** No dedicated library; trivially implemented with any LLM API.

**Recommendation:** **MUST HAVE.** Best bang-for-buck improvement. Easy to add.
Should be a core feature of py-qmd.

## 2. ColBERT / Late Interaction Models

**How it works:** Instead of compressing a document into a single vector, ColBERT
keeps per-token embeddings and scores via MaxSim (max similarity between query
and document tokens). ColPali extends this to visual documents (PDFs as images).

**Advantage:** Much better retrieval quality than single-vector dense search,
especially for long or nuanced queries. Retains fine-grained token-level matching.

**Complexity:** Moderate. Index size is larger (one vector per token). Requires
more storage and slightly slower retrieval.

**Python libraries:**
- `ragatouille` — wraps ColBERTv2, easiest to use
- `colbert-ai` — official implementation
- `pylate` — newer, lighter alternative

**Recommendation:** **STRONG CANDIDATE for Tier 2.** Replace or augment the dense
vector stage with ColBERT for significantly better retrieval quality.

## 3. RAPTOR (Recursive Abstractive Processing)

**How it works:** Clusters document chunks, generates LLM summaries of each cluster,
then recursively clusters and summarizes again, building a tree. Retrieval traverses
the tree from abstract to specific.

**Advantage:** Excellent for hierarchical/structured documents like markdown with
H1/H2/H3 headings. Captures both high-level themes and granular details.

**Complexity:** High. Requires LLM calls at index time for summarization. Recursive
clustering adds significant build-time cost.

**Python libraries:**
- `raptor-rag` — reference implementation
- LlamaIndex has a `RAPTOR` pack

**Recommendation:** **Tier 3.** Good fit for static content (like course materials
that don't change), but indexing cost is prohibitive for frequently updated content.
Consider for lecture transcripts and project docs specifically.

## 4. GraphRAG (Microsoft)

**How it works:** Extracts entities and relationships via LLM to build a knowledge
graph. Uses community detection (Leiden algorithm) to create hierarchical summaries.
Queries traverse the graph to find related information.

**Advantage:** Excels at multi-hop questions ("What error happens when you combine
indicator X with strategy Y?") and discovering connections between related Q&A
threads. Produces better global summaries.

**Complexity:** High. Expensive LLM-based graph construction. Microsoft's reference
implementation exists but is heavy.

**Python libraries:**
- `graphrag` — Microsoft's official package
- `nano-graphrag` — lightweight alternative (recommended for prototyping)
- LlamaIndex `KnowledgeGraphIndex`

**Recommendation:** **Tier 3 with high value for forum Q&A.** The cross-document
relationship discovery is exactly what makes forum Q&A hard — students ask the same
question in different ways, and answers reference each other. Use `nano-graphrag` to
prototype before committing to the full Microsoft stack.

## 5. Late Chunking

**How it works:** Run the full document through a long-context embedding model first
(getting contextualized token embeddings), then chunk the embedding sequence. Each
chunk's vectors retain full-document context without extra LLM calls.

**Advantage:** Chunks "know" their surrounding context naturally. No additional LLM
calls at index time (unlike contextual retrieval).

**Complexity:** Low, but requires a long-context embedding model.

**Python libraries:**
- Jina AI's embedding API supports this natively
- Can be done manually with any long-context model (e.g., `jina-embeddings-v2`)

**Recommendation:** **Good alternative to contextual retrieval** if you want to avoid
LLM calls at index time. Could offer both as options.

## 6. HyDE (Hypothetical Document Embeddings)

**How it works:** Given a query, generate a hypothetical answer with an LLM, then
embed that answer and use it for retrieval. The hypothetical answer is closer in
embedding space to real answers than the raw question is.

**Example:**
```
Query:     "Why does my indicator return NaN?"
HyDE doc:  "The indicator returns NaN because the lookback period exceeds the
            available data. Ensure your dataframe has enough rows before the
            start date to cover the indicator's window size."
```

**Advantage:** Bridges the query-document vocabulary gap. Works especially well for
technical/domain-specific content where students phrase questions differently than
the answers are written.

**Complexity:** Low. One LLM call per query at search time.

**Python libraries:** Built into LangChain (`HypotheticalDocumentEmbedder`), LlamaIndex.
Easy to implement from scratch.

**Recommendation:** **Tier 2.** Easy win for query-time improvement. Adds latency
(one LLM call per query) but pair with caching for repeated/similar queries.

## 7. Parent-Child Retrieval

**How it works:** Index small, precise chunks for accurate retrieval, but when a
match is found, return the larger parent context (e.g., the full section or document).

**Example:**
```
Indexed chunk:  "Use `get_data()` with `symbol='SPY'`"  (matches query)
Returned:       The entire "Data Access" section containing that chunk
```

**Advantage:** Gets the precision of small chunks with the context of large ones.

**Complexity:** Low. Store parent references as metadata on each chunk.

**Python libraries:** LlamaIndex and LangChain both support this natively.
Trivial to implement from scratch with metadata.

**Recommendation:** **MUST HAVE.** Simple, effective, and essential for providing
enough context in retrieved results.

## Priority Summary

| Priority | Technique | Tier | Effort | Impact |
|----------|-----------|------|--------|--------|
| 1 | Contextual retrieval | 1 | Low | Very high (~49% fewer failures) |
| 2 | Parent-child retrieval | 1 | Low | High (better context) |
| 3 | HyDE | 2 | Low | Medium-high (better query matching) |
| 4 | ColBERT | 2 | Moderate | High (better retrieval quality) |
| 5 | GraphRAG | 3 | High | High for forum Q&A specifically |
| 6 | RAPTOR | 3 | High | Medium (good for static hierarchical docs) |
| 7 | Late chunking | 2 | Low | Medium (alternative to contextual retrieval) |

## Sources

- [Anthropic: Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval)
- [ColBERT paper](https://arxiv.org/abs/2004.12832)
- [ragatouille GitHub](https://github.com/bclavie/RAGatouille)
- [RAPTOR paper](https://arxiv.org/abs/2401.18059)
- [Microsoft GraphRAG](https://github.com/microsoft/graphrag)
- [nano-graphrag](https://github.com/gusye1234/nano-graphrag)
- [HyDE paper](https://arxiv.org/abs/2212.10496)
- [Vector Database Comparison 2026 (4xxi)](https://4xxi.com/articles/vector-database-comparison/)
- [Hybrid Search: BM25 + Semantic (LanceDB)](https://medium.com/etoai/hybrid-search-combining-bm25-and-semantic-search-for-better-results-with-lan-1358038fe7e6)
- [Optimizing RAG with Hybrid Search (Superlinked)](https://superlinked.com/vectorhub/articles/optimizing-rag-with-hybrid-search-reranking)
- [Chunking Strategies for RAG (Weaviate)](https://weaviate.io/blog/chunking-strategies-for-rag)
