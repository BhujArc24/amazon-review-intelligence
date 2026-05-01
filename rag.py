import json
from data_loader import model, index, df_emb, client
from config import OPENAI_MODEL


def rewrite_query(question):
    """LLM pre-pass: turn user question into structured search params."""
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role":"system","content":"You turn user questions about product reviews into structured search parameters. Return ONLY valid JSON."},
                {"role":"user","content":f"""User question: "{question}"

Extract:
- search_queries: 1-3 short phrases optimized for semantic search over review text
- sentiment: "pos", "neg", or "any"
- product_hint: a keyword to filter product titles, or null

Return JSON only:
{{"search_queries":["..."],"sentiment":"...","product_hint":"..."}}"""}
            ], temperature=0)
        txt = resp.choices[0].message.content.strip()
        if txt.startswith('```'):
            txt = txt.split('```')[1].replace('json','',1).strip()
        return json.loads(txt)
    except Exception:
        return {"search_queries":[question],"sentiment":"any","product_hint":None}


def retrieve(queries, k=40):
    """Multi-query semantic retrieval, merged by max score."""
    import time
    
    all_idx = {}
    embed_total = 0
    search_total = 0
    
    for q in queries[:3]:
        embed_start = time.time()
        qv = model.encode([q], normalize_embeddings=True).astype('float32')
        embed_total += time.time() - embed_start
        
        search_start = time.time()
        D, I = index.search(qv, k)
        search_total += time.time() - search_start
        
        for idx, score in zip(I[0], D[0]):
            if idx not in all_idx or score > all_idx[idx]:
                all_idx[idx] = float(score)
    
    print(f"[METRIC-DETAIL] embed: {embed_total*1000:.0f}ms | faiss: {search_total*1000:.0f}ms")
    
    ranked = sorted(all_idx.items(), key=lambda x: -x[1])
    hits = df_emb.iloc[[i for i,_ in ranked]].copy()
    hits['score'] = [s for _,s in ranked]
    return hits


def run_rag(question, k=10):
    import time
    total_start = time.time()
    
    # Time query rewriting (first GPT call)
    rewrite_start = time.time()
    plan = rewrite_query(question)
    rewrite_latency = time.time() - rewrite_start
    
    queries = plan.get('search_queries') or [question]
    sentiment = plan.get('sentiment','any')
    product_hint = plan.get('product_hint')

    # Time retrieval (embed + FAISS search)
    retrieve_start = time.time()
    hits = retrieve(queries, k=40)
    retrieve_latency = time.time() - retrieve_start

    if sentiment in ('pos','neg'):
        hits = hits[hits['sentiment']==sentiment]
    if product_hint:
        mask = hits['product_title'].str.contains(product_hint, case=False, na=False)
        if mask.sum() >= 3:
            hits = hits[mask]
    hits = hits.head(k)

    if len(hits) == 0:
        return "No relevant reviews found for that question.", hits

    context = "\n\n".join([
        f"[Review {i+1}] Product: {r['product_title']} | Rating: {r['rating']}/5 | Sentiment: {r['sentiment']}\n{r['text'][:500]}"
        for i, (_, r) in enumerate(hits.iterrows())])

    # Time generation (final GPT call)
    gen_start = time.time()
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role":"system","content":"""You are a product review analyst. Answer using ONLY the reviews provided.
Format:
- Start with a bold TL;DR sentence.
- Then 3-5 themed insights as bullet points, each with a bold label followed by the insight.
- Cite reviews inline using the format (R3) or (R3, R5) — NEVER use brackets like [Review 3] because those break rendering.
- Be specific: name products, mention concrete features, cite reviewer language when relevant.
- Keep bullets tight — 1-2 sentences each, not paragraphs.
- If reviews don't answer the question, say so plainly.

Example good citation: "Users praise the glare-free screen (R4)."
Example bad citation: "Users praise the glare-free screen [Review 4]."
"""},
            {"role":"user","content":f"Question: {question}\n\nReviews:\n{context}"}
        ], temperature=0.2)
    gen_latency = time.time() - gen_start
    
    total_latency = time.time() - total_start
    
    print(f"[METRIC] rewrite: {rewrite_latency*1000:.0f}ms | retrieve: {retrieve_latency*1000:.0f}ms | gen: {gen_latency*1000:.0f}ms | total: {total_latency*1000:.0f}ms", flush=True)
    
    return resp.choices[0].message.content, hits


def generate_pros_cons(topic, pos_reviews, neg_reviews):
    """Generate top 3 pros and cons from pre-filtered positive and negative reviews."""
    pos_text = "\n".join([f"- {r['text'][:300]}" for _, r in pos_reviews.iterrows()])
    neg_text = "\n".join([f"- {r['text'][:300]}" for _, r in neg_reviews.iterrows()])
    prompt = f"""Analyze reviews for "{topic}". Extract TOP 3 PROS and TOP 3 CONS.

POSITIVE:
{pos_text}

NEGATIVE:
{neg_text}

Return EXACTLY in this format with no extra text:
PROS
1. [point] - [short explanation]
2. [point] - [short explanation]
3. [point] - [short explanation]
CONS
1. [point] - [short explanation]
2. [point] - [short explanation]
3. [point] - [short explanation]"""
    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[{"role":"user","content":prompt}],
        temperature=0.2,
    )
    txt = resp.choices[0].message.content
    pros_lines, cons_lines = [], []
    mode = None
    for line in txt.splitlines():
        l = line.strip()
        if l.upper().startswith('PROS'): mode = 'p'; continue
        if l.upper().startswith('CONS'): mode = 'c'; continue
        if l and l[0].isdigit():
            item = l.split('.',1)[-1].strip()
            if mode == 'p': pros_lines.append(item)
            elif mode == 'c': cons_lines.append(item)
    return pros_lines, cons_lines


def summarize_chart(chart_name, context_text):
    """Phase 3: 'Ask about this chart' — LLM explains a chart's insight."""
    try:
        resp = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role":"system","content":"You are a data analyst. Given a chart description, explain the key insight in 2-3 sentences. Be specific, concrete, actionable. No fluff."},
                {"role":"user","content":f"Chart: {chart_name}\n\nData:\n{context_text}\n\nWhat's the takeaway?"}
            ], temperature=0.3)
        return resp.choices[0].message.content
    except Exception as e:
        return f"Couldn't analyze right now: {str(e)[:80]}"


def compare_products(product_a, product_b):
    """Phase 3: head-to-head AI comparison of two products."""
    a_reviews = df_emb[df_emb['product_title']==product_a].head(15)
    b_reviews = df_emb[df_emb['product_title']==product_b].head(15)
    if len(a_reviews) < 3 or len(b_reviews) < 3:
        return "Not enough reviews to compare."

    a_text = "\n".join([f"- [{r['rating']}/5] {r['text'][:250]}" for _, r in a_reviews.iterrows()])
    b_text = "\n".join([f"- [{r['rating']}/5] {r['text'][:250]}" for _, r in b_reviews.iterrows()])

    resp = client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role":"system","content":"You compare two products based on customer reviews. Be concrete, balanced, and specific. Output in sections: Where A wins, Where B wins, Verdict."},
            {"role":"user","content":f"""Compare these two products.

PRODUCT A: {product_a}
Reviews:
{a_text}

PRODUCT B: {product_b}
Reviews:
{b_text}

Format:
**Where A Wins:** [2 specific points]
**Where B Wins:** [2 specific points]
**Verdict:** [one sentence on who should buy which]"""}
        ], temperature=0.3)
    return resp.choices[0].message.content