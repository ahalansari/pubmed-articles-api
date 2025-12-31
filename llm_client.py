"""
LLM Client for PubMed Articles API
Handles LLM-based search term generation, article selection, and summarization
Supports both LM Studio and vLLM backends with chunked summarization for long articles
"""

import os
import json
import re
from typing import Optional
from openai import OpenAI


class LLMClient:
    """Client for LLM operations using OpenAI-compatible APIs"""
    
    CHARS_PER_TOKEN = 4
    PROMPT_OVERHEAD_TOKENS = 500
    RESPONSE_TOKENS_RESERVE = 1024
    
    def __init__(self, backend: str = "lmstudio"):
        self.backend = backend.lower()
        
        if self.backend == "vllm":
            self.base_url = os.getenv("VLLM_LLM_BASE_URL", "http://localhost:8000/v1")
            self.model = os.getenv("VLLM_LLM_MODEL", "meta-llama/Meta-Llama-3-8B-Instruct")
            self.api_key = os.getenv("VLLM_API_KEY", "EMPTY")
            max_tokens_env = int(os.getenv("VLLM_MAX_TOKENS", "2048"))
            self.max_tokens = None if max_tokens_env <= 0 else max_tokens_env
            self.context_window = int(os.getenv("VLLM_CONTEXT_WINDOW", "8192"))
        else:
            self.base_url = os.getenv("LM_STUDIO_BASE_URL", "http://localhost:1234/v1")
            self.model = os.getenv("LM_STUDIO_MODEL", "default")
            self.api_key = "not-needed"
            max_tokens_env = int(os.getenv("LM_STUDIO_MAX_TOKENS", "2048"))
            self.max_tokens = None if max_tokens_env <= 0 else max_tokens_env
            self.context_window = int(os.getenv("LM_STUDIO_CONTEXT_WINDOW", "8192"))
        
        self.max_content_tokens = self.context_window - self.PROMPT_OVERHEAD_TOKENS - self.RESPONSE_TOKENS_RESERVE
        self.max_content_chars = self.max_content_tokens * self.CHARS_PER_TOKEN
        
        self.client = OpenAI(
            base_url=self.base_url,
            api_key=self.api_key
        )
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough approximation)"""
        return len(text) // self.CHARS_PER_TOKEN
    
    def _chunk_text(self, text: str, max_chars: int) -> list:
        """
        Split text into chunks that fit within context window.
        Tries to split on paragraph/sentence boundaries for coherence.
        """
        if len(text) <= max_chars:
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            end_pos = min(current_pos + max_chars, len(text))
            
            if end_pos < len(text):
                split_pos = end_pos
                
                para_break = text.rfind('\n\n', current_pos, end_pos)
                if para_break > current_pos + (max_chars // 2):
                    split_pos = para_break + 2
                else:
                    sentence_break = text.rfind('. ', current_pos, end_pos)
                    if sentence_break > current_pos + (max_chars // 2):
                        split_pos = sentence_break + 2
                    else:
                        space = text.rfind(' ', current_pos, end_pos)
                        if space > current_pos:
                            split_pos = space + 1
                
                chunks.append(text[current_pos:split_pos].strip())
                current_pos = split_pos
            else:
                chunks.append(text[current_pos:end_pos].strip())
                break
        
        return [c for c in chunks if c]
    
    def _summarize_chunk(self, chunk: str, chunk_num: int, total_chunks: int, title: str) -> str:
        """Summarize a single chunk of an article"""
        prompt = f"""You are a medical expert. Summarize this section of a medical article.

ARTICLE: {title}
SECTION: Part {chunk_num} of {total_chunks}

CONTENT:
{chunk}

Provide a concise summary of the key points in this section. Focus on:
- Main findings or claims
- Important data or statistics
- Clinical recommendations mentioned

Keep it brief (3-5 bullet points)."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a medical expert. Be concise and accurate."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=512
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"[Chunk {chunk_num} summary failed: {str(e)}]"
    
    def _combine_chunk_summaries(self, chunk_summaries: list, title: str, patient_context: Optional[dict] = None) -> str:
        """Combine multiple chunk summaries into a final coherent summary"""
        context_str = ""
        if patient_context:
            age = patient_context.get("age")
            gender = patient_context.get("gender")
            if age or gender:
                context_str = f"\n\nPATIENT CONTEXT: {age or 'Unknown'} year old {gender or 'patient'}"
        
        summaries_text = "\n\n".join([
            f"SECTION {i+1}:\n{summary}"
            for i, summary in enumerate(chunk_summaries)
        ])
        
        prompt = f"""You are a medical expert. Combine these section summaries into a cohesive clinical summary.

ARTICLE: {title}
{context_str}

SECTION SUMMARIES:
{summaries_text}

Create a unified summary with these sections (skip if not applicable):

KEY POINTS:
• Main findings (3-5 bullet points)

CLINICAL RELEVANCE:
• How this applies to clinical practice

TREATMENT/RECOMMENDATIONS:
• Key treatment recommendations or clinical guidelines

LIMITATIONS:
• Study limitations or caveats

Keep it concise but clinically useful."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a medical expert providing clinical summaries."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=self.max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            return f"Error combining summaries: {str(e)}\n\nPartial summaries:\n" + "\n\n".join(chunk_summaries)
    
    def generate_search_terms(self, case_scenario: Optional[str] = None, topic: Optional[str] = None) -> list:
        """
        Generate optimized PubMed search terms from a clinical case or topic
        
        Args:
            case_scenario: Clinical case description
            topic: Research topic
        
        Returns:
            List of optimized search terms
        """
        if case_scenario:
            prompt = f"""You are a medical research assistant. Given the following clinical case scenario, generate 3-5 specific PubMed search terms that would find the most relevant medical literature.

CASE SCENARIO:
{case_scenario}

Generate search terms that:
1. Focus on the key medical conditions and symptoms
2. Use standard medical terminology and MeSH terms where appropriate
3. Are specific enough to find relevant articles
4. Cover different aspects of the case (diagnosis, treatment, etc.)

Return ONLY a JSON array of search terms, nothing else. Example format:
["term 1", "term 2", "term 3"]"""
        else:
            prompt = f"""You are a medical research assistant. Given the following research topic, generate 3-5 optimized PubMed search terms.

TOPIC:
{topic}

Generate search terms that:
1. Use standard medical terminology and MeSH terms
2. Are specific enough to find relevant articles
3. Cover different aspects of the topic

Return ONLY a JSON array of search terms, nothing else. Example format:
["term 1", "term 2", "term 3"]"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a medical research assistant. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            json_match = re.search(r'\[.*?\]', content, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            return json.loads(content)
            
        except Exception:
            if case_scenario:
                words = case_scenario.split()[:10]
                return [" ".join(words)]
            return [topic] if topic else []
    
    def select_relevant_articles(self, articles: list, context: str, limit: int = 5) -> list:
        """
        Use LLM to select the most relevant articles from a list based on context
        
        Args:
            articles: List of article dictionaries with pmid, title, abstract
            context: Context for relevance (case scenario, topic, or keywords)
            limit: Maximum number of articles to select
        
        Returns:
            List of PMIDs of the most relevant articles in order of relevance
        """
        if len(articles) <= limit:
            return [a.get("pmid") for a in articles]
        
        max_abstract_len = 400
        max_articles = min(20, self.max_content_chars // (max_abstract_len + 100))
        
        articles_text = "\n\n".join([
            f"PMID: {a.get('pmid')}\nTitle: {a.get('title', 'No title')}\nAbstract: {(a.get('abstract', 'No abstract'))[:max_abstract_len]}..."
            for a in articles[:max_articles]
        ])
        
        prompt = f"""You are a medical research assistant. Given the following context and list of PubMed articles, select the {limit} most relevant articles.

CONTEXT:
{context[:500]}

ARTICLES:
{articles_text}

Select the {limit} most relevant articles based on:
1. Direct relevance to the context
2. Clinical applicability
3. Quality indicators (study type, journal)
4. Recency

Return ONLY a JSON array of the PMIDs in order of relevance (most relevant first). Example:
["12345678", "87654321", "11111111"]"""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a medical research assistant. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )
            
            content = response.choices[0].message.content.strip()
            json_match = re.search(r'\[.*?\]', content, re.DOTALL)
            if json_match:
                pmids = json.loads(json_match.group())
            else:
                pmids = json.loads(content)
            
            valid_pmids = [str(a.get("pmid")) for a in articles]
            selected = [p for p in pmids if str(p) in valid_pmids]
            
            if len(selected) < limit:
                for a in articles:
                    if str(a.get("pmid")) not in selected:
                        selected.append(str(a.get("pmid")))
                        if len(selected) >= limit:
                            break
            
            return selected[:limit]
            
        except Exception:
            return [a.get("pmid") for a in articles[:limit]]
    
    def summarize_article(self, article: dict, patient_context: Optional[dict] = None) -> str:
        """
        Generate a clinical summary of a medical article.
        Uses chunked summarization for articles exceeding context window.
        
        Args:
            article: Article dictionary with title, abstract, and optionally full_text
            patient_context: Optional patient demographics for context
        
        Returns:
            Clinical summary string
        """
        content = article.get("full_text") or article.get("abstract", "")
        if not content:
            return "No content available for summarization."
        
        title = article.get("title", "Untitled")
        
        chunk_max_chars = self.max_content_chars - 300
        
        if len(content) <= chunk_max_chars:
            return self._summarize_single(content, title, patient_context)
        
        chunks = self._chunk_text(content, chunk_max_chars)
        
        if len(chunks) == 1:
            return self._summarize_single(chunks[0], title, patient_context)
        
        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            summary = self._summarize_chunk(chunk, i + 1, len(chunks), title)
            chunk_summaries.append(summary)
        
        return self._combine_chunk_summaries(chunk_summaries, title, patient_context)
    
    def _summarize_single(self, content: str, title: str, patient_context: Optional[dict] = None) -> str:
        """Summarize content that fits within context window"""
        context_str = ""
        if patient_context:
            age = patient_context.get("age")
            gender = patient_context.get("gender")
            if age or gender:
                context_str = f"\n\nPATIENT CONTEXT: {age or 'Unknown'} year old {gender or 'patient'}"
        
        prompt = f"""You are a medical expert. Summarize the following medical article for clinical use.

TITLE: {title}

CONTENT:
{content}
{context_str}

Provide a structured summary with the following sections (skip sections that aren't applicable):

KEY POINTS:
• Main findings (3-5 bullet points)

CLINICAL RELEVANCE:
• How this applies to clinical practice

TREATMENT/RECOMMENDATIONS:
• Key treatment recommendations or clinical guidelines

LIMITATIONS:
• Study limitations or caveats (if applicable)

Keep the summary concise but clinically useful. Use bullet points."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a medical expert providing clinical summaries. Be accurate and concise."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def generate_combined_summary(self, articles: list, context: str) -> str:
        """
        Generate a combined summary across multiple articles.
        Uses chunking if combined content exceeds context window.
        
        Args:
            articles: List of article dictionaries
            context: Clinical context or question
        
        Returns:
            Combined summary addressing the context
        """
        max_per_article = self.max_content_chars // min(len(articles), 5) - 100
        
        articles_text = "\n\n---\n\n".join([
            f"ARTICLE {i+1}:\nTitle: {a.get('title', 'Untitled')}\nAbstract: {a.get('abstract', 'No abstract')[:max_per_article]}"
            for i, a in enumerate(articles[:5])
        ])
        
        if len(articles_text) + len(context) > self.max_content_chars:
            max_per_article = max_per_article // 2
            articles_text = "\n\n---\n\n".join([
                f"ARTICLE {i+1}:\nTitle: {a.get('title', 'Untitled')}\nAbstract: {a.get('abstract', 'No abstract')[:max_per_article]}"
                for i, a in enumerate(articles[:5])
            ])
        
        prompt = f"""You are a medical expert. Given the following clinical context and related medical articles, provide a comprehensive summary addressing the clinical question.

CLINICAL CONTEXT:
{context[:500]}

ARTICLES:
{articles_text}

Provide a synthesis that:
1. Addresses the clinical context directly
2. Integrates key findings from the articles
3. Highlights consensus and any disagreements
4. Provides actionable clinical recommendations

Format with clear sections and bullet points where appropriate."""
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a medical expert providing evidence-based clinical guidance."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=self.max_tokens
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            return f"Error generating combined summary: {str(e)}"
    
    def health_check(self) -> bool:
        """Check if LLM backend is available"""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=10
            )
            return True
        except Exception:
            return False
    
    def get_config(self) -> dict:
        """Return current LLM configuration for debugging"""
        return {
            "backend": self.backend,
            "model": self.model,
            "context_window": self.context_window,
            "max_tokens": self.max_tokens,
            "max_content_chars": self.max_content_chars,
            "chunking_enabled": True
        }
